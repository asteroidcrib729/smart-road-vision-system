import unittest

from uvtp.config import UVTPConfig
from uvtp.logic_gate import AnomalyLogicGate
from uvtp.types import BoundingBox, Detection, TrackedVehicleState


class TestLogicGate(unittest.TestCase):
    def setUp(self) -> None:
        self.config = UVTPConfig(
            ghost_min_consecutive_no_plate_frames=3,
            min_plate_area_px=500,
            min_ocr_confidence=0.4,
        )
        self.gate = AnomalyLogicGate(self.config)
        self.vehicle_box = BoundingBox(0, 0, 100, 100)

    def test_triggers_ghost_after_consecutive_invalid_frames(self):
        state = TrackedVehicleState(track_id="1", vehicle_class="car")
        for _ in range(3):
            self.gate.update_track(state, self.vehicle_box, [])
        self.assertTrue(state.is_ghost)
        self.assertEqual(state.last_reason, "ghost_threshold_reached")

    def test_valid_plate_resets_invalid_counter(self):
        state = TrackedVehicleState(track_id="1", vehicle_class="car")
        self.gate.update_track(state, self.vehicle_box, [])
        self.assertEqual(state.consecutive_invalid_plate_frames, 1)

        plate = Detection(
            label="license_plate",
            bbox=BoundingBox(10, 10, 50, 30),  # area 800
            confidence=0.9,
            ocr_confidence=0.7,
        )
        self.gate.update_track(state, self.vehicle_box, [plate])
        self.assertEqual(state.consecutive_invalid_plate_frames, 0)
        self.assertFalse(state.is_ghost)

    def test_rejects_small_plate(self):
        plate = Detection(
            label="license_plate",
            bbox=BoundingBox(10, 10, 20, 20),  # area 100
            confidence=0.95,
            ocr_confidence=0.99,
        )
        matched = self.gate.associate_plate(self.vehicle_box, [plate])
        self.assertIsNone(matched)


if __name__ == "__main__":
    unittest.main()