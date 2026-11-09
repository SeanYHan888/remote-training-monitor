#!/usr/bin/env python3
"""Completion waiter for Slurm jobs: one background command for one or several runs.

Standard library only. Polls every job in one SSH call and exits when the agent
has something to verify. Read-only toward the jobs.

Usage:
    slurm_waiter.py --host <ssh host | local> [--poll SECONDS] [--backstop-hours H] [--log FILE] JOB [JOB ...]

JOB is comma-separated key=value pairs:
    key=<target key>,job=<job id>,stage=queue
    key=<target key>,job=<job id>,stage=run,deadline=<ISO 8601 UTC>[,status_file=<remote path>,stall=<seconds>]

Stages:
    queue  exits when the job leaves the queue (started, or ended without running);
           bounded only by the backstop (--backstop-hours, default 24).
    run    exits when the job leaves its running states, when its deadline passes,
           or when status_file has not changed for `stall` seconds while it runs.

Lookup rules:
    - A failed lookup (SSH error, no answer) means keep waiting.
    - A job squeue no longer lists is asked of sacct (Slurm drops finished jobs from
      squeue after MinJobAge); only when both are silent is the lookup failed.
    - Slurm commands run with TZ=UTC, so every time printed is UTC.

Exit codes (the first event of a poll decides, in this order of priority):
    0  a job left the queue or its running states
    5  a stall rule fired
    3  a run-stage deadline passed
    4  the queue backstop passed
    2  usage error
The output names every event's key, then lists the last read of every job.
"""

import argparse
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

QUEUE_STATES = {"PENDING", "REQUEUED", "REQUEUE_HOLD", "REQUEUE_FED", "CONFIGURING"}
RUN_STATES = {"PENDING", "CONFIGURING", "RUNNING", "COMPLETING", "REQUEUED", "REQUEUE_HOLD",
              "REQUEUE_FED", "RESIZING", "SUSPENDED", "STAGE_OUT", "SIGNALING"}
EXIT_PRIORITY = (0, 5, 3, 4)
SENTINEL = "__slurm_waiter_end__"


def utc_now():
    return datetime.now(timezone.utc)


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(text):
    value = text.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    moment = datetime.fromisoformat(value)
    return moment.replace(tzinfo=timezone.utc) if moment.tzinfo is None else moment.astimezone(timezone.utc)


def parse_job(spec):
    fields = {}
    for part in spec.split(","):
        if "=" not in part:
            raise ValueError(f"{spec!r}: expected key=value pairs, got {part!r}")
        name, value = part.split("=", 1)
        fields[name.strip()] = value.strip()
    unknown = set(fields) - {"key", "job", "stage", "deadline", "status_file", "stall"}
    if unknown:
        raise ValueError(f"{spec!r}: unknown field(s) {', '.join(sorted(unknown))}")
    for name in ("key", "job", "stage"):
        if not fields.get(name):
            raise ValueError(f"{spec!r}: missing {name}=")
    if not re.fullmatch(r"[A-Za-z0-9._-]+", fields["key"]):
        raise ValueError(f"{spec!r}: key must match the Target Key pattern [A-Za-z0-9._-]+")
    if not fields["job"].replace("_", "").isdigit():
        raise ValueError(f"{spec!r}: job must be a Slurm job id")
    if fields["stage"] not in ("queue", "run"):
        raise ValueError(f"{spec!r}: stage must be queue or run")
    job = {"key": fields["key"], "job": fields["job"], "stage": fields["stage"],
           "deadline": None, "status_file": fields.get("status_file"), "stall": None}
    if fields["stage"] == "run":
        if not fields.get("deadline"):
            raise ValueError(f"{spec!r}: a run-stage job needs deadline= (start + time limit + margin, UTC)")
        job["deadline"] = parse_time(fields["deadline"])
    elif "deadline" in fields or "status_file" in fields or "stall" in fields:
        raise ValueError(f"{spec!r}: deadline, status_file and stall belong to stage=run")
    if bool(fields.get("status_file")) != bool(fields.get("stall")):
        raise ValueError(f"{spec!r}: status_file and stall go together")
    if fields.get("stall"):
        job["stall"] = int(fields["stall"])
    return job


def remote_script(jobs):
    """POSIX sh run on the cluster: one line per job, one per stall file, then a sentinel."""
    lines = ["export TZ=UTC"]
    for job in jobs:
        jid = shlex.quote(job["job"])
        lines.append(
            f"l=$(squeue -h -j {jid} -o '%i|%T|%r|%S' 2>/dev/null | head -n 1); "
            f"[ -n \"$l\" ] || l=$(sacct -n -X -P -j {jid} -o JobID,State,Reason,Start 2>/dev/null | head -n 1); "
            f"echo \"job|{job['job']}|$l\""
        )
        if job["status_file"]:
            path = shlex.quote(job["status_file"])
            lines.append(f"m=$(stat -c %Y {path} 2>/dev/null) && echo \"age|{job['key']}|$(( $(date +%s) - m ))\"")
    lines.append(f"echo {SENTINEL}")
    return "\n".join(lines) + "\n"


def lookup(host, jobs):
    """Return ({job id: (state, reason, start)}, {key: age seconds}) or None when the lookup failed."""
    script = remote_script(jobs)
    if host == "local":
        cmd = ["sh", "-c", script]
    else:
        cmd = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host, script]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0 or SENTINEL not in done.stdout:
        return None
    states, ages = {}, {}
    for line in done.stdout.splitlines():
        parts = line.split("|")
        if parts[0] == "job" and len(parts) >= 2:
            fields = parts[2:] + ["", "", "", ""]
            # fields: JobID, State, Reason, Start (empty when neither command knew the job)
            state = fields[1].split(" ")[0] if fields[1] else ""
            states[parts[1]] = (state, fields[2], fields[3])
        elif parts[0] == "age" and len(parts) == 3 and parts[2].lstrip("-").isdigit():
            ages[parts[1]] = int(parts[2])
    return states, ages


def events_for(jobs, read, now, backstop, last):
    events = []
    states, ages = read if read else ({}, {})
    for job in jobs:
        state = states.get(job["job"], ("", "", ""))[0]
        known = last.get(job["job"], ("",))[0] or "unknown"
        if job["stage"] == "queue":
            if state and state not in QUEUE_STATES:
                events.append((0, job["key"], f"job {job['job']} left the queue: {state}"))
            elif now >= backstop:
                events.append((4, job["key"], f"queue backstop {stamp(backstop)} passed; last state {known}"))
        else:
            if state and state not in RUN_STATES:
                events.append((0, job["key"], f"job {job['job']} left its running states: {state}"))
                continue
            age = ages.get(job["key"])
            if state and job["stall"] is not None and age is not None and age > job["stall"]:
                events.append((5, job["key"], f"stall rule: {job['status_file']} unchanged for {age} s while {state}"))
            if now >= job["deadline"]:
                events.append((3, job["key"], f"deadline {stamp(job['deadline'])} passed; last state {known}"))
    return events


def report(jobs, last, failed_lookups, events):
    code = min((e[0] for e in events), key=EXIT_PRIORITY.index)
    print(f"exit {code} at {stamp(utc_now())} (times UTC)")
    for _, key, text in sorted(events, key=lambda e: EXIT_PRIORITY.index(e[0])):
        print(f"event {key}: {text}")
    print("key | job | stage | state | reason | start")
    for job in jobs:
        state, reason, start = last.get(job["job"], ("", "", ""))
        print(f"{job['key']} | {job['job']} | {job['stage']} | {state or 'unknown (lookup failed)'} | "
              f"{reason or '-'} | {start or '-'}")
    if failed_lookups:
        print(f"failed lookups during the wait: {failed_lookups}")
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True, help="ssh host, or 'local' to run the Slurm commands here")
    parser.add_argument("--poll", type=float, default=180.0, help="seconds between polls (default 180)")
    parser.add_argument("--backstop-hours", type=float, default=24.0, help="queue-stage backstop (default 24)")
    parser.add_argument("--log", help="append one line per poll to this file")
    parser.add_argument("jobs", nargs="+", metavar="JOB")
    args = parser.parse_args(argv)
    try:
        jobs = [parse_job(spec) for spec in args.jobs]
    except ValueError as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        return 2
    if len({j["key"] for j in jobs}) != len(jobs):
        print("usage error: each target key appears once", file=sys.stderr)
        return 2

    backstop = utc_now() + timedelta(hours=args.backstop_hours)
    last, failed = {}, 0
    print(f"armed at {stamp(utc_now())} for " + ", ".join(f"{j['key']} ({j['job']}, {j['stage']})" for j in jobs), flush=True)
    while True:
        read = lookup(args.host, jobs)
        if read is None:
            failed += 1
        else:
            for jid, value in read[0].items():
                if value[0]:
                    last[jid] = value
        now = utc_now()
        if args.log:
            with open(args.log, "a") as handle:
                summary = "lookup failed" if read is None else " ".join(
                    f"{j['key']}={last.get(j['job'], ('?',))[0] or '?'}" for j in jobs)
                handle.write(f"{stamp(now)} {summary}\n")
        events = events_for(jobs, read, now, backstop, last)
        if events:
            return report(jobs, last, failed, events)
        time.sleep(args.poll)


if __name__ == "__main__":
    sys.exit(main())
