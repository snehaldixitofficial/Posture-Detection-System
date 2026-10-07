"""Guided recording control-flow tests; no real camera or invented observations."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research.dataset import record_session
from research.features import LABELS


class RecordingSessionTests(unittest.TestCase):
    def test_guided_session_preserves_all_class_and_take_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            calls = []
            def fake_record(args):
                calls.append((args.posture, args.take))
                return Path(folder) / f"fixture_{args.posture}_{args.take}.mp4"
            args = SimpleNamespace(subject="S01", dataset=folder, takes=2, start_take=1,
                                   seconds=60, trim=5, camera=0, extract_after=False)
            with patch("research.dataset.record", fake_record):
                record_session(args)
            self.assertEqual(calls, [(label, take) for take in (1, 2) for label in LABELS])
            state = json.loads(next(Path(folder).glob("session_*.json")).read_text())
            self.assertEqual(state["status"], "recordings_complete_review_required")
            self.assertEqual(len(state["clips"]), 8)

    def test_cancelling_stops_sequence(self):
        with tempfile.TemporaryDirectory() as folder:
            args = SimpleNamespace(subject="S01", dataset=folder, takes=2, start_take=1,
                                   seconds=60, trim=5, camera=0, extract_after=False)
            with patch("research.dataset.record", return_value=False) as recorder:
                record_session(args)
            self.assertEqual(recorder.call_count, 1)
            state = json.loads(next(Path(folder).glob("session_*.json")).read_text())
            self.assertEqual(state["status"], "cancelled")
            self.assertEqual(state["clips"], [])
