# Recovery Risk Judge

Use this shared policy before every proposed Watch and Fix action. Classify the
remediation, not merely the incident. The same failure can have a low-risk
artifact repair and a high-risk full-training rerun.

The judge is an internal reusable module, not another user-facing skill. It
returns:

```text
risk: LOW | HIGH
cause_evidence
proposed_action
preserved_invariants
rollback_point
retry_budget
resource_impact
verification
approval_required
```

## Low-risk rule

Classify an action `LOW` only when all of these are true:

1. Bounded evidence proves the cause well enough to justify the repair.
2. The action preserves the approved scientific or business intent: algorithm,
   objective, model meaning, data semantics, experiment condition, selection
   rule, and evaluation meaning do not change.
3. It stays inside the current approved phase, job set, resource envelope,
   destination scope, and retry budget.
4. It is additive, reversible, or safely repeatable; it does not delete,
   overwrite, prune, or hide prior failures.
5. Exact job, checkpoint, configuration, artifact, and destination identities
   are verified, and a duplicate action is excluded.
6. A rollback or preserved source artifact exists.
7. Verification can demonstrate that the repair restored the declared contract.
8. It does not require obtaining, exposing, rotating, or broadening credentials
   or permissions.

When all conditions pass and the monitoring contract says `auto_low_risk`,
repair and redo the failed step without asking. Preserve the original failure
under its original identity and use a unique retry identity.

Default to at most two automatic repair-and-redo attempts per distinct proven
cause unless the monitoring contract sets another bounded retry limit.

## High-risk rule

Classify an action `HIGH` if any low-risk condition fails, or if it would:

- change the algorithm, loss, objective, hyperparameters, schedule semantics,
  model architecture, dataset meaning, split, seed policy, evaluation,
  selection rule, phase plan, or interpretation;
- change a frozen environment or configuration after its approval gate without
  revalidation and a new approval packet;
- add runs, GPUs, wall time, storage, paid capacity, or retries beyond the
  approved resource envelope;
- delete, overwrite, prune, clean up, or replace authoritative artifacts;
- cross a phase gate or launch a materially different job;
- change upload destination, repository visibility, publication scope, or
  external recipient;
- acquire or expose credentials, weaken security, or broaden permissions; or
- rerun expensive completed training when a bounded artifact-only recovery can
  preserve the valid training result.

Set `AWAITING_USER_APPROVAL` and present the evidence, proposed change,
resource impact, rollback plan, verification plan, and exact approval request.

When evidence or impact is uncertain, classify `HIGH`.

## General low-risk patterns

These are examples, not an exhaustive bug list:

- retry a transient network, scheduler, download, or upload step using the same
  verified inputs and already authorized destination;
- correct a path, command, manifest, model-card, serialization, packaging, or
  handoff defect without changing the produced model or experiment semantics;
- rebuild or reinstall an isolated CUDA/PyTorch/dependency environment during
  its current setup phase, then rerun the full readiness suite;
- repair an export or checkpoint-conversion seam additively while preserving
  native training state, provenance, and the original failure;
- resume or resubmit the identical approved job from a verified checkpoint
  after infrastructure interruption, within retry and resource limits; or
- reuse already provisioned credentials through their approved secret
  mechanism without exposing or changing them.

## Special conditions

- **Upload failure:** fix and re-upload the same validated artifact to the same
  authorized destination when the cause is low risk. If capacity or quota is
  full, do not delete data, buy capacity, change visibility, or redirect the
  artifact unless a non-destructive alternative was pre-authorized.
- **Environment failure:** repair and rerun automatically when the environment
  is isolated, still inside the environment/setup contract, and all readiness
  tests will be repeated. A post-freeze dependency or driver change is high
  risk unless the governing Phase Plan explicitly allows re-freezing it.
- **Training retry:** an identical retry may be low risk within the approved
  job and resource envelope. Changing effective batch, precision, optimizer,
  data order, checkpoint semantics, or other experiment meaning is high risk.
- **Storage pressure:** measuring quota and stopping new work are low risk.
  Cleanup, pruning, overwrite, or deletion always requires explicit approval
  unless an exact deletion manifest was separately approved.
