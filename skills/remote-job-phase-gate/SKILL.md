---
name: remote-job-phase-gate
description: Monitor a multi-phase job, verify each phase, and launch only the exact named next phase after explicit matching approval.
license: MIT
compatibility: Requires the complete four-skill Remote Training Monitor collection and an agent with filesystem and shell access.
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

Reuse the single Watchdog heartbeat. Pause it when the monitor becomes
`WAITING`, after setting that field; after approval, update the same
heartbeat for the newly approved phase and reactivate it. Under `COMPLETION`,
reactivating means arming the queue stage for the new phase's attempt.

`SLEEP` may be used inside the currently approved phase of an `INTERVAL`
monitor; it changes only the interval. Return to `ACTIVE` before evaluating a
phase boundary.

## Approval

An Approval is appended to the plan's Approvals section as the user's words
plus the phase name, Plan Revision or approval-artifact hash it matches.

- Approving the Run Plan, or the project's approval artifact that the plan
  names as its `approval_source`, approves phase 1's launch action by name.
  Every later phase gates individually.
- A phase whose launch action is "already running" has no gate before it.
- A changed Gate Packet, launch action, resource impact or Plan Revision
  voids the standing approval; present a new gate.

For a not-yet-launched phase 1, matching approval moves the run state to
`APPROVED` and leads directly to the entry-condition, identity, resource and
duplicate checks and the exact launch in steps 4–5 below. There is no
preceding phase to observe. Record the first attempt (run state `QUEUED`),
then establish the heartbeat through the pending `start` route. A plan-only
request still requires a request to start before execution.

## Per-phase loop

1. Run Remote Job Watchdog for only the current phase.
2. When its exit checks pass, create a compact Gate Packet: phase name,
   evidence, artifact identities, checks run, failures or exclusions, exact
   next phase, exact launch action, resource impact and packet hash.
   If this is the final phase, instead verify all required outcomes and
   artifacts, report the run `PASSED`, set the monitor `OFF (terminal)` and
   create no Gate Packet.
3. Set the monitor `WAITING` with the reason `approve <key> <next phase>
   (gate <hash prefix>)` in `state.json`, pause the heartbeat, and ask once
   for approval tied to that named phase and packet hash.
4. After matching approval, revalidate entry conditions, target identities,
   resource limits and absence of duplicates.
5. Launch the exact approved next phase once, record its scheduler or process
   identities under a new attempt in History and `state.json`, reset the
   observation cursor, advance `current_phase`, set the run state `QUEUED`
   with a new `since`, and reactivate the same heartbeat.

The exact approved launch is Phase Gate's only direct target-plane write. It
may not edit the launch payload, repair a failure, substitute another phase,
expand resources or reuse approval for another attempt.

If the phase fails, report it and wait. Do not start another phase or repair it
without the appropriate authorization.

## Phase reports

Every report uses the eight-line shape in
`../remote-training-monitor/REPORT_FORMAT.md`.

- On non-final phase completion, STATE reads `PHASE n PASSED`, NEXT reads
  `approve <key> <next phase>` with the Gate Packet hash, the packet's
  contents are the evidence lines, and MONITOR reads `waiting on you`.
- On final-phase completion, STATE reads `PASSED` for the run and MONITOR
  `off (terminal)`.
- On phase failure, provide the Watchdog `FAILED` report, name on NEXT whether
  authorized Watch and Fix recovery is available, and either transfer the
  current phase under `auto_low_risk` or set the monitor
  `OFF (needs-decision)`. Do not create a next-phase approval request while
  the current phase is unresolved.
- On an intentionally stopped phase, STATE reads `PHASE n CANCELLED`, the
  evidence lists preserved work and the latest safe resume point, and the
  monitor is `OFF (needs-decision)`. No next-phase approval request.
- If the user asks to stop monitoring, set the monitor `OFF (stopped)`
  without a phase report.
