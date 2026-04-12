from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class VehicleProfile:
    predicted_color: Optional[str]
    predicted_make: Optional[str]
    predicted_type: Optional[str]
    orientation: Optional[str]
    confidence_score: float


class VehicleProfiler(Protocol):
    def profile(self, snapshot_best_url: str, direction: Optional[str] = None) -> VehicleProfile:
        ...


@dataclass
class NullVehicleProfiler:
    """Fallback profiler used until ML attribute heads are integrated."""

    default_color: Optional[str] = None
    default_make: Optional[str] = None
    default_type: Optional[str] = None
    default_orientation: Optional[str] = None
    confidence_score: float = 0.0

    def profile(self, snapshot_best_url: str, direction: Optional[str] = None) -> VehicleProfile:
        _ = snapshot_best_url
        orientation = self.default_orientation or ("Side-View" if direction else None)
        return VehicleProfile(
            predicted_color=self.default_color,
            predicted_make=self.default_make,
            predicted_type=self.default_type,
            orientation=orientation,
            confidence_score=self.confidence_score,
        )