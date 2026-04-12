import unittest
from datetime import datetime, timedelta, timezone

from uvtp.config import UVTPConfig
from uvtp.persistence import InMemoryReportDispatcher
from uvtp.profiling import VehicleProfile
from uvtp.tracker_loop import UVTPTrackerLoop, VehicleObservation
from uvtp.types import BoundingBox


class FakeReIDMatcher:
    """Simple matcher for deterministic tests based on scalar embeddings."""

    @staticmethod
    def cosine_distance(prev_embedding, next_embedding) -> float:
        return abs(float(prev_embedding) - float(next_embedding))

    def is_same_vehicle(self, prev_embedding, next_embedding) -> bool:
        return self.cosine_distance(prev_embedding, next_embedding) < 0.2


class StubProfiler:
    def profile(self, snapshot_best_url: str, direction=None) -> VehicleProfile:
        _ = direction
        if not snapshot_best_url:
            raise AssertionError("snapshot_best_url must not be empty")
        return VehicleProfile(
            predicted_color="White",
            predicted_make="Toyota",
            predicted_type="Sedan",
            orientation="Front-View",
            confidence_score=0.92,
        )


class InMemorySnapshotStorage:
    def __init__(self) -> None:
        self.writes: list[tuple[str, bytes, int]] = []

    def save_snapshot_bytes(self, image_bytes: bytes, destination_path: str, jpeg_quality: int = 80) -> str:
        self.writes.append((destination_path, image_bytes, jpeg_quality))
        return destination_path


class TestUVTPTrackerLoop(unittest.TestCase):
    def setUp(self):
        config = UVTPConfig(
            ghost_min_consecutive_no_plate_frames=3,
            min_plate_area_px=500,
            min_ocr_confidence=0.4,
        )
        self.dispatcher = InMemoryReportDispatcher()
        self.snapshot_storage = InMemorySnapshotStorage()
        self.loop = UVTPTrackerLoop(
            camera_id="CAM01",
            camera_location="University Road, Karachi",
            reid_matcher=FakeReIDMatcher(),
            profiler=StubProfiler(),
            snapshot_storage=self.snapshot_storage,
            report_dispatcher=self.dispatcher,
            config=config,
            session_close_after_lost_frames=2,
        )

    def test_reid_keeps_single_track_for_same_vehicle(self):
        now = datetime(2024, 2, 4, tzinfo=timezone.utc)
        box = BoundingBox(0, 0, 100, 100)

        self.loop.process_frame(
            [VehicleObservation("car", box, 0.9, embedding=0.10)],
            plate_detections=[],
            now=now,
        )
        self.loop.process_frame(
            [VehicleObservation("car", box, 0.9, embedding=0.11)],
            plate_detections=[],
            now=now,
        )

        self.assertEqual(len(self.loop.active_tracks), 1)

    def test_ghost_event_emitted_when_threshold_reached(self):
        now = datetime(2024, 2, 4, tzinfo=timezone.utc)
        box = BoundingBox(0, 0, 100, 100)

        events = []
        events.extend(
            self.loop.process_frame(
                [VehicleObservation("car", box, 0.9, embedding=0.10)],
                plate_detections=[],
                now=now,
            )
        )
        events.extend(
            self.loop.process_frame(
                [VehicleObservation("car", box, 0.9, embedding=0.11)],
                plate_detections=[],
                now=now,
            )
        )
        events.extend(
            self.loop.process_frame(
                [VehicleObservation("car", box, 0.9, embedding=0.12)],
                plate_detections=[],
                now=now,
            )
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].camera_id, "CAM01")
        self.assertTrue(events[0].event_id.startswith("UID-20240204-CAM01-"))

    def test_flush_closed_sessions_generates_report_with_profile_evidence_and_dispatch(self):
        now = datetime(2024, 2, 4, tzinfo=timezone.utc)

        observations = [
            VehicleObservation(
                "car",
                BoundingBox(3, 3, 40, 35),
                0.9,
                embedding=0.10,
                frame_size=(100, 100),
                sharpness_score=40.0,
                snapshot_jpeg_bytes=b"entry-jpg",
            ),
            VehicleObservation(
                "car",
                BoundingBox(2, 2, 70, 55),
                0.9,
                embedding=0.11,
                frame_size=(100, 100),
                sharpness_score=60.0,
                snapshot_jpeg_bytes=b"best-jpg",
            ),
            VehicleObservation(
                "car",
                BoundingBox(5, 5, 90, 75),
                0.9,
                embedding=0.12,
                frame_size=(100, 100),
                sharpness_score=80.0,
                snapshot_jpeg_bytes=b"exit-jpg",
            ),
        ]

        for obs in observations:
            self.loop.process_frame([obs], plate_detections=[], now=now)

        self.loop.process_frame([], plate_detections=[], now=now + timedelta(seconds=1))
        self.loop.process_frame([], plate_detections=[], now=now + timedelta(seconds=2))

        reports = self.loop.flush_closed_sessions(now=now + timedelta(seconds=3))
        self.assertEqual(len(reports), 1)

        payload = reports[0].to_dict()
        self.assertEqual(payload["camera_location"], "University Road, Karachi")
        self.assertEqual(payload["violation_type"], "UNIDENTIFIABLE_VEHICLE")

        profile = payload["vehicle_profile"]
        self.assertEqual(profile["predicted_color"], "White")
        self.assertEqual(profile["predicted_make"], "Toyota")
        self.assertEqual(profile["predicted_type"], "Sedan")
        self.assertEqual(profile["orientation"], "Front-View")
        self.assertGreaterEqual(profile["confidence_score"], 0.9)

        evidence = payload["evidence"]
        self.assertIsNotNone(evidence["snapshot_entry_url"])
        self.assertIsNotNone(evidence["snapshot_best_url"])
        self.assertIsNotNone(evidence["snapshot_exit_url"])
        self.assertIn("_best.jpg", evidence["snapshot_best_url"])

        self.assertGreaterEqual(len(self.snapshot_storage.writes), 3)
        self.assertEqual(self.snapshot_storage.writes[0][2], 80)

        self.assertEqual(len(self.dispatcher.sent_payloads), 1)
        self.assertEqual(self.dispatcher.sent_payloads[0]["event_id"], payload["event_id"])


if __name__ == "__main__":
    unittest.main()