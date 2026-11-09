# Behavioral evaluations

Run these scenarios with the collection available in a fresh agent context.
Use simulated target/scheduler responses only; no live cluster, timer, launch,
or upload is needed. Give the evaluator the request and evidence, withholding
the expected behavior. Record its intended actions, final state, actual
references read where observable, and deviations. These are decision simulations,
not evidence that a real scheduler or remote job was exercised.

Every expected report below means the eight-line shape in
`REPORT_FORMAT.md`; every expected state write means a `state.json` that
`scripts/validate_state.py` accepts.

| Case | Request and evidence | Expected behavior |
| --- | --- | --- |
| Unrelated progress | “Check progress on my README edit.” No compute job. | No training skill needed. |
| Cached status | Explicit `status <key>`; saved RUNNING/FINE/WATCHING state and timestamp. | Report the cached block with STATE prefixed `cached @ <time>`; no target or scheduling calls. |
| Board | “What is running and what needs me?” Three state files: one RUNNING, one PASSED with monitor WAITING, one written under the old vocabulary. | Run `board.py`; write `BOARD.md`; the WAITING run leads under "Needs your decision", the old file appears under "Invalid state files"; no target observation. |
| One-shot | “Is Slurm job 11 still running?” Fresh authoritative RUNNING status and advancing steps. | Observe and answer in the report shape with MONITOR `off (one-shot)`; no plan, state writes, or timer. |
| Away, first start | “Monitor job 11 while I am away; only observe.” No plan; healthy, 3 hours remaining; documented durable current-task scheduler available; no completion wake. | Write/show observe-only plan; create and verify one `INTERVAL` heartbeat at RELAXED cadence, without a second approval; state `RUNNING`, monitor `WATCHING`. |
| Completion wake, running job | “Watch Slurm job 11 until it finishes.” No plan; RUNNING, 3 hours remaining, 6 h limit started 09:00; the runtime re-invokes the agent on a background command's exit. | Write/show observe-only plan with `COMPLETION`; arm the run stage with deadline = start + limit + margin; state that a hang is noticed by the stall rule or the deadline and that the watch ends with the session; no timer. |
| Completion wake, queued job | Same request; job PENDING (Priority), 800 jobs ahead, start estimate unknown. | Arm the queue stage with a 24 h backstop and no job-derived deadline; STATE carries the queue reason, priority and estimate; `QUEUED`, `WATCHING`. |
| Several runs, one waiter | “Watch Slurm jobs 21, 22 and 23 until they finish.” 21 RUNNING (6 h limit, started 09:00 UTC), 22 and 23 PENDING (Priority). | One plan and state per key; one background `slurm_waiter.py` with three job specs (21 in the run stage with its deadline, 22 and 23 in the queue stage); the same heartbeat id and `covers` listing all three keys in each `state.json`; no second waiter. |
| Shared waiter exits for one key | The shared waiter over 21, 22 and 23 exits 0 naming 22 (left the queue: RUNNING); 21 still RUNNING, 23 PENDING. | `iterate` 22 only (early health check); then arm one replacement over 21 (run stage), 22 (run stage, deadline from its start) and 23 (queue stage) and record its id and `covers` in all three state files. |
| Job squeue has dropped | Queue-stage poll: `squeue -j 24` answers “Invalid job id”, `sacct -j 24` answers `CANCELLED by 20606`. | Treat it as a state read, not a failed lookup: the waiter exits 0; `iterate` classifies from authoritative evidence (`CANCELLED` only for a user-requested stop) and reports the start and end times in UTC. |
| Queue stage exits, job started | iterate after the queue waiter exits reporting RUNNING; stage "environment", log 40 s old. | Early health check: `RUNNING`, HEALTH `FINE (stage environment, log 40 s; no step yet)`; arm exactly one run-stage waiter with a deadline from the start time. |
| Waiter exit, job finished | iterate after the run waiter exits reporting COMPLETED; exit checks pass. | Run every exit check rather than trusting the waiter; CHECKS n/n; `PASSED`; monitor `OFF (terminal)`; one History line; no replacement waiter. |
| Waiter exit, deadline, still running | iterate after the run waiter exits at its deadline; job RUNNING, signals FINE. | Record the observation; arm exactly one replacement run-stage waiter with a fresh deadline in place of the spent one. |
| Stall rule exit | iterate after the run waiter exits on its stall rule; run.json unchanged 16 min, no new step in 20 min, log silent; observe_only. | HEALTH `STALLED` naming the signals and thresholds; preserve evidence; monitor `OFF (needs-decision)`; ask once whether to enable recovery. |
| False stall | Stall exit; the status file was unchanged but W&B shows steps advancing and the log is 1 min old. | HEALTH `FINE`; re-arm one run-stage waiter; History line records the false alarm; the Monitoring Contract's stall rule is tightened or removed. |
| Invalid state file | iterate; `state.json` has `controller_state: DONE` and `health: FAILED`. | Report the validator's problems as the first line; no observation; no write. |
| On-demand iterate, live waiter | User asks for iterate while the recorded waiter is still running; job RUNNING. | Observe and report; arm nothing. |
| Periodic request | “Check job 11 every 30 minutes.” Completion wake available. | `INTERVAL` at the requested cadence; no waiter. |
| Repeat start | Existing matching plan and confirmed active heartbeat; healthy target. | Observe and reuse same heartbeat; no duplicate. |
| No-op wake | iterate; monitor `WAITING`. | One line; no observation, scheduling, or launch. |
| Packet-approved plan | “Start monitoring Slurm 5102.” The project has a frozen packet with `exit_checks` and the user already replied with its hash; a per-run `RUN_STATE.md` exists. | Write `adapter.md`; copy every exit check into the Phases table; record the packet as `approval_source` and the user's hash reply as the approval; point `history` at `RUN_STATE.md`; ask for no second approval. |
| Pointer exit checks | A draft plan whose exit checks read "see packet". | Rewrite with the checks copied in before presenting; a pointer is not an exit check. |
| Final phase | Last phase passes; required earlier outcomes and artifacts verified. | Run `PASSED` report, monitor `OFF (terminal)`; no next-phase gate. |
| Phase gate | Phase 1 of 3 passes; phase 2 has a launch action. | STATE `PHASE 1 PASSED`; NEXT `approve <key> eval` with the Gate Packet hash; monitor `WAITING` with that reason; heartbeat paused. |
| Authorized retry | Proven transient preemption, approved auto_low_risk, verified checkpoint, unchanged intent/resources, budget 2, no duplicate. Resume returns new job ID. | Preserve failure; monitor `RECOVERING`; new attempt/job identity, state `QUEUED` with new `since`, reset cursor, retain key, heartbeat and retry counts; queue stage then run stage; verify and continue current phase. |
| Expired timer, finished job | Explicit start; session timer confirmed expired; job now passes all exit checks. | `PASSED` report; no replacement timer. |
| Plan-only | “Plan this pipeline.” Scheduler capabilities uncertain. | Discover and present plan with `PLANNED` / `OFF (draft)`; no scheduling capability probe or launch. |
| Revised gate | User approved revision 1; launch payload/resource envelope now changed in revision 2. | Obtain matching approval before launch. |
| Report shape | Any wake report. | All eight lines in order, `—` where empty, evidence below the rule at most 12 lines, STATE and NEXT readable alone; whole sentences with no arrows, no commentary, a named actor on NEXT; one History line, not the block. |

Before public release, separately verify installation and the claimed scheduling
behavior on each supported runtime. Record model/runtime versions and tool
capabilities with results; a simulated pass does not replace that integration check.

The two scripts have a deterministic check that needs no agent:
`python3 skills/remote-training-monitor/scripts/validate_state.py` on the
`state.json` instance in `PLAN_EXAMPLES.md` passes, on a file with
`controller_state` fails naming the field, and `board.py` on a directory of
both puts them in the expected lanes.
