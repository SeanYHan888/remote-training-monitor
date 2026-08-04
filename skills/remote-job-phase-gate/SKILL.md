---
name: remote-job-phase-gate
description: Monitor a multi-phase job, verify each phase, and launch only the exact named next phase after explicit matching approval.
user-invocable: true
---

# Remote Job Phase Gate

**Purpose:** turn a multi-step remote job into a sequence of verified phases
with a human approval boundary between them.

## Composition

Read `../remote-training-monitor/CONTROL_CONTRACT.md`. Use **Remote Job
Watchdog** as the observer and heartbeat owner for the current phase. Phase
Gate does not repair failures. When the monitoring contract authorizes
`auto_low_risk`, **Remote Job Watch and Fix** may repair the current approved
phase and must return here before any later phase starts.

For recurring monitoring, use the single heartbeat owned by Watchdog. Do not
create a second Phase Gate timer. The heartbeat prompt carries the current
phase contract. Pause it at `AWAITING_USER_APPROVAL`; after approval, update
that same heartbeat for the newly approved phase and reactivate it.

Watchdog Sleep Mode may be used inside the currently approved phase. It changes
only the heartbeat cadence and never permits a phase transition. Exit Sleep
Mode before evaluating a phase boundary, and pause the heartbeat when the gate
enters `AWAITING_USER_APPROVAL`.

## Phase contract

Make explicit: each named phase; entry condition; exit checks; expected
artifacts; current phase; the exact proposed next phase and launch action;
resource envelope; approval holder; and gate-packet hash.

## Per-phase loop

1. Run Remote Job Watchdog for only the current phase.
2. When its exit checks pass, create a compact gate packet: phase name,
   evidence, artifact identities, checks run, failures or exclusions, exact
   next phase, exact launch action, resource impact, and packet hash.
3. Set `AWAITING_USER_APPROVAL`, deactivate the phase loop, and ask once for
   approval tied to that named phase and packet hash.
4. After matching approval, revalidate entry conditions, target identities,
   resource limits, and absence of duplicates.
5. Launch the exact approved next phase once, record its scheduler or process
   identities, update the phase contract, and reactivate the same heartbeat.

The exact approved launch is Phase Gate's only direct target-plane write. It
may not edit the launch payload, repair a failure, substitute another phase,
expand resources, or reuse approval for another attempt. If evidence, launch
action, resource impact, or packet hash changes, invalidate approval and
present a new gate.

If the phase fails, report it and wait. Do not start another phase or repair it
without the appropriate authorization.

## Phase outcome reports

Inherit the Watchdog outcome report contract for the current phase.

- On phase completion, title the report `Phase finished`, place the short
  `FINISHED` report inside the gate packet, add the exact proposed next phase,
  set `AWAITING_USER_APPROVAL`, and pause the heartbeat.
- On phase failure, provide the actionable Watchdog report, identify whether
  authorized Watch and Fix recovery is available, and either transfer the
  current phase under `auto_low_risk` or wait. Do not create a next-phase
  approval request while the current phase is unresolved.
- On an intentionally stopped phase, provide the short `Phase stopped` report
  with preserved work, the latest safe resume point, and the exact next action.
  Pause the heartbeat and do not create a next-phase approval request.
- If the user asks to stop monitoring, pause the heartbeat without generating
  a phase outcome report.
