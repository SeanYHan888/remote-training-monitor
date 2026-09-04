---
status: accepted
---

# Run Plan and monitoring state live in a local file under the working directory

Codex has no in-session wait: a scheduled task fires as a fresh chat or a re-entered thread, and Codex CLI/IDE cannot arm one at all, so every heartbeat wake must be able to rebuild its context from disk. We keep the Run Plan (`plan.md`) and mutable monitoring state (`state.json`) in `.remote-monitor/<target-key>/` inside the project's working directory, excluded from git via `.git/info/exclude`, rather than on the remote host or only in conversation memory.

## Considered options

- **On the remote host, next to the job's logs.** Rejected: the agent's own filesystem is always reachable even when SSH is flaky, and the plan must survive a host that is reimaged, preempted, or shared between users.
- **Conversation memory only, with the target key in the task prompt.** Rejected: a Codex standalone task and a Claude session-bound monitor both lose it, and approvals would then have no durable record.
- **`~/.remote-monitor/<target-key>/`.** Rejected: it detaches the plan from the checkout that holds the launch scripts and configs Discovery inspects. The cost is a precondition: scheduled tasks must run in the project directory, never in a worktree.

## Consequences

- Every `iterate` wake reads the file before observing; a missing plan is a refusal, never a re-plan.
- Approvals, plan revisions, and recovery attempts are appended to the file, making it the audit trail.
- The directory is preserved after terminal states and named in the outcome report as evidence.
