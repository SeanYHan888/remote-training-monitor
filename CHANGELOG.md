# Changelog

All notable changes to Remote Training Monitor are documented here.

## Unreleased

- Replace the five state dimensions with three readable fields: one run
  lifecycle (`PLANNED`, `APPROVED`, `QUEUED`, `RUNNING`, `PASSED`, `FAILED`,
  `CANCELLED`), health while running (`FINE`, `SLOW`, `STALLED`, `UNKNOWN`)
  and the monitor (`WATCHING`, `RECOVERING`, `WAITING`, `OFF` with a reason).
  Wake mode and cadence become properties of the heartbeat. Old values are
  read through a mapping and rewritten on the next write (ADR 0002).
- Add `state.schema.json` and `scripts/validate_state.py`; every wake
  validates `state.json` after reading and before writing, and the heartbeat
  id is an id alone.
- Add `REPORT_FORMAT.md`: every wake, outcome, gate, recovery and cached
  status is one eight-line block (RUN, STATE, PROGRESS, CHECKS, HEALTH,
  CHANGED, MONITOR, NEXT) plus bounded evidence, and History gets one line per
  event.
- Add the `board` route, `BOARD_FORMAT.md` and `scripts/board.py`: a
  generated page of every run in a project in lanes (needs your decision,
  running, queued, planned, done, failed, invalid state files).
- Add Training signals to `ADAPTERS.md` with fine/slow/stalled bands, and a
  per-project `.remote-monitor/adapter.md` that caches commands, progress
  sources, the exit-check and approval sources, the history file and the
  planned-work source.
- Split the completion waiter into a queue stage (no deadline, exits when the
  job starts) and a run stage (deadline from start time, stall rule in
  shell), so a long queue wait no longer produces no-news wakes.
- Require exit checks to be copied into the plan verbatim; record a project's
  own approval artifact as the approval source instead of asking for a second
  approval; let the plan's History live in the project's per-run file.
- Add Wake Mode. `COMPLETION` arms one background waiter that wakes the agent
  when the job leaves its running states or a deadline passes, and is the
  default wherever the harness re-invokes the agent on a background command's
  exit (Claude Code). The 10/30/60-minute Cadence Modes move under `INTERVAL`,
  used for harnesses with no completion wake or on request.
- Record `wake_mode` in the Run Plan and `mode` plus `deadline` in the
  heartbeat state. Plans and state written before Wake Mode read as `INTERVAL`.
- Require `iterate` to reload and validate the plan before every observation.

## 0.1.0 - 2026-09-09

- Shorten discovery descriptions and route references by requested action.
- Detect scheduling capabilities without creating timers and verify heartbeat
  lifetime, identity, and execution directory.
- Keep monitor identity stable across attempts and terminate final phases
  without an extra approval gate.
- Add simulated behavioral evaluation cases and distinguish them from package
  validation and live integration checks.

- Package the router, read-only watchdog, phase gate, and bounded recovery
  workflow as one four-skill collection.
- Add skills.sh discovery metadata and a one-command collection install.
- Add a versioned Claude Code plugin and self-hosted marketplace definition.
- Add plan-first monitoring, harness-aware heartbeats, approval-gated phase
  transitions, and low-risk recovery boundaries.
