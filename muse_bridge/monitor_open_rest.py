"""Display-only research monitor for a validated local Muse checkpoint.

It reads a headset and writes probability/quality decisions; it has no glove,
actuator, network bridge or movement command dependency.
"""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import uuid

import joblib
import numpy as np
from brainflow.exit_codes import BrainFlowError

from muse_device import CHANNELS, connected_muse, signal_quality
from record_open_rest import LABELS, PROTOCOL
from train_open_rest import FEATURE_VERSION, window_features

RATE = 256
WINDOW = 2 * RATE
INTERVAL = 0.25
OUTPUT_DIR = Path(__file__).resolve().parent / "data" / "monitor"


def validate_checkpoint(checkpoint, participant):
    if checkpoint.get("participant") != participant or checkpoint.get("feature_version") != FEATURE_VERSION:
        raise ValueError("Checkpoint belongs to another participant or feature version")
    if checkpoint.get("sample_rate") != RATE or tuple(checkpoint.get("channels", ())) != CHANNELS:
        raise ValueError("Checkpoint does not match the Muse 2 channel layout and rate")
    if checkpoint.get("split", {}).get("protocol") != PROTOCOL:
        raise ValueError("Expected a two-class Muse checkpoint with recorded session partitions")
    if tuple(checkpoint["model"].classes_) != tuple(sorted(LABELS)):
        raise ValueError("Checkpoint classifier must contain REST and OPEN_INTENT")


def classify_window(model, raw, descriptor, now=None, threshold=0.75, previous_timestamp=None):
    """Decide from fresh EEG only; never interpret a stale or poor signal."""
    now = time.time() if now is None else now
    result = {"state": "BAD_SIGNAL", "p_open": None, "signal_reasons": []}
    if descriptor["sampling_rate"] != RATE or list(descriptor["eeg_channels"]) != [1, 2, 3, 4]:
        result["signal_reasons"].append("unsupported_board_layout")
        return result
    if raw.shape[1] < WINDOW:
        result["signal_reasons"].append("waiting_for_two_seconds_of_eeg")
        return result
    timestamps = raw[descriptor["timestamp_channel"], -WINDOW:]
    eeg = raw[descriptor["eeg_channels"], -WINDOW:]
    if previous_timestamp is not None and timestamps[-1] <= previous_timestamp:
        result["signal_reasons"].append("no_new_eeg_samples")
        return result
    age = now - timestamps[-1]
    if not np.isfinite(age) or age < -0.5 or age >= 2:
        result["signal_reasons"].append("stale_or_invalid_eeg_timestamp")
        return result
    quality = signal_quality(eeg, timestamps, RATE, 2)
    if not quality["usable"]:
        result["signal_reasons"] = quality["reasons"]
        return result
    feature = window_features(eeg, RATE)
    probabilities = model.predict_proba(feature.reshape(1, -1))[0]
    classes = tuple(model.classes_)
    p_open = float(probabilities[classes.index("OPEN_INTENT")])
    if not np.isfinite(p_open) or not 0 <= p_open <= 1:
        result["signal_reasons"].append("invalid_prediction_probability")
        return result
    result["p_open"] = p_open
    if p_open >= threshold:
        result["state"] = "OPEN_INTENT"
    elif 1 - p_open >= threshold:
        result["state"] = "REST"
    else:
        result["state"] = "UNCERTAIN"
    return result


class CandidateTracker:
    """Count would-be activations for bench research, never issue a command."""

    def __init__(self, consecutive=3, cooldown=5):
        self.consecutive = consecutive
        self.cooldown = cooldown
        self.streak = 0
        self.next_allowed = 0

    def update(self, state, now):
        if state != "OPEN_INTENT":
            self.streak = 0
            return False
        if now < self.next_allowed:
            self.streak = 0
            return False
        self.streak += 1
        if self.streak < self.consecutive:
            return False
        self.streak = 0
        self.next_allowed = now + self.cooldown
        return True


def monitor(board, descriptor, checkpoint, output_dir, duration, condition, threshold):
    if descriptor["sampling_rate"] != RATE or list(descriptor["eeg_channels"]) != [1, 2, 3, 4]:
        raise ValueError("Expected Muse 2 with TP9/AF7/AF8/TP10 at 256 Hz")
    output_dir.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    output = output_dir / (name + ".csv")
    tracker = CandidateTracker()
    count, bad, candidates = 0, 0, 0
    start = time.monotonic()
    next_tick = start
    last_display = None
    last_timestamp = None
    with output.open("x", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["utc_time", "elapsed_seconds", "condition", "state", "p_open", "signal_reasons", "candidate_event"])
        try:
            while time.monotonic() - start < duration:
                next_tick += INTERVAL
                now = time.time()
                try:
                    raw = board.get_current_board_data(WINDOW)
                except BrainFlowError:
                    raw = None
                    decision = {"state": "BAD_SIGNAL", "p_open": None, "signal_reasons": ["stream_read_failed"]}
                else:
                    decision = classify_window(checkpoint["model"], raw, descriptor, now, threshold, last_timestamp)
                    if raw.shape[1] >= WINDOW and np.isfinite(raw[descriptor["timestamp_channel"], -1]):
                        last_timestamp = max(last_timestamp or float("-inf"), float(raw[descriptor["timestamp_channel"], -1]))
                candidate = tracker.update(decision["state"], time.monotonic())
                count += 1
                bad += decision["state"] == "BAD_SIGNAL"
                candidates += candidate
                elapsed = time.monotonic() - start
                writer.writerow([datetime.now(timezone.utc).isoformat(), "{:.3f}".format(elapsed), condition,
                                 decision["state"], decision["p_open"], "|".join(decision["signal_reasons"]), int(candidate)])
                file.flush()
                if decision["state"] != last_display or candidate or count % 4 == 0:
                    probability = "—" if decision["p_open"] is None else "{:.2f}".format(decision["p_open"])
                    print("{:6.1f}s  {:12s}  P(open)={}  candidate={}".format(elapsed, decision["state"], probability, candidate), flush=True)
                    last_display = decision["state"]
                time.sleep(max(0, next_tick - time.monotonic()))
        except KeyboardInterrupt:
            print("Stopped; partial monitor log saved.", flush=True)
    elapsed = time.monotonic() - start
    summary = {"condition": condition, "elapsed_seconds": round(elapsed, 2), "decisions": count,
               "bad_signal_decisions": bad, "candidate_events": candidates,
               "candidate_events_per_minute": round(candidates * 60 / elapsed, 3) if elapsed else None,
               "log": str(output), "classifier_controls_glove": False,
               "note": "Threshold and persistence are exploratory starting settings; candidate events are not physical activations."}
    (output_dir / (name + "_summary.json")).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser(description="Display-only Muse probability and signal check; never controls the glove")
    parser.add_argument("--participant", required=True)
    parser.add_argument("--model", type=Path, help="Trusted checkpoint generated locally by train_open_rest.py")
    parser.add_argument("--device-name", default="")
    parser.add_argument("--duration", type=int, default=60, help="Seconds of live monitoring (5–600)")
    parser.add_argument("--condition", choices=("unlabeled", "rest", "imagined_open"), default="unlabeled")
    parser.add_argument("--threshold", type=float, default=0.75, help="Exploratory confidence threshold")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    if not args.participant or not args.participant.isascii() or not all(c.isalnum() or c in "-_" for c in args.participant):
        parser.error("Participant must use ASCII letters, numbers, - or _")
    if not 5 <= args.duration <= 600 or not np.isfinite(args.threshold) or not 0.5 < args.threshold < 1:
        parser.error("Duration must be 5–600 seconds and threshold between 0.5 and 1")
    model_path = args.model or Path(__file__).resolve().parent / "models" / (args.participant + "_open_rest.joblib")
    # joblib uses pickle: load checkpoints you created locally, never downloaded files.
    checkpoint = joblib.load(model_path)
    validate_checkpoint(checkpoint, args.participant)
    print("Display-only Muse monitor. No actuator interface exists in this process.", flush=True)
    with connected_muse(args.device_name) as (board, descriptor):
        print(json.dumps(monitor(board, descriptor, checkpoint, args.output_dir, args.duration, args.condition, args.threshold), indent=2))


if __name__ == "__main__":
    main()
