---
name: remote-job-watchdog
description: Observe an existing training or compute job and report progress, health, and completion. Use for one-shot job checks or read-only monitoring until a job finishes.
license: MIT
compatibility: Requires the complete four-skill Remote Training Monitor collection and an agent with filesystem and shell access.
---

# Remote Job Watchdog

**Purpose:** provide reliable target updates while keeping target observation
separate from monitoring-plane control.

For observation, read `../remote-training-monitor/CONTROL_CONTRACT.md` and
the matching section of `../remote-training-monitor/ADAPTERS.md`.
For monitor setup, use the router's `start` route and
`../remote-training-monitor/PLAN_FORMAT.md`. Read
`../remote-training-monitor/HARNESSES.md` only when managing the heartbeat.

## Internal functions

Watchdog separates target observation from monitoring control.
One-shot checks use only Target Observer and return its evidence.

### Target Observer

Operate read-only on the target plane:

1. Resolve the exact target through its authoritative control plane.
2. Inspect bounded new scheduler status, logs, artifacts, progress, and health
   from the cursor forward.
3. Classify job state as `RUNNING`, `FINISHED`, `FAILED`, or `STOPPED`.
4. Classify health independently as `HEALTHY`, `DEGRADED`, `STALLED`, or
   `AMBIGUOUS`.
5. Verify completion using the phase's declared exit checks and artifacts; a
   live PID, scheduler label, or noisy log alone is not sufficient.
6. Return evidence and the next cursor to Heartbeat Controller.

Target Observer never restarts, resumes, requeues, resubmits, uploads, edits,
installs, cleans up, creates credentials, sends external messages, or changes
the target in any other way. Diagnostics are target-read-only.

### Heartbeat Controller

Operate only on the monitoring plane:

1. Write the cursor and observation fields to `state.json`; append material
   changes to the plan's History.
2. Create, update, reactivate, or pause the one heartbeat for the Target Key,
   using the available background or scheduling mechanism. Record its identity
   in `state.json` and reuse a recorded identity instead of creating another.
3. Report only authoritative changes and required outcome reports.
4. Set the controller state before pausing, so a wake that still fires is a
   no-op wake.

A one-shot check writes no plan or state file and creates no heartbeat.
It returns the observation directly; it does not call Heartbeat Controller.

## Wake Mode

A monitor wakes the agent in one of two ways. On `start`, Heartbeat Controller
chooses one and records it in the Monitoring Contract:

- `COMPLETION` (default): one background waiter polls the control plane in
  shell and wakes the agent once, when the current attempt leaves its running
  states. No Observation happens while the job runs, so a long job costs no
  agent turns. Use it whenever the harness re-invokes the agent when a
  background command exits, as Claude Code does. The waiter is defined in
  `../remote-training-monitor/HARNESSES.md`.
- `INTERVAL`: a timer wakes the agent at a Cadence Mode. Use it only when the
  harness has no completion wake, or when the user asks for periodic check-ins.

In both modes, estimate expected total and remaining duration from
authoritative evidence: scheduler time limit, elapsed time, completed work,
throughput, phase history, or application progress. State the estimate and its
basis in the Monitoring Contract; state weak evidence as weak. `COMPLETION`
sets the waiter's deadline from it; `INTERVAL` chooses the Cadence Mode from it.

`COMPLETION` wakes the agent as soon as a failure ends the job. A job that
hangs without exiting is noticed only through a stall rule in the waiter or at
the deadline. Say this when arming the waiter.

### Cadence Mode (`INTERVAL` only)

1. Choose the mode, unless the user names one:
   - `ACTIVE` (10 min) when about an hour or less remains, the job is
     unstable or newly launched or recovered, or a phase boundary is near;
   - `RELAXED` (30 min) for everything else;
   - `SLEEP` (60 min) only when the user asks for it.
2. On `start`, establish one heartbeat at that interval using the harness guide.
   During `iterate`, update only an existing heartbeat; never create one.
3. Re-estimate after a material throughput change, recovery, or phase
   transition and update the same heartbeat when the mode changes.

## Heartbeat durability

A heartbeat is **durable** when its documented behavior survives the session
that armed it, or **session-bound** when it ends with that session. Verify
capabilities and resume behavior using `../remote-training-monitor/HARNESSES.md`.

Match the mechanism to the horizon: durable when the target will outlive the
session or the user steps away, session-bound when the user is present and
wants events streamed live. A session-bound heartbeat's silence after the
session closes reads exactly like a healthy job, so the report that arms one
says what stops when the session ends. A completion waiter is session-bound.

Explicit `start` resolves the recorded heartbeat and observes the current
attempt before resuming. Do not assume a durable timer is still active, or
that a session timer or waiter has expired, without checking.

## Sleep (`INTERVAL` only)

`SLEEP` is an explicit low-frequency mode for stable jobs watched while the
user is away. It reuses the existing heartbeat and changes only its interval.

Before entering: resolve the exact job, verify it is healthy, write the cursor,
record the remaining-duration estimate, and keep the existing success, failure,
and stop conditions. Prefer at least two healthy Observations after launch or
recovery; on an immediate request, disclose the greater detection delay.

Return to `ACTIVE` on the same heartbeat when any of these occurs:

- the expected remaining duration falls to about one hour or less;
- the job becomes unstable, stalled, failed, or ambiguous;
- a repair, restart, resume, requeue, or resubmission occurs;
- the workflow changes phase or approaches a Phase Gate exit check; or
- the user asks to wake.

At `FINISHED`, `FAILED`, `STOPPED`, or `AWAITING_USER_APPROVAL`, follow the
shared outcome or gate contract rather than leaving a sleep heartbeat running.

## Iteration

Every wake runs `iterate <target-key>`:

1. Read `state.json`. A controller state of `PAUSED` or
   `AWAITING_USER_APPROVAL` is a no-op wake: one line, no Observation.
2. Read this target's `plan.md` from the same state directory on every active
   wake. Verify both files' Target Keys match the requested key and their
   Plan Revisions match. Load the current phase's observation commands, exit
   checks, expected artifacts, recovery policy and limits, and applicable
   approvals. If required context is missing or inconsistent, report the
   affected path and issue, then end the iteration before observation or
   target action. Saved conversation context does not replace this read.
3. Target Observer returns state, health, evidence, and next cursor.
4. Heartbeat Controller records it. Under `INTERVAL`, it updates the Cadence
   Mode if needed. Under `COMPLETION`, a waiter's exit is only the prompt to
   observe, never evidence of completion. If the job is still `RUNNING` and
   healthy after its waiter exited, arm one new waiter with a fresh deadline
   and record it in place of the spent one. A wake that arrives while the
   recorded waiter is still alive, such as an `iterate` the user asked for,
   arms nothing.
5. For job state `FAILED`, health `STALLED`, or actionable health `DEGRADED`:
   - with `observe_only`, preserve evidence, pause, report, and ask once
     whether to enable recovery;
   - with `auto_low_risk`, transfer the incident to **Remote Job Watch and
     Fix**, which runs the Recovery Risk Judge before acting.
6. For terminal states or a phase exit, apply the shared outcome contract.

Classify the job as `STOPPED` only when authoritative evidence shows that the
job or phase itself was intentionally stopped or cancelled without a failure.
Timeout, preemption, abnormal cancellation, or an unexpected stop are `FAILED`
unless authoritative evidence proves the job completed its declared exit
checks. A user request to stop monitoring is not a job classification:
Heartbeat Controller pauses the heartbeat and acknowledges briefly; the target
may continue running.
