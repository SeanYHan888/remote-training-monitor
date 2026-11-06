# Changelog

All notable changes to Remote Training Monitor are documented here.

## Unreleased

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
