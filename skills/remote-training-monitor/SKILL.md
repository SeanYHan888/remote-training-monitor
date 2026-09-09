---
name: remote-training-monitor
description: Plan and coordinate monitoring of long-running training, evaluation, and compute jobs. Use for recurring monitoring, approval-gated pipelines, or authorized recovery; route one-shot job checks to Watchdog.
license: MIT
compatibility: Requires all four skills from this repository and an agent with filesystem and shell access. Recurring monitoring also requires scheduler or background-process support.
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
| `start` / recurring watch | Read `CONTROL_CONTRACT.md` and `../remote-job-watchdog/SKILL.md`. Reuse an existing plan or create one using `PLAN_FORMAT.md`; apply its approval rule, then establish one heartbeat using `HARNESSES.md`. |
| `iterate <key>` | Read saved state first. If paused or awaiting approval, exit without observing. Otherwise use Watchdog for one iteration and the plan's authorized policy. Never re-plan or create a heartbeat. |
| `approve <key> <phase or revision>` | Read the plan and `../remote-job-phase-gate/SKILL.md`; record matching user approval. Continue an approved pending start or phase launch, then resume the same heartbeat. |
| `stop <key>` | Read saved state and the lifecycle in `CONTROL_CONTRACT.md`; pause monitoring through `HARNESSES.md`, leaving the job untouched. |
| `wake <key>` / `sleep <key>` | Use Watchdog's Cadence Mode guidance and `HARNESSES.md` to update the existing monitor. These change cadence, not authority or a paused approval gate. |

A missing plan/state for a keyed command is a concise diagnostic naming the
expected path and execution directory. Only an explicit `start` may establish
or resume a monitor, including continuation of that start after approval.
Read references only for the chosen route; reuse material already loaded.

“Monitor while I'm away” means `start`; for an existing monitor it reuses that
monitor. Absence alone does not request `SLEEP`. An explicit request for hourly
or sleep monitoring selects that cadence after establishing the monitor.

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
