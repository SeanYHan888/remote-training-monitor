---
name: remote-training-monitor
description: Check on, watch, or monitor a job and report its state, progress, and failures - training runs, GPU jobs, Slurm/Kubernetes/Docker/systemd workloads, or any long-running script. TRIGGER when the user says "check the training", "check progress", "how's the run going", "is the job still running", "is it stuck", "did it finish", "watch this job", "monitor job 12345", "tell me when it's done", "what happened to my run", or names a job id, run id, or cluster job to look at. Also trigger when a multi-phase pipeline must stop for approval between phases, or when the user authorizes automatic recovery of routine failures ("watch and fix", "keep it running"). Read-only toward the job by default - it observes and reports, and never restarts, resubmits, cancels, or edits anything unless recovery is explicitly authorized.
user-invocable: true
---

# Remote Training Monitor

Use this as the main entry point for training jobs and pipelines. Resolve the
requested authority, then load the shared contract and only the specialized
skills needed for the request:

1. Read `CONTROL_CONTRACT.md`.
2. Read the matching section of `ADAPTERS.md`.
3. Use **Remote Job Watchdog** for observation and heartbeat control.
4. Add **Remote Job Phase Gate** when named phases require approval.
5. Add **Remote Job Watch and Fix** when the user authorizes autonomous
   low-risk recovery; read `RISK_POLICY.md` before any repair.

## Intent detection

| User intent | Policy to activate |
| --- | --- |
| "Watch", "monitor", "check progress", or "tell me when it finishes" | Watchdog with `observe_only` recovery |
| A multi-phase plan that must stop for approval | Add Phase Gate |
| "Watch and fix", "keep it running", "handle routine failures", or equivalent | Add Watch and Fix with `auto_low_risk` recovery |
| "Sleep" or "monitor while I am away" | Change Watchdog cadence only |

Policies compose. A multi-phase training plan may use Watchdog, Phase Gate,
and Watch and Fix together. Sleep Mode changes cadence, not authority.

When recovery intent is ambiguous, use `observe_only`. Do not silently acquire
repair authority. Once `auto_low_risk` is authorized for the monitoring
contract, Watch and Fix may diagnose, repair, and redo low-risk failed steps
without asking about each incident. High-risk changes still stop at
`AWAITING_USER_APPROVAL`.

## Composition

```text
                         +-- Phase Gate: exact approved phase launches
Watchdog foundation ----+
                         +-- Watch and Fix: bounded low-risk recovery
```

Watchdog always owns target observation and the single monitoring heartbeat.
Phase Gate and Watch and Fix are independent policies layered onto it; neither
creates a second timer. If both apply, recovery is limited to the current
approved phase and control returns to Phase Gate before any later phase starts.

The user may change cadence or recovery policy between iterations. Update the
same monitoring contract and heartbeat instead of starting a new monitor.

## Compatibility and safety defaults

- Default to Watchdog and `observe_only` when intent is unclear.
- A detected bug does not itself grant repair authority.
- A previously authorized `auto_low_risk` policy does permit automatic
  recovery after the Recovery Risk Judge classifies the proposed action low
  risk.
- Phase completion never implies approval for the next phase.
- Job completion, job failure, job stop, and stopping monitoring follow the
  distinct outcome rules in `CONTROL_CONTRACT.md`.
