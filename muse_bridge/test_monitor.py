"""Offline monitor checks with synthetic fixtures; no headset or actuator."""

import unittest

import numpy as np

from monitor_open_rest import CandidateTracker, classify_window, validate_checkpoint
from record_open_rest import LABELS, PROTOCOL
from train_open_rest import FEATURE_VERSION, features, window_features


class FixedModel:
    classes_ = np.array(["OPEN_INTENT", "REST"])

    def __init__(self, p_open):
        self.p_open = p_open

    def predict_proba(self, input_features):
        assert input_features.shape == (1, 8)
        return np.array([[self.p_open, 1 - self.p_open]])


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.descriptor = {"sampling_rate": 256, "eeg_channels": [1, 2, 3, 4], "timestamp_channel": 6}
        t = np.arange(512) / 256
        self.raw = np.zeros((8, 512))
        for channel in range(4):
            self.raw[channel + 1] = 7 * np.sin(2 * np.pi * (10 + channel) * t)
        self.raw[6] = 1700000000 + t
        self.now = self.raw[6, -1] + 0.2

    def test_training_features_equal_two_live_windows(self):
        eeg = np.hstack([self.raw[1:5], self.raw[1:5]])
        expected = np.stack([window_features(eeg[:, :512]), window_features(eeg[:, 512:])])
        np.testing.assert_allclose(features(eeg), expected, rtol=1e-12, atol=1e-12)

    def test_classifies_fresh_signal_and_rejects_stale_or_bad(self):
        model = FixedModel(0.9)
        self.assertEqual(classify_window(model, self.raw, self.descriptor, self.now)["state"], "OPEN_INTENT")
        self.assertEqual(classify_window(FixedModel(0.1), self.raw, self.descriptor, self.now)["state"], "REST")
        self.assertEqual(classify_window(FixedModel(0.5), self.raw, self.descriptor, self.now)["state"], "UNCERTAIN")
        repeated = classify_window(model, self.raw, self.descriptor, self.now + 0.25,
                                   previous_timestamp=self.raw[6, -1])
        self.assertEqual(repeated["state"], "BAD_SIGNAL")
        self.assertEqual(repeated["signal_reasons"], ["no_new_eeg_samples"])
        stale = classify_window(model, self.raw, self.descriptor, self.now + 3)
        self.assertEqual(stale["state"], "BAD_SIGNAL")
        self.assertIsNone(stale["p_open"])
        self.assertEqual(classify_window(model, self.raw[:, :255], self.descriptor, self.now)["state"], "BAD_SIGNAL")
        bad = self.raw.copy()
        bad[1] = 0
        self.assertEqual(classify_window(model, bad, self.descriptor, self.now)["state"], "BAD_SIGNAL")
        self.assertEqual(classify_window(model, self.raw, {**self.descriptor, "eeg_channels": [2, 1, 3, 4]}, self.now)["state"], "BAD_SIGNAL")

    def test_candidate_requires_three_predictions_and_respects_quality_and_cooldown(self):
        tracker = CandidateTracker()
        self.assertFalse(tracker.update("OPEN_INTENT", 1))
        self.assertFalse(tracker.update("OPEN_INTENT", 1.25))
        self.assertFalse(tracker.update("BAD_SIGNAL", 1.5))
        self.assertFalse(tracker.update("OPEN_INTENT", 2))
        self.assertFalse(tracker.update("OPEN_INTENT", 2.25))
        self.assertTrue(tracker.update("OPEN_INTENT", 2.5))
        self.assertFalse(tracker.update("OPEN_INTENT", 2.75))
        self.assertFalse(tracker.update("OPEN_INTENT", 7.5))
        self.assertFalse(tracker.update("OPEN_INTENT", 7.75))
        self.assertTrue(tracker.update("OPEN_INTENT", 8))

    def test_checkpoint_requires_correct_participant_feature_schema_and_classes(self):
        checkpoint = {"participant": "P01", "feature_version": FEATURE_VERSION, "sample_rate": 256,
                      "channels": ["TP9", "AF7", "AF8", "TP10"], "split": {"protocol": PROTOCOL},
                      "model": FixedModel(0.8)}
        validate_checkpoint(checkpoint, "P01")
        with self.assertRaisesRegex(ValueError, "participant"):
            validate_checkpoint(checkpoint, "P02")
        with self.assertRaisesRegex(ValueError, "feature version"):
            validate_checkpoint({**checkpoint, "feature_version": "different"}, "P01")
        with self.assertRaisesRegex(ValueError, "channel layout"):
            validate_checkpoint({**checkpoint, "channels": LABELS}, "P01")


if __name__ == "__main__":
    unittest.main()
