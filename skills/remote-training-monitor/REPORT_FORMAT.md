# Report Format

Every report a monitor produces has the same shape, whether it is a wake
report, a terminal report, a gate, a recovery outcome or a cached `status`
answer. The shape is eight labelled lines in a fixed order, a horizontal rule,
and at most twelve lines of evidence. Each report also leaves one History line.
A reader who knows the shape finds STATE and NEXT without searching.

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

- Write all eight lines, in this order, inside one code block. Put `—` on a
  line that has nothing to report. Labels are upper case and padded to eight
  columns so the block aligns in a monospace view.
- STATE and NEXT must each make sense on their own. A reader who sees only
  those two lines knows what the run is doing and what happens next.
- A block covers one run. Several runs go on a board (`BOARD_FORMAT.md`).
- Write times in the zone the plan declares, or UTC when it declares none.
  `since` on STATE is when the run entered its current state, not when the
  monitor last observed it.
- Each evidence line names or links a log, an id, a path or a revision. A
  stack trace takes one line: the exception, the file and the version.
- When the monitor needs a decision from the user, MONITOR names what it
  waits for and NEXT names what happens once the decision arrives. Ask the
  question once, after the block.
- Never put a secret on any line.

## Wording

The reader is deciding whether to act, often on a phone. When the `unslop`
skill is installed, run every report through it. Without it, these rules,
cited by unslop's rule ids, cover a report:

- Whole sentences on CHANGED, NEXT and every evidence line, with their
  articles and verbs. Spell out arrows and shorthand: "then", "because",
  "needs", not `→` or `->`. The `·` separator on RUN, PROGRESS and MONITOR is
  the one exception. (33)
- Name the actor. "checks ran at 07:20Z", not "checks were run"; NEXT says who
  does the action. (29)
- A value, not an adjective. "1.9 step/s, down from 2.4", not "slower"; "no
  step for 12 min", not "appears stalled". HEALTH names the signal that
  decided it and its value. (27, 30)
- Plain words. "use", "start", "wait", "fail", not "leverage", "surface",
  "harness" as a metaphor, "north star". (7, 26, 31)
- No metaphor or flourish. A job does not "limp" or "hum along"; it runs at a
  rate. (32)
- No commentary. No "good news", "unfortunately", "as expected", no
  exclamation marks, no "let me know". (20, 22, 24)
- Straight quotes. No em dashes in prose; the `—` placeholder on an empty line
  is a glyph, not punctuation. (13, 19)

## Per situation

- **QUEUED wake.** STATE carries the queue position, the priority and the
  scheduler's start estimate (`PENDING Priority · sprio 474 · est. start
  22:22 ET`). PROGRESS and HEALTH are `—`.
- **RUNNING, FINE.** PROGRESS has the rate and ETA from the Training signals.
  CHANGED names the step range since the last report.
- **RUNNING, SLOW or STALLED.** HEALTH names the signal and the threshold it
  crossed. NEXT is the recovery policy's action: under `observe_only`, your
  decision; under `auto_low_risk`, the Risk Judge, then a repair or a wait.
- **PASSED.** CHECKS reads `n/n`, and the evidence lists each check with its
  value. MONITOR is `off (terminal)`, or `waiting on you` after a non-final
  phase.
- **FAILED.** STATE has the exit code and the stage (`FAILED exit 1:0 · stage
  training · 43 s`). The evidence opens with the first relevant failure line
  and the last known good progress. NEXT says whether recovery is allowed and
  by whom.
- **CANCELLED.** STATE names who cancelled. The evidence lists the preserved
  work and the latest safe resume point.
- **Gate (phase passed, next phase gated).** STATE reads `PHASE n PASSED`.
  NEXT reads `approve <key> <phase>` with the Gate Packet hash. The packet's
  contents are the evidence lines.
- **Recovery outcome.** The evidence lines are the original failure, the
  rollback point, the repair, the risk decision, the verification and the
  retry count.
- **`status <key>` (cached).** STATE is prefixed `cached @ <last_observed>`.
  Nothing else changes.
- **No-op wake.** Write no block. Write one line: `<key>: monitor
  <WAITING|OFF> (<reason>), no observation.`

## History line

Each report appends one line to the plan's History. The block itself is never
appended.

```text
- <time> <STATE line without its label>. Next: <NEXT line without its label>
```

A heartbeat replacement, a corrected timestamp or a related job noticed in
passing each get their own one-line History entry, not a paragraph.

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
NEXT     the operator rebuilds the ablation packet on c808cb4 and sends its hash
────────────────────────────────────────────────────────────
run/run.json: stage training_pass, archive uploaded, packet 9f3c2a1e…
run/local_completion.json: PASS, global_step 6, controller_rule_check PASS
trajectories/controller.csv: 12 rows with no gaps; every row satisfies the update rule
W&B run finished with per-step metrics
run/final_checkpoint_fresh_load.json PASS; hub_revision_verification.json PASS
Slurm .err holds only a download advisory and shard progress bars
state directory .remote-monitor/slurm-4830/
```

History line for it:

```text
- 2026-11-07T07:20Z PASSED (COMPLETED 0:0, 20 min on gpu-07). Next: the operator rebuilds the ablation packet on c808cb4 and sends its hash
```
