"""Evaluate a saved personal model on a later, untouched EEG session.

This script only reads trusted local checkpoints and prints offline results.
It cannot connect to or command the glove.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import joblib
import numpy as np

from train import BANDS, CHANNELS, LABELS, load_trials, score_model, trial_features


def evaluate_new_session(checkpoint, trials, participant):
    if checkpoint["evaluation"]["participant"] != participant:
        raise ValueError("Checkpoint participant does not match the recordings")
    if tuple(checkpoint["channels"]) != CHANNELS or tuple(map(tuple, checkpoint["bands"])) != BANDS:
        raise ValueError("Checkpoint feature layout does not match this evaluator")
    if any(trial["sample_rate"] != checkpoint["sample_rate"] for trial in trials):
        raise ValueError("Checkpoint sample rate does not match the recordings")
    history = checkpoint["evaluation"]
    prior = set(history["training_sessions"]) | {history["held_out_session"]}
    candidates = sorted({(trial["session_epoch"], trial["session_id"]) for trial in trials if trial["session_id"] not in prior})
    if not candidates:
        raise ValueError("Record another independent session after training before evaluating this checkpoint")
    newest = candidates[-1][1]
    records = [trial for trial in trials if trial["session_id"] == newest]
    clean = [(trial, features) for trial in records if (features := trial_features(trial)) is not None]
    counts = Counter(trial["label"] for trial, _ in clean)
    if any(counts[label] < 3 for label in LABELS):
        raise ValueError("The new session needs at least three usable trials per class; found {}".format(dict(counts)))
    model = checkpoint["model"]
    predictions = [model.classes_[np.argmax(model.predict_proba(features).mean(axis=0))] for _, features in clean]
    return {
        "participant": participant, "new_session": newest,
        "usable_trials": len(clean), "rejected_artifact_trials": len(records) - len(clean),
        "evaluation": score_model(model, clean),
        "trial_predictions": [{"trial_index": trial["trial_index"], "actual": trial["label"], "predicted": str(prediction)} for (trial, _), prediction in zip(clean, predictions)],
        "note": "Offline follow-up only. Predicted labels do not control the glove and are not clinical validation.",
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate a trusted Synova checkpoint on a new independent session")
    parser.add_argument("--participant", required=True)
    parser.add_argument("--model", type=Path, help="Trusted checkpoint saved by train.py")
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    args = parser.parse_args()
    model_path = args.model or Path(__file__).resolve().parent / "models" / (args.participant + ".joblib")
    # joblib uses pickle; never load a checkpoint obtained from someone else.
    checkpoint = joblib.load(model_path)
    trials = load_trials(sorted(args.data_dir.glob("*.jsonl")), args.participant)
    print(json.dumps(evaluate_new_session(checkpoint, trials, args.participant), indent=2))


if __name__ == "__main__":
    main()
