# Remote Training Control Contract

The shared interface for Watchdog, Phase Gate, and Watch and Fix. Read it once
per invocation before applying a route-specific policy.

A **heartbeat** is the single recurring wake for one Target Key. Which
mechanism provides it is the harness's business; `HARNESSES.md` has the rows.
Every wake runs `iterate <target-key>` and reads the state file before
observing.

## Run Plan

Every recurring monitor has a Run Plan at
`.remote-monitor/<target-key>/plan.md` and its `state.json`, formatted as in
`PLAN_FORMAT.md`. The Monitoring Contract section records:

- stable Target Key, exact job or run identities, working directory, and owner;
- authoritative control plane and observation adapter;
- current phase, declared entry condition, exit checks, and expected artifacts;
- success, failure, and intentional-stop evidence;
- Cadence Mode, heartbeat durability, and the single heartbeat identity;
- recovery policy: `observe_only` or `auto_low_risk`;
- retry budget, rollback point requirements, and verification checks;
- approval holder and exact approval-gated phase transitions; and
- resource, cost, storage, publication, and destructive-action limits.

The Target Key distinguishes attempts. Never reuse a heartbeat, checkpoint,
output path, upload revision, or job identity because two jobs have similar
names.

## Authority planes

| Policy | Target observation | Monitoring control | Target recovery | Phase launch |
| --- | --- | --- | --- | --- |
| Watchdog | Read | Create/update/pause one heartbeat; write state | None | None |
| Phase Gate | Read | Reuse Watchdog heartbeat | None by itself | Exact named phase, once, after matching approval |
| Watch and Fix | Read | Reuse Watchdog heartbeat | Low-risk actions inside `auto_low_risk` policy | None |

`Read-only` means read-only toward the monitored target. Watchdog may change
only its monitoring-plane state: the heartbeat, the state file, plan Approvals
and History, and reports. It may not change the training job, remote
scheduler, environment, code, configuration, artifacts, credentials, or
external destinations.

When Phase Gate and Watch and Fix compose, low-risk recovery operates only
inside the current approved phase. It never grants the next-phase launch.

## Independent state dimensions

Do not mix these dimensions:

- **Job state:** `RUNNING`, `FINISHED`, `FAILED`, or `STOPPED`.
- **Health:** `HEALTHY`, `DEGRADED`, `STALLED`, or `AMBIGUOUS`.
- **Controller state:** `ACTIVE`, `SLEEP`, `RECOVERING`,
  `AWAITING_USER_APPROVAL`, or `PAUSED`.
- **Cadence Mode:** `ACTIVE` at 10 minutes, `RELAXED` at 30 minutes, or
  `SLEEP` at 60 minutes.

A running job may be stalled or degraded. `AWAITING_USER_APPROVAL` is a
controller state, not a job outcome.

## Policy transitions

- Watchdog transfers a failed or stalled target to Watch and Fix automatically
  only when the plan already says `auto_low_risk`.
- Without that authorization, Watchdog preserves evidence, pauses, and asks
  once whether to enable recovery.
- Watch and Fix returns a recovered multi-phase job to Phase Gate before any
  later phase.
- Phase Gate may launch the exact approved next phase once, record the new
  target identities in History, and reactivate the same heartbeat.
- The user may switch between `observe_only` and `auto_low_risk`, or between
  Cadence Modes, at any point. Preserve the Target Key, cursor, and heartbeat
  identity; a recovery-policy change bumps the Plan Revision.

## Heartbeat lifecycle

One Watchdog-owned heartbeat per Target Key:

1. Create it only for a recurring monitoring request, after the Run Plan is
   written and the approval rule is satisfied.
2. Record its identity in `state.json`; `start` reuses a recorded identity
   rather than creating a second heartbeat.
3. Reuse and update it when cadence, phase, or recovery state changes. Phase
   Gate, recovery, and sleep share it.
4. Pause it for `FINISHED`, `STOPPED`, `AWAITING_USER_APPROVAL`, a user
   request to stop monitoring, or a `FAILED` state that is not transferred to
   an authorized recovery loop. Set the controller state first, so a wake that
   still fires is a no-op wake.
5. Reactivate it only when the same Run Plan resumes or an approved next phase
   receives new exact identities.

## Outcome reports

Every `FINISHED`, `FAILED`, or `STOPPED` classification produces one
user-facing report, appends to History, and pauses or explicitly transfers the
heartbeat. Each report names the state directory as preserved evidence.

- `FINISHED`: short report with passed checks, artifact identities, elapsed
  duration when available, and next action.
- `FAILED`: actionable report with first relevant failure evidence, last known
  good progress, likely cause and confidence, affected artifacts, recovery
  eligibility, and exact next action.
- `STOPPED`: short report with who or what intentionally stopped the job when
  known, preserved work, latest safe resume point, and exact next action.
- Phase completion uses `Phase finished`, embeds the short finished report in
  the Gate Packet, and enters `AWAITING_USER_APPROVAL`.

An unexpected cancellation, timeout, preemption, or abnormal stop is
`FAILED`, not `STOPPED`, unless authoritative evidence proves completion.

A user request to **stop monitoring** pauses only the heartbeat and receives a
brief acknowledgement, not an outcome report. The underlying job may continue.

Keep evidence bounded. Name or link authoritative logs, manifests, revisions,
and scheduler identities instead of pasting large logs.
