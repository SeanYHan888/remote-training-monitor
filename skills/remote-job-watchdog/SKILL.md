---
name: remote-job-watchdog
description: Observe an existing training or compute job and report progress, health, and completion. Use for one-shot job checks or read-only monitoring until a job finishes.
license: MIT
compatibility: Requires the complete four-skill Remote Training Monitor collection and an agent with filesystem and shell access.
---

# Remote Job Watchdog

**Purpose:** provide reliable target updates while keeping target observation
separate from monitoring-plane control.

For observation, read the matching control-plane section and "Training
signals" in `../remote-training-monitor/ADAPTERS.md`, and the project's
`.remote-monitor/adapter.md` when it exists. For the state vocabulary read
`../remote-training-monitor/CONTROL_CONTRACT.md`; for the report shape
`../remote-training-monitor/REPORT_FORMAT.md`. For monitor setup use the
router's `start` route and `../remote-training-monitor/PLAN_FORMAT.md`. Read
`../remote-training-monitor/HARNESSES.md` only when managing the heartbeat.

## Internal functions

Watchdog separates target observation from monitoring control.
One-shot checks use only Target Observer and return its report.

### Target Observer

Operate read-only on the target plane:

1. Resolve the exact target through its authoritative control plane.
2. Inspect bounded new scheduler status, logs, artifacts and the Training
   signals from the cursor forward.
3. Classify the run state: `QUEUED`, `RUNNING`, or a terminal candidate
   (`PASSED`, `FAILED`, `CANCELLED`) once the attempt has left its running
   states.
4. While `RUNNING`, compute health from the signals: `FINE`, `SLOW`,
   `STALLED` or `UNKNOWN`, with the deciding signal and its value.
5. A terminal candidate becomes `PASSED` only when every exit check of the
   phase passes; a live PID, scheduler label or noisy log alone is not
   sufficient. Record each check's result.
6. Return the run state, health, progress numbers, check results, evidence
   and the next cursor to Heartbeat Controller.

Target Observer never restarts, resumes, requeues, resubmits, uploads, edits,
installs, cleans up, creates credentials, sends external messages or changes
the target in any other way. Diagnostics are target-read-only.

### Heartbeat Controller

Operate only on the monitoring plane:

1. Write `run_state`, `since` (when the state changed), `health`, `progress`,
   `checks`, `next_action`, the cursor and `last_observed` to `state.json`;
   validate it with `scripts/validate_state.py` before saving. Append one
   History line in the report's History-line shape.
2. Create, update, reactivate or pause the one heartbeat for the Target Key,
   using the available background or scheduling mechanism. Record its id in
   `state.json` and reuse a recorded id instead of creating another. Under
   `COMPLETION` every key the session watches shares one waiter, recorded
   with `covers` (`../remote-training-monitor/HARNESSES.md`, "Several runs,
   one waiter").
3. Report in the eight-line shape, worded per its Wording rules. Report
   every wake that changes the run
   state, health or checks, every start, and every required action; a wake
   that changes nothing under `INTERVAL` is one line unless periodic reports
   were requested.
4. Set the monitor field before pausing, so a wake that still fires is a
   no-op wake.

A one-shot check writes no plan or state file and creates no heartbeat.
It returns the report directly; it does not call Heartbeat Controller.

## Wake Mode

A monitor wakes the agent in one of two ways. On `start`, Heartbeat Controller
chooses one and records it in the Monitoring Contract and the heartbeat:

- `COMPLETION` (default): one background waiter polls the control plane in
  shell and wakes the agent when there is something to verify. It has two
  stages (`HARNESSES.md`): the queue stage exits when the job starts, the run
  stage when the attempt leaves its running states, a stall rule fires, or the
  deadline passes. A long job costs two or three agent turns. One waiter
  covers every run the session watches; for Slurm it is the bundled
  `scripts/slurm_waiter.py`. Use it whenever
  the harness re-invokes the agent when a background command exits, as Claude
  Code does.
- `INTERVAL`: a timer wakes the agent at a Cadence. Use it only when the
  harness has no completion wake, or when the user asks for periodic check-ins.

In both modes, estimate expected total and remaining duration from
authoritative evidence: scheduler time limit, elapsed time, completed work,
throughput, phase history or application progress. State the estimate and its
basis in the Monitoring Contract and on the PROGRESS line; state weak evidence
as weak. `COMPLETION` sets the run-stage deadline from the time limit;
`INTERVAL` chooses the Cadence from the estimate.

### Cadence (`INTERVAL` only)

1. Choose the cadence, unless the user names one:
   - `ACTIVE` (10 min) when about an hour or less remains, the job is
     unstable or newly launched or recovered, or a phase boundary is near;
   - `RELAXED` (30 min) for everything else;
   - `SLEEP` (60 min) only when the user asks for it.
2. On `start`, establish one heartbeat at that interval using the harness guide.
   During `iterate`, update only an existing heartbeat; never create one.
3. Re-estimate after a material throughput change, recovery or phase
   transition and update the same heartbeat when the cadence changes.

`SLEEP` is for a stable job watched while the user is away. Before entering
it, verify health `FINE` on at least two Observations after launch or
recovery, or disclose the greater detection delay on an immediate request.
Return to `ACTIVE` on the same heartbeat when about an hour or less remains,
health leaves `FINE`, a repair or new attempt happens, a phase boundary
approaches, or the user asks to wake. Cadence changes nothing but the
interval.

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

## Iteration

Every wake runs `iterate <target-key>`:

1. Read and validate `state.json` (`scripts/validate_state.py`). A rejected
   file is reported with its first problems; the iteration ends. A monitor of
   `WAITING` or `OFF` is a no-op wake: one line, no Observation.
2. Read this target's `plan.md` from the same state directory on every active
   wake. Verify both files' Target Keys match the requested key and their
   Plan Revisions match. Load the current phase's observation commands, exit
   checks, expected artifacts, signal thresholds, recovery policy and limits,
   and applicable approvals. If required context is missing or inconsistent,
   report the affected path and issue, then end the iteration before
   observation or target action. Saved conversation context does not replace
   this read.
3. Target Observer returns run state, health, progress, checks, evidence and
   the next cursor.
4. Heartbeat Controller records it. Under `INTERVAL`, it updates the Cadence
   if needed. Under `COMPLETION`, a waiter's exit is only the prompt to
   observe, never evidence of completion:
   - queue stage exited and the job is `RUNNING`: this is the early health
     check; arm the run stage with a deadline from the start time;
   - run stage exited on a terminal state: run the exit checks, classify, no
     replacement;
   - run stage exited on its stall rule: classify from the full Training
     signals; `STALLED` follows step 5; a false alarm re-arms one run-stage
     waiter and tightens or removes the rule in the Monitoring Contract;
   - run stage exited at its deadline with the job still `RUNNING` and
     `FINE`: arm one replacement run-stage waiter with a fresh deadline and
     record it in place of the spent one;
   - a wake that arrives while the recorded waiter is still alive, such as an
     `iterate` the user asked for, arms nothing;
   - a shared waiter exited: run this Iteration for each key the exit names,
     then arm one replacement over every covered key still `WATCHING`, each in
     its current stage, recorded in each of their state files.
5. For `FAILED`, or health `STALLED`, or `SLOW` with an action the plan
   names:
   - with `observe_only`, preserve evidence, set the monitor
     `OFF (needs-decision)`, report, and ask once whether to enable recovery;
   - with `auto_low_risk`, set the monitor `RECOVERING` and transfer the
     incident to **Remote Job Watch and Fix**, which runs the Recovery Risk
     Judge before acting.
6. For terminal states or a phase exit, apply the contract's Reports section.

Classify `CANCELLED` only when authoritative evidence shows the job or phase
was intentionally stopped at the user's request without a failure. Timeout,
preemption, abnormal cancellation or an unexpected stop are `FAILED` unless
authoritative evidence proves the job passed its exit checks. A user request
to stop monitoring is not a run classification: Heartbeat Controller sets the
monitor `OFF (stopped)` and acknowledges in one line; the target may continue.
