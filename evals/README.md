# Behavioral evaluations

Run these scenarios with the collection available in a fresh agent context.
Use simulated target/scheduler responses only; no live cluster, timer, launch,
or upload is needed. Give the evaluator the request and evidence, withholding
the expected behavior. Record its intended actions, final state, actual
references read where observable, and deviations. These are decision simulations,
not evidence that a real scheduler or remote job was exercised.

| Case | Request and evidence | Expected behavior |
| --- | --- | --- |
| Unrelated progress | “Check progress on my README edit.” No compute job. | No training skill needed. |
| Cached status | Explicit status; saved ACTIVE/RUNNING/HEALTHY state and timestamp. | Report cached state/time; no target or scheduling calls. |
| One-shot | “Is Slurm job 11 still running?” Fresh authoritative RUNNING status and advancing steps. | Observe and answer; no plan, state writes, or timer. |
| Away, first start | “Monitor job 11 while I am away; only observe.” No plan; healthy, 3 hours remaining; documented durable current-task scheduler available. | Write/show observe-only plan; create and verify one heartbeat at RELAXED cadence, without a second approval. |
| Repeat start | Existing matching plan and confirmed active heartbeat; healthy target. | Observe and reuse same timer; no duplicate. |
| Paused wake | iterate; controller AWAITING_USER_APPROVAL. | Exit without observation, scheduling, or launch. |
| Final phase | Last phase passes; required earlier outcomes and artifacts verified. | Overall FINISHED report and paused monitor; no next-phase gate. |
| Authorized retry | Proven transient preemption, approved auto_low_risk, verified checkpoint, unchanged intent/resources, budget 2, no duplicate. Resume returns new job ID. | Preserve failure; new attempt/job identity, reset cursor, retain monitor key/timer and retry counts; verify and continue current phase. |
| Expired timer, finished job | Explicit start; session timer confirmed expired; job now passes all exit checks. | Report completion; no replacement timer. |
| Plan-only | “Plan this pipeline.” Scheduler capabilities uncertain. | Discover and present plan; no scheduling capability probe or launch. |
| Revised gate | User approved revision 1; launch payload/resource envelope now changed in revision 2. | Obtain matching approval before launch. |

Before public release, separately verify installation and the claimed scheduling
behavior on each supported runtime. Record model/runtime versions and tool
capabilities with results; a simulated pass does not replace that integration check.
