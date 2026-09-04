---
name: remote-job-phase-gate
description: Monitor a multi-phase job, verify each phase, and launch only the exact named next phase after explicit matching approval.
user-invocable: true
---

# Remote Job Phase Gate

**Purpose:** turn a multi-step remote job into a sequence of verified phases
with a human approval boundary between them.

## Composition

Read `../remote-training-monitor/CONTROL_CONTRACT.md`. The phases come from
the Run Plan's Phase Plan (`../remote-training-monitor/PLAN_FORMAT.md`); Phase
Gate never invents a phase the plan does not name. Use **Remote Job Watchdog**
as the observer and heartbeat owner for the current phase. Phase Gate does not
repair failures. When the plan authorizes `auto_low_risk`, **Remote Job Watch
and Fix** may repair the current approved phase and returns here before any
later phase starts.

Reuse the single Watchdog heartbeat. Pause it at `AWAITING_USER_APPROVAL`
after setting that controller state; after approval, update the same
heartbeat for the newly approved phase and reactivate it.

`SLEEP` may be used inside the currently approved phase; it changes only the
interval. Return to `ACTIVE` before evaluating a phase boundary.

## Approval

An Approval is appended to the plan's Approvals section as the user's words
plus the phase name or Plan Revision it matches.

- Approving the Run Plan approves phase 1's launch action by name. Every later
  phase gates individually.
- A phase whose launch action is "already running" has no gate before it.
- A changed Gate Packet, launch action, resource impact, or Plan Revision
  voids the standing approval; present a new gate.

## Per-phase loop

1. Run Remote Job Watchdog for only the current phase.
2. When its exit checks pass, create a compact Gate Packet: phase name,
   evidence, artifact identities, checks run, failures or exclusions, exact
   next phase, exact launch action, resource impact, and packet hash.
3. Set `AWAITING_USER_APPROVAL` in `state.json`, pause the heartbeat, and ask
   once for approval tied to that named phase and packet hash.
4. After matching approval, revalidate entry conditions, target identities,
   resource limits, and absence of duplicates.
5. Launch the exact approved next phase once, record its scheduler or process
   identities in History and `state.json`, advance `current_phase`, and
   reactivate the same heartbeat.

The exact approved launch is Phase Gate's only direct target-plane write. It
may not edit the launch payload, repair a failure, substitute another phase,
expand resources, or reuse approval for another attempt.

If the phase fails, report it and wait. Do not start another phase or repair it
without the appropriate authorization.

## Phase outcome reports

Inherit the Watchdog outcome report contract for the current phase.

- On phase completion, title the report `Phase finished`, place the short
  `FINISHED` report inside the Gate Packet, add the exact proposed next phase,
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
