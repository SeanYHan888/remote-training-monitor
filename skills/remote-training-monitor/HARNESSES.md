# Harnesses

The harness is the agent runtime the skill is executing in. Detect it from the
tools available in the session, record it in the Run Plan frontmatter, and
follow only the matching row. Evidence rules, state files, and authority are
identical across harnesses; only the waiting mechanism differs.

Detection order: a durable scheduling tool wins; then a session-bound wait
tool; then none. When tools are ambiguous, attempt to arm a durable heartbeat
and fall through this ladder on failure. An unrecognised harness follows the
Codex CLI row.

| Harness | Detect by | Durable heartbeat | Session-bound wait | Pause |
| --- | --- | --- | --- | --- |
| Claude Code | scheduled-wakeup, cron-routine, or background-monitor tools | cron routine | background monitor, or scheduled wakeup in this session | stop the wakeup or delete the routine |
| Codex desktop app | a scheduled-task (automation) tool callable from chat | scheduled task, in-chat by default | background terminal, 5-minute polls | update or delete the task if possible |
| Codex CLI / IDE | no scheduling tool | none; user-run cron calling `codex exec` | background terminal, 5-minute polls | stop polling |

Every row keeps the no-op wake as its backstop: an `iterate` that finds the
controller paused in `state.json` exits with one line, so a heartbeat that
could not be paused does no harm.

## Claude Code

- User present and wants live events: session-bound background monitor.
- Target will outlive the session or the user steps away: durable cron routine
  with the prompt `$remote-training-monitor iterate <target-key>`.
- A session-bound wait carries a disclosure in the report that announces it:
  it stops when the session closes, and that silence reads like a healthy job.

## Codex desktop app

- Arm a scheduled task **inside the current chat** at the Cadence Mode
  interval, prompt `$remote-training-monitor iterate <target-key>`. The thread
  keeps context and results land where the user already is.
- A standalone task (fresh chat per run, results in the Scheduled view) is the
  option to offer when the user says they are stepping away.
- Precondition, stated when the task is created: the task runs in the project
  directory, never in a background worktree, or the plan file is unreachable.
- Pause and delete by the agent are undocumented. Attempt them; rely on the
  no-op wake.

## Codex CLI / IDE

No scheduled task can be armed from here. `start` does both of these in one
report:

1. Poll in-session with the background terminal, one poll of at most five
   minutes at a time, bounded to the smaller of the estimated remaining time
   and twelve polls. Say plainly that polling stops when the session closes.
2. Hand the user the durable option, filled in:

   ```bash
   */10 * * * * cd <project-dir> && codex exec "\$remote-training-monitor iterate <target-key>"
   ```

   Use the Cadence Mode interval for the cron field. The user installs it; the
   skill never edits a crontab.

## Failure modes this table exists for

- **Silent death**: a session-bound wait ends with its session while the job
  runs on. Cured by preferring durable heartbeats and disclosing the rest.
- **Duplicate tasks**: two heartbeats for one target. Cured by the heartbeat
  identity in `state.json`; `start` reuses it before creating anything.
- **Blocked turn**: a wait longer than the harness's poll cap. Cured by the
  five-minute poll bound and the twelve-poll ceiling.
