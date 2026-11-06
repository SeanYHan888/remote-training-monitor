# Run Plan Format

One directory per Target Key holds the human-facing Run Plan and the
machine-facing state:

```text
<project-dir>/.remote-monitor/<target-key>/
├── plan.md      # Run Plan: Phase Plan, Monitoring Contract, Approvals, History
└── state.json   # mutable fields a wake reads before observing
```

`plan.md` is read by people and rewritten only in the ways listed under
Mutation. `state.json` is what `iterate` parses, so a wake never has to find a
cursor inside prose.

## Target Key

The Target Key identifies the monitored workflow, not its current attempt.
For an already running job, derive it from the control-plane scope and initial
immutable job identity, for example `slurm-cluster-a-4821`. For a pipeline
not yet launched, generate a unique local run ID. Use a filesystem-safe key.
Once written, the key and state directory remain stable across phases and retries.

Record each phase launch or retry with a distinct `attempt_id`, exact remote
identity, and artifact paths in History; retain prior failure evidence. Update
`current_attempt` and reset observation cursors for the new attempt. Keep
retry counts across attempts. An unrelated workflow gets its own key.
Existing plans retain their original keys; do not rename them to match these
examples or overwrite an existing directory for a similarly named job.

## Repo hygiene

On first write, if the project is a git repository, append
`.remote-monitor/` to the exclude file resolved by `git rev-parse --git-path info/exclude`
when it is not already ignored. That
keeps the directory out of commits without editing any tracked file. After a
terminal state the directory is kept and named in the outcome report.

## Discovery and approval

Inspect launch scripts, job specs, configs, working directories, checkpoints,
and bounded logs read-only. Draft phases from the evidence; use one phase
named `run` when there is no multi-phase workflow. Ask only for missing
information needed to identify the target, define success, or establish authority.
Use `PLAN_EXAMPLES.md` when an example would clarify the plan format.

- `plan` writes and presents the plan without scheduling or launching.
- `start` with `observe_only` and no launch action proceeds after presenting
  the plan; it does not require another approval.
- A launch or `auto_low_risk` policy requires matching approval of the concrete
  plan. Record already supplied approval when it covers that exact scope;
  otherwise present the plan and wait. Approval covers phase 1's named launch
  and the stated recovery envelope. Later phases gate individually.
- Changes to phase semantics, resources, or recovery policy bump the revision
  and invalidate standing approvals.

## plan.md

```markdown
---
target_key: slurm-4821
harness: claude-code | codex-desktop | codex-cli
control_plane: slurm | kubernetes | docker | systemd | managed | process | custom
project_dir: /abs/path
wake_mode: COMPLETION | INTERVAL
cadence_mode: ACTIVE | RELAXED | SLEEP   # INTERVAL only; omit under COMPLETION
recovery_policy: observe_only | auto_low_risk
plan_revision: 1
created: 2026-09-04T12:00:00Z
---

# Run Plan: <one-line description>

## Phases

| # | Phase | Entry condition | Exit checks | Expected artifacts | Launch action |
| --- | --- | --- | --- | --- | --- |
| 1 | train | ... | ... | ... | already running / exact command |

## Monitoring Contract

- Target identities: job id, attempt, owner, working directory on the host
- Adapter and exact observation commands
- Success, failure, and intentional-stop evidence
- Wake Mode and its basis: the waiter's exit conditions and deadline, or the
  Cadence Mode (estimated remaining time, stability)
- Recovery policy, retry budget, rollback point requirements
- Approval holder
- Resource, cost, storage, publication, and destructive-action limits
- Discovery gaps: what could not be found and what the user supplied

## Approvals

<!-- append-only: timestamp, who, what was approved, plan revision -->

## History

<!-- append-only: phase outcomes, recovery attempts, wake and cadence changes -->
```

A phase whose launch action is "already running" has no gate before it. A
phase with a real launch action gates on Approval.

## state.json

```json
{
  "target_key": "slurm-4821",
  "plan_revision": 1,
  "heartbeat": { "harness": "claude-code", "mode": "completion", "id": "<background task id>", "deadline": "2026-09-04T16:30:00Z", "durability": "session-bound", "project_dir": "/abs/path" },
  "controller_state": "ACTIVE",
  "current_phase": 1,
  "current_attempt": { "attempt_id": "phase-1-attempt-1", "control_plane": "slurm", "scope": "cluster-a", "job_id": "4821" },
  "job_state": "RUNNING",
  "health": "HEALTHY",
  "cursor": { "log_offset": 0, "last_step": 0, "last_checkpoint": null, "scheduler_seen": "..." },
  "last_observed": "2026-09-04T12:30:00Z",
  "estimated_remaining_min": 240,
  "retries": { "<cause>": 0 }
}
```

This is an example instance, not a JSON Schema. Enum values are defined in
`CONTROL_CONTRACT.md`; heartbeat durability is `durable`, `session-bound`,
or `unknown`. Before scheduling, `heartbeat` is null; before first launch,
`current_attempt`, `job_state`, `health`, and `last_observed` may be null.
Use `PAUSED` for a draft and `AWAITING_USER_APPROVAL` for a pending gate.

An `INTERVAL` heartbeat records `"mode": "interval"` with `interval_min` in
place of `deadline`. A plan without `wake_mode`, or a heartbeat without
`mode`, was written before Wake Mode existed and is `INTERVAL`.

`iterate` reads this file first. Controller state `PAUSED` or
`AWAITING_USER_APPROVAL` makes the wake a no-op wake.

## Mutation

- The skill appends to Approvals and History and updates `current_phase`,
  wake mode, cadence, and state fields.
- Phase semantics, resource envelope, and recovery policy change only by
  bumping `plan_revision`, which voids every standing Approval. The Gate
  Packet hash rule in Phase Gate is this rule applied per phase.
- A wake never edits Phases and never re-plans. A missing `plan.md` is a
  one-line refusal naming the expected path and directory.
- Approvals are recorded as the user's words plus the phase name or revision
  they match. "Looks good" against revision 2 is not an approval of revision 3.
