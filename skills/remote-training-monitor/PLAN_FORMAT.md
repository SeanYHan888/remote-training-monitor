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

`<control-plane>-<immutable-id>[-attempt-N]`, for example `slurm-4821`,
`k8s-train-abc12-attempt-2`, `proc-a1b2c3`. The immutable id comes from the
control plane, never from a job name. The user may add a label; the key still
carries the id. A resubmission or retry gets a new attempt suffix and a new
directory.

## Repo hygiene

On first write, if the project is a git repository, append
`.remote-monitor/` to `.git/info/exclude` when it is not already ignored. That
keeps the directory out of commits without editing any tracked file. After a
terminal state the directory is kept and named in the outcome report.

## plan.md

```markdown
---
target_key: slurm-4821
harness: claude-code | codex-desktop | codex-cli
control_plane: slurm | kubernetes | docker | systemd | managed | process | custom
project_dir: /abs/path
cadence_mode: ACTIVE | RELAXED | SLEEP
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
- Cadence Mode and its basis (estimated remaining time, stability)
- Recovery policy, retry budget, rollback point requirements
- Approval holder
- Resource, cost, storage, publication, and destructive-action limits
- Discovery gaps: what could not be found and what the user supplied

## Approvals

<!-- append-only: timestamp, who, what was approved, plan revision -->

## History

<!-- append-only: phase outcomes, recovery attempts, cadence changes -->
```

A phase whose launch action is "already running" has no gate before it. A
phase with a real launch action gates on Approval.

## state.json

```json
{
  "target_key": "slurm-4821",
  "plan_revision": 1,
  "heartbeat": { "harness": "codex-desktop", "id": "<task id or routine name>", "interval_min": 30 },
  "controller_state": "ACTIVE | SLEEP | RECOVERING | AWAITING_USER_APPROVAL | PAUSED",
  "current_phase": 1,
  "job_state": "RUNNING | FINISHED | FAILED | STOPPED",
  "health": "HEALTHY | DEGRADED | STALLED | AMBIGUOUS",
  "cursor": { "log_offset": 0, "last_step": 0, "last_checkpoint": null, "scheduler_seen": "..." },
  "last_observed": "2026-09-04T12:30:00Z",
  "estimated_remaining_min": 240,
  "retries": { "<cause>": 0 }
}
```

`iterate` reads this file first. Controller state `PAUSED` or
`AWAITING_USER_APPROVAL` makes the wake a no-op wake.

## Mutation

- The skill appends to Approvals and History and updates `current_phase`,
  cadence, and state fields.
- Phase semantics, resource envelope, and recovery policy change only by
  bumping `plan_revision`, which voids every standing Approval. The Gate
  Packet hash rule in Phase Gate is this rule applied per phase.
- A wake never edits Phases and never re-plans. A missing `plan.md` is a
  one-line refusal naming the expected path and directory.
- Approvals are recorded as the user's words plus the phase name or revision
  they match. "Looks good" against revision 2 is not an approval of revision 3.
