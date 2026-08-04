---
name: remote-job-watchdog
description: Watch a running job read-only and report its state, progress, and failures, using a single background monitor or scheduled check for recurring updates. Use when the user wants a job observed but not touched - "watch this run", "keep an eye on the job", "tell me when it finishes", "check if it's still going". Covers training runs, GPU and Slurm jobs, containers, and long scripts. Never restarts, resubmits, requeues, cancels, uploads, or edits the job.
user-invocable: true
---

# Remote Job Watchdog

**Purpose:** provide reliable target updates while keeping target observation
separate from monitoring-plane control.

Read `../remote-training-monitor/CONTROL_CONTRACT.md` and the matching section
of `../remote-training-monitor/ADAPTERS.md` before the first check.

## Internal functions

Watchdog contains two internal functions. They are not separate user-facing
skills because every observation iteration needs both and they share one
monitoring contract.

### Target Observer

Operate read-only on the target plane:

1. Resolve the exact target through its authoritative control plane.
2. Inspect bounded new scheduler status, logs, artifacts, progress, and health.
3. Classify job state as `RUNNING`, `FINISHED`, `FAILED`, or `STOPPED`.
4. Classify health independently as `HEALTHY`, `DEGRADED`, `STALLED`, or
   `AMBIGUOUS`.
5. Verify completion using declared checks and artifacts; a live PID, scheduler
   label, or noisy log alone is not sufficient.
6. Return evidence and the next cursor to Heartbeat Controller.

Target Observer never restarts, resumes, requeues, resubmits, uploads, edits,
installs, cleans up, creates credentials, sends external messages, or changes
the target in any other way. Diagnostics are target-read-only.

### Heartbeat Controller

Operate only on the monitoring plane:

1. Save the bounded cursor and observation record.
2. Create, update, reactivate, or pause the one harness heartbeat (Codex
   heartbeat, or Claude Code scheduled wakeup or cron routine) for the stable
   target key.
3. Report only authoritative changes and required outcome reports.
4. Never create separate phase, recovery, or sleep timers.

Heartbeat Controller may write monitoring state but may not change the target.
A non-recurring check does not create a heartbeat.

## Active cadence

For a recurring request, Heartbeat Controller:

1. Estimate the expected total and remaining job duration from authoritative
   evidence such as the scheduler time limit, elapsed time, completed work,
   throughput, phase history, or application progress. State the estimate and
   its basis; do not invent precision when evidence is weak.
2. Unless the user specifies a cadence, choose an interval from 10 to 20
   minutes:
   - 10 minutes for short jobs, imminent transitions, unstable jobs, or an
     expected remaining time of about one hour or less;
   - 15 minutes when duration or stability is uncertain;
   - 20 minutes for stable, long-running jobs whose meaningful state normally
     changes slowly.
3. Create one heartbeat automation (Codex heartbeat, or Claude Code scheduled
   wakeup or cron routine) at that cadence. Reuse and update the
   existing heartbeat for the stable target key rather than creating a
   duplicate.
4. Re-estimate after a material throughput change, recovery, or phase
   transition and update the existing heartbeat when a different interval in
   the 10-to-20-minute range is more appropriate.

Save only bounded new evidence and report progress only when authoritative
evidence changes.

## Heartbeat durability

A heartbeat is either **durable**, surviving the session that armed it, like a
cron routine or a Codex heartbeat automation; or **session-bound**, like a
background monitor that ends when its session does.

Match the mechanism to the horizon. Choose a durable heartbeat when the target
will outlive the session or the user steps away, and a session-bound monitor
when the user is present and wants events streamed live.

A session-bound heartbeat stops notifying the moment its session ends while the
target keeps running, and that silence reads exactly like a healthy job. Arming
one against a target that may outlive the session carries a disclosure: say so
in the report that announces it, and name what stops if the session closes.

Resuming a monitored target starts by re-resolving the heartbeat. A
session-bound one is gone and is re-armed against the same stable target key; a
durable one is still running and is reused. Observe the target before
reporting, because it may have reached a terminal state while unwatched, which
is an outcome report rather than a fresh observation.

## Sleep Mode

Sleep Mode is an explicit low-frequency monitoring mode for stable jobs that
should continue to be watched while the user is away.

- `sleep` uses a 60-minute heartbeat by default.
- `deep sleep` uses a 90-minute heartbeat only when the user explicitly asks
  for it and authoritative evidence indicates an exceptionally long, stable
  job.
- Sleep Mode reuses the existing Watchdog heartbeat. Never create a separate
  sleep timer.
- Before entering Sleep Mode, resolve the exact job, verify that it is healthy,
  record the current progress cursor, estimate the remaining duration, and
  preserve the existing success, failure, and stop conditions.
- Prefer at least two healthy observations after launch or recovery before
  entering Sleep Mode. If the user asks to enter immediately, disclose the
  greater detection delay.
- Sleep Mode changes observation frequency only. It never expands repair,
  phase-transition, destructive-action, credential, or external-communication
  authority.

Exit Sleep Mode and update the same heartbeat to the normal 10-to-20-minute
cadence when any of these occurs:

- the expected remaining duration falls to about one hour or less;
- the job becomes unstable, stalled, failed, or ambiguous;
- a repair, restart, resume, requeue, or resubmission occurs;
- the workflow changes phase or approaches a Phase Gate exit check; or
- the user asks to wake or resume active monitoring.

At `FINISHED`, `FAILED`, `STOPPED`, or `AWAITING_USER_APPROVAL`, follow
the shared outcome or gate contract rather than leaving a sleep heartbeat
running.

## Iteration

1. Target Observer returns state, health, evidence, and next cursor.
2. Heartbeat Controller records it and updates cadence if needed.
3. For job state `FAILED`, health `STALLED`, or actionable health `DEGRADED`:
   - with `observe_only`, preserve evidence, pause, report, and ask once
     whether to enable recovery;
   - with `auto_low_risk`, transfer the incident to **Remote Job Watch and
     Fix**, which must run the Recovery Risk Judge before acting.
4. For terminal states or a phase exit, apply the shared outcome contract.

Classify the job as `STOPPED` only when authoritative evidence shows that the
job or phase itself was intentionally stopped or cancelled without a failure.
Timeout, preemption, abnormal cancellation, or an unexpected stop are `FAILED`
unless authoritative evidence proves the job completed its declared exit
checks. A user request to stop monitoring is not a job classification:
Heartbeat Controller pauses the heartbeat and acknowledges briefly; the target
may continue running.

Use the outcome report definitions in the shared control contract.
