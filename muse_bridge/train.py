"""Train and evaluate a personal, offline EEG imagery baseline.

Only labeled raw trials from record.py or import_csv.py are accepted. The newest entire session is held
out, and all windows from a trial stay together. This script never sends glove
commands or reports a score from demo/synthetic signals.
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.signal import welch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

LABELS = ("REST", "OPEN", "CLOSE")
CHANNELS = ("TP9", "AF7", "AF8", "TP10")
BANDS = ((4, 8), (8, 13), (13, 30))
SCHEMA_VERSION = 1


def load_trials(paths, participant):
    trials = []
    seen = set()
    imported_sources = set()
    for path in paths:
        with path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    if row["participant"] != participant:
                        continue
                    key = (row["session_id"], row["trial_index"])
                    if key in seen:
                        raise ValueError("duplicate trial")
                    seen.add(key)
                    if "source_file" in row:
                        if row["source_file"] in imported_sources:
                            raise ValueError("CSV recording imported more than once")
                        imported_sources.add(row["source_file"])
                    if row["schema_version"] != SCHEMA_VERSION or tuple(row["channels"]) != CHANNELS or row["units"] != "microvolts":
                        raise ValueError("unsupported schema, channels, or units")
                    if row["label"] not in LABELS or type(row["sample_rate"]) is not int or row["sample_rate"] < 64:
                        raise ValueError("invalid label or sample rate")
                    if type(row["trial_index"]) is not int or row["trial_index"] < 1 or not isinstance(row["session_id"], str) or not row["session_id"]:
                        raise ValueError("invalid trial or session ID")
                    started = datetime.fromisoformat(row["session_started_at"])
                    if started.tzinfo is None:
                        raise ValueError("session start must include a timezone")
                    row["session_epoch"] = started.timestamp()
                    eeg = np.asarray(row["samples"], dtype=float)
                    if eeg.shape != (4, 4 * row["sample_rate"]):
                        raise ValueError("expected exactly four seconds on four channels")
                    if not np.isfinite(eeg).all():
                        raise ValueError("non-finite EEG")
                    row["eeg"] = eeg
                    trials.append(row)
                except (KeyError, TypeError, ValueError, OverflowError) as exc:
                    raise ValueError("{}:{}: {}".format(path, line_number, exc)) from exc
    if not trials:
        raise ValueError("No real trials found for participant {!r}".format(participant))
    rates = {row["sample_rate"] for row in trials}
    if len(rates) != 1:
        raise ValueError("All sessions must use the same sampling rate")
    sessions = {}
    for row in trials:
        session = sessions.setdefault(row["session_id"], (row["session_started_at"], row["participant"]))
        if session != (row["session_started_at"], row["participant"]):
            raise ValueError("Inconsistent session metadata")
    return trials


def window_features(window, sample_rate):
    """Return 12 log-band-power features or None for an obvious signal artifact."""
    centered = window - np.median(window, axis=1, keepdims=True)
    spread = centered.std(axis=1)
    if (np.max(np.abs(centered), axis=1) > 250).any() or (spread < 0.5).any():
        return None
    frequencies, density = welch(centered, fs=sample_rate, nperseg=sample_rate, axis=1)
    return np.asarray([
        np.log10(np.mean(density[channel, (frequencies >= low) & (frequencies < high)]) + 1e-12)
        for channel in range(4) for low, high in BANDS
    ])


def trial_features(trial):
    size = 2 * trial["sample_rate"]
    windows = [trial["eeg"][:, offset:offset + size] for offset in range(0, trial["eeg"].shape[1] - size + 1, size)]
    features = [window_features(window, trial["sample_rate"]) for window in windows]
    # Discard the whole trial if a window is unusable; no selective label leakage.
    if not features or any(feature is None for feature in features):
        return None
    return np.stack(features)


def prepare_split(trials):
    sessions = sorted({(row["session_epoch"], row["session_id"]) for row in trials})
    if len(sessions) < 2:
        raise ValueError("Record at least two separate sessions; the newest is held out")
    test_session = sessions[-1][1]
    train, test = [], []
    rejected = Counter()
    for trial in trials:
        features = trial_features(trial)
        if features is None:
            rejected[trial["session_id"]] += 1
            continue
        (test if trial["session_id"] == test_session else train).append((trial, features))
    for name, items, minimum in (("training", train, 6), ("held-out", test, 3)):
        counts = Counter(trial["label"] for trial, _ in items)
        missing = [label for label in LABELS if counts[label] < minimum]
        if missing:
            raise ValueError("{} set needs at least {} clean trials per class; short: {}. Rejected artifact trials: {}".format(name, minimum, ", ".join(missing), dict(rejected)))
    return train, test, test_session, rejected


def inspect_trials(trials):
    """Summarize recorded and usable trials without fitting a model."""
    sessions = sorted({(row["session_epoch"], row["session_id"]) for row in trials})
    result = []
    for _, session_id in sessions:
        rows = [row for row in trials if row["session_id"] == session_id]
        clean = Counter(row["label"] for row in rows if trial_features(row) is not None)
        recorded = Counter(row["label"] for row in rows)
        result.append({
            "session_id": session_id,
            "recorded": {label: recorded[label] for label in LABELS},
            "usable": {label: clean[label] for label in LABELS},
            "rejected_artifact_trials": sum(recorded.values()) - sum(clean.values()),
            "imported_csv_trials": sum("source_file" in row for row in rows),
        })
    earlier = Counter()
    for item in result[:-1]:
        earlier.update(item["usable"])
    newest = result[-1]["usable"]
    return {
        "sessions": result,
        "ready_to_evaluate": len(result) >= 2 and all(earlier[label] >= 6 and newest[label] >= 3 for label in LABELS),
        "minimum": "At least 6 usable trials per class in earlier session(s) and 3 per class in the newest session",
    }


def fit_evaluate(train, test):
    # StandardScaler is fit only inside the training set. Each complete trial
    # contributes an equal number of non-overlapping two-second windows.
    x_train = np.vstack([features for _, features in train])
    y_train = [trial["label"] for trial, features in train for _ in features]
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced"))
    model.fit(x_train, y_train)
    majority_label = Counter(trial["label"] for trial, _ in train).most_common(1)[0][0]
    return model, score_model(model, test, majority_label)


def score_model(model, test, majority_label=None):
    """Score complete labeled trials, averaging each trial's window predictions."""
    actual = [trial["label"] for trial, _ in test]
    predicted = [model.classes_[np.argmax(model.predict_proba(features).mean(axis=0))] for _, features in test]
    matrix = confusion_matrix(actual, predicted, labels=LABELS)
    report = {
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
        "macro_f1": float(f1_score(actual, predicted, labels=LABELS, average="macro", zero_division=0)),
        "confusion_matrix": matrix.tolist(), "labels": list(LABELS),
        "held_out_class_counts": dict(Counter(actual)),
        "rest_false_activations": int(sum(matrix[0, 1:])),
        "rest_trials": int(sum(matrix[0, :])),
        "per_class_recall": {label: float(matrix[i, i] / sum(matrix[i, :])) for i, label in enumerate(LABELS)},
    }
    if majority_label is not None:
        report["training_majority_class"] = majority_label
        report["majority_baseline_balanced_accuracy"] = float(balanced_accuracy_score(actual, [majority_label] * len(actual)))
    return report


def main():
    parser = argparse.ArgumentParser(description="Evaluate Muse 2 imagery from real, labeled sessions")
    parser.add_argument("--participant", required=True)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("--output", type=Path, help="Optional local model checkpoint (never enables glove control)")
    parser.add_argument("--inspect", action="store_true", help="Report trial quality and class counts without training")
    args = parser.parse_args()
    paths = sorted(args.data_dir.glob("*.jsonl"))
    trials = load_trials(paths, args.participant)
    if args.inspect:
        print(json.dumps(inspect_trials(trials), indent=2))
        return
    train, test, test_session, rejected = prepare_split(trials)
    model, metrics = fit_evaluate(train, test)
    result = {
        "participant": args.participant, "training_sessions": sorted({trial["session_id"] for trial, _ in train}),
        "held_out_session": test_session, "training_trials": len(train), "held_out_trials": len(test),
        "rejected_artifact_trials": dict(rejected), "evaluation": metrics,
        "note": "Offline feasibility result only; no glove commands or clinical validation.",
    }
    print(json.dumps(result, indent=2))
    if args.output:
        import joblib
        args.output.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": model, "channels": CHANNELS, "sample_rate": train[0][0]["sample_rate"], "bands": BANDS, "evaluation": result}, args.output)
        print("Saved local research checkpoint: {}".format(args.output))


if __name__ == "__main__":
    main()
