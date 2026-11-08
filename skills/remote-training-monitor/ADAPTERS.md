# Target Observation Adapters

Read the single section matching the target's authoritative control plane,
then Training signals. When the project has `.remote-monitor/adapter.md`
(`PLAN_FORMAT.md`, "Project adapter"), its commands and sources replace the
generic ones here. SSH is transport, not authority: use it to run the selected
adapter on the remote host.

Every adapter must resolve a stable target identity, current lifecycle state,
bounded new logs, the Training signals below, terminal-state mapping and the
declared exit checks. Telemetry systems such as W&B are supporting evidence
unless they also own the job lifecycle.

## Lifecycle by control plane

### Slurm

- Resolve identity and current state with `squeue`, then
  `scontrol show job <job_id>`.
- Use `sacct -j <job_id> -X -n -o State,ExitCode,Elapsed,NodeList` for
  completed or failed jobs and steps.
- Resolve `StdOut` and `StdErr` from scheduler metadata before reading bounded
  output.
- While PENDING: `squeue -j <id> -o '%T %r %S'` gives the reason and the
  scheduler's start estimate; `sprio -j <id>` the priority and its parts.
- Treat the scheduler's terminal state as lifecycle-authoritative; also require
  every exit check named by the plan.

### Kubernetes

- Resolve identity and state with `kubectl get job|pod` and
  `kubectl describe`.
- Read bounded or timestamped output with `kubectl logs`; include
  prior-container logs when restart evidence matters.
- Check conditions, restart counts, events, requested health probes and
  expected artifacts before classifying.

### Docker or Podman

- Resolve the exact container ID with `docker|podman inspect`.
- Use bounded `logs` and `stats --no-stream`.
- Confirm exit status, restart policy and count, health status, mounts and
  expected artifacts.

### systemd

- Resolve state with `systemctl show` or `systemctl status`.
- Read a bounded, timestamped journal segment with `journalctl`.
- Use unit result, exit status, activation state and declared artifacts as
  terminal evidence.

### Managed training platform

- Prefer the platform's job API or CLI over dashboard text or process-name
  searches.
- Resolve the exact project, run, attempt, region and immutable job identity.
- Use platform lifecycle state as authoritative and separately verify required
  checkpoints, metrics, exports and handoff artifacts.
- Do not treat an experiment-tracking run as the job owner unless the platform
  actually controls execution.

### Generic process

- Resolve the PID through submitted metadata or a unique
  parent/working-directory/configuration mapping, then inspect it with `ps`.
- Read bounded logs from resolved process metadata or application
  configuration.
- Combine process existence with start time, exit record, heartbeat, resource
  signals and declared artifacts; PID existence alone is not progress.

### Custom batch system

- Prefer its status API or CLI over process-name searches.
- Resolve scheduler-owned output paths and terminal states from that control
  plane.
- Record exact commands and evidence rules in the monitoring contract before
  the first iteration.

## Training signals

Health is computed, not felt. On every `RUNNING` Observation measure the
signals the plan names, write the numbers into `state.json` (`progress`) and
classify with the bands below. The plan may tighten or loosen a band in its
Monitoring Contract; the defaults are:

| Signal | Typical source | `FINE` | `SLOW` | `STALLED` |
| --- | --- | --- | --- | --- |
| Stage | application status file (`run.json` `status.stage`), phase marker | advances as planned | — | unchanged 15 min while the control plane says running |
| Step rate and ETA | tracker metrics per step, optimizer log, progress bar in StdErr | within 20% of the plan's estimate | 20–50% under it | no new step in twice the expected step interval, at least 10 min |
| Loss or objective | tracker metrics, metrics file | finite and moving | flat for 50 steps | NaN or inf in any logged value |
| Checkpoints | `checkpoint-*/` or `ckpt/step-*/` mtimes | on the declared cadence | one missed | two missed |
| Log age | StdErr or main log mtime against now | under 5 min | 5–15 min | over 15 min |
| Restarts | pod or container restart count, requeue count | 0 | 1 | climbing |

Rules:

- The worst measured signal decides: one `STALLED` signal makes health
  `STALLED`; otherwise one `SLOW` signal makes it `SLOW`; otherwise `FINE`.
- A signal that cannot be read (SSH down, file not yet created) is not a
  stall. If no signal could be read, health is `UNKNOWN` and the HEALTH line
  says which reads failed.
- Early in a run, before the first step or checkpoint, only Stage and Log age
  apply. Say so on the HEALTH line (`FINE (stage training, log 40 s old; no
  step yet)`).
- Rate and ETA come from the last measured window (the steps since the
  previous Observation, or the last 50 steps), not from the whole run, and the
  PROGRESS line names the basis when it is weak.
- A `STALLED` or `SLOW` classification follows the recovery policy in
  `CONTROL_CONTRACT.md`. The signal, its value and the threshold go on the
  HEALTH line.

### Queue signals (`QUEUED`)

While the control plane holds the job, the STATE line carries the reason it
is waiting, its priority relative to the jobs ahead of it, and the scheduler's
own start estimate when there is one. These are not health; they are what the
user wants to know while nothing runs. A job whose start estimate keeps moving
later is reported as such, with the two most recent estimates.
