import unittest
import json
import tempfile
from pathlib import Path
from copy import deepcopy

try:
    import numpy as np
    from evaluate_new import evaluate_new_session
    from train import BANDS, CHANNELS
    from train import fit_evaluate, inspect_trials, load_trials, prepare_split
except ImportError:
    np = None


@unittest.skipIf(np is None, "Install scientific dependencies from requirements.txt")
class TrainingTests(unittest.TestCase):
    def test_newest_session_is_never_in_training_and_scores_trials(self):
        trials = []
        sample_rate = 256
        t = np.arange(4 * sample_rate) / sample_rate
        for session_index, session in enumerate(("first", "second")):
            for label, frequency in (("REST", 6), ("OPEN", 10), ("CLOSE", 20)):
                for index in range(6):
                    eeg = np.stack([8 * np.sin(2 * np.pi * frequency * t + channel / 5) for channel in range(4)])
                    trials.append({
                        "session_id": session,
                        "session_started_at": "2026-10-{:02d}T00:00:00+00:00".format(session_index + 1),
                        "session_epoch": 1760000000 + session_index * 86400,
                        "trial_index": index, "sample_rate": sample_rate,
                        "label": label, "eeg": eeg,
                    })
        train, test, held_out, rejected = prepare_split(trials)
        self.assertEqual(held_out, "second")
        self.assertEqual({row["session_id"] for row, _ in train}, {"first"})
        self.assertEqual({row["session_id"] for row, _ in test}, {"second"})
        self.assertEqual(dict(rejected), {})
        model, report = fit_evaluate(train, test)
        self.assertEqual(sum(sum(row) for row in report["confusion_matrix"]), 18)
        self.assertEqual(report["rest_trials"], 6)
        self.assertEqual(report["held_out_class_counts"], {"REST": 6, "OPEN": 6, "CLOSE": 6})
        self.assertAlmostEqual(report["majority_baseline_balanced_accuracy"], 1 / 3)
        quality = inspect_trials(trials)
        self.assertTrue(quality["ready_to_evaluate"])
        self.assertEqual(quality["sessions"][-1]["usable"], {"REST": 6, "OPEN": 6, "CLOSE": 6})
        trials[-1]["eeg"] = np.zeros((4, 4 * sample_rate))
        quality = inspect_trials(trials)
        self.assertEqual(quality["sessions"][-1]["rejected_artifact_trials"], 1)
        checkpoint = {"model": model, "channels": CHANNELS, "bands": BANDS, "sample_rate": sample_rate,
                      "evaluation": {"participant": "P01", "training_sessions": ["first"], "held_out_session": "second"}}
        with self.assertRaisesRegex(ValueError, "another independent session"):
            evaluate_new_session(checkpoint, trials, "P01")
        later = [deepcopy(row) for row in trials[:18] if row["trial_index"] < 3]
        for row in later:
            row["session_id"] = "third"
            row["session_epoch"] = 1760300000
        result = evaluate_new_session(checkpoint, trials + later, "P01")
        self.assertEqual(result["new_session"], "third")
        self.assertEqual(len(result["trial_predictions"]), 9)

    def test_loader_rejects_unequal_trial_lengths(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "P01_session.jsonl"
            record = {
                "schema_version": 1, "participant": "P01", "session_id": "first",
                "session_started_at": "2026-10-22T19:00:00+00:00", "trial_index": 1,
                "label": "REST", "sample_rate": 256,
                "channels": ["TP9", "AF7", "AF8", "TP10"], "units": "microvolts",
                "samples": [[1] * 1000 for _ in range(4)],
            }
            file.write_text(json.dumps(record) + "\n")
            with self.assertRaisesRegex(ValueError, "exactly four seconds"):
                load_trials([file], "P01")


if __name__ == "__main__":
    unittest.main()
