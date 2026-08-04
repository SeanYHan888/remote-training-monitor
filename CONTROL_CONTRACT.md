# Remote Training Control Contract

This is the shared interface for Watchdog, Phase Gate, and Watch and Fix. Read
it once per invocation before applying a route-specific policy.

Throughout these skills, a **heartbeat** is the harness's single recurring
monitoring automation for a target: in Codex, a heartbeat automation; in
Claude Code, a scheduled wakeup, cron routine, or background monitor serving
the same role. The lifecycle rules below apply to whichever mechanism the
current harness provides.

## Monitoring contract

Resolve and record:

- stable target key, exact job or run identities, working directory, and owner;
- authoritative control plane and observation adapter;
- current phase, declared entry condition, exit checks, and expected artifacts;
- success, failure, and intentional-stop evidence;
- progress cursor and last authoritative observation;
- cadence mode, heartbeat durability, and the single heartbeat automation
  identity;
- recovery policy: `observe_only` or `auto_low_risk`;
- retry budget, rollback point requirements, and verification checks;
- approval holder and exact approval-gated phase transitions; and
- resource, cost, storage, publication, and destructive-action limits.

The stable target key must distinguish different attempts. Never reuse a
heartbeat, checkpoint, output path, upload revision, or job identity merely
because two jobs have similar names.

## Authority planes

| Policy | Target observation | Monitoring control | Target recovery | Phase launch |
| --- | --- | --- | --- | --- |
| Watchdog | Read | Create/update/pause one heartbeat; save cursor | None | None |
| Phase Gate | Read | Reuse Watchdog heartbeat | None by itself | Exact named phase, once, after matching approval |
| Watch and Fix | Read | Reuse Watchdog heartbeat | Low-risk actions inside `auto_low_risk` policy | None |

`Read-only` means read-only toward the monitored target. Watchdog may change
only its monitoring-plane state: the Codex or Claude Code heartbeat, progress cursor, and
reports. It may not change the training job, remote scheduler, environment,
code, configuration, artifacts, credentials, or external destinations.

When Phase Gate and Watch and Fix compose, low-risk recovery may operate only
inside the current approved phase. It never grants the next-phase launch.

## Independent state dimensions

Do not mix these dimensions:

- **Job state:** `RUNNING`, `FINISHED`, `FAILED`, or `STOPPED`.
- **Health:** `HEALTHY`, `DEGRADED`, `STALLED`, or `AMBIGUOUS`.
- **Controller state:** `ACTIVE`, `SLEEP`, `RECOVERING`,
  `AWAITING_USER_APPROVAL`, or `PAUSED`.
- **Cadence:** active adaptive `10`, `15`, or `20` minutes; `SLEEP` at
  `60` minutes; or explicit `DEEP_SLEEP` at `90` minutes.

A running job may be stalled or degraded. `AWAITING_USER_APPROVAL` is a
controller state, not a job outcome.

## Policy transitions

- Watchdog may transfer a failed or stalled target to Watch and Fix
  automatically only when the monitoring contract already says
  `auto_low_risk`.
- Without that authorization, Watchdog preserves evidence, pauses, and asks
  once whether to enable recovery.
- Watch and Fix returns a recovered multi-phase job to Phase Gate before any
  later phase.
- Phase Gate may launch the exact approved next phase once, record the new
  target identities, and reactivate the same heartbeat.
- The user may switch between `observe_only` and `auto_low_risk`, or between
  active and sleep cadence, at any point. Preserve the target key, cursor, and
  heartbeat identity.

## Heartbeat lifecycle

Use one Watchdog-owned heartbeat (a Codex heartbeat automation, or a Claude
Code scheduled wakeup or cron routine) per stable target key:

1. Create it only for a recurring monitoring request.
2. Reuse and update it when cadence, phase, or recovery state changes.
3. Never create a separate Phase Gate, recovery, or sleep timer.
4. Pause it for `FINISHED`, `STOPPED`, `AWAITING_USER_APPROVAL`, a user
   request to stop monitoring, or a `FAILED` state that is not transferred to
   an authorized recovery loop.
5. Reactivate it only when the same target contract resumes or an approved next
   phase receives new exact identities.

## Outcome reports

Every `FINISHED`, `FAILED`, or `STOPPED` classification produces one
user-facing report and pauses or explicitly transfers the heartbeat.

- `FINISHED`: short report with passed checks, artifact identities, elapsed
  duration when available, and next action.
- `FAILED`: actionable report with first relevant failure evidence, last known
  good progress, likely cause and confidence, affected artifacts, recovery
  eligibility, and exact next action.
- `STOPPED`: short report with who or what intentionally stopped the job when
  known, preserved work, latest safe resume point, and exact next action.
- Phase completion uses `Phase finished`, embeds the short finished report in
  the gate packet, and enters `AWAITING_USER_APPROVAL`.

An unexpected cancellation, timeout, preemption, or abnormal stop is
`FAILED`, not `STOPPED`, unless authoritative evidence proves completion.

A user request to **stop monitoring** pauses only the heartbeat and receives a
brief acknowledgement, not an outcome report. The underlying job may continue.

Keep evidence bounded. Name or link authoritative logs, manifests, revisions,
and scheduler identities instead of pasting large logs.
