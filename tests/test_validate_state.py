"""Tests for the shared-waiter rules in skills/remote-training-monitor/scripts/validate_state.py."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "skills/remote-training-monitor/scripts/validate_state.py"


def state(**heartbeat):
    hb = {"harness": "claude-code", "mode": "completion", "id": "b2180saa9",
          "deadline": "2026-11-10T05:00:00Z", "durability": "session-bound", "project_dir": "/p"}
    hb.update(heartbeat)
    return {
        "target_key": "slurm-aicr-1704883", "run_name": "pex-lsc-s42", "plan_revision": 1,
        "run_state": "QUEUED", "since": "2026-11-08T05:00:00Z", "health": None,
        "monitor": {"state": "WATCHING", "reason": None}, "heartbeat": hb, "current_phase": 1,
        "current_attempt": {"attempt_id": "phase-1-attempt-1", "control_plane": "slurm", "scope": "aicr",
                            "job_id": "1704883"},
        "progress": {}, "checks": {"passed": 0, "total": 9}, "cursor": {},
        "next_action": "wait for the job to start", "last_observed": "2026-11-09T06:51:40Z", "retries": {},
    }


class ValidateCoversTest(unittest.TestCase):
    def validate(self, data):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(data, handle)
        done = subprocess.run([sys.executable, str(SCRIPT), handle.name], capture_output=True, text=True)
        Path(handle.name).unlink()
        return done.returncode, done.stdout

    def test_heartbeat_without_covers_is_valid(self):
        self.assertEqual(self.validate(state())[0], 0)

    def test_shared_waiter_listing_this_key_is_valid(self):
        code, out = self.validate(state(covers=["slurm-aicr-1704883", "slurm-aicr-1717323"]))
        self.assertEqual(code, 0, out)

    def test_covers_must_include_this_key(self):
        code, out = self.validate(state(covers=["slurm-aicr-1717323"]))
        self.assertEqual(code, 1)
        self.assertIn("must include this state's target_key", out)

    def test_covers_only_for_a_completion_waiter(self):
        code, out = self.validate(state(mode="interval", interval_min=30, covers=["slurm-aicr-1704883"]))
        self.assertEqual(code, 1)
        self.assertIn("only a completion waiter is shared", out)

    def test_covers_lists_each_key_once(self):
        code, out = self.validate(state(covers=["slurm-aicr-1704883", "slurm-aicr-1704883"]))
        self.assertEqual(code, 1)
        self.assertIn("lists a key twice", out)


if __name__ == "__main__":
    unittest.main()
