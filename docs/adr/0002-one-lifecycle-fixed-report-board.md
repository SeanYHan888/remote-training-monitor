---
status: accepted
---

# One run lifecycle, a fixed report shape, and a generated board

The first version described a monitored job in five independent dimensions (job state, health, controller state, wake mode, cadence mode) and listed what a report must contain without fixing how it looks. On the first real run the agent wrote values outside the enums (`controller_state: DONE`, `health: FAILED`), put prose into the heartbeat id, recorded a completion waiter under an interval cadence, and produced History entries of a dozen lines each. On the next run it abandoned the skill for the project's own per-run notes file, which was clearer. The skill also had no answer to "what is running, what is queued, what did we plan", because it modelled one job at a time.

We replace the five dimensions with three fields a person can read (run state, health while running, monitor), validate `state.json` against a schema on every read and write, fix every report to one eight-line shape, and generate a board across all monitors in a project from their state files.

## Considered options

- **Keep the five dimensions and add validation.** Rejected: validation would have caught the invalid values, but a reader still has to combine five fields to answer "is it running and is anyone watching". The dimensions that are properties of the heartbeat (wake mode, cadence) now live in the heartbeat record; the one that is about the monitor (controller state) becomes `monitor`; `SLEEP` was a cadence pretending to be a state.
- **Rename only, no schema or script.** Rejected: the drift on the first run shows that instructions alone do not hold an enum. A stdlib-only validator costs nothing to run and gives a wake a precise refusal.
- **A free-form report with a required content list** (the previous rule). Rejected: every report came out as a different paragraph, and the reader relearned where to look each time. A fixed shape with a `—` for empty lines is the cheapest way to make STATE and NEXT findable.
- **A hand-maintained board.** Rejected: it would be stale by the second wake. The board is generated from state files, so the only way to keep it current is to keep `state.json` current, which the wake must do anyway.
- **Keeping History inside plan.md when the project has its own run file.** Rejected: two timelines per run is how the first run ended up with a `RUN_STATE.md` that disagreed with the plan about the submit time. The plan may point at the project's file and write there.

## Consequences

- Health is computed from named Training signals with default bands; a plan may change a band, a wake may not invent one.
- The completion waiter has two stages: queue (no deadline, exits on start) and run (deadline from start time, stall rule in shell). Queue wait no longer produces no-news wakes.
- Exit checks are copied into the plan verbatim; a project approval artifact is recorded as the approval source rather than re-approved.
- State files written under the old vocabulary are read through a mapping and rewritten on the next write; `scripts/validate_state.py` refuses anything else.
- The authority planes, the Risk Judge, the one-heartbeat rule and the plan-revision rule are unchanged.
