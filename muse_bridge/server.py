"""Muse 2 bridge for live display and labeled CSV capture on the Mac.

The separate record.py CLI creates controlled trials for offline model training.
"""

import argparse
import csv
import hmac
import json
import math
import re
import secrets
import threading
import time
from collections import deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_QUICK_RECORDING_SECONDS = 600


class MuseSource:
    def __init__(self, recording_dir=None):
        self.recording_dir = Path(recording_dir or Path.home() / "Documents" / "Synova Recordings")
        self.board = None
        self.channels = []
        self.timestamp_channel = None
        self.sample_rate = 0
        self.state = "starting"
        self.message = "Waiting for Muse 2."
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.latest_at = None
        self.samples = [deque(maxlen=512) for _ in range(4)]
        self.recording = None
        self._file = None
        self._writer = None
        self.last_recording = None
        self.started_at = time.time()

    def _record_row(self, timestamp, values):
        with self.lock:
            if self._writer is None:
                return
            self._writer.writerow(["{:.6f}".format(timestamp)] + ["{:.6f}".format(value) for value in values])
            self.recording["rows"] += 1
            if self.recording["rows"] % 256 == 0:
                self._file.flush()

    def _consume(self, data):
        with self.lock:
            if len(self.channels) != 4 or self.timestamp_channel is None or data.shape[1] == 0:
                return
            for index in range(data.shape[1]):
                timestamp = float(data[self.timestamp_channel, index])
                values = [float(data[channel, index]) for channel in self.channels]
                if not all(math.isfinite(value) and abs(value) < 1e8 for value in values) or not math.isfinite(timestamp) or timestamp <= 0:
                    continue
                for stream, value in zip(self.samples, values):
                    stream.append(value)
                self.latest_at = timestamp
                self._record_row(timestamp, values)

    def run(self):
        while not self.stopping.is_set():
            board = None
            prepared = streaming = False
            try:
                from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams

                with self.lock:
                    self.state = "searching"
                    self.message = "Searching for Muse 2…"
                board_id = BoardIds.MUSE_2_BOARD.value
                board = BoardShim(board_id, BrainFlowInputParams())
                board.prepare_session()
                prepared = True
                board.start_stream()
                streaming = True
                with self.lock:
                    self.board = board
                    self.channels = list(BoardShim.get_eeg_channels(board_id))[:4]
                    self.timestamp_channel = BoardShim.get_timestamp_channel(board_id)
                    self.sample_rate = BoardShim.get_sampling_rate(board_id)
                    self.samples = [deque(maxlen=self.sample_rate * 2) for _ in range(4)]
                    self.state = "connected"
                    self.message = "Waiting for fresh Muse 2 EEG…"
                if len(self.channels) != 4:
                    raise RuntimeError("Expected four Muse 2 EEG channels")
                while not self.stopping.wait(0.1):
                    with self.lock:
                        self._consume(board.get_board_data())
                        if self.recording and time.time() - self.recording["started_at"] >= MAX_QUICK_RECORDING_SECONDS:
                            self._stop_recording_locked()
                            self.message = "Quick recording reached the 10-minute limit and was saved."
                        if self.latest_at and 0 <= time.time() - self.latest_at < 3:
                            self.state = "live"
                            self.message = "Live Muse 2 EEG from this Mac."
                        else:
                            self.state = "connected"
                            self.message = "Muse 2 signal paused or waiting for EEG samples."
            except Exception as exc:
                with self.lock:
                    self.state = "retrying"
                    self.message = "Muse 2 unavailable: {}. Check Bluetooth, power and BrainFlow.".format(exc)
            finally:
                with self.lock:
                    self._stop_recording_locked()
                    self.board = None
                    self.latest_at = None
                    self.samples = [deque(maxlen=512) for _ in range(4)]
                if streaming:
                    try:
                        board.stop_stream()
                    except Exception:
                        pass
                if prepared:
                    try:
                        board.release_session()
                    except Exception:
                        pass
            self.stopping.wait(5)

    def _stop_recording_locked(self):
        if self._file is not None:
            self._file.close()
            self.last_recording = dict(self.recording)
            self.last_recording["active"] = False
        self._file = None
        self._writer = None
        self.recording = None

    def start_recording(self, label):
        with self.lock:
            if self.board is None or self.state != "live":
                raise ValueError("Wait for fresh Muse 2 EEG before recording")
            if self.recording is not None:
                raise ValueError("A recording is already active")
            safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(label))[:40].strip("_") or "unlabeled"
            self.recording_dir.mkdir(parents=True, exist_ok=True)
            name = "{}_{}_{}.csv".format(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), safe, secrets.token_hex(4))
            self._file = (self.recording_dir / name).open("x", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)
            self._writer.writerow(["timestamp", "TP9", "AF7", "AF8", "TP10"])
            self.recording = {"active": True, "label": safe, "name": name, "rows": 0, "started_at": time.time()}
            return self.snapshot()

    def stop_recording(self):
        with self.lock:
            if self.recording is None:
                raise ValueError("No recording is active")
            self._stop_recording_locked()
            return self.snapshot()

    def snapshot(self):
        with self.lock:
            age = time.time() - self.latest_at if self.latest_at else None
            fresh = self.board is not None and age is not None and 0 <= age < 3 and all(len(s) > 1 for s in self.samples)
            return {
                "bridge_version": "1.1", "state": self.state,
                "connected": bool(fresh), "sample_rate": self.sample_rate if fresh else 0,
                "channels": ["TP9", "AF7", "AF8", "TP10"] if fresh else [],
                "samples": [list(stream) for stream in self.samples] if fresh else [],
                "captured_at": self.latest_at if fresh else None, "sample_age": age if fresh else None,
                "uptime_seconds": int(time.time() - self.started_at),
                "recording": self.recording or {"active": False, "label": None, "name": None, "rows": 0},
                "last_recording": self.last_recording,
                "message": self.message if fresh or self.board is None else "Muse 2 signal paused or waiting for EEG samples.",
            }


def make_handler(source, access_key):
    class Handler(BaseHTTPRequestHandler):
        def authorized(self):
            return hmac.compare_digest(self.headers.get("Authorization", ""), "Bearer " + access_key)

        def do_GET(self):
            if self.path != "/api/status":
                self.respond(404, {"error": "Not found"})
            elif not self.authorized():
                self.respond(401, {"error": "Invalid access key"})
            else:
                self.respond(200, source.snapshot())

        def do_POST(self):
            if self.path not in ("/api/recording/start", "/api/recording/stop"):
                self.respond(404, {"error": "Not found"})
                return
            if not self.authorized():
                self.respond(401, {"error": "Invalid access key"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 <= size <= 512:
                    raise ValueError("Invalid request size")
                body = json.loads(self.rfile.read(size) or b"{}")
                if self.path.endswith("/start"):
                    label = body.get("label", "")
                    if not isinstance(label, str) or not label.strip() or len(label) > 80:
                        raise ValueError("A short label is required")
                    status = source.start_recording(label)
                else:
                    status = source.stop_recording()
                self.respond(200, status)
            except (ValueError, AttributeError) as exc:
                self.respond(409, {"error": str(exc)})

        def respond(self, status, payload):
            body = json.dumps(payload, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Muse 2 to Synova iPhone bridge")
    parser.add_argument("--host", default="127.0.0.1", help="Use 0.0.0.0 for an iPhone on the same trusted Wi-Fi")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--access-key", default=secrets.token_urlsafe(24))
    args = parser.parse_args()
    if len(args.access_key) < 16:
        parser.error("--access-key must contain at least 16 characters")
    source = MuseSource()
    thread = threading.Thread(target=source.run, daemon=True)
    thread.start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(source, args.access_key))
    print("Synova Muse bridge listening on {}:{}".format(args.host, args.port), flush=True)
    print("Access key: {}".format(args.access_key), flush=True)
    print("On iPhone, enter this Mac's local IP address and the access key in Settings.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        source.stopping.set()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    main()
