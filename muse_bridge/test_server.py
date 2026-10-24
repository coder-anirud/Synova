import json
import threading
import tempfile
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from record import LABELS, trial_order
from server import MuseSource, make_handler


class FakeSource:
    def __init__(self):
        self.recording = False

    def snapshot(self):
        return {"connected": False, "sample_rate": 0, "channels": [], "samples": [], "recording": {"active": self.recording}, "message": "Waiting for Muse 2."}

    def start_recording(self, label):
        self.recording = True
        return self.snapshot()

    def stop_recording(self):
        self.recording = False
        return self.snapshot()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        try:
            self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource(), "test-access-key-12345"))
        except PermissionError:
            self.skipTest("This environment blocks loopback sockets")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:{}/api/status".format(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_requires_access_key(self):
        with self.assertRaises(HTTPError) as error:
            urlopen(self.url)
        self.assertEqual(error.exception.code, 401)

    def test_returns_truthful_disconnected_status(self):
        request = Request(self.url, headers={"Authorization": "Bearer test-access-key-12345"})
        with urlopen(request) as response:
            status = json.load(response)
        self.assertFalse(status["connected"])
        self.assertEqual(status["samples"], [])

    def test_unknown_path_is_not_found(self):
        request = Request(self.url.replace("/api/status", "/api/other"), headers={"Authorization": "Bearer test-access-key-12345"})
        with self.assertRaises(HTTPError) as error:
            urlopen(request)
        self.assertEqual(error.exception.code, 404)

    def test_recording_commands_require_key_and_change_status(self):
        url = self.url.replace("/status", "/recording/start")
        unauthorized = Request(url, data=b'{"label":"signal_check"}', method="POST")
        with self.assertRaises(HTTPError) as error:
            urlopen(unauthorized)
        self.assertEqual(error.exception.code, 401)
        authorized = Request(url, data=b'{"label":"signal_check"}', method="POST", headers={"Authorization": "Bearer test-access-key-12345"})
        with urlopen(authorized) as response:
            status = json.load(response)
        self.assertTrue(status["recording"]["active"])


class CsvRecordingTests(unittest.TestCase):
    def test_quick_recording_sanitizes_name_and_writes_samples(self):
        with tempfile.TemporaryDirectory() as folder:
            source = MuseSource(folder)
            source.board = object()
            source.state = "live"
            source.sample_rate = 256
            source.latest_at = 123.5
            status = source.start_recording("signal check / unsafe")
            self.assertTrue(status["recording"]["active"])
            source._record_row(123.5, [1.0, 2.0, 3.0, 4.0])
            status = source.stop_recording()
            self.assertFalse(status["last_recording"]["active"])
            name = status["last_recording"]["name"]
            self.assertNotIn("/", name)
            with open("{}/{}".format(folder, name), encoding="utf-8") as saved:
                rows = saved.read().splitlines()
            self.assertEqual(rows[0], "timestamp,TP9,AF7,AF8,TP10")
            self.assertIn("123.500000,1.000000,2.000000,3.000000,4.000000", rows[1])


class RecordingPlanTests(unittest.TestCase):
    def test_trial_order_is_balanced_and_reproducible(self):
        first = trial_order(6, seed=42)
        second = trial_order(6, seed=42)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 18)
        self.assertEqual({label: first.count(label) for label in LABELS}, {label: 6 for label in LABELS})
        for offset in range(0, len(first), 3):
            self.assertEqual(set(first[offset:offset + 3]), set(LABELS))


if __name__ == "__main__":
    unittest.main()
