"""Collect labeled, raw Muse 2 trials for offline Synova research.

Run this instead of server.py: only one process can own the headset at a time.
Each completed trial is flushed to JSONL immediately. No simulated EEG is used.
"""

import argparse
import json
import math
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

LABELS = ("REST", "OPEN", "CLOSE")
CHANNELS = ("TP9", "AF7", "AF8", "TP10")


def trial_order(blocks, seed=None):
    rng = random.Random(seed)
    order = []
    for _ in range(blocks):
        block = list(LABELS)
        rng.shuffle(block)
        order.extend(block)
    return order


def capture_trial(board, eeg_channels, sampling_rate, duration=4.5, discard=0.5):
    """Discard pre-cue samples and the first 0.5 seconds after the cue."""
    board.get_board_data()  # flush the previous cue and inter-trial period
    required = round(duration * sampling_rate)
    deadline = time.monotonic() + duration + 1.0
    while board.get_board_data_count() < required and time.monotonic() < deadline:
        time.sleep(0.02)
    raw = board.get_board_data()
    start = round(discard * sampling_rate)
    expected = round((duration - discard) * sampling_rate)
    channels = [raw[channel, start:start + expected].tolist() for channel in eeg_channels]
    if any(len(row) < expected for row in channels):
        raise ValueError("EEG samples missing; check headset fit and retry this trial")
    if any(not math.isfinite(value) for row in channels for value in row):
        raise ValueError("EEG contains non-finite samples; check headset fit and retry this trial")
    return channels


def main():
    parser = argparse.ArgumentParser(description="Record Muse 2 REST/OPEN/CLOSE imagery trials")
    parser.add_argument("--participant", required=True, help="Local pseudonym, not a real name")
    parser.add_argument("--blocks", type=int, default=6, help="One shuffled trial of each label per block")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    args = parser.parse_args()
    if not 1 <= args.blocks <= 100:
        parser.error("--blocks must be between 1 and 100")
    if not args.participant.isascii() or not all(c.isalnum() or c in "-_" for c in args.participant):
        parser.error("--participant must use only ASCII letters, numbers, - and _")

    from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams

    board_id = BoardIds.MUSE_2_BOARD.value
    sampling_rate = BoardShim.get_sampling_rate(board_id)
    eeg_channels = list(BoardShim.get_eeg_channels(board_id))[:4]
    if len(eeg_channels) != 4:
        raise RuntimeError("Expected four Muse 2 EEG channels")
    started = datetime.now(timezone.utc)
    session_id = started.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    path = args.output_dir / (args.participant + "_" + session_id + ".jsonl")
    board = BoardShim(board_id, BrainFlowInputParams())
    prepared = False
    streaming = False
    try:
        print("Connecting Muse 2. Keep the headset fitted and your hand still.", flush=True)
        board.prepare_session()
        prepared = True
        board.start_stream()
        streaming = True
        time.sleep(2)
        print("Recording to {}. This file contains sensitive raw EEG.".format(path), flush=True)
        print("REST: relax. OPEN/CLOSE: imagine moving your hand without moving it.", flush=True)
        print("Read each upcoming instruction, then look away or close your eyes for the common GO cue.", flush=True)
        input("Press Return when ready. Control-C ends safely. ")
        with path.open("x", encoding="utf-8") as output:
            for index, label in enumerate(trial_order(args.blocks), start=1):
                print("\nTrial {}/{}: prepare {}. GO in 2 seconds...".format(index, args.blocks * 3, label), flush=True)
                time.sleep(2)
                print(">>> GO <<<", flush=True)
                try:
                    samples = capture_trial(board, eeg_channels, sampling_rate)
                except ValueError as exc:
                    print("Skipped trial {}: {}".format(index, exc), flush=True)
                    continue
                record = {
                    "schema_version": 1, "participant": args.participant,
                    "session_id": session_id, "session_started_at": started.isoformat(),
                    "trial_index": index, "label": label,
                    "sample_rate": sampling_rate, "channels": CHANNELS,
                    "samples": samples, "units": "microvolts",
                    "cue_discard_seconds": 0.5,
                }
                output.write(json.dumps(record, allow_nan=False) + "\n")
                output.flush()
                print("Saved {} ({} samples/channel).".format(label, len(samples[0])), flush=True)
        print("Finished: {}".format(path), flush=True)
    finally:
        try:
            if streaming:
                board.stop_stream()
        finally:
            if prepared:
                board.release_session()


if __name__ == "__main__":
    main()
