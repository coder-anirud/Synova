"""Session-separated binary baseline for the Muse adaptation of NeuroGrip.

The newest session is reserved, not scored during fitting. A persisted split
keeps that session out of future training runs. No synthetic-data CLI exists.
"""

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import numpy as np
from scipy.signal import welch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from muse_device import CHANNELS, signal_quality
from record_open_rest import DATA_DIR, LABELS, PROTOCOL

FEATURE_VERSION = "muse-mu-beta-logpower-v1"
STUDY_TIMEZONE = ZoneInfo("America/New_York")


def discover_sessions(data_dir, participant):
    sessions = []
    for path in sorted(data_dir.glob("*/session.json")):
        meta = json.loads(path.read_text())
        if meta.get("participant") != participant:
            continue
        if meta.get("protocol") != PROTOCOL or meta.get("schema_version") != 2 or meta.get("recording_source") != "muse2":
            raise ValueError("Unsupported recording protocol/source: {}".format(path))
        if meta.get("channels") != list(CHANNELS) or meta.get("sample_rate") != 256 or meta.get("units") != "microvolts":
            raise ValueError("Unexpected Muse channel order, rate or units: {}".format(path))
        started = datetime.fromisoformat(meta["session_started_at"])
        if started.tzinfo is None:
            raise ValueError("Session time must include a timezone")
        if not isinstance(meta.get("session_id"), str) or not meta["session_id"]:
            raise ValueError("Session ID is required")
        sessions.append({"path": path.parent, "meta": meta, "epoch": started.timestamp()})
    if not sessions:
        raise ValueError("No two-class Muse recordings for this participant. Run record_open_rest.py first.")
    if len({s["meta"]["session_id"] for s in sessions}) != len(sessions):
        raise ValueError("Duplicate session IDs")
    return sorted(sessions, key=lambda s: (s["epoch"], s["meta"]["session_id"]))


def features(eeg, sample_rate=256):
    """Two 2-second windows, four channels × mu/beta log spectral power.

Welch band selection is the baseline's preprocessing. It does not claim to
implement the plan's full notch/bandpass/CSP comparison.
"""
    if eeg.shape != (4, 4 * sample_rate):
        raise ValueError("Features require exactly four seconds on four channels")
    return np.stack([window_features(eeg[:, offset:offset + 2 * sample_rate], sample_rate)
                     for offset in (0, 2 * sample_rate)])


def window_features(eeg, sample_rate=256):
    """The same eight features for training windows and display-only live inference."""
    if eeg.shape != (4, 2 * sample_rate) or not np.isfinite(eeg).all():
        raise ValueError("Features require exactly two finite seconds on four channels")
    centered = eeg - np.median(eeg, axis=1, keepdims=True)
    frequencies, density = welch(centered, fs=sample_rate, nperseg=sample_rate, axis=1)
    powers = [np.mean(density[:, (frequencies >= low) & (frequencies < high)], axis=1)
              for low, high in ((8, 13), (13, 30))]
    return np.log10(np.stack(powers, axis=1).reshape(8) + 1e-12)


def usable_trials(session):
    meta = session["meta"]
    clean, rejected = [], Counter()
    seen = set()
    for line_number, line in enumerate((session["path"] / "trials.jsonl").read_text().splitlines(), 1):
        row = json.loads(line)
        index = row.get("trial_index")
        if type(index) is not int or index < 1 or index in seen or row.get("label") not in LABELS:
            raise ValueError("Invalid/duplicate trial in {}:{}".format(session["path"], line_number))
        seen.add(index)
        if row.get("protocol") != PROTOCOL or row.get("schema_version") != 2:
            raise ValueError("Trial protocol does not match session")
        if index in meta.get("excluded_trials", []):
            rejected["participant_marked"] += 1
            continue
        if not row.get("quality", {}).get("usable"):
            rejected["recording_quality"] += 1
            continue
        eeg = np.asarray(row["samples"], dtype=float)
        timestamps = np.asarray(row["timestamps"], dtype=float)
        if eeg.shape != (4, 1024) or timestamps.shape != (1024,):
            raise ValueError("Kept trial must contain exactly four seconds on four channels")
        if not signal_quality(eeg, timestamps, 256, 4)["usable"]:
            rejected["rechecked_quality"] += 1
            continue
        fingerprint = hashlib.sha256(eeg.astype("<f8").tobytes()).hexdigest()
        clean.append({"trial_index": index, "label": row["label"], "features": features(eeg),
                      "fingerprint": fingerprint, "session_id": meta["session_id"]})
    return clean, dict(rejected)


def select_split(sessions, pilot=False):
    complete = [s for s in sessions if s["meta"].get("completed") and not s["meta"].get("practice", False)]
    minimum = 3 if pilot else 6
    if len(complete) < minimum:
        raise ValueError("Need {} complete sessions ({} found). --pilot allows an early three-session experiment.".format(minimum, len(complete)))
    if not pilot:
        first = datetime.fromisoformat(complete[0]["meta"]["session_started_at"]).astimezone(STUDY_TIMEZONE).date()
        last = datetime.fromisoformat(complete[-1]["meta"]["session_started_at"]).astimezone(STUDY_TIMEZONE).date()
        if (last - first).days < 6:
            raise ValueError("Full-study sessions must cover at least seven calendar dates; use --pilot for an early experiment")
    return {"protocol": PROTOCOL, "training": [s["meta"]["session_id"] for s in complete[:-2]],
            "validation": complete[-2]["meta"]["session_id"], "final_test": complete[-1]["meta"]["session_id"],
            "pilot": pilot}


def require_counts(trials, minimum, partition):
    counts = Counter(t["label"] for t in trials)
    if any(counts[label] < minimum for label in LABELS):
        raise ValueError("{} needs {} usable trials/class; found {}".format(partition, minimum, dict(counts)))


def score(model, trials):
    actual = [t["label"] for t in trials]
    predicted = [str(model.classes_[np.argmax(model.predict_proba(t["features"]).mean(axis=0))]) for t in trials]
    matrix = confusion_matrix(actual, predicted, labels=LABELS)
    return {"balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
            "majority_baseline_balanced_accuracy": 0.5,
            "macro_f1": float(f1_score(actual, predicted, labels=LABELS, average="macro", zero_division=0)),
            "labels": list(LABELS), "confusion_matrix": matrix.tolist(),
            "class_counts": dict(Counter(actual)), "rest_false_predictions": int(matrix[0, 1]),
            "rest_trials": int(matrix[0].sum()),
            "predictions": [{"trial_index": t["trial_index"], "actual": t["label"], "predicted": p} for t, p in zip(trials, predicted)],
            "note": "Offline predictions only. Trial errors are not actuator false activations per minute."}


def fit_baseline(training, validation):
    require_counts(training, 6, "Training")
    require_counts(validation, 3, "Validation")
    fingerprints = [t["fingerprint"] for t in training + validation]
    if len(set(fingerprints)) != len(fingerprints):
        raise ValueError("Duplicate EEG trials across training/validation")
    model = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=1000, random_state=0))
    model.fit(np.vstack([t["features"] for t in training]), [t["label"] for t in training for _ in t["features"]])
    return model, score(model, validation)


def main():
    parser = argparse.ArgumentParser(description="Train the two-class Muse baseline with frozen session partitions")
    parser.add_argument("--participant", required=True)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--inspect", action="store_true", help="Count trials and quality exclusions without training")
    parser.add_argument("--pilot", action="store_true", help="Allow an early three-session experiment")
    parser.add_argument("--output", type=Path, help="New checkpoint path; existing files are never overwritten")
    parser.add_argument("--final-test", type=Path, help="Evaluate a trusted local checkpoint on its reserved session once")
    args = parser.parse_args()
    if not args.participant or not args.participant.isascii() or not all(c.isalnum() or c in "-_" for c in args.participant):
        parser.error("Use a pseudonym with ASCII letters, numbers, - or _")
    if args.final_test and (args.inspect or args.output or args.pilot):
        parser.error("--final-test cannot be combined with inspect, output or pilot")
    sessions = discover_sessions(args.data_dir, args.participant)
    lookup = {s["meta"]["session_id"]: s for s in sessions}
    if args.inspect:
        for session in sessions:
            clean, rejected = usable_trials(session)
            print(json.dumps({"session_id": session["meta"]["session_id"], "complete": session["meta"].get("completed", False),
                              "practice_excluded_from_model": bool(session["meta"].get("practice", False)),
                              "usable": dict(Counter(t["label"] for t in clean)), "rejected": rejected}))
        print("Plan target: 6 sessions, 30 trials/class/session, across at least 7 calendar days. Quality counts are not accuracy.")
        return
    if args.final_test:
        # joblib uses pickle: accept only checkpoints you created locally.
        checkpoint = joblib.load(args.final_test)
        if checkpoint.get("participant") != args.participant or checkpoint.get("feature_version") != FEATURE_VERSION:
            raise ValueError("Checkpoint participant or feature version mismatch")
        session = lookup[checkpoint["split"]["final_test"]]
        result_path = session["path"] / "final_evaluation.json"
        if result_path.exists():
            raise ValueError("Final session already evaluated. Review {} without tuning on it.".format(result_path))
        trials, rejected = usable_trials(session)
        require_counts(trials, 3, "Final test")
        if len({t["fingerprint"] for t in trials}) != len(trials):
            raise ValueError("Final test contains duplicate EEG trials")
        if any(t["fingerprint"] in checkpoint["development_fingerprints"] for t in trials):
            raise ValueError("Final test contains EEG duplicated from model development")
        report = {"partition": "final_test", "session_id": session["meta"]["session_id"],
                  "evaluation": score(checkpoint["model"], trials), "rejected": rejected,
                  "checkpoint": args.final_test.name}
        with result_path.open("x") as output:
            json.dump(report, output, indent=2, allow_nan=False)
        print(json.dumps(report, indent=2))
        return
    split_path = args.data_dir / (args.participant + "_split.json")
    if split_path.exists():
        split = json.loads(split_path.read_text())
        if bool(split.get("pilot")) != args.pilot:
            raise ValueError("The frozen split is for a {} study. Keep pilot and full-study partitions separate.".format("pilot" if split.get("pilot") else "full"))
    else:
        split = select_split(sessions, args.pilot)
    ids = split["training"] + [split["validation"], split["final_test"]]
    if len(set(ids)) != len(ids) or any(i not in lookup for i in ids):
        raise ValueError("Frozen partitions overlap or reference missing sessions")
    if split.get("protocol") != PROTOCOL or any(not lookup[i]["meta"].get("completed") or lookup[i]["meta"].get("practice", False) for i in ids):
        raise ValueError("Frozen partitions must use complete sessions with the matching protocol")
    training, rejected = [], {}
    for session_id in split["training"]:
        clean, failures = usable_trials(lookup[session_id])
        training.extend(clean)
        rejected[session_id] = failures
    validation, rejected[split["validation"]] = usable_trials(lookup[split["validation"]])
    # No final-test trial bytes are read on this path.
    model, metrics = fit_baseline(training, validation)
    report = {"participant": args.participant, "split": split, "training_trials": len(training),
              "validation": metrics, "rejected": rejected, "final_test_scored": False,
              "note": "Muse feasibility baseline; no motor-cortex coverage, actuator control, or clinical validation."}
    if not split_path.exists():
        with split_path.open("x") as output:
            json.dump(split, output, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {"model": model, "participant": args.participant, "split": split,
                      "feature_version": FEATURE_VERSION, "sample_rate": 256, "channels": CHANNELS,
                      "development_fingerprints": [t["fingerprint"] for t in training + validation], "report": report}
        with args.output.open("xb") as output:
            joblib.dump(checkpoint, output)
        print("Saved research checkpoint: {}".format(args.output))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
