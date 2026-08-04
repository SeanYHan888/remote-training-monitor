# Remote Training Monitor

Remote Training Monitor is a four-skill Codex toolkit for safely observing,
gating, and recovering long-running training jobs and pipelines. It gives an AI
coding agent a structured way to answer questions such as:

- “Is my training job still running?”
- “What progress has it made?”
- “Did it finish successfully?”
- “Is it stalled or unhealthy?”
- “Watch this pipeline and stop before the next phase.”
- “Watch and fix routine failures within this approved scope.”

The toolkit supports Slurm, Kubernetes, Docker/Podman, systemd, managed
training platforms, generic processes, and custom batch systems.

## What kind of project is this?

This repository contains **agent skills**, not a standalone monitoring service
or dashboard. A skill is a directory of Markdown instructions and metadata
that teaches Codex when to activate a workflow, which evidence to inspect,
what actions are allowed, and where it must stop for human approval.

`remote-training-monitor` is the user-facing router. It selects and composes
three companion skills while defaulting ambiguous requests to read-only
observation:

| Skill | Role | Target authority |
| --- | --- | --- |
| [`remote-training-monitor`](skills/remote-training-monitor/) | Detect intent and compose the policies | No independent target writes |
| [`remote-job-watchdog`](skills/remote-job-watchdog/) | Observe state, progress, health, logs, and artifacts | Read-only |
| [`remote-job-phase-gate`](skills/remote-job-phase-gate/) | Verify phase completion and launch one exact next phase | Matching approval required |
| [`remote-job-watch-and-fix`](skills/remote-job-watch-and-fix/) | Diagnose and retry proven low-risk failures | Explicit `auto_low_risk` authorization required |

## Safety model

The skills form a safety ladder rather than one all-powerful monitor:

```text
remote-training-monitor (intent router)
              |
              v
remote-job-watchdog (read-only foundation and one heartbeat)
              |
              +--> remote-job-phase-gate (approval-bound phase launch)
              |
              +--> remote-job-watch-and-fix (authorized low-risk recovery)
```

Important defaults:

- Monitoring is read-only toward the target job unless the user grants more
  authority.
- A detected bug does not grant permission to fix it.
- Completing one phase does not grant permission to start the next phase.
- Phase Gate and Watch and Fix reuse the Watchdog heartbeat; they do not create
  competing timers.
- Recovery inside a multi-phase workflow is limited to the currently approved
  phase.
- Destructive, scientific, architectural, credential, publication, and
  resource-expanding changes require explicit approval.
- Stopping monitoring does not stop the underlying job.

The shared [control contract](skills/remote-training-monitor/CONTROL_CONTRACT.md)
defines job, health, controller, cadence, and outcome states. The
[adapter guide](skills/remote-training-monitor/ADAPTERS.md) identifies the
authoritative control plane for each target type. The
[recovery risk policy](skills/remote-training-monitor/RISK_POLICY.md) separates
bounded automatic repairs from approval-required changes.

## How it works

When invoked, the router:

1. Resolves a stable job identity and its authoritative control plane.
2. Chooses the matching observation adapter.
3. Records a monitoring contract: expected outputs, success and failure
   evidence, cadence, retry limits, approval gates, and resource boundaries.
4. Activates Watchdog and layers Phase Gate or Watch and Fix only when the
   request grants the corresponding authority.
5. Keeps job state, health, controller state, and monitoring cadence separate.
6. Uses bounded logs and authoritative scheduler or platform evidence.
7. Produces a concise terminal report and pauses monitoring when the job
   finishes, fails, stops, or reaches an approval gate.

The risk policy permits automatic recovery only when evidence supports the
cause, the repair preserves the approved experiment meaning, the action is
reversible or additive, identities are verified, and the work stays inside a
bounded retry and resource envelope.

## Installation

Clone the collection outside the active skills directory, then link each skill
into `~/.codex/skills`:

```bash
mkdir -p ~/.codex/skill-sources ~/.codex/skills
git clone https://github.com/SeanYHan888/remote-training-monitor.git \
  ~/.codex/skill-sources/remote-training-monitor

ln -s ~/.codex/skill-sources/remote-training-monitor/skills/remote-training-monitor \
  ~/.codex/skills/remote-training-monitor
ln -s ~/.codex/skill-sources/remote-training-monitor/skills/remote-job-watchdog \
  ~/.codex/skills/remote-job-watchdog
ln -s ~/.codex/skill-sources/remote-training-monitor/skills/remote-job-phase-gate \
  ~/.codex/skills/remote-job-phase-gate
ln -s ~/.codex/skill-sources/remote-training-monitor/skills/remote-job-watch-and-fix \
  ~/.codex/skills/remote-job-watch-and-fix
```

If any destination already exists, compare or remove that existing installation
before creating its link. Restart Codex after installation so it discovers all
four skills.

To update later:

```bash
git -C ~/.codex/skill-sources/remote-training-monitor pull --ff-only
```

## Usage

Invoke the router explicitly:

```text
Use $remote-training-monitor to check Slurm job 12345 and report its progress.
```

Or use natural language matching its trigger description:

```text
Watch this training run and tell me when it finishes. Do not change anything.
```

```text
Monitor this three-phase pipeline. After each phase, stop and wait for my
approval before launching the next one.
```

```text
Watch and fix routine failures, but do not change the model, data,
hyperparameters, evaluation, GPU count, or publication destination.
```

For best results, provide the job ID or run ID, working directory, control
plane, expected artifacts, and explicit limits on cost, retries, storage, and
external writes.

## Repository layout

```text
remote-training-monitor/
├── README.md
├── LICENSE
└── skills/
    ├── remote-training-monitor/
    │   ├── SKILL.md                 # Trigger rules and capability routing
    │   ├── CONTROL_CONTRACT.md      # Shared states, authority, lifecycle
    │   ├── ADAPTERS.md              # Target-specific observation guidance
    │   ├── RISK_POLICY.md           # Recovery risk classification
    │   └── agents/
    │       └── openai.yaml          # Codex display metadata
    ├── remote-job-watchdog/
    │   └── SKILL.md                 # Read-only observer and heartbeat owner
    ├── remote-job-phase-gate/
    │   └── SKILL.md                 # Approval-gated phase transitions
    └── remote-job-watch-and-fix/
        └── SKILL.md                 # Bounded low-risk recovery
```

## Design principles

- Prefer the scheduler or platform that owns the job lifecycle over indirect
  telemetry.
- Treat SSH as transport, not as the source of truth.
- Verify exact identities before reading, retrying, or publishing anything.
- Preserve original failures and use unique retry identities.
- Keep logs bounded and point to authoritative artifacts instead of pasting
  large outputs.
- When evidence or impact is uncertain, stop and ask.

## License

This project is available under the [MIT License](LICENSE).
