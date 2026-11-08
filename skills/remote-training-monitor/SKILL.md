---
name: remote-training-monitor
description: Plan and coordinate monitoring of long-running training, evaluation, and compute jobs. Use for watching a job until it finishes, a board of every run in a project, approval-gated pipelines, or authorized recovery; route one-shot job checks to Watchdog.
license: MIT
compatibility: Requires all four skills from this repository, Python 3 for the bundled scripts, and an agent with filesystem and shell access. Monitoring also requires background-process or scheduler support.
---

# Remote Training Monitor

Route requests using the table below. The complete collection includes the
three sibling skills: Watchdog, Phase Gate, and Watch and Fix. If a required
companion is missing, report the missing path and the collection install command:
`npx skills@latest add SeanYHan888/remote-training-monitor --skill '*'`.

Every report uses the eight-line shape in `REPORT_FORMAT.md`; every state
file the shape in `state.schema.json`. Read the "State vocabulary" section of
`CONTROL_CONTRACT.md` once per session; read the rest of that file when a
route enters recovery or a phase gate, or when authority is in question.

## Routing

| Request / verb | Action and references |
| --- | --- |
| One-shot job check | Use `../remote-job-watchdog/SKILL.md` for one observation; no plan, state or heartbeat. Answer in the report shape with MONITOR `off (one-shot)`. |
| `board`, or `status` with no key | Run `python3 <this skill dir>/scripts/board.py <project-dir>`, write its output to `.remote-monitor/BOARD.md`, append `## Planned elsewhere` from the project adapter's `planned_source` when one exists (`BOARD_FORMAT.md`), and show the board. No target observation. |
| `status <key>` | Validate and read `.remote-monitor/<key>/state.json`; report it as a cached block (`REPORT_FORMAT.md`, "status"). No target observation or scheduler call. |
| `plan` | Read `PLAN_FORMAT.md` and the matching section of `ADAPTERS.md`; read or write `.remote-monitor/adapter.md`; discover, write and present the plan with run state `PLANNED` and monitor `OFF (draft)`. Stop before launching or scheduling. |
| `start` / watch until done | Read `PLAN_FORMAT.md`, `HARNESSES.md` and `../remote-job-watchdog/SKILL.md`. Reuse an existing plan or create one; apply its approval rule; observe; arm one heartbeat (a completion wake where the harness supports one, an interval timer otherwise); report. |
| `iterate <key>` | Follow Watchdog's Iteration, including the state validation, the no-op guard and the plan reload before observation. Never re-plan or add a heartbeat; arm a waiter only as Iteration allows. |
| `approve <key> <phase or revision>` | Read the plan and `../remote-job-phase-gate/SKILL.md`; record matching user approval. Continue an approved pending start or phase launch, then resume the same heartbeat. |
| `stop <key>` | Set the monitor `OFF (stopped)`, pause the heartbeat (`HARNESSES.md`), acknowledge in one line. The job is untouched. |
| `wake <key>` / `sleep <key>` | `INTERVAL` heartbeats only: change the cadence on the existing heartbeat (Watchdog's Cadence; `HARNESSES.md`). Nothing else changes. A `COMPLETION` heartbeat has no cadence: say so in one line and offer `iterate <key>` for an observation now. |

A missing plan or state for a keyed command is a concise diagnostic naming the
expected path and execution directory. A state file the validator rejects is
reported with its first problems and ends the route before any observation.
Only an explicit `start` may establish or resume a monitor, including
continuation of that start after approval. Read references only for the chosen
route; reuse material already loaded.

"Monitor while I'm away" means `start`; for an existing monitor it reuses that
monitor. Without a stated cadence, `start` uses `COMPLETION` where the harness
supports it: the agent is woken when the job starts and when it ends, not on a
timer. An explicit request for periodic check-ins ("every 30 minutes", hourly,
sleep) selects `INTERVAL` at that cadence. Absence alone does not request
`SLEEP`. "What is running" or "where are we" means `board`.

## Policy composition

Watchdog owns observation and the single heartbeat. Add
`../remote-job-phase-gate/SKILL.md` for multiple phases or a launch action.
Add `../remote-job-watch-and-fix/SKILL.md` when the plan authorizes
`auto_low_risk`; read `RISK_POLICY.md` before a repair. Recovery applies only to
the current approved phase and returns control before the next phase gate.

Ambiguous recovery intent uses `observe_only`. The plan records authorized
actions, resource limits and stopping conditions; discovering a failure does
not expand that authority.

## Completion

A one-shot check ends with an evidence-backed report. `board` ends with the
written board. `plan` ends with the written plan and unresolved discovery
gaps. `start` ends only after the plan and approval requirements are satisfied
and the heartbeat is verified and recorded, or a concrete scheduling or
approval blocker is reported. An iteration records its observation in
`state.json` and one History line, reports in the eight-line shape, and either
leaves the monitor `WATCHING`, transfers to authorized recovery, or sets it
`WAITING` or `OFF` with the reason.
