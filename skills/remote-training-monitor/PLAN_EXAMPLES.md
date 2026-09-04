# Run Plan Examples

Patterns to copy. Each is complete enough to arm a heartbeat from.

## Single-phase Slurm training, already running, observe only

```markdown
---
target_key: slurm-4821
harness: claude-code
control_plane: slurm
project_dir: /home/sean/proj/llm-ft
cadence_mode: RELAXED
recovery_policy: observe_only
plan_revision: 1
created: 2026-09-04T09:12:00Z
---

# Run Plan: fine-tune 7B on mix-v3, job 4821

## Phases

| # | Phase | Entry condition | Exit checks | Expected artifacts | Launch action |
| --- | --- | --- | --- | --- | --- |
| 1 | run | job 4821 RUNNING on gpu-a100 | sacct State=COMPLETED; `train.log` ends with "training complete"; step counter reaches 20000 | `ckpt/step-20000/`, `metrics.jsonl` | already running |

## Monitoring Contract

- Identities: Slurm job 4821, user sean, workdir `/scratch/sean/llm-ft/run-0904`
- Adapter: Slurm. `squeue -j 4821`, `scontrol show job 4821`, `sacct -j 4821`; logs from StdOut path
- Success: exit checks above. Failure: State in FAILED/TIMEOUT/PREEMPTED, or traceback in StdErr. Stop: State=CANCELLED by sean
- Cadence: RELAXED. Basis: 20000 steps at ~1.9 step/s observed, ~2.9 h remaining, two healthy observations
- Recovery: observe_only. Approval holder: sean
- Limits: none granted; read-only
- Discovery gaps: none

## Approvals

## History

- 2026-09-04T09:12Z started, heartbeat cron `rtm-slurm-4821` at 30 min
```

## Three-phase train, eval, upload with Phase Gate and low-risk recovery

```markdown
---
target_key: slurm-4830
harness: codex-desktop
control_plane: slurm
project_dir: /Users/sean/proj/llm-ft
cadence_mode: ACTIVE
recovery_policy: auto_low_risk
plan_revision: 1
created: 2026-09-04T10:00:00Z
---

# Run Plan: train, evaluate, and publish mix-v3 checkpoint

## Phases

| # | Phase | Entry condition | Exit checks | Expected artifacts | Launch action |
| --- | --- | --- | --- | --- | --- |
| 1 | train | job 4830 RUNNING | sacct COMPLETED; step 20000; final loss logged | `ckpt/step-20000/` | already running |
| 2 | eval | phase 1 FINISHED, checkpoint present | `eval/results.json` with all 5 benchmarks; exit 0 | `eval/results.json` | `sbatch eval.sbatch --ckpt ckpt/step-20000` |
| 3 | upload | phase 2 FINISHED, results reviewed | `hf upload` exit 0; remote revision hash recorded | HF repo revision | `python upload.py --ckpt ckpt/step-20000 --repo org/mix-v3` |

## Monitoring Contract

- Identities: job 4830 now; later phases get their own ids recorded in History
- Adapter: Slurm as above; phase 3 is a generic process
- Success/failure/stop per phase exit checks; unexpected cancellation is FAILED
- Cadence: ACTIVE. Basis: ~50 min remaining in phase 1
- Recovery: auto_low_risk, retry budget 2 per cause, rollback point = last checkpoint. Approval holder: sean
- Limits: 1 node, no new GPUs, no deletion, destination only org/mix-v3, no visibility change
- Discovery gaps: eval benchmark list confirmed by sean

## Approvals

- 2026-09-04T10:05Z sean: "approved, run it" — revision 1; phase 1 launch (already running) and auto_low_risk recovery

## History
```

Phase 2 and phase 3 each wait at `AWAITING_USER_APPROVAL` for an approval that
names them.

## Batch inference in Kubernetes, observe only, one phase

```markdown
---
target_key: k8s-infer-mixv3-7f2c1
harness: codex-cli
control_plane: kubernetes
project_dir: /home/sean/proj/serving
cadence_mode: ACTIVE
recovery_policy: observe_only
plan_revision: 1
created: 2026-09-04T14:20:00Z
---

# Run Plan: score 2M prompts with mix-v3, Job infer-mixv3

## Phases

| # | Phase | Entry condition | Exit checks | Expected artifacts | Launch action |
| --- | --- | --- | --- | --- | --- |
| 1 | run | Job infer-mixv3 active, 8/8 pods | Job condition Complete; `gs://out/mixv3/_SUCCESS`; 2,000,000 rows in manifest | `gs://out/mixv3/part-*.parquet` | already running |

## Monitoring Contract

- Identities: namespace ml, Job infer-mixv3, uid 7f2c1…
- Adapter: Kubernetes. `kubectl get job/infer-mixv3 -n ml`, `kubectl logs --since=…`, events, restart counts
- Success: exit checks. Failure: condition Failed, restart count climbing, OOMKilled. Stop: Job deleted by sean
- Cadence: ACTIVE. Basis: ~40 min remaining at observed throughput
- Recovery: observe_only. Approval holder: sean
- Discovery gaps: none
- Harness note: codex-cli, in-session polling bounded to 8 polls; cron one-liner handed to sean

## Approvals

## History
```
