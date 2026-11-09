---
status: accepted
---

# One waiter per session, and a bundled Slurm waiter

The skill gave each Target Key its own heartbeat and showed the Slurm waiter as two shell templates the agent filled in. On a project that watched three or four queued jobs at once from two approval packets, and needed a wake when any one finished, the agent skipped the skill and wrote its own waiter. That waiter had no backstop and was lost with the session. Running the templates once per key would have given one session several waiters. Two template defects also showed up. A job that `squeue` no longer lists returns the same empty answer as a dropped SSH connection, so the queue stage waited for its 24-hour backstop on a job that had already ended (Slurm drops a finished job from `squeue` after `MinJobAge`, 300 s on that cluster). And Slurm printed times in the cluster's local zone, which the agent reported as UTC.

We let the Target Keys one session watches share one completion waiter, recorded as each key's heartbeat with `covers`. We ship the Slurm waiter as `scripts/slurm_waiter.py`: one SSH call per poll for every job, `TZ=UTC` on every Slurm command, a fall-back from `squeue` to `sacct`, and tests with stub commands.

## Considered options

- **One waiter per key.** Rejected: a session with N waiters is woken N times by unrelated events and has to tell which waiter fired. Replacement after one exit races with the others.
- **Fix the inline templates only.** Rejected: the agent filled the templates in differently each time, and a shell loop pasted into a prompt cannot be tested. A script with tests gives the same behavior every time and is shorter to call.
- **A durable cluster-side watcher (cron on the login node).** Rejected for now: it needs operator setup and credentials outside the session, and the harness still has to be woken.

## Consequences

- `state.json` gains an optional `heartbeat.covers`. The validator requires it to include the file's own key, to list each key once, and to appear only on a completion waiter. The board shows when one waiter covers several runs.
- After a shared waiter exits, the agent iterates each key the exit names, then arms one replacement over every key still watching. `start` and `stop` on one key replace the live waiter with one over the new set.
- Other control planes keep the two stage shapes and the three lookup rules (state actually read, accounting before "failed", UTC). Their waiters are still written in the session.
