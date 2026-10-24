"""Two-class NeuroGrip protocol adapted to the four fixed Muse 2 channels.

Persists unfiltered EEG, software markers, all trial decisions and metadata.
No actuator connection. Legacy three-class recordings remain separate.
"""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import time
import uuid

import numpy as np

from muse_device import CHANNELS, check_chunk, collect_seconds, connected_muse, signal_quality

PROTOCOL = "muse-open-rest-v1"
LABELS = ("REST", "OPEN_INTENT")
DATA_DIR = Path(__file__).resolve().parent / "data" / "open_rest"


def session_schedule(per_class=30, seed=None):
    """Two independently shuffled, balanced runs; recovery is label-independent."""
    rng = random.Random(seed)
    schedule = []
    for run in (1, 2):
        labels = list(LABELS) * (per_class // 2)
        rng.shuffle(labels)
        schedule.extend({"run": run, "label": label, "recovery_seconds": rng.uniform(3, 5)} for label in labels)
    return schedule


def extract_trial(raw, descriptor, marker):
    matches = np.flatnonzero(raw[descriptor["marker_channel"]] == marker)
    if len(matches) != 1:
        return {"quality": {"usable": False, "reasons": ["missing_or_duplicate_cue_marker"]}}
    start = int(matches[0])
    count = 4 * descriptor["sampling_rate"]
    eeg = raw[descriptor["eeg_channels"], start:start + count]
    timestamps = raw[descriptor["timestamp_channel"], start:start + count]
    quality = signal_quality(eeg, timestamps, descriptor["sampling_rate"], 4)
    end_matches = np.flatnonzero(raw[descriptor["marker_channel"]] == marker + 1)
    if len(end_matches) != 1 or abs(int(end_matches[0]) - start - count) > descriptor["sampling_rate"] * 0.1:
        quality["reasons"].append("cue_duration_mismatch")
        quality["usable"] = False
    return {"samples": eeg.tolist(), "timestamps": timestamps.tolist(), "quality": quality,
            "cue_sample_timestamp": float(raw[descriptor["timestamp_channel"], start])}


def main():
    parser = argparse.ArgumentParser(description="Record REST versus imagined right-hand opening")
    parser.add_argument("--participant", required=True, help="Pseudonym, such as P01")
    parser.add_argument("--per-class", type=int, help="Even number, split across two runs (30 for the study; 6 for practice)")
    parser.add_argument("--break-seconds", type=int, help="300 for the study; 0 for practice")
    parser.add_argument("--practice", action="store_true", help="Short exploratory run excluded from future model training")
    parser.add_argument("--seed", type=int, help="Optional reproducible cue order")
    parser.add_argument("--device-name", default="")
    parser.add_argument("--output-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    if args.per_class is None:
        args.per_class = 6 if args.practice else 30
    if args.break_seconds is None:
        args.break_seconds = 0 if args.practice else 300
    if not args.participant or not args.participant.isascii() or not all(c.isalnum() or c in "-_" for c in args.participant):
        parser.error("Use a nonempty participant code with ASCII letters, numbers, - or _")
    if args.per_class < 2 or args.per_class > 100 or args.per_class % 2 or not 0 <= args.break_seconds <= 900:
        parser.error("--per-class must be even, 2–100; --break-seconds must be 0–900")
    seed = args.seed if args.seed is not None else random.SystemRandom().randrange(2 ** 32)
    schedule = session_schedule(args.per_class, seed)
    started = datetime.now(timezone.utc)
    session_id = started.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    folder = args.output_dir / (args.participant + "_" + session_id)
    print("REST: remain still. OPEN_INTENT: imagine the feeling of slowly opening your RIGHT hand.")
    print("Keep the real hand, jaw and head still, and keep the same eyes-open fixation for both cues.")
    print("Use the headset on battery. Keep any powered glove off your hand and disconnected.")
    print("The GO and END cues are identical for both classes. Only the preparation instruction changes.")
    if args.practice:
        print("Practice recording: saved for inspection, excluded from all model training and evaluation.")
    notes = input("Optional session notes (sleep, caffeine, fatigue, fit); no real names: ")
    with connected_muse(args.device_name) as (board, descriptor):
        collect_seconds(board, 2)
        quality = check_chunk(collect_seconds(board, 4), descriptor, 3.75)
        print(json.dumps(quality, indent=2))
        if not quality["usable"]:
            raise ValueError("Signal check failed. Adjust fit and rerun before collecting trials.")
        input("Signal check passed. Press Return to start the two runs; Control-C saves completed work. ")
        folder.mkdir(parents=True, exist_ok=False)
        metadata = {"protocol": PROTOCOL, "schema_version": 2, "participant": args.participant,
                    "session_id": session_id, "session_started_at": started.isoformat(),
                    "recording_source": "muse2", "sample_rate": descriptor["sampling_rate"],
                    "channels": list(CHANNELS), "units": "microvolts", "notes": notes,
                    "seed": seed, "schedule": schedule, "break_seconds": args.break_seconds,
                    "initial_quality": quality, "completed": False, "practice": args.practice,
                    "excluded_trials": [],
                    "timing_note": "Software cue request times and BrainFlow next-sample markers; display/audio latency is unmeasured.",
                    "imu_recorded": False}
        meta_path = folder / "session.json"
        def save_metadata():
            meta_path.write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        save_metadata()
        print("Saving raw EEG and events to {}".format(folder), flush=True)
        try:
            with (folder / "raw.csv").open("x", newline="") as raw_file, (folder / "trials.jsonl").open("x") as trial_file:
                writer = csv.writer(raw_file)
                writer.writerow(["timestamp", *CHANNELS, "marker"])
                def persist(chunk):
                    rows = [descriptor["timestamp_channel"], *descriptor["eeg_channels"], descriptor["marker_channel"]]
                    writer.writerows(chunk[rows].T.tolist())
                    raw_file.flush()
                for index, item in enumerate(schedule, 1):
                    print("\nRun {} | Trial {}/{} | Prepare {}".format(item["run"], index, len(schedule), item["label"]), flush=True)
                    prepare = collect_seconds(board, 2, persist)
                    marker = 100 + index * 10
                    cue_time = time.time()
                    cue_clock = time.monotonic()
                    board.insert_marker(marker)
                    print("\a>>> GO <<<", flush=True)
                    imagery = collect_seconds(board, 4, persist)
                    end_time = time.time()
                    board.insert_marker(marker + 1)
                    print("\aEND — relax", flush=True)
                    recovery = collect_seconds(board, item["recovery_seconds"], persist)
                    trial = {"protocol": PROTOCOL, "schema_version": 2, "trial_index": index,
                             "run": item["run"], "label": item["label"], "marker": marker,
                             "cue_requested_at": cue_time, "cue_monotonic": cue_clock,
                             "cue_end_requested_at": end_time, "recovery_seconds": item["recovery_seconds"]}
                    trial.update(extract_trial(np.concatenate([prepare, imagery, recovery], axis=1), descriptor, marker))
                    trial_file.write(json.dumps(trial, allow_nan=False) + "\n")
                    trial_file.flush()
                    print("{}: {}".format("Kept" if trial["quality"]["usable"] else "Rejected", ", ".join(trial["quality"]["reasons"]) or "basic checks passed"), flush=True)
                    if index in (args.per_class, len(schedule)):
                        while True:
                            response = input("Trial numbers with accidental movement/blinks or missed cues in this run (comma-separated; Return for none): ")
                            try:
                                excluded = [int(value.strip()) for value in response.split(",") if value.strip()]
                                if any(n < index - args.per_class + 1 or n > index for n in excluded):
                                    raise ValueError()
                                break
                            except ValueError:
                                print("Enter trial numbers from this run, separated by commas.")
                        metadata["excluded_trials"].extend(excluded)
                        save_metadata()
                    if index == args.per_class:
                        print("Break for {} seconds. Keep headset position unchanged.".format(args.break_seconds), flush=True)
                        if args.break_seconds:
                            collect_seconds(board, args.break_seconds, persist)
                        input("Press Return when ready for run 2. ")
                # Flush samples acquired during the final annotation prompt too.
                tail = board.get_board_data()
                if tail.shape[1]:
                    persist(tail)
                metadata["completed"] = True
        except KeyboardInterrupt:
            print("\nStopped. Completed trials and raw data are saved; session marked incomplete.")
        finally:
            metadata["ended_at"] = datetime.now(timezone.utc).isoformat()
            save_metadata()
        print("Saved: {}".format(folder))


if __name__ == "__main__":
    main()
