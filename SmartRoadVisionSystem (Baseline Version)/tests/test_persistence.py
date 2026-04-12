import json
import tempfile
import unittest
from pathlib import Path

from uvtp.persistence import JsonlReportDispatcher, LocalSnapshotStorage


class TestPersistenceHelpers(unittest.TestCase):
    def test_local_snapshot_storage_writes_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = Path(tmp) / "evidence" / "x.jpg"
            storage = LocalSnapshotStorage()
            out = storage.save_snapshot_bytes(b"abc", str(dst), jpeg_quality=80)
            self.assertEqual(out, str(dst))
            self.assertTrue(dst.exists())
            self.assertEqual(dst.read_bytes(), b"abc")

    def test_jsonl_report_dispatcher_appends_json_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "reports.jsonl"
            dispatcher = JsonlReportDispatcher(output_path=str(out))
            dispatcher.dispatch({"event_id": "1"})
            dispatcher.dispatch({"event_id": "2"})

            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["event_id"], "1")
            self.assertEqual(json.loads(lines[1])["event_id"], "2")


if __name__ == "__main__":
    unittest.main()