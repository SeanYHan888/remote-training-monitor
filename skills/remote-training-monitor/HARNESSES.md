# Harness capabilities

Read this file when creating, changing or resuming a monitor's heartbeat.
Inspect the callable background and scheduling tools and their documented
persistence, execution directory, interval limits and pause/update operations.
Detection is read-only: never create a timer or waiter as a capability probe.
An unknown runtime uses only capabilities it actually exposes.

## Selection

Prefer a completion wake. It spends no agent turns while the job runs and
wakes the agent when there is something to verify. Use an interval timer only
when the runtime cannot re-invoke the agent on a background command's exit, or
when the user asks for periodic check-ins.

For an interval timer, prefer a verified durable mechanism when the job will
outlive the session. Use a session-bound mechanism when that is what the
runtime supplies, clearly stating when monitoring ends. A tool named cron or
background does not by itself establish durability. If persistence is unknown,
report it as unknown.

| Runtime | Heartbeat guidance |
| --- | --- |
| Claude Code | Completion wake. Run the waiter as one background shell command (background Bash, or the Monitor tool); the session is re-invoked when it exits. Arm no scheduled wakeup, cron or loop beside it. The waiter is session-bound. For a requested `INTERVAL`, inspect the exposed scheduling tool's lifetime and limits, use durable routines only if explicitly supported, and treat session-only cron/wakeups as session-bound. |
| Codex desktop | No completion wake. Use the current task's heartbeat at Watchdog's Cadence by default. Use a standalone scheduled task only when explicitly requested. Inspect the automation tool for supported creation, update and pause fields. |
| CLI, IDE or other runtime | Completion wake when the runtime re-invokes the agent on a background command's exit. Otherwise use an available scheduler or bounded session wait. Without a durable mechanism, explain the limitation and provide an operator-managed scheduling option if needed. |

## Completion wake

The waiter is one background shell command. It polls the control plane without
involving the agent and exits when the agent has something to verify. It is
read-only toward the target. A job's life has two waits with different
shapes, so the waiter has two stages; each exit is one agent wake.

### Queue stage (run state `QUEUED`)

Queue wait is unbounded and unknown in advance, so this stage has no deadline
derived from the job. It exits when the job **starts** (so the agent can do an
early health check and arm the run stage) or when it leaves the queue without
running (cancelled, failed at launch). A backstop of 24 hours, or the plan's
own figure, is the only time limit, and its exit says so.

- **Exit on a state it actually read.** A failed or empty lookup (dropped SSH,
  scheduler timeout, accounting lag) means keep waiting.
- **Poll every 2–5 minutes.** The queue changes slowly and the control plane is
  shared.
- **Output.** Print the exit reason, the state read, and the queue reason and
  start estimate at the last poll, so the wake report's STATE line has them.

Slurm over SSH, with `<host>`, `<job_id>` and the backstop seconds filled in:

```bash
backstop=$(( $(date +%s) + <seconds> ))
while [ "$(date +%s)" -lt "$backstop" ]; do
  line=$(ssh -n -o BatchMode=yes -o ConnectTimeout=20 <host> "squeue -j <job_id> -h -o '%T|%r|%S'" 2>/dev/null)
  state=${line%%|*}
  case "$state" in
    ""|PENDING|REQUEUED|CONFIGURING) sleep 180 ;;
    RUNNING|COMPLETING|COMPLETED|FAILED|CANCELLED*|TIMEOUT|PREEMPTED|NODE_FAIL|OUT_OF_MEMORY)
      echo "left queue: $line"; exit 0 ;;
    *) sleep 180 ;;
  esac
done
echo "queue backstop reached; last read: ${line:-none}"; exit 4
```

### Run stage (run state `RUNNING`)

Armed after the early health check. It exits when the current attempt leaves
its running states, when a stall rule fires, or at a deadline that starts
counting from the job's **start time**, never from submission.

- **Exit on a state it actually read.** The waiter exits when the control plane
  reports the exact current attempt outside its running states. A failed or
  empty lookup means keep waiting, not finished.
- **Deadline.** The job's time limit plus a margin (10 min, or the plan's
  figure), measured from the start time the scheduler reports. Without a time
  limit, twice the remaining-duration estimate. Record it in the plan and on
  the MONITOR line as the backstop.
- **Phase exit.** When the current phase ends without its job terminating, add
  the appearance of that phase's exit artifact as an exit condition.
- **Stall rule.** When the plan declares stall evidence that shell can test
  (the Training signals' Stage or Log age: a status file or log unmodified for
  N minutes while the job runs), the waiter exits on it with its own exit
  code, so a hang is noticed in N minutes instead of at the deadline. Put the
  rule in the waiter whenever the plan has one. Without one, say that a hang is
  noticed only at the deadline.
- **Poll interval.** One to five minutes.
- **Output.** Print the exit reason and the last state read. Distinct exit
  codes: 0 terminal state read, 3 deadline, 5 stall rule.

Slurm over SSH, with `<host>`, `<job_id>`, `<deadline_epoch>` (start time plus
limit plus margin), `<status_file>` and `<stall_seconds>` filled in from the
plan:

```bash
while [ "$(date +%s)" -lt <deadline_epoch> ]; do
  state=$(ssh -n -o BatchMode=yes -o ConnectTimeout=20 <host> "sacct -j <job_id> -X -n -o State" 2>/dev/null | awk 'NR==1 {print $1}')
  case "$state" in
    ""|PENDING|RUNNING|REQUEUED|RESIZING|SUSPENDED|COMPLETING)
      age=$(ssh -n -o BatchMode=yes -o ConnectTimeout=20 <host> "echo \$(( \$(date +%s) - \$(stat -c %Y <status_file> 2>/dev/null || date +%s) ))" 2>/dev/null)
      if [ -n "$age" ] && [ "$age" -gt <stall_seconds> ]; then
        echo "stall rule: <status_file> unchanged for ${age}s while $state"; exit 5
      fi
      sleep 120 ;;
    *) echo "left running states: $state"; exit 0 ;;
  esac
done
echo "deadline reached; last state read: ${state:-none}"; exit 3
```

Other control planes follow the same two shapes, using the lifecycle command
from their section of `ADAPTERS.md`.

When either stage exits, run `iterate <target-key>`. The exit is the prompt to
observe: completion is established only by the plan's exit checks, a start is
established by the Observation, and a stall exit is checked against the full
Training signals before health is `STALLED`. Watchdog's Iteration says when to
arm the next stage or a replacement.

A waiter dies with its session while the job continues. When arming one, tell
the user that closing the session ends the watch, and that `start` in a new
session observes first and then arms a new waiter if the job is still queued
or running.

## Establish or resume

After the Run Plan and its approval rule are satisfied:

1. Resolve the recorded heartbeat ID against the scheduler or background task
   list before creating anything. Reuse an existing matching heartbeat. If
   lookup is unavailable or ambiguous, report that uncertainty rather than
   create a potential duplicate.
2. On every explicit `start`, observe the current target, including when the
   recorded timer or waiter is already active, before reactivating a paused
   monitor or replacing a confirmed-expired session timer or waiter. Terminal
   outcomes and approval gates take precedence over reactivation.
3. Arm the heartbeat. Under `COMPLETION`, start the stage matching the run
   state: queue stage for `QUEUED`, run stage for `RUNNING`. Under `INTERVAL`,
   schedule `$remote-training-monitor iterate <target-key>` at Watchdog's
   selected cadence, preserving any required invocation namespace. Verify the
   execution directory can read the existing plan and state; a worktree is
   acceptable only when it can access that same state, not a divergent copy.
4. Verify and record the returned ID, wake mode, deadline or interval,
   lifetime and execution directory in `state.json`; set the monitor to
   `WATCHING`. Report success only after confirmation, in the
   `REPORT_FORMAT.md` shape. Keep unchanged observations quiet unless periodic
   reports were requested; report material changes, completion, failure, a
   start, or required action.

For updates or pauses, use the scheduler's supported operations on that ID;
pause a live waiter by stopping its background command. Set the monitor field
before pausing. If the operation fails, preserve its ID and disclose the
failure; subsequent wakes must honor the no-op-wake guard. An `iterate` never
creates or replaces a timer, and arms a waiter only to replace one that has
already exited or to move from the queue stage to the run stage.

## Session-only interval fallback

Use the runtime's wait mechanism with its actual per-call limit. Bound the
total polling horizon in the plan and report that monitoring ends with the
session or that horizon. Do not claim monitoring is active after polling ends.

If the user needs operator-managed cron, supply a command with absolute
executable and project paths, safely quoted arguments and the required
environment. Validate the cadence expression: hourly is `0 * * * *`, not
`*/60 * * * *`. Explain that the operator installs it and that scheduler
availability and agent credentials must persist outside the interactive shell.
