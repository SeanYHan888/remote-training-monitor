---
name: remote-training-monitor
description: Plan and coordinate monitoring of long-running training, evaluation, and compute jobs. Use for watching a job until it finishes, approval-gated pipelines, or authorized recovery; route one-shot job checks to Watchdog.
license: MIT
compatibility: Requires all four skills from this repository and an agent with filesystem and shell access. Monitoring also requires background-process or scheduler support.
---

# Remote Training Monitor

Route requests using the table below. The complete collection includes the
three sibling skills: Watchdog, Phase Gate, and Watch and Fix. If a required
companion is missing, report the missing path and the collection install command:
`npx skills@latest add SeanYHan888/remote-training-monitor --skill '*'`.

## Routing

| Request / verb | Action and references |
| --- | --- |
| One-shot job check | Use `../remote-job-watchdog/SKILL.md` for one observation; no plan or heartbeat. |
| `status <key>` | Read `.remote-monitor/<key>/state.json`; report saved state and observation timestamp, explicitly identifying it as cached. No target observation or scheduler call. |
| `plan` | Read `PLAN_FORMAT.md` and the relevant section of `ADAPTERS.md`; discover, write, and present the plan. Stop before launching or scheduling. |
| `start` / watch until done | Read `CONTROL_CONTRACT.md` and `../remote-job-watchdog/SKILL.md`. Reuse an existing plan or create one using `PLAN_FORMAT.md`; apply its approval rule, then establish one heartbeat using `HARNESSES.md`: a completion wake where the harness supports one, an interval timer otherwise. |
| `iterate <key>` | Follow Watchdog's Iteration steps, including the saved-state guard and required plan reload and validation before observation. Never re-plan or add a heartbeat; replace a completion waiter only as Iteration allows. |
| `approve <key> <phase or revision>` | Read the plan and `../remote-job-phase-gate/SKILL.md`; record matching user approval. Continue an approved pending start or phase launch, then resume the same heartbeat. |
| `stop <key>` | Read saved state and the lifecycle in `CONTROL_CONTRACT.md`; pause monitoring through `HARNESSES.md`, leaving the job untouched. |
| `wake <key>` / `sleep <key>` | `INTERVAL` monitors only. Use Watchdog's Cadence Mode guidance and `HARNESSES.md` to update the existing monitor. These change cadence, not authority or a paused approval gate. A `COMPLETION` monitor has no cadence: say so in one line and offer `iterate <key>` for an observation now. |

A missing plan/state for a keyed command is a concise diagnostic naming the
expected path and execution directory. Only an explicit `start` may establish
or resume a monitor, including continuation of that start after approval.
Read references only for the chosen route; reuse material already loaded.

“Monitor while I'm away” means `start`; for an existing monitor it reuses that
monitor. Without a stated cadence, `start` uses `COMPLETION` where the harness
supports it: the agent is woken when the job ends, not on a timer. An explicit
request for periodic check-ins ("every 30 minutes", hourly, sleep) selects
`INTERVAL` at that cadence. Absence alone does not request `SLEEP`.

## Policy composition

Watchdog owns observation and the single heartbeat. Add
`../remote-job-phase-gate/SKILL.md` for multiple phases or a launch action.
Add `../remote-job-watch-and-fix/SKILL.md` when the plan authorizes
`auto_low_risk`; read `RISK_POLICY.md` before a repair. Recovery applies only to
the current approved phase and returns control before the next phase gate.

Ambiguous recovery intent uses `observe_only`. The plan records authorized
actions, resource limits, and stopping conditions; discovering a failure does
not expand that authority. The shared contract defines lifecycle and outcomes.

## Completion

A one-shot check ends with an evidence-backed answer. `plan` ends with the
written plan and unresolved discovery gaps. `start` ends only after the plan
and approval requirements are satisfied and the heartbeat is verified and
recorded, or a concrete scheduling/approval blocker is reported. An iteration
records its observation and either leaves monitoring active, transfers to
authorized recovery, or reports a terminal outcome or approval gate.
