# Harness capabilities

Read this file when creating, changing, or resuming recurring monitoring.
Inspect the callable scheduling tools and their documented persistence,
execution directory, interval limits, and pause/update operations. Detection
is read-only: never create a timer as a capability probe. An unknown runtime
uses only capabilities it actually exposes.

## Selection

Prefer a verified durable mechanism when the job will outlive the session.
Use a session-bound mechanism when that is what the runtime supplies, clearly
stating when monitoring ends. A tool named cron or background does not by
itself establish durability. If persistence is unknown, report it as unknown.

| Runtime | Scheduling guidance |
| --- | --- |
| Codex desktop | Use the current task's heartbeat by default. Use a standalone scheduled task only when explicitly requested. Inspect the automation tool for supported creation, update, and pause fields. |
| Claude Code | Inspect the exposed scheduling tool's lifetime and limits. Use durable routines only if explicitly supported; treat session-only cron/wakeups as session-bound. |
| CLI, IDE, or other runtime | Use an available scheduler or bounded session wait. Without a durable mechanism, explain the limitation and provide an operator-managed scheduling option if needed. |

## Establish or resume

After the Run Plan and its approval rule are satisfied:

1. Resolve the recorded heartbeat ID against the scheduler before creating
   anything. Reuse an existing matching heartbeat. If lookup is unavailable
   or ambiguous, report that uncertainty rather than create a potential duplicate.
2. On every explicit `start`, observe the current target, including when the
   recorded timer is already active, before reactivating a paused
   monitor or replacing a confirmed-expired session timer. Terminal outcomes
   and approval gates take precedence over reactivation.
3. Schedule `$remote-training-monitor iterate <target-key>` at Watchdog's
   selected cadence. Preserve any required invocation namespace. Verify the
   execution directory can read the existing plan and state; a worktree is
   acceptable only when it can access that same state, not a divergent copy.
4. Verify and record the returned ID, interval, lifetime, and execution
   directory in `state.json`. Report success only after confirmation. Keep
   unchanged/non-actionable observations quiet unless periodic reports were
   requested; notify on material changes, completion, failure, or required action.

For updates or pauses, use the scheduler's supported operations on that ID.
Set controller state before pausing. If the operation fails, preserve its ID
and disclose the failure; subsequent wakes must honor the paused-state guard.
An `iterate` never creates or replaces a timer.

## Session-only fallback

Use the runtime's wait mechanism with its actual per-call limit. Bound the
total polling horizon in the plan and report that monitoring ends with the
session or that horizon. Do not claim monitoring is active after polling ends.

If the user needs operator-managed cron, supply a command with absolute
executable and project paths, safely quoted arguments, and the required
environment. Validate the cadence expression: hourly is `0 * * * *`, not
`*/60 * * * *`. Explain that the operator installs it and that scheduler
availability and agent credentials must persist outside the interactive shell.
