# Remote Training Monitor

[![skills.sh](https://skills.sh/b/SeanYHan888/remote-training-monitor)](https://skills.sh/SeanYHan888/remote-training-monitor)

Remote Training Monitor is a four-skill toolkit for Claude Code and Codex that
plans, observes, gates, and recovers long-running remote jobs: training runs,
batch inference, evaluation sweeps, and any pipeline that outlives a chat
turn. It gives an AI coding agent a structured way to answer questions such as:

- "Is my training job still running?"
- "What progress has it made, and when will it finish?"
- "Did it finish successfully?"
- "Is it stalled or unhealthy?"
- "What is running, what is queued, what did we plan, and what needs me?"
- "Plan this pipeline and stop for my approval between phases."
- "Watch and fix routine failures within this approved scope."

Every answer has the same shape: an eight-line report (RUN, STATE, PROGRESS,
CHECKS, HEALTH, CHANGED, MONITOR, NEXT) for one run, or a board of every run
in the project in lanes.

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

Every monitor begins with a **Run Plan**, written before the heartbeat is
armed and stored at `.remote-monitor/<target-key>/` in the
project directory (kept out of git via the repository's local exclude file):

- `plan.md` holds the Phase Plan (each phase's entry condition, exit checks,
  artifacts, and launch action), the Monitoring Contract (identities, adapter,
  wake mode, evidence rules, recovery policy, limits), and append-only Approvals
  and History sections.
- `state.json` holds the run state, health, monitor, heartbeat identity,
  progress, check results, next action and cursor, so any wake can resume from
  disk and the board can be generated from it. Its shape is `state.schema.json`,
  and `scripts/validate_state.py` checks every read and write against it.
- An optional `.remote-monitor/adapter.md` caches, once per project, the exact
  observation commands, progress sources, exit-check and approval sources, and
  the project's own per-run history file, so every plan and wake reuses them.

The Target Key stays stable across phases and retries. Each new attempt records
its own job identity and artifact paths while reusing the monitor and heartbeat.

The plan is drafted from read-only discovery of launch scripts, configs, and
logs; the agent asks only for what it could not find. An observe-only plan
starts immediately after being shown. A plan with a launch action or
`auto_low_risk` recovery waits for approval, and approving it approves phase
1's launch by name. Later phases still gate individually. One-shot checks
("is job 12345 still running?") skip planning.

## Entry points

The router accepts fixed verbs so that a scheduled prompt is unambiguous:
`plan`, `start`, `iterate <key>`, `status <key>`, `board`,
`approve <key> <phase>`, `stop <key>`, `wake <key>`, `sleep <key>`. Every
heartbeat wake runs `iterate`, which validates and reads `state.json` first
and exits in one line when the monitor is waiting on the user or off. A wake
never re-plans and never adds a second heartbeat. `status <key>` reports
cached state with its timestamp; `board` (or `status` with no key) writes and
shows `.remote-monitor/BOARD.md`, every run in the project in lanes: needs
your decision, running, queued, planned, done, failed. "Monitor while I'm
away" starts or reuses monitoring; only an explicit request for periodic
check-ins selects timed wakes. `wake` and `sleep` apply to timed monitors
only.

A run moves through one lifecycle: `PLANNED` → `APPROVED` → `QUEUED` →
`RUNNING` → `PASSED`, `FAILED` or `CANCELLED`. `PASSED` means the plan's exit
checks passed, not that the scheduler said COMPLETED. While `RUNNING`, health
is `FINE`, `SLOW`, `STALLED` or `UNKNOWN`, computed from named training
signals (stage, step rate and ETA, loss, checkpoints, log age, restarts) with
default bands a plan may adjust. The monitor itself is `WATCHING`,
`RECOVERING`, `WAITING` on you, or `OFF` with a reason.

## Harnesses

The waiting mechanism is the only thing that differs between harnesses;
evidence rules, state files, and authority are identical.

| Harness | Mechanism |
| --- | --- |
| Claude Code | Completion wake: one background shell command waits for the job to end and the session is re-invoked when it exits. Session-bound. Timed wakes only on request. |
| Codex desktop app | Timed wakes on the current-task heartbeat by default; standalone scheduling only when requested. Verify access to the same plan directory. |
| Codex CLI / IDE | Completion wake if the runtime re-invokes the agent when a background command exits; otherwise an available scheduler or bounded session polling. Disclose session limits and offer operator-managed scheduling when needed. |

Capability detection is read-only. The heartbeat is armed after the plan and
any required approval; the agent verifies it rather than assuming it exists.

A monitor has one of two wake modes:

- `COMPLETION` (default where supported): a background waiter polls the
  scheduler in shell and wakes the agent when there is something to verify.
  Its queue stage has no deadline and exits when the job starts, so the agent
  can run an early health check; its run stage exits when the job leaves its
  running states, when the plan's stall rule fires, or at a deadline counted
  from the start time. One waiter covers every run a session watches; for
  Slurm it is the bundled `scripts/slurm_waiter.py`, which reads times in UTC
  and asks `sacct` about jobs `squeue` has dropped. A long job costs two or
  three agent turns. A crash
  wakes the agent at once; a hang is noticed by the stall rule, or at the
  deadline when the plan has none.
- `INTERVAL`: timed wakes at a Cadence, for harnesses with no completion wake
  or when you ask for periodic check-ins. `ACTIVE` (10 min) when under about
  an hour remains, the job is unstable, or a phase boundary is near;
  `RELAXED` (30 min) otherwise; `SLEEP` (60 min) only when you ask.

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
  competing timers or waiters.
- Recovery inside a multi-phase workflow is limited to the currently approved
  phase.
- Destructive, scientific, architectural, credential, publication, and
  resource-expanding changes require explicit approval.
- Stopping monitoring does not stop the underlying job.
- The `.remote-monitor/<target-key>/` directory is preserved after every
  terminal state as evidence.

The shared [control contract](skills/remote-training-monitor/CONTROL_CONTRACT.md)
defines the run lifecycle, health, the monitor states and the authority
planes. The [report format](skills/remote-training-monitor/REPORT_FORMAT.md)
fixes the eight-line shape of every report, and the
[board format](skills/remote-training-monitor/BOARD_FORMAT.md) the generated
page of every run. The [harness guide](skills/remote-training-monitor/HARNESSES.md)
selects the waiting mechanism. The [plan format](skills/remote-training-monitor/PLAN_FORMAT.md)
and [examples](skills/remote-training-monitor/PLAN_EXAMPLES.md) define the Run
Plan, the project adapter and `state.json`. The
[adapter guide](skills/remote-training-monitor/ADAPTERS.md) identifies the
authoritative control plane for each target type and defines the training
signals health is computed from. The
[recovery risk policy](skills/remote-training-monitor/RISK_POLICY.md) separates
bounded automatic repairs from approval-required changes.

## How it works

When invoked to watch a job, the router:

1. Resolves the entry point and detects the harness.
2. Resolves a stable Target Key and the job's authoritative control plane.
3. Runs read-only discovery and writes the Run Plan; presents it and applies
   the approval rule.
4. Arms one heartbeat via Watchdog and layers Phase Gate or Watch and Fix only
   when the plan grants the corresponding authority.
5. On every wake, validates and reads `state.json`, observes bounded new
   evidence and the training signals, and writes the run state, health,
   progress, checks and next action back. Under `COMPLETION` the wakes are
   normally the job starting and the job ending.
6. Produces one eight-line report and sets the monitor off, or waiting on
   you, when the job passes, fails, is cancelled, or reaches an approval gate.

The final phase produces an overall completion report after all required
outcomes and artifacts are verified. It does not request next-phase approval.

## Installation

Choose one installation method. Installing through both methods gives Claude
Code duplicate copies of the same skills.

### skills.sh (Codex, Claude Code, and other agents)

Install the complete four-skill toolkit:

```bash
npx skills@latest add SeanYHan888/remote-training-monitor --skill '*'
```

The router composes the three companion skills and their shared control files,
so partial installation is not supported.

The installer lets you choose which supported agents receive the skills. Use
`npx skills update` later to pull a newer version.

### Claude Code plugin

Add this repository as a marketplace, then install the managed bundle:

```text
/plugin marketplace add SeanYHan888/remote-training-monitor
/plugin install remote-training-monitor@seanyhan888-skills
```

Plugin skills use Claude Code's namespace. Invoke the router explicitly as
`/remote-training-monitor:remote-training-monitor`, or describe the monitoring
task in natural language.

### Manual source installation

Clone the repository when you want to inspect or modify the skills directly,
then link each directory under `skills/` into your agent's skill directory.
Restart the harness after a manual install so it discovers all four skills.

To update later:

```bash
git -C /path/to/remote-training-monitor pull --ff-only
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
What is running right now, what is queued, and what needs my decision?
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
├── .claude-plugin/                 # Claude Code bundle metadata
├── .github/workflows/              # Distribution validation CI
├── CHANGELOG.md
├── RELEASING.md
├── scripts/validate-release.sh     # Local and CI release checks
├── skills.sh.json                 # skills.sh page grouping
├── README.md
├── CONTEXT.md                       # Glossary of the terms the skills use
├── LICENSE
├── docs/adr/                        # Architecture decision records
└── skills/
    ├── remote-training-monitor/
    │   ├── SKILL.md                 # Entry points, plan-first, routing
    │   ├── CONTROL_CONTRACT.md      # Run lifecycle, health, monitor, authority
    │   ├── REPORT_FORMAT.md         # The eight-line report every wake produces
    │   ├── BOARD_FORMAT.md          # The generated board of every run
    │   ├── HARNESSES.md             # Claude Code vs Codex waiting mechanisms
    │   ├── PLAN_FORMAT.md           # Run Plan, project adapter, state.json
    │   ├── PLAN_EXAMPLES.md         # Finished plans to copy
    │   ├── ADAPTERS.md              # Control-plane observation and training signals
    │   ├── RISK_POLICY.md           # Recovery risk classification
    │   ├── state.schema.json        # Shape of state.json
    │   ├── scripts/
    │   │   ├── validate_state.py    # Checks a state.json against the schema
    │   │   └── board.py             # Renders the board from every state.json
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
- Resolve uncertainty with bounded read-only evidence; request approval when
  a proposed action exceeds the established authority.

## Validation

`bash scripts/validate-release.sh` checks package structure and discovery.
The behavioral scenarios in [evals/README.md](evals/README.md) exercise routing,
approval gates, completion, and recovery using simulated evidence. Record
results separately: neither packaging checks nor simulations establish live
scheduler or cluster reliability.

## License

This project is available under the [MIT License](LICENSE).
