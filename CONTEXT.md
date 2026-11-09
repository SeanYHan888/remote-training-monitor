# Remote Training Monitor

A set of agent skills for observing, gating, and recovering long-running remote jobs (training, inference, evaluation, data prep) from an AI coding harness such as Claude Code or Codex.

## Language

### Planning

**Run Plan**:
The single document, written before recurring monitoring starts, that describes a target job as named phases and states how it will be watched. It has two sections: the Phase Plan and the Monitoring Contract.
_Avoid_: plan (unqualified), training plan, spec

**Phase Plan**:
The section of a Run Plan listing each phase of the pipeline with its entry condition, exit checks, expected artifacts, and launch action. Exit checks are written out in full; a pointer to another file is not an exit check.
_Avoid_: phase contract, pipeline, workflow

**Monitoring Contract**:
The section of a Run Plan stating the target identity, control plane, adapter, Training signals, wake mode, success/failure/stop evidence, recovery policy, retry budget, approval source and holder, and resource limits.
_Avoid_: monitoring plan, contract (unqualified)

**Phase**:
One named step of a pipeline with a declared entry condition, exit checks, and expected artifacts.
_Avoid_: step, stage (which means an application-reported progress marker here)

**Plan-first**:
The rule that any request which arms a heartbeat produces and presents a Run Plan before the first observation. A one-shot check does not.

**Plan Revision**:
A counter in the Run Plan that increments whenever phase semantics, resource envelope, or recovery policy change. Any standing Approval is bound to one revision and is void once it changes.
_Avoid_: version, edit

**Discovery**:
The read-only inspection of launch scripts, configs, working directory, logs, and artifacts that the planner performs to draft phases before asking the user anything.
_Avoid_: exploration, scan

**Project Adapter**:
The optional `.remote-monitor/adapter.md` that caches, once per project, the exact observation commands, progress sources, exit-check source, approval source, history file and planned-work source Discovery found. Read-only toward the project.
_Avoid_: config, settings

**Approval Source**:
The project's own artifact that an approval refers to when the project has one, such as a frozen packet whose hash the user replies with. The Run Plan imports its exit checks and records it instead of asking for a second approval of the same scope.
_Avoid_: packet (outside a project that uses that word)

### Target

**Target**:
The specific job, run, or process being monitored, resolved through its authoritative control plane.
_Avoid_: the training, the run (when identity matters)

**Target Key**:
The stable identifier for one monitored workflow, used to name its Run Plan, state, and heartbeat. Each phase launch or retry has a separate attempt identity; the Target Key persists across those attempts.
_Avoid_: job name, run name (which is the human label shown on reports and the board)

**Control Plane**:
The scheduler or platform that owns the target's lifecycle and is authoritative for its state (Slurm, Kubernetes, Docker, systemd, a managed platform, or a plain process).
_Avoid_: backend, cluster

**Adapter**:
The observation recipe for one kind of control plane.

### State

**Run State**:
The one lifecycle of a monitored run: `PLANNED`, `APPROVED`, `QUEUED`, `RUNNING`, `PASSED`, `FAILED`, `CANCELLED`. `PASSED` means the exit checks passed, not that the scheduler said COMPLETED. `CANCELLED` means the user asked for the stop.
_Avoid_: job state, FINISHED, STOPPED, DONE, status (unqualified)

**Health**:
How a `RUNNING` job is doing, computed from Training signals: `FINE`, `SLOW`, `STALLED`, `UNKNOWN`. Null outside `RUNNING`.
_Avoid_: HEALTHY, DEGRADED, AMBIGUOUS, "looks fine"

**Training Signals**:
The measured quantities health is computed from: stage, step rate and ETA, loss, checkpoints, log age, restarts, each with fine/slow/stalled bands in `ADAPTERS.md` that a plan may adjust.
_Avoid_: vibes, progress (unqualified)

**Monitor**:
What the monitor itself is doing, as opposed to the job: `WATCHING`, `RECOVERING`, `WAITING` (on the user), `OFF` with a reason (`draft`, `terminal`, `stopped`, `needs-decision`).
_Avoid_: controller state, ACTIVE, PAUSED, AWAITING_USER_APPROVAL, DONE

### Monitoring

**Harness**:
The agent runtime the skill is executing in: Claude Code, the Codex desktop app, or Codex CLI/IDE. Each offers different waiting mechanisms.
_Avoid_: platform, environment, client

**Heartbeat**:
The single wake mechanism for one Target Key: a Waiter (which the Target Keys one session watches share), or an interval timer such as a Claude Code scheduled wakeup or cron routine or a Codex in-chat or standalone scheduled task. Its id is recorded alone in `state.json`; its history is History.
_Avoid_: timer, automation, poller, cron (as a generic term)

**Wake Mode**:
How a heartbeat wakes the agent: `COMPLETION` (when the job starts, when the attempt leaves its running states, on a stall rule, or at the deadline) or `INTERVAL` (timed wakes at a Cadence). `COMPLETION` is the default wherever the harness re-invokes the agent when a background command exits.
_Avoid_: polling mode, schedule type

**Waiter**:
The background shell command that provides a `COMPLETION` heartbeat. It has a queue stage (exits when the job starts; backstop only) and a run stage (exits on a terminal state it read, a stall rule, or a deadline counted from the start time). One Waiter covers every Target Key a session watches, each in its own stage; for Slurm it is the bundled `scripts/slurm_waiter.py`. Its exit prompts an Observation; it is never evidence of completion.
_Avoid_: watcher, poller, background monitor

**Cadence**:
The interval of an `INTERVAL` heartbeat: `ACTIVE` (10 minutes), `RELAXED` (30 minutes), or `SLEEP` (60 minutes). A property of the heartbeat, changed by `sleep` and `wake`; never a state of the run or the monitor.
_Avoid_: cadence mode, deep sleep, poll interval, frequency

**Cursor**:
The bounded record of the last authoritative observation, used so the next heartbeat reads only new evidence.
_Avoid_: checkpoint (which means a model checkpoint here), offset

**Observation**:
One read-only inspection of the target that yields run state, health, progress, check results, evidence, and a new cursor.
_Avoid_: check, poll, tick

**Report**:
The eight-line block (`RUN`, `STATE`, `PROGRESS`, `CHECKS`, `HEALTH`, `CHANGED`, `MONITOR`, `NEXT`) plus bounded evidence that every wake, outcome, gate and recovery produces, in `REPORT_FORMAT.md`. One run per Report.
_Avoid_: update, summary, status message

**History Line**:
The one dated line a Report appends to the plan's History (or the project's history file): the STATE line and the NEXT line. Never the whole Report.
_Avoid_: log entry, note

**Board**:
The generated page of every run in a project, in lanes (needs your decision, running, queued, planned, done, failed), built by `scripts/board.py` from every `state.json`. In `BOARD_FORMAT.md`.
_Avoid_: dashboard, overview, status page

**Entry Point**:
One of the fixed verbs the router accepts so that a heartbeat prompt is unambiguous: `plan`, `start`, `iterate`, `status`, `board`, `approve`, `stop`, `wake`, `sleep`.
_Avoid_: command, subcommand, mode

**No-op Wake**:
An `iterate` that finds the monitor `WAITING` or `OFF` in the state file and exits with one line, performing no Observation. It is the guaranteed backstop when a heartbeat cannot be paused.
_Avoid_: skipped tick, idle run

### Authority

**Recovery Policy**:
The authority granted for repairs: `observe_only` or `auto_low_risk`.

**Gate Packet**:
The compact evidence bundle presented at a phase boundary that a matching approval refers to.
_Avoid_: approval request, summary

**Approval**:
An explicit user statement that matches a specific Run Plan revision, Approval Source hash, Gate Packet, or high-risk repair. Never implied by phase completion or by the passage of time.
_Avoid_: confirmation, go-ahead, sign-off
