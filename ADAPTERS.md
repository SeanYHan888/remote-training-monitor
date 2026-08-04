# Target Observation Adapters

Read the single section matching the target's authoritative control plane. SSH
is transport, not authority: use it to run the selected adapter on the remote
host.

Every adapter must resolve a stable target identity, current lifecycle state,
bounded new logs, health evidence, terminal-state mapping, and declared
artifact checks. Telemetry systems such as W&B are supporting evidence unless
they also own the job lifecycle.

## Slurm

- Resolve identity and current state with `squeue`, then
  `scontrol show job <job_id>`.
- Use `sacct -j <job_id>` for completed or failed jobs and steps.
- Resolve `StdOut` and `StdErr` from scheduler metadata before reading bounded
  output.
- Treat the scheduler's terminal state as lifecycle-authoritative; also require
  every completion manifest named by the monitoring contract.

## Kubernetes

- Resolve identity and state with `kubectl get job|pod` and
  `kubectl describe`.
- Read bounded or timestamped output with `kubectl logs`; include
  prior-container logs when restart evidence matters.
- Check conditions, restart counts, events, requested health probes, and
  expected artifacts before classifying.

## Docker or Podman

- Resolve the exact container ID with `docker|podman inspect`.
- Use bounded `logs` and `stats --no-stream`.
- Confirm exit status, restart policy and count, health status, mounts, and
  expected artifacts.

## systemd

- Resolve state with `systemctl show` or `systemctl status`.
- Read a bounded, timestamped journal segment with `journalctl`.
- Use unit result, exit status, activation state, and declared artifacts as
  terminal evidence.

## Managed training platform

- Prefer the platform's job API or CLI over dashboard text or process-name
  searches.
- Resolve the exact project, run, attempt, region, and immutable job identity.
- Use platform lifecycle state as authoritative and separately verify required
  checkpoints, metrics, exports, and handoff artifacts.
- Do not treat an experiment-tracking run as the job owner unless the platform
  actually controls execution.

## Generic process

- Resolve the PID through submitted metadata or a unique
  parent/working-directory/configuration mapping, then inspect it with `ps`.
- Read bounded logs from resolved process metadata or application
  configuration.
- Combine process existence with start time, exit record, heartbeat, resource
  signals, and declared artifacts; PID existence alone is not progress.

## Custom batch system

- Prefer its status API or CLI over process-name searches.
- Resolve scheduler-owned output paths and terminal states from that control
  plane.
- Record exact commands and evidence rules in the monitoring contract before
  the first iteration.
