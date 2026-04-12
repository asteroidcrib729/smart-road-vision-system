from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return max(0.0, self.x2 - self.x1)

    @property
    def height(self) -> float:
        return max(0.0, self.y2 - self.y1)

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def contains_point(self, x: float, y: float) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def intersection_area(self, other: "BoundingBox") -> float:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        if ix1 >= ix2 or iy1 >= iy2:
            return 0.0
        return (ix2 - ix1) * (iy2 - iy1)

    def iou(self, other: "BoundingBox") -> float:
        inter = self.intersection_area(other)
        union = self.area + other.area - inter
        if union <= 0:
            return 0.0
        return inter / union


@dataclass(frozen=True)
class Detection:
    label: str
    bbox: BoundingBox
    confidence: float
    ocr_confidence: Optional[float] = None


@dataclass
class TrackedVehicleState:
    track_id: str
    vehicle_class: str
    total_frames_seen: int = 0
    consecutive_invalid_plate_frames: int = 0
    is_ghost: bool = False
    matched_plate_confidence: float = 0.0
    last_reason: str = field(default="")