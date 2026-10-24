import csv
import io
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from import_csv import convert_file
from record import trial_order
from server import MuseSource, make_handler


class RecordingPipelineTests(unittest.TestCase):
    def test_cue_order_is_balanced_and_reproducible(self):
        order = trial_order(6, seed=42)
        self.assertEqual(order, trial_order(6, seed=42))
        self.assertEqual(Counter(order), {"REST": 6, "OPEN": 6, "CLOSE": 6})
        for index in range(0, len(order), 3):
            self.assertEqual(set(order[index:index + 3]), {"REST", "OPEN", "CLOSE"})

    def test_import_guided_recording_and_reject_dropouts(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "20261022T190000Z_imagine_open_ab12cd34.csv"
            with file.open("w", newline="", encoding="utf-8") as output:
                writer = csv.writer(output)
                writer.writerow(["timestamp", "TP9", "AF7", "AF8", "TP10"])
                for index in range(256 * 7):
                    writer.writerow([1700000000 + index / 256, 1, 2, 3, 4])
            label, rate, samples, _ = convert_file(file)
            self.assertEqual((label, rate), ("OPEN", 256))
            self.assertEqual([len(row) for row in samples], [1024] * 4)
            with file.open("w", newline="", encoding="utf-8") as output:
                writer = csv.writer(output)
                writer.writerow(["timestamp", "TP9", "AF7", "AF8", "TP10"])
                for index in range(256 * 7):
                    writer.writerow([1700000000 + index / 256 + (0.2 if index > 500 else 0), 1, 2, 3, 4])
            with self.assertRaisesRegex(ValueError, "dropouts"):
                convert_file(file)

    def test_bridge_keeps_labeled_csv_local_and_requires_key_for_start(self):
        with tempfile.TemporaryDirectory() as folder:
            source = MuseSource(folder)
            source.board = object()
            source.state = "live"
            source.sample_rate = 256
            handler_type = make_handler(source, "test-access-key-12345")
            handler = handler_type.__new__(handler_type)
            handler.path = "/api/recording/start"
            handler.headers = {"Authorization": "Bearer wrong", "Content-Length": "16"}
            handler.rfile = io.BytesIO(b'{"label":"rest"}')
            replies = []
            handler.respond = lambda code, payload: replies.append((code, payload))
            handler.do_POST()
            self.assertEqual(replies[-1][0], 401)
            self.assertIsNone(source.recording)

            handler.headers = {"Authorization": "Bearer test-access-key-12345", "Content-Length": "29"}
            body = b'{"label":"imagine open / unsafe"}'
            handler.headers["Content-Length"] = str(len(body))
            handler.rfile = io.BytesIO(body)
            handler.do_POST()
            self.assertEqual(replies[-1][0], 200)
            source._record_row(123.5, [1, 2, 3, 4])
            source.stop_recording()
            name = source.last_recording["name"]
            self.assertNotIn("/", name)
            lines = (Path(folder) / name).read_text().splitlines()
            self.assertEqual(lines[0], "timestamp,TP9,AF7,AF8,TP10")
            self.assertEqual(lines[1], "123.500000,1.000000,2.000000,3.000000,4.000000")


if __name__ == "__main__":
    unittest.main()
