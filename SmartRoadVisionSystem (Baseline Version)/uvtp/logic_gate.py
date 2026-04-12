from typing import Iterable, Optional

from .config import UVTPConfig
from .types import BoundingBox, Detection, TrackedVehicleState


class AnomalyLogicGate:
    """Determines whether a tracked vehicle should be flagged as unidentifiable."""

    def __init__(self, config: Optional[UVTPConfig] = None):
        self.config = config or UVTPConfig()

    def associate_plate(
        self,
        vehicle_bbox: BoundingBox,
        plate_detections: Iterable[Detection],
    ) -> Optional[Detection]:
        """
        Associate the best plate for a vehicle using deterministic rules:
        1) plate area and OCR confidence must pass config minimums
        2) center-point inside vehicle bbox OR overlap ratio >= 0.5
        3) pick highest detection confidence among valid candidates
        """
        candidates = []
        for plate in plate_detections:
            if plate.label != "license_plate":
                continue
            if plate.bbox.area < self.config.min_plate_area_px:
                continue
            ocr = plate.ocr_confidence if plate.ocr_confidence is not None else 0.0
            if ocr < self.config.min_ocr_confidence:
                continue

            cx, cy = plate.bbox.center
            inside = vehicle_bbox.contains_point(cx, cy)
            overlap_ratio = 0.0
            if plate.bbox.area > 0:
                overlap_ratio = vehicle_bbox.intersection_area(plate.bbox) / plate.bbox.area

            if inside or overlap_ratio >= 0.5:
                candidates.append(plate)

        if not candidates:
            return None

        return max(candidates, key=lambda p: p.confidence)

    def update_track(
        self,
        state: TrackedVehicleState,
        vehicle_bbox: BoundingBox,
        plate_detections: Iterable[Detection],
    ) -> TrackedVehicleState:
        """Advance one frame and update ghost status for this track."""
        state.total_frames_seen += 1

        if state.vehicle_class.lower() not in self.config.valid_vehicle_classes:
            state.last_reason = "non_target_vehicle_class"
            return state

        matched_plate = self.associate_plate(vehicle_bbox, plate_detections)
        if matched_plate:
            state.consecutive_invalid_plate_frames = 0
            state.matched_plate_confidence = matched_plate.confidence
            state.last_reason = "valid_plate_visible"
            return state

        state.consecutive_invalid_plate_frames += 1
        state.last_reason = "no_valid_plate"

        if (
            not state.is_ghost
            and state.consecutive_invalid_plate_frames
            >= self.config.ghost_min_consecutive_no_plate_frames
        ):
            state.is_ghost = True
            state.last_reason = "ghost_threshold_reached"

        return state