import unittest
from datetime import datetime, timezone

from uvtp.session import SessionIdGenerator


class TestSessionIdGenerator(unittest.TestCase):
    def test_session_id_format(self):
        gen = SessionIdGenerator(camera_id="CAM01")
        now = datetime(2024, 2, 4, tzinfo=timezone.utc)
        self.assertEqual(gen.next_id(now), "UID-20240204-CAM01-0001")
        self.assertEqual(gen.next_id(now), "UID-20240204-CAM01-0002")


if __name__ == "__main__":
    unittest.main()