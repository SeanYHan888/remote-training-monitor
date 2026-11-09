"""Tests for skills/remote-training-monitor/scripts/slurm_waiter.py.

Stub squeue, sacct, stat and ssh on PATH stand in for a cluster. Each stub reads
its answer for a job id from a file in FAKE_DIR, so a test states the cluster's
answers as files. Run: python3 -m unittest discover -s tests
"""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills/remote-training-monitor/scripts/slurm_waiter.py"

# squeue/sacct stubs: print FAKE_DIR/<tool>_<job id> if it exists, else exit 1 as Slurm does
# for an unknown job id. The literal "$TZ" in an answer file is expanded, so a test can see the
# zone the waiter exported.
TOOL_STUB = textwrap.dedent("""\
    #!/bin/sh
    tool=$(basename "$0")
    while [ $# -gt 0 ]; do
      if [ "$1" = "-j" ]; then shift; jid=$1; fi
      shift
    done
    f="$FAKE_DIR/${tool}_$jid"
    [ -f "$f" ] || { echo "slurm_load_jobs error: Invalid job id specified" >&2; exit 1; }
    sed "s/\\$TZ/$TZ/g" "$f"
    """)
STAT_STUB = textwrap.dedent("""\
    #!/bin/sh
    echo $(( $(date +%s) - $(cat "$FAKE_DIR/stat_age") ))
    """)
SSH_FAIL_STUB = "#!/bin/sh\necho 'ssh: connect to host x: Connection refused' >&2\nexit 255\n"


def iso(delta_minutes):
    return (datetime.now(timezone.utc) + timedelta(minutes=delta_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


class WaiterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        for name, body in (("squeue", TOOL_STUB), ("sacct", TOOL_STUB), ("stat", STAT_STUB)):
            path = self.bin / name
            path.write_text(body)
            path.chmod(0o755)

    def tearDown(self):
        self.tmp.cleanup()

    def answer(self, tool, job, line):
        (self.dir / f"{tool}_{job}").write_text(line + "\n")

    def run_waiter(self, *jobs, host="local", backstop_hours="24"):
        env = dict(os.environ, FAKE_DIR=str(self.dir), PATH=f"{self.bin}:{os.environ['PATH']}")
        done = subprocess.run(
            [sys.executable, str(SCRIPT), "--host", host, "--poll", "0.05", "--backstop-hours", backstop_hours, *jobs],
            capture_output=True, text=True, env=env, timeout=30)
        return done.returncode, done.stdout + done.stderr

    def test_queue_stage_exits_when_the_job_starts(self):
        self.answer("squeue", "11", "11|RUNNING|None|2026-11-09T10:00:00")
        code, out = self.run_waiter("key=a,job=11,stage=queue")
        self.assertEqual(code, 0, out)
        self.assertIn("event a: job 11 left the queue: RUNNING", out)
        self.assertIn("a | 11 | queue | RUNNING | None | 2026-11-09T10:00:00", out)

    def test_pending_job_keeps_waiting_until_the_backstop(self):
        self.answer("squeue", "11", "11|PENDING|Priority|2026-11-10T04:00:00")
        code, out = self.run_waiter("key=a,job=11,stage=queue", backstop_hours="0")
        self.assertEqual(code, 4, out)
        self.assertIn("last state PENDING", out)
        self.assertIn("a | 11 | queue | PENDING | Priority | 2026-11-10T04:00:00", out)

    def test_job_squeue_forgot_is_read_from_sacct(self):
        # squeue no longer lists the job (exit 1); accounting still knows it was cancelled.
        self.answer("sacct", "11", "11|CANCELLED by 20606|None|None")
        code, out = self.run_waiter("key=a,job=11,stage=queue")
        self.assertEqual(code, 0, out)
        self.assertIn("event a: job 11 left the queue: CANCELLED", out)

    def test_job_neither_command_knows_is_a_failed_lookup_not_an_exit(self):
        code, out = self.run_waiter("key=a,job=11,stage=queue", backstop_hours="0")
        self.assertEqual(code, 4, out)
        self.assertIn("unknown (lookup failed)", out)

    def test_ssh_failure_is_a_failed_lookup(self):
        ssh = self.bin / "ssh"
        ssh.write_text(SSH_FAIL_STUB)
        ssh.chmod(0o755)
        code, out = self.run_waiter("key=a,job=11,stage=queue", host="cluster", backstop_hours="0")
        self.assertEqual(code, 4, out)
        self.assertIn("failed lookups during the wait: 1", out)

    def test_slurm_commands_run_in_utc(self):
        self.answer("squeue", "11", "11|RUNNING|None|$TZ")
        code, out = self.run_waiter("key=a,job=11,stage=queue")
        self.assertEqual(code, 0, out)
        self.assertIn("a | 11 | queue | RUNNING | None | UTC", out)

    def test_run_stage_exits_on_a_terminal_state(self):
        self.answer("sacct", "12", "12|COMPLETED|None|2026-11-09T10:00:00")
        code, out = self.run_waiter(f"key=b,job=12,stage=run,deadline={iso(60)}")
        self.assertEqual(code, 0, out)
        self.assertIn("event b: job 12 left its running states: COMPLETED", out)

    def test_run_stage_deadline(self):
        self.answer("squeue", "12", "12|RUNNING|None|2026-11-09T10:00:00")
        code, out = self.run_waiter(f"key=b,job=12,stage=run,deadline={iso(-1)}")
        self.assertEqual(code, 3, out)
        self.assertIn("passed; last state RUNNING", out)

    def test_run_stage_stall_rule(self):
        self.answer("squeue", "12", "12|RUNNING|None|2026-11-09T10:00:00")
        (self.dir / "stat_age").write_text("1000\n")
        code, out = self.run_waiter(f"key=b,job=12,stage=run,deadline={iso(60)},status_file=/x/run.json,stall=900")
        self.assertEqual(code, 5, out)
        self.assertIn("stall rule: /x/run.json unchanged for 1000 s while RUNNING", out)

    def test_several_jobs_exit_on_the_first_event_and_list_every_job(self):
        self.answer("squeue", "11", "11|PENDING|Priority|2026-11-10T04:00:00")
        self.answer("squeue", "12", "12|RUNNING|None|2026-11-09T09:00:00")
        self.answer("sacct", "13", "13|FAILED|None|2026-11-09T08:00:00")
        code, out = self.run_waiter("key=a,job=11,stage=queue",
                                    f"key=b,job=12,stage=run,deadline={iso(60)}",
                                    f"key=c,job=13,stage=run,deadline={iso(60)}")
        self.assertEqual(code, 0, out)
        self.assertIn("event c: job 13 left its running states: FAILED", out)
        self.assertNotIn("event a", out)
        self.assertNotIn("event b", out)
        for row in ("a | 11 | queue | PENDING", "b | 12 | run | RUNNING", "c | 13 | run | FAILED"):
            self.assertIn(row, out)

    def test_terminal_state_outranks_a_deadline_in_the_same_poll(self):
        self.answer("sacct", "12", "12|COMPLETED|None|2026-11-09T09:00:00")
        self.answer("squeue", "13", "13|RUNNING|None|2026-11-09T09:00:00")
        code, out = self.run_waiter(f"key=b,job=12,stage=run,deadline={iso(60)}",
                                    f"key=c,job=13,stage=run,deadline={iso(-1)}")
        self.assertEqual(code, 0, out)
        self.assertIn("event c: deadline", out)

    def test_usage_errors(self):
        for spec in ("key=a,job=11,stage=run",                 # run stage without a deadline
                     "key=a,job=11,stage=queue,deadline=2026-11-09T00:00:00Z",
                     "key=a b,job=11,stage=queue",             # key outside the Target Key pattern
                     "key=a,job=11;rm,stage=queue",            # job id that is not a job id
                     "key=a,job=11,stage=run,deadline=2026-11-09T00:00:00Z,stall=60"):
            code, out = self.run_waiter(spec)
            self.assertEqual(code, 2, f"{spec}: {out}")
        code, out = self.run_waiter("key=a,job=11,stage=queue", "key=a,job=12,stage=queue")
        self.assertEqual(code, 2, out)


if __name__ == "__main__":
    unittest.main()
