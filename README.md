# Remote Training Monitor

Remote Training Monitor is a Codex skill for safely observing long-running
training jobs and pipelines. It gives an AI coding agent a structured way to
answer questions such as:

- “Is my training job still running?”
- “What progress has it made?”
- “Did it finish successfully?”
- “Is it stalled or unhealthy?”
- “Watch this pipeline and stop before the next phase.”
- “Watch and fix routine failures within this approved scope.”

The skill supports Slurm, Kubernetes, Docker/Podman, systemd, managed training
platforms, generic processes, and custom batch systems.

## What kind of project is this?

This repository contains an **agent skill**, not a standalone monitoring
service or dashboard. A skill is a directory of Markdown instructions and
metadata that teaches Codex when to activate a workflow, which evidence to
inspect, what actions are allowed, and where it must stop for human approval.

Remote Training Monitor is the entry-point and policy router for a composable
monitoring workflow. It defaults to read-only observation when the user's
intent is ambiguous.

## Safety model

The skill separates three levels of authority:

| Capability | Purpose | May change the training job? |
| --- | --- | --- |
| Watchdog | Observe state, progress, health, logs, and artifacts | No |
| Phase Gate | Launch one exact approved next phase | Only after matching approval |
| Watch and Fix | Repair and retry proven low-risk failures | Only when explicitly authorized |

These capabilities compose in one direction:

```text
Read-only observation
        |
        +--> approval-gated phase launches
        |
        +--> explicitly authorized low-risk recovery
```

Important defaults:

- Monitoring is read-only toward the target job unless the user grants more
  authority.
- A detected bug does not grant permission to fix it.
- Completing one phase does not grant permission to start the next phase.
- Destructive, scientific, architectural, credential, publication, and
  resource-expanding changes require explicit approval.
- Stopping monitoring does not stop the underlying job.

## How it works

When invoked, the skill:

1. Resolves a stable job identity and its authoritative control plane.
2. Chooses the matching observation adapter.
3. Records a monitoring contract: expected outputs, success and failure
   evidence, cadence, retry limits, approval gates, and resource boundaries.
4. Keeps job state, health, controller state, and monitoring cadence separate.
5. Uses bounded logs and authoritative scheduler or platform evidence.
6. Produces a concise terminal report and pauses monitoring when the job
   finishes, fails, stops, or reaches an approval gate.

The included risk policy allows automatic recovery only when the cause is
supported by evidence, the repair preserves the approved experiment meaning,
the action is reversible or additive, identities are verified, and the work
stays inside a bounded retry and resource envelope.

## Installation

Clone the repository into your personal Codex skills directory:

```bash
git clone https://github.com/SeanYHan888/remote-training-monitor.git \
  ~/.codex/skills/remote-training-monitor
```

Restart Codex after installation so it discovers the skill.

The router is designed to compose with these companion skills when they are
installed:

- `remote-job-watchdog`
- `remote-job-phase-gate`
- `remote-job-watch-and-fix`

Without the companions, this repository still provides the shared monitoring,
adapter, and recovery-policy contracts, but the specialized workflows are not
packaged here.

## Usage

You can invoke the skill explicitly:

```text
Use $remote-training-monitor to check Slurm job 12345 and report its progress.
```

Or use natural language that matches its trigger description:

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

For the best results, provide the job ID or run ID, working directory, control
plane, expected artifacts, and any explicit limits on cost, retries, storage,
or external writes.

## Repository layout

```text
remote-training-monitor/
├── SKILL.md                 # Trigger rules and capability routing
├── CONTROL_CONTRACT.md      # Shared states, authority, and lifecycle rules
├── ADAPTERS.md              # Slurm, Kubernetes, container, and process checks
├── RISK_POLICY.md           # Low-risk versus approval-required recovery
└── agents/
    └── openai.yaml          # Codex display metadata and default prompt
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
