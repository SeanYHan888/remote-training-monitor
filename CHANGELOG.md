# Changelog

All notable changes to Remote Training Monitor are documented here.

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
