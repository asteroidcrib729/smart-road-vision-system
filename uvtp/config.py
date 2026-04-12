from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class UVTPConfig:
    """Centralized UVTP runtime thresholds and constants."""

    ghost_min_consecutive_no_plate_frames: int = 15
    min_plate_area_px: float = 500.0
    min_ocr_confidence: float = 0.40
    valid_vehicle_classes: Tuple[str, ...] = ("car", "truck", "bike")
    reid_cosine_match_threshold: float = 0.20
    feature_input_size: Tuple[int, int] = (256, 256)
