#!/usr/bin/env python3
"""Render the run board from every .remote-monitor/*/state.json in a project.

Standard library only. Reads each state file, groups the runs into lanes and
prints Markdown (default) or JSON. A state file that fails validation is listed
in its own lane rather than dropped, so a broken monitor stays visible.

Usage:
    board.py [<project-dir>] [--days 7] [--json]

Lanes, in order; a run sits in exactly one:
    Needs your decision   monitor WAITING, or OFF (needs-decision)
    Running               RUNNING
    Queued                QUEUED, APPROVED
    Planned               PLANNED
    Done                  PASSED within --days
    Failed or cancelled   FAILED, CANCELLED within --days
    Invalid state files   anything validate_state.py rejects
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_state  # noqa: E402

LANES = [
    "Needs your decision",
    "Running",
    "Queued",
    "Planned",
    "Done",
    "Failed or cancelled",
    "Invalid state files",
]


def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def lane_for(state, cutoff):
    monitor = state.get("monitor") or {}
    if monitor.get("state") == "WAITING" or (
        monitor.get("state") == "OFF" and monitor.get("reason") == "needs-decision"
    ):
        return "Needs your decision"
    run_state = state.get("run_state")
    if run_state == "RUNNING":
        return "Running"
    if run_state in ("QUEUED", "APPROVED"):
        return "Queued"
    if run_state == "PLANNED":
        return "Planned"
    since = parse_time(state.get("since")) or parse_time(state.get("last_observed"))
    if since is not None and since < cutoff:
        return None
    if run_state == "PASSED":
        return "Done"
    if run_state in ("FAILED", "CANCELLED"):
        return "Failed or cancelled"
    return None


def monitor_text(state):
    monitor = state.get("monitor") or {}
    hb = state.get("heartbeat") or {}
    kind = monitor.get("state", "?")
    if kind == "WATCHING":
        if hb.get("mode") == "completion":
            shared = f" · one waiter for {len(hb['covers'])} runs" if len(hb.get("covers") or []) > 1 else ""
            return f"watching · wakes on exit, backstop {hb.get('deadline') or '—'}{shared}"
        return f"watching · every {hb.get('interval_min', '?')} min"
    if kind == "WAITING":
        return f"waiting on you: {monitor.get('reason') or '—'}"
    if kind == "RECOVERING":
        return "recovering"
    return f"off ({monitor.get('reason') or '—'})"


def job_text(state):
    attempt = state.get("current_attempt") or {}
    plane = attempt.get("control_plane")
    job = attempt.get("job_id")
    if not job:
        return "—"
    return f"{plane} {job}" if plane else str(job)


def progress_text(state):
    p = state.get("progress") or {}
    parts = []
    if p.get("step") is not None and p.get("total_steps"):
        parts.append(f"{p['step']}/{p['total_steps']}")
    elif p.get("stage"):
        parts.append(p["stage"])
    if p.get("eta"):
        parts.append(f"ETA {p['eta']}")
    checks = state.get("checks") or {}
    if state.get("run_state") in ("PASSED", "FAILED") and checks.get("total"):
        parts.append(f"checks {checks.get('passed', 0)}/{checks['total']}")
    return " · ".join(parts) or "—"


def collect(project_dir, days):
    root = Path(project_dir) / ".remote-monitor"
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = {lane: [] for lane in LANES}
    schema = json.loads((Path(__file__).resolve().parent.parent / "state.schema.json").read_text())
    for state_path in sorted(root.glob("*/state.json")):
        try:
            state = json.loads(state_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            rows["Invalid state files"].append({"key": state_path.parent.name, "problem": f"not JSON: {exc}"})
            continue
        errors = []
        validate_state.check(state, schema, "state", errors)
        if not errors:
            validate_state.semantic(state, errors)
        if errors:
            rows["Invalid state files"].append({"key": state_path.parent.name, "problem": "; ".join(errors[:3])})
            continue
        lane = lane_for(state, cutoff)
        if lane is None:
            continue
        rows[lane].append(
            {
                "key": state["target_key"],
                "run": state["run_name"],
                "job": job_text(state),
                "state": state["run_state"],
                "health": state.get("health") or "—",
                "since": state.get("since") or "—",
                "progress": progress_text(state),
                "monitor": monitor_text(state),
                "next": state.get("next_action", "—"),
            }
        )
    for lane in LANES:
        rows[lane].sort(key=lambda r: r.get("since", ""), reverse=True)
    return rows


def render_markdown(rows, project_dir, days):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    needs = len(rows["Needs your decision"])
    out = [f"# Run board · {Path(project_dir).name} · {now}", ""]
    out.append(
        f"Needs you: {needs} · running: {len(rows['Running'])} · queued: {len(rows['Queued'])} · "
        f"planned: {len(rows['Planned'])} · done ({days} d): {len(rows['Done'])} · "
        f"failed ({days} d): {len(rows['Failed or cancelled'])}"
    )
    out.append("")
    for lane in LANES:
        items = rows[lane]
        if not items:
            continue
        out.append(f"## {lane}")
        out.append("")
        if lane == "Invalid state files":
            out.append("| Key | Problem |")
            out.append("| --- | --- |")
            for r in items:
                out.append(f"| {r['key']} | {r['problem']} |")
        else:
            out.append("| Run | Job | State | Health | Since | Progress | Monitor | Next |")
            out.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for r in items:
                out.append(
                    f"| {r['run']} | {r['job']} | {r['state']} | {r['health']} | {r['since']} | "
                    f"{r['progress']} | {r['monitor']} | {r['next']} |"
                )
        out.append("")
    if sum(len(v) for v in rows.values()) == 0:
        out.append("No monitors under .remote-monitor/.")
    return "\n".join(out).rstrip() + "\n"


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 2
    args = [a for a in argv[1:] if not a.startswith("--")]
    project_dir = args[0] if args else "."
    days = 7
    if "--days" in argv:
        days = int(argv[argv.index("--days") + 1])
    rows = collect(project_dir, days)
    if "--json" in argv:
        print(json.dumps(rows, indent=2))
    else:
        sys.stdout.write(render_markdown(rows, project_dir, days))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
