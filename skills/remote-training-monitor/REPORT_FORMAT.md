# Report Format

Every report a monitor produces has one shape: a wake report, a terminal
report, a gate, a recovery outcome, a cached `status` answer, and the History
line that records it. Eight labelled lines in a fixed order, then a rule, then
bounded evidence. The reader learns once where to look.

## The eight lines

```text
RUN      <run name> · <control plane> <job id> · attempt <id> · <approval: packet hash prefix or revision>
STATE    <run state>  (<authoritative evidence, short>)        was <previous state> since <time>
PROGRESS <step>/<total> · <rate> · ETA <time> · checkpoints <list> · <key artifact ids>
CHECKS   <passed>/<total> exit checks  (<failed or pending ones by name>)
HEALTH   <FINE | SLOW | STALLED | UNKNOWN>  (<the signal that decided it, with its value>)
CHANGED  <what is new since the last report, with times>
MONITOR  <watching: wakes on exit, backstop <time> | every <n> min | waiting on you: <decision> | recovering: attempt <id> | off (<reason>)>. Also watched: <other keys and states>
NEXT     <the one action that happens next, and who does it>
────────────────────────────────────────────────────────────
<evidence, one item per line, at most 12 lines: names, ids, paths, links>
```

Rules:

- All eight lines, always, in this order, inside one code block. A line with
  nothing to say reads `—`. Labels are upper case, padded to eight columns, so
  the block aligns in a monospace view.
- STATE and NEXT each stand alone: a reader who sees only those two lines
  knows what the run is doing and what happens next.
- One run per block. Several runs are a board (`BOARD_FORMAT.md`).
- Times carry the zone the plan declares, UTC when it declares none.
  `since` on STATE is when the run entered its current state, not when it was
  last observed.
- Evidence below the rule names or links logs, ids, paths and revisions. A
  stack trace is one line: the exception, the file and the version.
- A decision wanted from the user is named on MONITOR (what is waited for) and
  on NEXT (what happens once it arrives). The question itself follows the
  block, asked once.
- Secrets never appear on any line.

## Per situation

- **QUEUED wake:** STATE carries queue position, priority and the scheduler's
  start estimate (`PENDING Priority · sprio 474 · est. start 22:22 ET`).
  PROGRESS and HEALTH read `—`.
- **RUNNING, FINE:** PROGRESS has rate and ETA from the Training signals;
  CHANGED names the step range since the last report.
- **RUNNING, SLOW or STALLED:** HEALTH names the signal and the threshold it
  crossed; NEXT is the recovery policy's action (`observe_only`: your
  decision; `auto_low_risk`: Risk Judge, then repair or wait).
- **PASSED:** CHECKS reads `n/n`; evidence lists each check with its value;
  MONITOR is `off (terminal)` or, for a non-final phase, `waiting on you`.
- **FAILED:** STATE has the exit code and the stage (`FAILED exit 1:0 · stage
  training · 43 s`); evidence opens with the first relevant failure line and
  the last known good progress; NEXT names recovery eligibility.
- **CANCELLED:** STATE names who cancelled; evidence lists preserved work and
  the latest safe resume point.
- **Gate (phase passed, next phase gated):** STATE `PHASE n PASSED`; NEXT
  `approve <key> <phase>` with the Gate Packet hash; the packet's contents
  are the evidence lines.
- **Recovery outcome:** evidence lines are the original failure, the rollback
  point, the repair, the risk decision, the verification and the retry count.
- **`status <key>` (cached):** STATE is prefixed `cached @ <last_observed>`;
  nothing else changes.
- **No-op wake:** no block. One line: `<key>: monitor <WAITING|OFF>
  (<reason>), no observation.`

## History line

Each report appends one line to the plan's History, never the block:

```text
- <time> <STATE line without its label> → <NEXT line without its label>
```

What replaced what in the heartbeat, a corrected timestamp, a related job
noticed in passing: each is its own one-line History entry, not a paragraph.

## Example

The completion of a smoke test, as its final wake reports it:

```text
RUN      mix-v3 smoke 4gpu a2 · slurm 4830 · attempt a2 · packet 9f3c2a1e…
STATE    PASSED  (COMPLETED 0:0, 20 min on gpu-07)        was QUEUED since 04:20Z
PROGRESS 6/6 steps · 249 s training · checkpoints 3, 6 · HF model rev 0470f637…
CHECKS   14/14 exit checks
HEALTH   —
CHANGED  started 06:51Z · finished 07:12Z · checks ran 07:20Z
MONITOR  off (terminal). Also watched: slurm-4831 RUNNING, slurm-4832 QUEUED
NEXT     rebuild the ablation packet on c808cb4 → needs the operator's hash
────────────────────────────────────────────────────────────
run/run.json: status.stage training_pass · archive uploaded · packet 9f3c2a1e…
run/local_completion.json: PASS · global_step 6 · controller_rule_check PASS
trajectories/controller.csv: 12 rows, gap-free, every row satisfies the update rule
W&B run finished; per-step metrics present
run/final_checkpoint_fresh_load.json PASS · hub_revision_verification.json PASS
Slurm .err: download advisory and shard bars only
state dir: .remote-monitor/slurm-4830/
```

History line for it:

```text
- 2026-11-07T07:20Z PASSED (COMPLETED 0:0, 20 min on gpu-07) → rebuild the ablation packet on c808cb4, needs the operator's hash
```
