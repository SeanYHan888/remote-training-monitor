# Harness capabilities

Read this file when creating, changing, or resuming a monitor's heartbeat.
Inspect the callable background and scheduling tools and their documented
persistence, execution directory, interval limits, and pause/update operations.
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
| Claude Code | Completion wake. Run the waiter as one background shell command (background Bash, or the Monitor tool); the session is re-invoked when it exits. Arm no scheduled wakeup, cron, or loop beside it. The waiter is session-bound. For a requested `INTERVAL`, inspect the exposed scheduling tool's lifetime and limits, use durable routines only if explicitly supported, and treat session-only cron/wakeups as session-bound. |
| Codex desktop | No completion wake. Use the current task's heartbeat at Watchdog's Cadence Mode by default. Use a standalone scheduled task only when explicitly requested. Inspect the automation tool for supported creation, update, and pause fields. |
| CLI, IDE, or other runtime | Completion wake when the runtime re-invokes the agent on a background command's exit. Otherwise use an available scheduler or bounded session wait. Without a durable mechanism, explain the limitation and provide an operator-managed scheduling option if needed. |

## Completion wake

The waiter is one background shell command. It polls the control plane without
involving the agent and exits when the agent has something to verify. It is
read-only toward the target.

- **Exit on a state it actually read.** The waiter exits when the control plane
  reports the exact current attempt outside its pending and running states. A
  failed or empty lookup (dropped SSH, scheduler timeout, accounting lag) means
  keep waiting, not finished.
- **Deadline.** The waiter also exits at a deadline and says so. Use the end of
  the scheduler's time limit plus queue wait and a margin when there is one;
  otherwise twice the remaining-duration estimate. Record it in the plan.
- **Phase exit.** When the current phase ends without its job terminating, add
  the appearance of that phase's exit artifact as an exit condition.
- **Stall rule, optional.** When the plan declares stall evidence that shell
  can test, such as a log or progress file unmodified for N minutes while the
  job runs, the waiter may exit on it. Without one, a hang is noticed only at
  the deadline.
- **Poll interval.** One to five minutes. Polling is cheap, but the control
  plane is shared.
- **Output.** Print the exit reason and the last state read. Use a distinct
  exit code for the deadline.

Slurm over SSH, with `<host>`, `<job_id>`, and the seconds until the deadline
filled in from the plan:

```bash
deadline=$(( $(date +%s) + <seconds> ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  state=$(ssh -n -o BatchMode=yes -o ConnectTimeout=20 <host> "sacct -j <job_id> -X -n -o State" 2>/dev/null | awk 'NR==1 {print $1}')
  case "$state" in
    ""|PENDING|RUNNING|REQUEUED|RESIZING|SUSPENDED|COMPLETING) sleep 120 ;;
    *) echo "left running states: $state"; exit 0 ;;
  esac
done
echo "deadline reached; last state read: ${state:-none}"; exit 3
```

Other control planes follow the same shape, using the lifecycle command from
their section of `ADAPTERS.md`.

When the waiter exits, run `iterate <target-key>`. The exit is the prompt to
observe: completion is established only by the plan's exit checks. Watchdog's
Iteration says when to arm a replacement waiter.

A waiter dies with its session while the job continues. When arming one, tell
the user that closing the session ends the watch, and that `start` in a new
session observes first and then arms a new waiter if the job is still running.

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
3. Arm the heartbeat. Under `COMPLETION`, start one waiter for the current
   attempt. Under `INTERVAL`, schedule
   `$remote-training-monitor iterate <target-key>` at Watchdog's selected
   cadence, preserving any required invocation namespace. Verify the
   execution directory can read the existing plan and state; a worktree is
   acceptable only when it can access that same state, not a divergent copy.
4. Verify and record the returned ID, wake mode, deadline or interval,
   lifetime, and execution directory in `state.json`. Report success only
   after confirmation. Keep unchanged/non-actionable observations quiet unless
   periodic reports were requested; notify on material changes, completion,
   failure, or required action.

For updates or pauses, use the scheduler's supported operations on that ID;
pause a live waiter by stopping its background command. Set controller state
before pausing. If the operation fails, preserve its ID and disclose the
failure; subsequent wakes must honor the paused-state guard. An `iterate`
never creates or replaces a timer, and arms a waiter only to replace one that
has already exited.

## Session-only interval fallback

Use the runtime's wait mechanism with its actual per-call limit. Bound the
total polling horizon in the plan and report that monitoring ends with the
session or that horizon. Do not claim monitoring is active after polling ends.

If the user needs operator-managed cron, supply a command with absolute
executable and project paths, safely quoted arguments, and the required
environment. Validate the cadence expression: hourly is `0 * * * *`, not
`*/60 * * * *`. Explain that the operator installs it and that scheduler
availability and agent credentials must persist outside the interactive shell.
