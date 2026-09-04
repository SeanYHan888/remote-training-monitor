---
name: remote-training-monitor
description: Plan, check on, watch, or monitor a job and report its state, progress, and failures - training runs, inference or evaluation jobs, Slurm/Kubernetes/Docker/systemd workloads, or any long-running script. TRIGGER when the user says "check the training", "check progress", "how's the run going", "is the job still running", "is it stuck", "did it finish", "watch this job", "monitor job 12345", "tell me when it's done", "what happened to my run", "plan this training", "plan and run this pipeline", or names a job id, run id, or cluster job to look at. Also trigger when a multi-phase pipeline must stop for approval between phases, or when the user authorizes automatic recovery of routine failures ("watch and fix", "keep it running"). Read-only toward the job by default - it observes and reports, and never restarts, resubmits, cancels, or edits anything unless recovery is explicitly authorized.
user-invocable: true
---

# Remote Training Monitor

Entry point for planning, watching, gating, and recovering long-running remote
jobs. Every recurring monitor is **plan-first**: a Run Plan is written and
shown before the first heartbeat is armed, because on some harnesses the plan
file is the only context the next wake will have.

## Procedure

1. Resolve the entry point (table below) from the explicit verb or the
   natural-language intent.
2. Detect the harness and read its row in `HARNESSES.md`.
3. Read `CONTROL_CONTRACT.md`, then the matching section of `ADAPTERS.md`.
4. For `plan` or `start`: run Discovery and write the Run Plan as specified in
   `PLAN_FORMAT.md`; `PLAN_EXAMPLES.md` shows finished plans. Present it.
5. Apply the approval rule, then hand the target to **Remote Job Watchdog**.
   Layer **Remote Job Phase Gate** when the plan has more than one phase or a
   launch action, and **Remote Job Watch and Fix** when the plan's recovery
   policy is `auto_low_risk` (read `RISK_POLICY.md` before any repair).

## Entry points

A heartbeat prompt must be unambiguous, so the router accepts fixed verbs.
Natural language maps onto them; a scheduled task always uses the verb form
`$remote-training-monitor <verb> <target-key>`.

| Verb | Effect | Arms a heartbeat? |
| --- | --- | --- |
| `plan` | Discovery, write and present the Run Plan | No |
| `start` | `plan` if no plan exists, then arm the heartbeat | Yes |
| `iterate <key>` | One Observation for the Target Key; what every wake runs | Reuses |
| `status <key>` | Report from `state.json` without observing | No |
| `approve <key> <phase or revision>` | Append an Approval to the plan | No |
| `stop <key>` | Pause the heartbeat; the job is untouched | No |
| `wake <key>` / `sleep <key>` | Set Cadence Mode `ACTIVE` / `SLEEP` | Reuses |

`iterate` with no plan file at the expected path refuses in one line naming
the path and the directory it expected to run in. A wake never re-plans and
never re-arms.

## Plan-first

| Request | Plan? |
| --- | --- |
| One-shot: "is job 12345 still running?", "did it finish?" | No. Observe once, answer. |
| Recurring: "watch", "tell me when done", "monitor while I'm away" | Yes, then arm. |
| Multi-phase or "plan and run" | Yes, then gate. |

Discovery is read-only: launch scripts, sbatch or job specs, configs, the
working directory, existing checkpoints and logs. Draft phases from what is
found, mark gaps, and ask only for what could not be discovered. When nothing
phase-shaped exists, the plan has one phase named `run`.

Approval rule:

- Recovery policy `observe_only` and no launch action: show the plan and start
  observing immediately.
- Any launch action or `auto_low_risk`: show the plan and wait. Approving the
  plan approves phase 1's launch action by name; every later phase still gates.
- A change to phases, resource envelope, or recovery policy bumps the Plan
  Revision and voids standing approvals.

## Intent detection

| User intent | Entry point and policy |
| --- | --- |
| "Check", "is it running", "did it finish" | One Observation, `observe_only`, no plan |
| "Watch", "monitor", "tell me when it finishes" | `start`, Watchdog, `observe_only` |
| "Plan this training", "what phases" | `plan` |
| "Plan and run", "stop for approval between phases" | `start` with Phase Gate |
| "Watch and fix", "keep it running", "handle routine failures" | `start` with Watch and Fix, `auto_low_risk` |
| "Sleep", "monitor while I am away" | `sleep`: Cadence Mode only |

Policies compose. Sleep changes cadence, never authority. When recovery intent
is ambiguous, use `observe_only`; repair authority is granted in the plan, not
acquired by finding a bug.

## Composition

```text
                         +-- Phase Gate: exact approved phase launches
Watchdog foundation ----+
                         +-- Watch and Fix: bounded low-risk recovery
```

Watchdog owns target observation and the single heartbeat per Target Key.
Phase Gate and Watch and Fix layer onto it; neither creates a second timer.
When both apply, recovery is limited to the current approved phase and control
returns to Phase Gate before any later phase starts.

Cadence or recovery policy changes between iterations update the same plan,
state file, and heartbeat.

## Safety defaults

- Default to Watchdog and `observe_only` when intent is unclear.
- Phase completion never implies approval for the next phase.
- `FINISHED`, `FAILED`, `STOPPED`, and stopping monitoring follow the distinct
  outcome rules in `CONTROL_CONTRACT.md`.
- The state directory is preserved after every terminal state and named in the
  outcome report as evidence.
