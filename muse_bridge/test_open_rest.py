"""Synthetic fixtures test software behavior, never headset/model performance."""

from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from check_headset import run_probe
from muse_device import CHANNELS, signal_quality
from record_open_rest import PROTOCOL, extract_trial, session_schedule


def fixture_eeg(seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(1024) / 256
    return np.stack([10 * np.sin(2 * np.pi * (10 + channel) * t) for channel in range(4)]) + rng.normal(0, 0.2, (4, 1024))


class OpenRestTests(unittest.TestCase):
    def test_two_runs_are_balanced_with_label_independent_recovery(self):
        schedule = session_schedule(30, 42)
        self.assertEqual(schedule, session_schedule(30, 42))
        self.assertEqual(len(schedule), 60)
        for run in (1, 2):
            for label in ("REST", "OPEN_INTENT"):
                self.assertEqual(sum(x["run"] == run and x["label"] == label for x in schedule), 15)
        self.assertTrue(all(3 <= x["recovery_seconds"] <= 5 for x in schedule))

    def test_rejects_flatline_dropout_large_artifact_and_nonfinite(self):
        timestamps = 1700000000 + np.arange(1024) / 256
        clean = fixture_eeg()
        self.assertTrue(signal_quality(clean, timestamps, 256, 4)["usable"])
        for kind in ("flat", "amplitude", "nan", "gap", "reversed", "short"):
            eeg, times = clean.copy(), timestamps.copy()
            if kind == "flat": eeg[0] = 0
            if kind == "amplitude": eeg[0, 500] = 1000
            if kind == "nan": eeg[0, 500] = np.nan
            if kind == "gap": times[500:] += 0.1
            if kind == "reversed": times[500] = times[499]
            if kind == "short": eeg, times = eeg[:, :-1], times[:-1]
            with self.subTest(kind=kind):
                self.assertFalse(signal_quality(eeg, times, 256, 4)["usable"])

    def test_epoch_is_marker_aligned_and_rejects_missing_end_marker(self):
        descriptor = {"eeg_channels": [1, 2, 3, 4], "timestamp_channel": 6, "marker_channel": 7, "sampling_rate": 256}
        raw = np.zeros((8, 1600))
        raw[6] = 1700000000 + np.arange(1600) / 256
        raw[1:5, 256:1280] = fixture_eeg()
        raw[7, 256] = 110
        raw[7, 1280] = 111
        result = extract_trial(raw, descriptor, 110)
        self.assertTrue(result["quality"]["usable"])
        np.testing.assert_array_equal(result["samples"], fixture_eeg())
        self.assertEqual(result["cue_sample_timestamp"], raw[6, 256])
        raw[7, 1280] = 0
        self.assertIn("cue_duration_mismatch", extract_trial(raw, descriptor, 110)["quality"]["reasons"])
        raw[7, 256] = 0
        self.assertFalse(extract_trial(raw, descriptor, 110)["quality"]["usable"])

    def test_bluetooth_failure_has_actionable_diagnostic(self):
        completed = type("Result", (), {"stdout": "Bluetooth is not enabled", "stderr": "", "returncode": 1})()
        with patch("check_headset.subprocess.run", return_value=completed):
            result = run_probe()
        self.assertEqual(result["status"], "connection_failed")
        self.assertIn("System Settings", result["message"])

    def test_fitting_never_reads_final_trials_and_freezes_split(self):
        from train_open_rest import discover_sessions, main, select_split, usable_trials

        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            for number in range(6):
                folder = base / ("session" + str(number))
                folder.mkdir()
                meta = {"participant": "P01", "protocol": PROTOCOL, "schema_version": 2,
                        "recording_source": "muse2", "channels": list(CHANNELS), "sample_rate": 256,
                        "units": "microvolts", "session_id": "s" + str(number), "completed": True,
                        "session_started_at": (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=number * 2)).isoformat(),
                        "excluded_trials": [12]}
                (folder / "session.json").write_text(json.dumps(meta))
                if number == 5:
                    # Deliberately unreadable: fitting must not touch this file.
                    (folder / "trials.jsonl").write_text("FINAL SESSION MUST STAY UNREAD")
                    continue
                rows = []
                for trial in range(12):
                    rows.append({"protocol": PROTOCOL, "schema_version": 2, "trial_index": trial + 1,
                                 "label": "REST" if trial < 6 else "OPEN_INTENT", "quality": {"usable": True},
                                 "samples": fixture_eeg(number * 100 + trial).tolist(),
                                 "timestamps": (1700000000 + number * 86400 + trial * 10 + np.arange(1024) / 256).tolist()})
                (folder / "trials.jsonl").write_text("\n".join(json.dumps(row) for row in rows))
            sessions = discover_sessions(base, "P01")
            split = select_split(sessions)
            self.assertEqual(split["training"], ["s0", "s1", "s2", "s3"])
            self.assertEqual((split["validation"], split["final_test"]), ("s4", "s5"))
            practice = {**sessions[-1], "meta": {**sessions[-1]["meta"], "session_id": "practice-later", "practice": True},
                        "epoch": sessions[-1]["epoch"] + 10000}
            self.assertEqual(select_split(sessions + [practice]), split)
            compressed = [{**session, "meta": {**session["meta"], "session_started_at":
                           (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=index)).isoformat()}}
                          for index, session in enumerate(sessions)]
            with self.assertRaisesRegex(ValueError, "seven calendar dates"):
                select_split(compressed)
            clean, rejected = usable_trials(sessions[0])
            self.assertEqual(len(clean), 11)
            self.assertEqual(rejected, {"participant_marked": 1})
            model_path = base / "baseline.joblib"
            with patch("sys.argv", ["train_open_rest.py", "--participant", "P01", "--data-dir", str(base), "--output", str(model_path)]), redirect_stdout(io.StringIO()) as output:
                main()
            report = json.loads(output.getvalue().split("\n", 1)[1])
            self.assertFalse(report["final_test_scored"])
            self.assertEqual(json.loads((base / "P01_split.json").read_text()), split)
            final_rows = []
            for trial in range(6):
                final_rows.append({"protocol": PROTOCOL, "schema_version": 2, "trial_index": trial + 1,
                                   "label": "REST" if trial < 3 else "OPEN_INTENT", "quality": {"usable": True},
                                   "samples": fixture_eeg(900 + trial).tolist(),
                                   "timestamps": (1700900000 + trial * 10 + np.arange(1024) / 256).tolist()})
            (base / "session5" / "trials.jsonl").write_text("\n".join(json.dumps(row) for row in final_rows))
            with patch("sys.argv", ["train_open_rest.py", "--participant", "P01", "--data-dir", str(base), "--final-test", str(model_path)]), redirect_stdout(io.StringIO()):
                main()
                with self.assertRaisesRegex(ValueError, "already evaluated"):
                    main()
            result = json.loads((base / "session5" / "final_evaluation.json").read_text())
            self.assertEqual(result["session_id"], "s5")
            self.assertEqual(result["evaluation"]["class_counts"], {"REST": 3, "OPEN_INTENT": 3})


if __name__ == "__main__":
    unittest.main()
