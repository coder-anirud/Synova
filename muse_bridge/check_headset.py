"""Bounded real-hardware check. Does not save raw EEG or use simulated data."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from muse_device import CHANNELS, check_chunk, collect_seconds, connected_muse


def probe(seconds, name, timeout):
    with connected_muse(name, timeout) as (board, descriptor):
        collect_seconds(board, 2)  # settling period
        raw = collect_seconds(board, seconds)
        quality = check_chunk(raw, descriptor, max(2, seconds - 0.25))
        return {"status": "signal_received", "device": "Muse 2", "sample_rate": descriptor["sampling_rate"],
                "channels": list(CHANNELS), "quality": quality,
                "note": "Heuristic signal check only; no impedance measurement or classifier validation."}


def run_probe(seconds=8, name="", timeout=10):
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--seconds", str(seconds),
               "--timeout", str(timeout), "--device-name", name]
    try:
        child = subprocess.run(command, text=True, capture_output=True, timeout=timeout + seconds + 20)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "message": "Bluetooth connection or acquisition stalled; the check was stopped."}
    # Native Bluetooth libraries may print additional text to stdout.
    for line in reversed(child.stdout.splitlines()):
        if line.startswith("SYNOVA_RESULT="):
            return json.loads(line.split("=", 1)[1])
    logs = (child.stdout + child.stderr).lower()
    if "bluetooth is not enabled" in logs or "bluetooth is disabled" in logs:
        message = "Bluetooth is off or unavailable to this process. Enable it and allow Bluetooth access for the launching app in System Settings."
    else:
        message = "Muse connection failed. Turn on the headset, close Muse/Mind Monitor and other bridge windows, and check Bluetooth permissions."
    return {"status": "connection_failed", "message": message, "process_exit_code": child.returncode}


def main():
    parser = argparse.ArgumentParser(description="Check a real Muse 2 connection and four EEG channels")
    parser.add_argument("--device-name", default="", help="Optional advertised name, e.g. Muse-XXXX")
    parser.add_argument("--seconds", type=int, default=8)
    parser.add_argument("--timeout", type=int, default=10)
    parser.add_argument("--output", type=Path, help="Optional JSON diagnostic summary; contains no raw EEG")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 4 <= args.seconds <= 60 or not 1 <= args.timeout <= 30:
        parser.error("Use 4–60 seconds and a 1–30 second discovery timeout")
    if args.worker:
        print("SYNOVA_RESULT=" + json.dumps(probe(args.seconds, args.device_name, args.timeout), allow_nan=False))
        return
    print("Checking real Muse 2. Keep it fitted and sit still. Close other Muse connections.", flush=True)
    result = run_probe(args.seconds, args.device_name, args.timeout)
    result["checked_at"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(result, indent=2, allow_nan=False))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return 0 if result.get("quality", {}).get("usable") else 1


if __name__ == "__main__":
    sys.exit(main())
