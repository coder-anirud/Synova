"""Convert selected iPhone-guided CSV recordings into offline trial JSONL.

Choose files from ONE sitting per invocation. Free recordings are not labeled
trials. The first second after recording starts is skipped to avoid the tap/cue.
"""

import argparse
import csv
import json
import math
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

CHANNELS = ("TP9", "AF7", "AF8", "TP10")
FILE_LABELS = {"rest": "REST", "imagine_open": "OPEN", "imagine_close": "CLOSE"}


def convert_file(path):
    match = re.match(r"^\d{8}T\d{6}Z_(rest|imagine_open|imagine_close)_[0-9a-f]+\.csv$", path.name)
    if not match:
        raise ValueError("{}: expected a labeled Synova recording filename".format(path))
    with path.open(newline="", encoding="utf-8") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["timestamp", *CHANNELS]:
            raise ValueError("{}: unexpected CSV columns".format(path))
        rows = list(reader)
    if len(rows) < 512:
        raise ValueError("{}: recording too short".format(path))
    times = [float(row["timestamp"]) for row in rows]
    if not all(math.isfinite(timestamp) for timestamp in times):
        raise ValueError("{}: non-finite timestamp".format(path))
    intervals = [right - left for left, right in zip(times, times[1:])]
    if any(interval <= 0 for interval in intervals):
        raise ValueError("{}: non-monotonic timestamps".format(path))
    rate = round(1 / statistics.median(intervals))
    if not 200 <= rate <= 300:
        raise ValueError("{}: unsupported sample rate {}".format(path, rate))
    start = times[0] + 1.0
    selected = [(row, timestamp) for row, timestamp in zip(rows, times) if timestamp >= start][:4 * rate]
    if len(selected) < 4 * rate:
        raise ValueError("{}: fewer than four seconds of continuous samples after cue discard".format(path))
    if any(right[1] - left[1] > 3 / rate for left, right in zip(selected, selected[1:])):
        raise ValueError("{}: EEG dropouts inside the trial".format(path))
    samples = [[float(row[channel]) for row, _ in selected] for channel in CHANNELS]
    if not all(math.isfinite(value) for channel in samples for value in channel):
        raise ValueError("{}: non-finite EEG sample".format(path))
    return FILE_LABELS[match.group(1)], rate, samples, times[0]


def main():
    parser = argparse.ArgumentParser(description="Import labeled iPhone-guided Muse CSV files from one sitting")
    parser.add_argument("--participant", required=True)
    parser.add_argument("--session-id", required=True, help="Unique identifier for this sitting, e.g. 20261022-evening")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "data")
    parser.add_argument("files", nargs="+", type=Path, help="Choose only REST / imagined OPEN / imagined CLOSE files from one sitting")
    args = parser.parse_args()
    if not all(re.fullmatch(r"[A-Za-z0-9_-]+", value) for value in (args.participant, args.session_id)):
        parser.error("participant and session ID must contain only ASCII letters, numbers, - or _")
    if len(set(args.files)) != len(args.files):
        parser.error("The same input file was listed twice")
    converted = [(path, *convert_file(path)) for path in sorted(args.files)]
    rates = {rate for _, _, rate, _, _ in converted}
    if len(rates) != 1:
        parser.error("Selected recordings have different sample rates")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    destination = args.output_dir / (args.participant + "_" + args.session_id + ".jsonl")
    session_started_at = datetime.fromtimestamp(min(item[4] for item in converted), timezone.utc).isoformat()
    with destination.open("x", encoding="utf-8") as output:
        for index, (path, label, rate, samples, _) in enumerate(converted, start=1):
            output.write(json.dumps({
                "schema_version": 1, "participant": args.participant, "session_id": args.session_id,
                "session_started_at": session_started_at, "trial_index": index, "label": label,
                "sample_rate": rate, "channels": CHANNELS, "samples": samples,
                "units": "microvolts", "cue_discard_seconds": 1.0,
                "source_file": path.name,
            }, allow_nan=False) + "\n")
    print("Imported {} labeled trials to {}".format(len(converted), destination))


if __name__ == "__main__":
    main()
