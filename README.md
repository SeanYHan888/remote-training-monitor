# Remote Training Monitor

Remote Training Monitor is a four-skill toolkit for Claude Code and Codex that
plans, observes, gates, and recovers long-running remote jobs: training runs,
batch inference, evaluation sweeps, and any pipeline that outlives a chat
turn. It gives an AI coding agent a structured way to answer questions such as:

- "Is my training job still running?"
- "What progress has it made?"
- "Did it finish successfully?"
- "Is it stalled or unhealthy?"
- "Plan this pipeline and stop for my approval between phases."
- "Watch and fix routine failures within this approved scope."

The toolkit supports Slurm, Kubernetes, Docker/Podman, systemd, managed
training platforms, generic processes, and custom batch systems.

## What kind of project is this?

This repository contains **agent skills**, not a standalone monitoring service
or dashboard. A skill is a directory of Markdown instructions and metadata
that teaches an agent when to activate a workflow, which evidence to inspect,
what actions are allowed, and where it must stop for human approval.

`remote-training-monitor` is the user-facing router. It selects and composes
three companion skills while defaulting ambiguous requests to read-only
observation:

| Skill | Role | Target authority |
| --- | --- | --- |
| [`remote-training-monitor`](skills/remote-training-monitor/) | Detect intent, write the Run Plan, compose the policies | No independent target writes |
| [`remote-job-watchdog`](skills/remote-job-watchdog/) | Observe state, progress, health, logs, and artifacts | Read-only |
| [`remote-job-phase-gate`](skills/remote-job-phase-gate/) | Verify phase completion and launch one exact next phase | Matching approval required |
| [`remote-job-watch-and-fix`](skills/remote-job-watch-and-fix/) | Diagnose and retry proven low-risk failures | Explicit `auto_low_risk` authorization required |

## Plan-first

Every recurring watch begins with a **Run Plan**, written before the first
heartbeat is armed and stored at `.remote-monitor/<target-key>/` in the
project directory (kept out of git via `.git/info/exclude`):

- `plan.md` holds the Phase Plan (each phase's entry condition, exit checks,
  artifacts, and launch action), the Monitoring Contract (identities, adapter,
  cadence, evidence rules, recovery policy, limits), and append-only Approvals
  and History sections.
- `state.json` holds the cursor, controller state, heartbeat identity, and
  current phase, so any wake can resume from disk.

The plan is drafted from read-only discovery of launch scripts, configs, and
logs; the agent asks only for what it could not find. An observe-only plan
starts immediately after being shown. A plan with a launch action or
`auto_low_risk` recovery waits for approval, and approving it approves phase
1's launch by name. Later phases still gate individually. One-shot checks
("is job 12345 still running?") skip planning.

## Entry points

The router accepts fixed verbs so that a scheduled prompt is unambiguous:
`plan`, `start`, `iterate <key>`, `status <key>`, `approve <key> <phase>`,
`stop <key>`, `wake <key>`, `sleep <key>`. Every heartbeat wake runs
`iterate`, which reads `state.json` first and exits in one line when the
controller is paused or awaiting approval. A wake never re-plans and never
re-arms a heartbeat.

## Harnesses

The waiting mechanism is the only thing that differs between harnesses;
evidence rules, state files, and authority are identical.

| Harness | Durable heartbeat | Session-bound wait |
| --- | --- | --- |
| Claude Code | cron routine | background monitor or in-session scheduled wakeup |
| Codex desktop app | scheduled task inside the chat (must run in the project directory, not a worktree) | background terminal, five-minute polls |
| Codex CLI / IDE | none; the skill hands you a `codex exec` cron one-liner | bounded background-terminal polling, with disclosure that it ends with the session |

Cadence is one of three modes: `ACTIVE` (10 min) when under about an hour
remains, the job is unstable, or a phase boundary is near; `RELAXED` (30 min)
otherwise; `SLEEP` (60 min) only when you ask.

## Safety model

The skills form a safety ladder rather than one all-powerful monitor:

```text
remote-training-monitor (intent router, Run Plan author)
              |
              v
remote-job-watchdog (read-only foundation and one heartbeat)
              |
              +--> remote-job-phase-gate (approval-bound phase launch)
              |
              +--> remote-job-watch-and-fix (authorized low-risk recovery)
```

Important defaults:

- Monitoring is read-only toward the target job unless the Run Plan grants
  more authority.
- A detected bug does not grant permission to fix it.
- Completing one phase does not grant permission to start the next phase.
- Phase Gate and Watch and Fix reuse the Watchdog heartbeat; they do not create
  competing timers.
- Recovery inside a multi-phase workflow is limited to the currently approved
  phase.
- Destructive, scientific, architectural, credential, publication, and
  resource-expanding changes require explicit approval.
- Stopping monitoring does not stop the underlying job.
- The `.remote-monitor/<target-key>/` directory is preserved after every
  terminal state as evidence.

The shared [control contract](skills/remote-training-monitor/CONTROL_CONTRACT.md)
defines job, health, controller, and cadence states. The
[harness guide](skills/remote-training-monitor/HARNESSES.md) selects the
waiting mechanism. The [plan format](skills/remote-training-monitor/PLAN_FORMAT.md)
and [examples](skills/remote-training-monitor/PLAN_EXAMPLES.md) define the Run
Plan. The [adapter guide](skills/remote-training-monitor/ADAPTERS.md)
identifies the authoritative control plane for each target type. The
[recovery risk policy](skills/remote-training-monitor/RISK_POLICY.md) separates
bounded automatic repairs from approval-required changes.

## How it works

When invoked for a recurring watch, the router:

1. Resolves the entry point and detects the harness.
2. Resolves a stable Target Key and the job's authoritative control plane.
3. Runs read-only discovery and writes the Run Plan; presents it and applies
   the approval rule.
4. Arms one heartbeat via Watchdog and layers Phase Gate or Watch and Fix only
   when the plan grants the corresponding authority.
5. On every wake, reads `state.json`, observes bounded new evidence, and keeps
   job state, health, controller state, and cadence separate.
6. Produces a concise report and pauses monitoring when the job finishes,
   fails, stops, or reaches an approval gate.

## Installation

### Claude Code

```bash
mkdir -p ~/.claude/skill-sources ~/.claude/skills
git clone https://github.com/SeanYHan888/remote-training-monitor.git \
  ~/.claude/skill-sources/remote-training-monitor
for s in remote-training-monitor remote-job-watchdog remote-job-phase-gate remote-job-watch-and-fix; do
  ln -s ~/.claude/skill-sources/remote-training-monitor/skills/$s ~/.claude/skills/$s
done
```

### Codex

```bash
mkdir -p ~/.codex/skill-sources ~/.codex/skills
git clone https://github.com/SeanYHan888/remote-training-monitor.git \
  ~/.codex/skill-sources/remote-training-monitor
for s in remote-training-monitor remote-job-watchdog remote-job-phase-gate remote-job-watch-and-fix; do
  ln -s ~/.codex/skill-sources/remote-training-monitor/skills/$s ~/.codex/skills/$s
done
```

If any destination already exists, compare or remove that existing installation
before creating its link. Restart the harness after installation so it
discovers all four skills.

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
Plan this three-phase pipeline. After each phase, stop and wait for my
approval before launching the next one.
```

```text
Watch and fix routine failures, but do not change the model, data,
hyperparameters, evaluation, GPU count, or publication destination.
```

A scheduled task or cron entry uses the verb form:

```text
$remote-training-monitor iterate slurm-4821
```

For best results, provide the job ID or run ID, working directory, control
plane, expected artifacts, and explicit limits on cost, retries, storage, and
external writes. Anything you leave out, discovery tries to find; anything it
cannot find, the plan marks as a gap and asks about.

## Repository layout

```text
remote-training-monitor/
├── README.md
├── CONTEXT.md                       # Glossary of the terms the skills use
├── LICENSE
├── docs/adr/                        # Architecture decision records
└── skills/
    ├── remote-training-monitor/
    │   ├── SKILL.md                 # Entry points, plan-first, routing
    │   ├── CONTROL_CONTRACT.md      # Shared states, authority, lifecycle
    │   ├── HARNESSES.md             # Claude Code vs Codex waiting mechanisms
    │   ├── PLAN_FORMAT.md           # Run Plan and state.json schema
    │   ├── PLAN_EXAMPLES.md         # Finished plans to copy
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

- Plan before watching; the plan file is the context every wake resumes from.
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
