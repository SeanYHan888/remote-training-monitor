# Run Plan Examples

Illustrative plans. Verify identities, current evidence, approvals and the
runtime's scheduling capabilities before arming a heartbeat.

## Single-phase Slurm training, already running, observe only

```markdown
---
target_key: slurm-4821
run_name: fine-tune 7B on mix-v3
harness: claude-code
control_plane: slurm
project_dir: /home/ml-user/projects/llm-ft
wake_mode: COMPLETION
recovery_policy: observe_only
timezone: UTC
plan_revision: 1
created: 2026-09-04T09:12:00Z
---

# Run Plan: fine-tune 7B on mix-v3, job 4821

## Phases

| # | Phase | Entry condition | Exit checks | Expected artifacts | Launch action |
| --- | --- | --- | --- | --- | --- |
| 1 | run | job 4821 RUNNING on gpu-a100 | sacct State=COMPLETED 0:0 · `train.log` ends with "training complete" · step counter reaches 20000 | `ckpt/step-20000/`, `metrics.jsonl` | already running |

## Monitoring Contract

- Identities: Slurm job 4821, user ml-user, workdir `/scratch/ml-user/llm-ft/run-0904`
- Adapter: Slurm. `squeue -j 4821`, `scontrol show job 4821`, `sacct -j 4821`; logs from StdOut path
- Training signals: step rate from `metrics.jsonl` (plan 1.9 step/s); checkpoints every 2000 steps under `ckpt/`; log age from StdErr. Default bands.
- Success: exit checks above. Failure: State in FAILED/TIMEOUT/PREEMPTED, or traceback in StdErr. Stop: State=CANCELLED by ml-user
- Wake: COMPLETION, run stage (the job is already running). Deadline 2026-09-04T15:30Z = start 09:00Z + 6 h limit + 30 min. Stall rule: `metrics.jsonl` unchanged 15 min. Basis: 20000 steps at ~1.9 step/s observed, ~2.9 h remaining
- Recovery: observe_only. Approval holder: operator
- Limits: none granted; read-only
- Discovery gaps: none

## Approvals

## History

- 2026-09-04T09:12Z RUNNING (step 12400/20000, 1.9 step/s, ETA 10:40Z). Next: run-stage waiter bg-7f2c armed, backstop 15:30Z, session-bound
```

## Three-phase train, eval, upload with Phase Gate and low-risk recovery

```markdown
---
target_key: slurm-4830
run_name: mix-v3 train, eval, upload
harness: codex-desktop
control_plane: slurm
project_dir: /Users/operator/projects/llm-ft
wake_mode: INTERVAL
recovery_policy: auto_low_risk
timezone: UTC
plan_revision: 1
created: 2026-09-04T10:00:00Z
---

# Run Plan: train, evaluate, and publish mix-v3 checkpoint

## Phases

| # | Phase | Entry condition | Exit checks | Expected artifacts | Launch action |
| --- | --- | --- | --- | --- | --- |
| 1 | train | job 4830 RUNNING | sacct COMPLETED 0:0 · step 20000 · final loss logged | `ckpt/step-20000/` | already running |
| 2 | eval | phase 1 PASSED, checkpoint present | `eval/results.json` has all 5 benchmarks · exit 0 | `eval/results.json` | `sbatch eval.sbatch --ckpt ckpt/step-20000` |
| 3 | upload | phase 2 PASSED, results reviewed | `hf upload` exit 0 · remote revision hash recorded | HF repo revision | `python upload.py --ckpt ckpt/step-20000 --repo org/mix-v3` |

## Monitoring Contract

- Identities: job 4830 now; later phases get their own ids recorded in History
- Adapter: Slurm as above; phase 3 is a generic process
- Training signals: phase 1 step rate and checkpoints; phases 2–3 stage from the job's stdout and log age
- Success/failure/stop per phase exit checks; unexpected cancellation is FAILED
- Wake: INTERVAL at ACTIVE (Codex desktop has no completion wake). Basis: ~50 min remaining in phase 1
- Recovery: auto_low_risk, retry budget 2 per cause, rollback point = last checkpoint. Approval holder: operator
- Limits: 1 node, no new GPUs, no deletion, destination only org/mix-v3, no visibility change
- Discovery gaps: eval benchmark list confirmed by operator

## Approvals

- 2026-09-04T10:05Z operator: "approved, run it" — revision 1; phase 1 launch (already running) and auto_low_risk recovery

## History
```

Phase 2 and phase 3 each wait with the monitor `WAITING` for an approval that
names them. After upload passes its exit checks and all required artifacts are
verified, report the run `PASSED` and set the monitor `OFF (terminal)`. A
retry within a phase keeps `slurm-4830` and its heartbeat, while recording a
new attempt and job identity.

## Smoke test approved by a project packet, history in the project's file

A project that already approves runs with a frozen packet and keeps a per-run
state file. The plan imports the packet's checks and points History at the
project's file; `.remote-monitor/adapter.md` holds the commands.

```markdown
---
target_key: slurm-cluster-a-5102
run_name: mix-v3 smoke 4gpu a2
harness: claude-code
control_plane: slurm
project_dir: /Users/operator/projects/llm-ft
adapter: .remote-monitor/adapter.md
wake_mode: COMPLETION
recovery_policy: observe_only
approval_source: evidence/docs/smoke-4gpu-a2/SMOKE_4GPU_A2_PACKET.json sha256 9f3c2a1e…
history: evidence/docs/smoke-4gpu-a2/RUN_STATE.md
timezone: America/New_York
plan_revision: 1
created: 2026-11-07T04:20:00Z
---

# Run Plan: 4-GPU smoke test of the per-example controller, attempt a2

## Phases

| # | Phase | Entry condition | Exit checks | Expected artifacts | Launch action |
| --- | --- | --- | --- | --- | --- |
| 1 | run | submitted as Slurm 5102 | sacct COMPLETED 0:0 · `run/run.json` status.stage = training_pass · archive.stage = uploaded · hf.model_revision set · `run/local_completion.json` status PASS with controller_rule_check PASS · `trajectories/controller.csv` gap-free, two rows per step · W&B run finished with per-step controller metrics · `run/final_checkpoint_fresh_load.json` PASS · `run/hub_revision_verification.json` PASS | `outputs/<run>/run/`, HF repo `<org>/<run>` | already running |

Exit checks copied from `packet_body.exit_checks` of the approval source (8 checks).

## Monitoring Contract

- Identities: Slurm 5102 on cluster-a (`ssh cluster-a`, user operator), run `<run>`, attempt a2, output dir `/scratch/operator/llm-ft/outputs/<run>`
- Adapter: per adapter.md
- Training signals: stage from `run/run.json`; step rate from W&B; log age from StdErr. Stall band for stage: 15 min (the known credentials hang)
- Success: the exit checks. Failure: any other terminal state, or run.json status failed (it names the stage). Stop: only a cancel the operator asks for
- Wake: COMPLETION. Queue stage (846 jobs pending; recent smokes waited 24 min to 3.5 h), backstop 24 h. Run stage after the early health check: deadline = start + 1 h 30 min limit + 10 min; stall rule on run.json 15 min
- Recovery: observe_only. A re-attempt is a new packet; no retry, cancel or cleanup by the skill
- Approval source: the packet above; holder: operator
- Limits: read-only toward the cluster. After the run: `runs.py pull`, commit, `runs.py check`, as the packet authorizes

## Approvals

- 2026-11-07T04:13Z operator replied with the packet SHA-256 `9f3c2a1e…` — revision 1; observe_only needs nothing further

## History

History: evidence/docs/smoke-4gpu-a2/RUN_STATE.md
```

Its `state.json` while queued:

```json
{
  "target_key": "slurm-cluster-a-5102",
  "run_name": "mix-v3 smoke 4gpu a2",
  "plan_revision": 1,
  "run_state": "QUEUED",
  "since": "2026-11-07T04:20:00Z",
  "health": null,
  "monitor": { "state": "WATCHING", "reason": null },
  "heartbeat": { "harness": "claude-code", "mode": "completion", "id": "bg-q1", "deadline": "2026-11-08T04:20:00Z", "interval_min": null, "cadence": null, "durability": "session-bound", "project_dir": "/Users/operator/projects/llm-ft" },
  "current_phase": 1,
  "current_attempt": { "attempt_id": "a2", "control_plane": "slurm", "scope": "cluster-a", "job_id": "5102" },
  "progress": { "step": null, "total_steps": 6, "rate": null, "eta": null, "last_checkpoint": null, "stage": null },
  "checks": { "passed": 0, "total": 8 },
  "cursor": { "scheduler_seen": "PENDING Priority est 22:22 ET" },
  "next_action": "early health check 4 min after start",
  "last_observed": "2026-11-07T04:21:00Z",
  "estimated_remaining_min": null,
  "retries": {}
}
```

## Batch inference in Kubernetes, observe only, one phase

```markdown
---
target_key: k8s-infer-mixv3-7f2c1
run_name: score 2M prompts with mix-v3
harness: codex-cli
control_plane: kubernetes
project_dir: /home/ml-user/projects/serving
wake_mode: INTERVAL
recovery_policy: observe_only
timezone: UTC
plan_revision: 1
created: 2026-09-04T14:20:00Z
---

# Run Plan: score 2M prompts with mix-v3, Job infer-mixv3

## Phases

| # | Phase | Entry condition | Exit checks | Expected artifacts | Launch action |
| --- | --- | --- | --- | --- | --- |
| 1 | run | Job infer-mixv3 active, 8/8 pods | Job condition Complete · `gs://out/mixv3/_SUCCESS` · 2,000,000 rows in manifest | `gs://out/mixv3/part-*.parquet` | already running |

## Monitoring Contract

- Identities: namespace ml, Job infer-mixv3, uid 7f2c1…
- Adapter: Kubernetes. `kubectl get job/infer-mixv3 -n ml`, `kubectl logs --since=…`, events, restart counts
- Training signals: rows scored per minute from the pod logs; restarts; log age
- Success: exit checks. Failure: condition Failed, restart count climbing, OOMKilled. Stop: Job deleted by ml-user
- Wake: INTERVAL at ACTIVE. Basis: ~40 min remaining at observed throughput
- Recovery: observe_only. Approval holder: operator
- Discovery gaps: none
- Harness note: codex-cli, in-session polling bounded to 40 minutes; per-call waits follow runtime limits. Operator-managed scheduling is needed to outlive the session.

## Approvals

## History
```
