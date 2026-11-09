# Remote Training Control Contract

The shared vocabulary and authority rules for every monitor. `REPORT_FORMAT.md`
says how an observation is reported, `PLAN_FORMAT.md` where plan and state
live, `HARNESSES.md` how the heartbeat is armed.

A **heartbeat** is the single wake mechanism for one Target Key: a completion
waiter or an interval timer. Every wake runs `iterate <target-key>` and reads
`state.json` before observing.

## State vocabulary

Three fields describe a monitored run. A report shows exactly these three;
`state.json` stores them in the shape of `state.schema.json`, and
`scripts/validate_state.py` refuses any other value.

### Run state

One lifecycle from plan to outcome:

| Run state | Meaning | Set by |
| --- | --- | --- |
| `PLANNED` | Run Plan written; the launch is not yet approved, or nothing is submitted | `plan` |
| `APPROVED` | the launch is approved and may be submitted | `approve`, or `start` with an approval already supplied |
| `QUEUED` | submitted and held by the control plane, not running (Slurm PENDING, Kubernetes Pending) | Observation |
| `RUNNING` | the control plane reports the current attempt running | Observation |
| `PASSED` | the attempt left its running states and every exit check of the phase passed | Observation plus exit checks |
| `FAILED` | terminal without passing: non-zero exit, timeout, preemption, OOM, a failed exit check, an unexpected stop | Observation |
| `CANCELLED` | the user asked for this stop and authoritative evidence shows it (`scancel` by the owner) | Observation |

A scheduler COMPLETED is `RUNNING` until the exit checks run, then `PASSED` or
`FAILED`. An unexpected cancellation, timeout or preemption is `FAILED`;
`CANCELLED` needs the user's request behind it. A job already running when the
monitor starts enters at `QUEUED` or `RUNNING`. In a multi-phase run each phase
passes the same way; the run as a whole is `PASSED` only after the final phase.

### Health

Only while `RUNNING`; `null` otherwise. Computed from the Training signals in
`ADAPTERS.md`, never from a feeling about the logs:

- `FINE`: every measured signal inside its fine band.
- `SLOW`: a signal in its slow band (throughput down, a checkpoint missed).
- `STALLED`: a signal past its stalled threshold (stage unchanged, no new
  step, log silent) while the control plane still says running.
- `UNKNOWN`: the signals could not be read (dropped SSH, missing files). Say
  which.

### Monitor

What the monitor itself is doing:

- `WATCHING`: a heartbeat is armed. The MONITOR line shows its mode:
  `wakes on exit, backstop <time>` or `every <n> min`.
- `RECOVERING`: Watch and Fix holds the current attempt.
- `WAITING`: waiting on the user. The heartbeat is paused; `reason` names the
  decision (a phase approval, a recovery decision, a high-risk repair).
- `OFF`: no heartbeat. `reason` is `draft`, `terminal`, `stopped` (the user
  stopped monitoring) or `needs-decision` (a failure under `observe_only`).

Wake Mode (`COMPLETION` or `INTERVAL`) and Cadence (`ACTIVE` 10 min,
`RELAXED` 30 min, `SLEEP` 60 min) are properties of the heartbeat, recorded
inside it. `sleep <key>` and `wake <key>` change the cadence and nothing else.

A wake that finds the monitor `WAITING` or `OFF` is a no-op wake: one line, no
Observation.

### Files written before this vocabulary

Read `FINISHED` as `PASSED`, `STOPPED` as `CANCELLED`; controller `ACTIVE` and
`SLEEP` as `WATCHING`, `AWAITING_USER_APPROVAL` as `WAITING`, `PAUSED` as
`OFF`; health `HEALTHY` as `FINE`, `DEGRADED` as `SLOW`, `AMBIGUOUS` as
`UNKNOWN`. Rewrite the file in the new shape on the next write.

## Run Plan

Every monitor has a Run Plan at `.remote-monitor/<target-key>/plan.md` with
its `state.json`, formatted as in `PLAN_FORMAT.md`. The Monitoring Contract
section records:

- stable Target Key, exact job or run identities, working directory, owner;
- authoritative control plane, observation adapter and the project adapter
  file when one exists;
- current phase, declared entry condition, exit checks, expected artifacts;
- success, failure and intentional-stop evidence;
- Wake Mode with its deadline or Cadence, heartbeat durability, the single
  heartbeat identity;
- recovery policy: `observe_only` or `auto_low_risk`;
- retry budget, rollback point requirements, verification checks;
- approval source, approval holder and the approval-gated transitions;
- resource, cost, storage, publication and destructive-action limits.

The Target Key is stable for the workflow. Attempts have separate identities
and preserved evidence (`PLAN_FORMAT.md`). Resolve the current attempt
explicitly; similarity of job names never establishes identity.

## Authority planes

| Policy | Target observation | Monitoring control | Target recovery | Phase launch |
| --- | --- | --- | --- | --- |
| Watchdog | Read | Create/update/pause one heartbeat; write state | None | None |
| Phase Gate | Read | Reuse Watchdog heartbeat | None by itself | Exact named phase, once, after matching approval |
| Watch and Fix | Read | Reuse Watchdog heartbeat | Low-risk actions inside `auto_low_risk` policy | None |

`Read-only` means read-only toward the monitored target. Watchdog may change
only its monitoring-plane state: the heartbeat, the state file, plan Approvals
and History, and reports. It may not change the training job, remote
scheduler, environment, code, configuration, artifacts, credentials or
external destinations.

When Phase Gate and Watch and Fix compose, low-risk recovery operates only
inside the current approved phase. It never grants the next-phase launch.

## Policy transitions

- Watchdog transfers a `FAILED` or `STALLED` target to Watch and Fix
  automatically only when the plan already says `auto_low_risk`; the monitor
  becomes `RECOVERING`.
- Without that authorization, Watchdog preserves evidence, sets the monitor
  `OFF (needs-decision)` and asks once whether to enable recovery.
- Watch and Fix returns a recovered multi-phase job to Phase Gate before any
  later phase.
- Phase Gate may launch the exact approved next phase once, record the new
  target identities in History, and reactivate the same heartbeat.
- The user may switch between `observe_only` and `auto_low_risk`, or change
  the Wake Mode or Cadence, at any point. Preserve the Target Key and cursor
  and keep one heartbeat; a recovery-policy change bumps the Plan Revision.

## Heartbeat lifecycle

One Watchdog-owned heartbeat per Target Key. Under `COMPLETION`, the keys one
session watches share one waiter, recorded as each key's heartbeat with
`covers` (`HARNESSES.md`, "Several runs, one waiter"):

1. Create it only for a monitoring request, never for a one-shot check, after
   the Run Plan is written and the approval rule is satisfied.
2. Record its identity in `state.json`: the id alone, at most 64 characters.
   What replaced what, and why, is a History line. `start` reuses a recorded
   identity rather than creating a second heartbeat.
3. Reuse and update it when cadence, phase or recovery state changes. Phase
   Gate, recovery and sleep share it. A completion waiter watches one attempt
   and fires once: a new attempt, a new phase, a job that started while the
   queue waiter watched, or a job still running after its waiter exited gets
   one replacement waiter, recorded as the same heartbeat. Never run two
   waiters for one Target Key, or two waiters in one session.
4. Pause it for `PASSED`, `CANCELLED`, `WAITING`, a user request to stop
   monitoring, or a `FAILED` state not transferred to an authorized recovery
   loop. Set the monitor field first, so a wake that still fires is a no-op
   wake. A waiter that has already exited needs no pause; a live one is
   stopped.
5. Reactivate it only when the same Run Plan resumes or an approved next phase
   receives new exact identities.

## Reports

Every wake, terminal classification, gate and recovery outcome produces one
report in the shape of `REPORT_FORMAT.md`, appends one History line, and
pauses or explicitly transfers the heartbeat. A report names the state
directory as preserved evidence.

- `PASSED`: every exit check with its value, artifact identities, elapsed
  duration, next action.
- `FAILED`: first relevant failure evidence, last known good progress, likely
  cause with confidence, affected artifacts, recovery eligibility, exact next
  action.
- `CANCELLED`: who or what stopped the job, preserved work, latest safe
  resume point, exact next action.
- A non-final phase that passes reports `PHASE n PASSED`, carries the Gate
  Packet below the rule, and sets the monitor `WAITING`.
- The final phase verifies every required phase outcome and artifact, reports
  the run `PASSED`, and sets the monitor `OFF (terminal)`. No next-phase gate.

A user request to **stop monitoring** sets the monitor `OFF (stopped)` and
gets a one-line acknowledgement, not a report. The job may continue.

Keep evidence bounded: name or link logs, manifests, revisions and scheduler
identities instead of pasting them.
