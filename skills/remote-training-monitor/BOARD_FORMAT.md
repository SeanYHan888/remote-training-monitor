# Run Board

One page that answers, for a whole project: what is running, what is queued,
what is planned, what finished, what failed, and what waits on the user. A
report (`REPORT_FORMAT.md`) is one run; the board is every run.

## Where it comes from

`scripts/board.py <project-dir>` reads every `.remote-monitor/*/state.json`,
validates each against `state.schema.json`, groups the valid ones into lanes
and prints Markdown. Nobody types anything on the board, so it is only as
good as the state files. A monitor that writes `run_name`, `since`,
`progress`, `checks` and `next_action` on every wake fills its row; one that
does not gets dashes.

The `board` route runs the script, writes the output to
`.remote-monitor/BOARD.md`, and shows it. `status` with no key does the same.

## Lanes

A run sits in exactly one lane, the first that matches:

| Lane | Condition |
| --- | --- |
| Needs your decision | monitor `WAITING`, or `OFF (needs-decision)` |
| Running | `RUNNING` |
| Queued | `QUEUED`, `APPROVED` |
| Planned | `PLANNED` |
| Done | `PASSED` within the last `--days` (default 7) |
| Failed or cancelled | `FAILED`, `CANCELLED` within the last `--days` |
| Invalid state files | a `state.json` the validator rejects, with the first problems |

Columns: Run · Job · State · Health · Since · Progress · Monitor · Next. The
header line counts each lane so the first line alone says whether anything
needs the user.

## Planned work without a Run Plan

Runs that exist only as a packet, a plan document or a queue entry elsewhere
in the project are not on the board until a Run Plan exists for them. When the
project adapter (`PLAN_FORMAT.md`, "Project adapter") names a
`planned_source`, the `board` route reads it after the script runs and appends
one section, `## Planned elsewhere`, with one line per item: name, what it
waits on, where it is written. The route reads that source and writes nothing
into it.

## Example

```text
# Run board · llm-ft · 2026-11-07T07:25Z

Needs you: 1 · running: 1 · queued: 1 · planned: 1 · done (7 d): 1 · failed (7 d): 1

## Needs your decision

| Run | Job | State | Health | Since | Progress | Monitor | Next |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mix-v3 train, eval, upload | slurm 4830 | PASSED | — | 2026-11-07T06:40Z | checks 5/5 | waiting on you: approve slurm-4830 eval (gate 7c1d…) | approve slurm-4830 eval |

## Running

| Run | Job | State | Health | Since | Progress | Monitor | Next |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline smoke a2 (1 of 2) | slurm 4831 | RUNNING | FINE | 2026-11-07T04:00Z | 3/6 · ETA 2026-11-07T07:40Z | watching · wakes on exit, backstop 2026-11-07T09:30Z | exit checks on completion |

## Queued

| Run | Job | State | Health | Since | Progress | Monitor | Next |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline smoke a2 (2 of 2) | slurm 4832 | QUEUED | — | 2026-11-07T04:01Z | — | watching · wakes on exit, backstop 2026-11-08T04:00Z | early health check 4 min after start |

## Planned

| Run | Job | State | Health | Since | Progress | Monitor | Next |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mix-v3 ablation | — | PLANNED | — | 2026-11-06T18:00Z | — | off (draft) | operator rebuilds the packet on c808cb4 and sends its hash |

## Failed or cancelled

| Run | Job | State | Health | Since | Progress | Monitor | Next |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mix-v3 smoke 4gpu a1 | slurm 4829 | FAILED | — | 2026-11-07T03:12Z | checks 0/14 | off (terminal) | superseded by a2 |
```
