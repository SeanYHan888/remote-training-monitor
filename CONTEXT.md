# Remote Training Monitor

A set of agent skills for observing, gating, and recovering long-running remote jobs (training, inference, evaluation, data prep) from an AI coding harness such as Claude Code or Codex.

## Language

### Planning

**Run Plan**:
The single document, written before recurring monitoring starts, that describes a target job as named phases and states how it will be watched. It has two sections: the Phase Plan and the Monitoring Contract.
_Avoid_: plan (unqualified), training plan, spec

**Phase Plan**:
The section of a Run Plan listing each phase of the pipeline with its entry condition, exit checks, expected artifacts, and launch action.
_Avoid_: phase contract, pipeline, workflow

**Monitoring Contract**:
The section of a Run Plan stating the target identity, control plane, adapter, cadence mode, success/failure/stop evidence, recovery policy, retry budget, approval holder, and resource limits.
_Avoid_: monitoring plan, contract (unqualified)

**Phase**:
One named step of a pipeline with a declared entry condition, exit checks, and expected artifacts.
_Avoid_: step, stage

**Plan-first**:
The rule that any request which arms a heartbeat produces and presents a Run Plan before the first observation. A one-shot check does not.

**Plan Revision**:
A counter in the Run Plan that increments whenever phase semantics, resource envelope, or recovery policy change. Any standing Approval is bound to one revision and is void once it changes.
_Avoid_: version, edit

**Discovery**:
The read-only inspection of launch scripts, configs, working directory, logs, and artifacts that the planner performs to draft phases before asking the user anything.
_Avoid_: exploration, scan

### Target

**Target**:
The specific job, run, or process being monitored, resolved through its authoritative control plane.
_Avoid_: the training, the run (when identity matters)

**Target Key**:
The stable identifier for one monitored workflow, used to name its Run Plan, state, and heartbeat. Each phase launch or retry has a separate attempt identity; the Target Key persists across those attempts.
_Avoid_: job name, run name

**Control Plane**:
The scheduler or platform that owns the target's lifecycle and is authoritative for its state (Slurm, Kubernetes, Docker, systemd, a managed platform, or a plain process).
_Avoid_: backend, cluster

**Adapter**:
The observation recipe for one kind of control plane.

### Monitoring

**Harness**:
The agent runtime the skill is executing in: Claude Code, the Codex desktop app, or Codex CLI/IDE. Each offers different waiting mechanisms.
_Avoid_: platform, environment, client

**Heartbeat**:
The single wake mechanism for one Target Key: a Waiter, or an interval timer such as a Claude Code scheduled wakeup or cron routine or a Codex in-chat or standalone scheduled task.
_Avoid_: timer, automation, poller, cron (as a generic term)

**Wake Mode**:
How a heartbeat wakes the agent: `COMPLETION` (once, when the current attempt leaves its running states or the deadline passes) or `INTERVAL` (timed wakes at a Cadence Mode). `COMPLETION` is the default wherever the harness re-invokes the agent when a background command exits.
_Avoid_: polling mode, schedule type

**Waiter**:
The background shell command that provides a `COMPLETION` heartbeat. It polls the control plane without involving the agent and exits on a terminal state it actually read, on the deadline, or on a declared phase-exit or stall condition. Its exit prompts an Observation; it is never evidence of completion.
_Avoid_: watcher, poller, background monitor

**Cadence Mode**:
The interval of an `INTERVAL` heartbeat, expressed as one of three modes: `ACTIVE` (10 minutes), `RELAXED` (30 minutes), or `SLEEP` (60 minutes).
_Avoid_: deep sleep, poll interval, frequency

**Cursor**:
The bounded record of the last authoritative observation, used so the next heartbeat reads only new evidence.
_Avoid_: checkpoint (which means a model checkpoint here), offset

**Observation**:
One read-only inspection of the target that yields job state, health, evidence, and a new cursor.
_Avoid_: check, poll, tick

**Entry Point**:
One of the fixed verbs the router accepts so that a heartbeat prompt is unambiguous: `plan`, `start`, `iterate`, `status`, `approve`, `stop`, `wake`, `sleep`.
_Avoid_: command, subcommand, mode

**No-op Wake**:
An `iterate` that finds the controller paused in the state file and exits with one line, performing no Observation. It is the guaranteed backstop when a heartbeat cannot be paused.
_Avoid_: skipped tick, idle run

### Authority

**Recovery Policy**:
The authority granted for repairs: `observe_only` or `auto_low_risk`.

**Gate Packet**:
The compact evidence bundle presented at a phase boundary that a matching approval refers to.
_Avoid_: approval request, summary

**Approval**:
An explicit user statement that matches a specific Run Plan revision, Gate Packet, or high-risk repair. Never implied by phase completion or by the passage of time.
_Avoid_: confirmation, go-ahead, sign-off
