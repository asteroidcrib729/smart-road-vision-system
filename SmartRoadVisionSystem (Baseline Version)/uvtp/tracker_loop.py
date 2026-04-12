from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional, Protocol, Tuple

from .config import UVTPConfig
from .logic_gate import AnomalyLogicGate
from .persistence import LocalSnapshotStorage, ReportDispatcher, SnapshotStorage
from .profiling import NullVehicleProfiler, VehicleProfiler
from .session import SessionIdGenerator
from .types import BoundingBox, Detection, TrackedVehicleState


class ReIDMatcher(Protocol):
    def is_same_vehicle(self, prev_embedding, next_embedding) -> bool:
        ...

    def cosine_distance(self, prev_embedding, next_embedding) -> float:
        ...


@dataclass
class VehicleObservation:
    label: str
    bbox: BoundingBox
    confidence: float
    embedding: object
    frame_size: Optional[Tuple[int, int]] = None  # (width, height)
    sharpness_score: float = 0.0
    snapshot_jpeg_bytes: Optional[bytes] = None


@dataclass
class ActiveTrack:
    internal_track_id: str
    state: TrackedVehicleState
    last_bbox: BoundingBox
    last_embedding: object
    first_seen_frame: int
    last_seen_frame: int
    session_id: Optional[str] = None
    session_opened_at: Optional[datetime] = None
    snapshots: Dict[str, Optional[str]] = field(
        default_factory=lambda: {"entry": None, "best": None, "exit": None}
    )
    _best_area: float = 0.0
    _best_sharpness: float = 0.0


@dataclass
class UVTPEvent:
    event_id: str
    timestamp: str
    camera_id: str
    violation_type: str = "UNIDENTIFIABLE_VEHICLE"
    track_id: str = ""


@dataclass
class UVTPReport:
    event_id: str
    timestamp: str
    camera_location: str
    violation_type: str
    vehicle_profile: Dict[str, Any]
    evidence: Dict[str, Optional[str]]
    tracking_metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UVTPTrackerLoop:
    camera_id: str
    reid_matcher: ReIDMatcher
    camera_location: str = ""
    config: UVTPConfig = field(default_factory=UVTPConfig)
    profiler: VehicleProfiler = field(default_factory=NullVehicleProfiler)
    snapshot_storage: SnapshotStorage = field(default_factory=LocalSnapshotStorage)
    report_dispatcher: Optional[ReportDispatcher] = None
    session_close_after_lost_frames: int = 30
    evidence_root: str = "/evidence"
    visibility_border_margin_px: int = 2
    snapshot_jpeg_quality: int = 80
    logic_gate: AnomalyLogicGate = field(init=False)
    session_generator: SessionIdGenerator = field(init=False)
    frame_index: int = 0
    _track_counter: int = 0
    active_tracks: Dict[str, ActiveTrack] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.logic_gate = AnomalyLogicGate(self.config)
        self.session_generator = SessionIdGenerator(camera_id=self.camera_id)

    def _next_track_id(self) -> str:
        self._track_counter += 1
        return f"T{self._track_counter:05d}"

    def _match_track(self, obs: VehicleObservation) -> Optional[ActiveTrack]:
        candidates: list[tuple[float, ActiveTrack]] = []

        for track in self.active_tracks.values():
            try:
                if self.reid_matcher.is_same_vehicle(track.last_embedding, obs.embedding):
                    distance = self.reid_matcher.cosine_distance(track.last_embedding, obs.embedding)
                    candidates.append((distance, track))
            except Exception:
                continue

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    def _snapshot_path(self, event_id: str, kind: str, now: datetime) -> str:
        return f"{self.evidence_root}/{now:%Y/%m}/{event_id}_{kind}.jpg"

    def _persist_snapshot(self, obs: VehicleObservation, path: str) -> None:
        if obs.snapshot_jpeg_bytes is None:
            return
        self.snapshot_storage.save_snapshot_bytes(
            obs.snapshot_jpeg_bytes,
            path,
            jpeg_quality=self.snapshot_jpeg_quality,
        )

    def _is_fully_visible(self, bbox: BoundingBox, frame_size: Optional[Tuple[int, int]]) -> bool:
        if frame_size is None:
            return False
        width, height = frame_size
        m = self.visibility_border_margin_px
        return bbox.x1 >= m and bbox.y1 >= m and bbox.x2 <= (width - m) and bbox.y2 <= (height - m)

    def _update_snapshots(self, track: ActiveTrack, obs: VehicleObservation, now: datetime) -> None:
        if not track.session_id:
            return

        area = obs.bbox.area
        sharpness = obs.sharpness_score

        if track.snapshots["entry"] is None and self._is_fully_visible(obs.bbox, obs.frame_size):
            path = self._snapshot_path(track.session_id, "entry", now)
            track.snapshots["entry"] = path
            self._persist_snapshot(obs, path)

        if (
            track.snapshots["best"] is None
            or area > track._best_area
            or (area == track._best_area and sharpness > track._best_sharpness)
        ):
            track._best_area = area
            track._best_sharpness = sharpness
            path = self._snapshot_path(track.session_id, "best", now)
            track.snapshots["best"] = path
            self._persist_snapshot(obs, path)

        exit_path = self._snapshot_path(track.session_id, "exit", now)
        track.snapshots["exit"] = exit_path
        self._persist_snapshot(obs, exit_path)

    def process_frame(
        self,
        vehicle_observations: Iterable[VehicleObservation],
        plate_detections: Iterable[Detection],
        now: Optional[datetime] = None,
    ) -> list[UVTPEvent]:
        self.frame_index += 1
        now = now or datetime.now(tz=timezone.utc)
        events: list[UVTPEvent] = []

        for obs in vehicle_observations:
            if obs.label.lower() not in self.config.valid_vehicle_classes:
                continue

            matched_track = self._match_track(obs)
            if matched_track is None:
                internal_id = self._next_track_id()
                state = TrackedVehicleState(track_id=internal_id, vehicle_class=obs.label)
                matched_track = ActiveTrack(
                    internal_track_id=internal_id,
                    state=state,
                    last_bbox=obs.bbox,
                    last_embedding=obs.embedding,
                    first_seen_frame=self.frame_index,
                    last_seen_frame=self.frame_index,
                )
                self.active_tracks[internal_id] = matched_track

            self.logic_gate.update_track(matched_track.state, obs.bbox, plate_detections)
            matched_track.last_bbox = obs.bbox
            matched_track.last_embedding = obs.embedding
            matched_track.last_seen_frame = self.frame_index

            if matched_track.state.is_ghost and matched_track.session_id is None:
                matched_track.session_id = self.session_generator.next_id(now)
                matched_track.session_opened_at = now
                events.append(
                    UVTPEvent(
                        event_id=matched_track.session_id,
                        timestamp=now.isoformat(),
                        camera_id=self.camera_id,
                        track_id=matched_track.internal_track_id,
                    )
                )

            if matched_track.state.is_ghost:
                self._update_snapshots(matched_track, obs, now)

        return events

    def _finalize_evidence(self, track: ActiveTrack) -> Dict[str, Optional[str]]:
        entry = track.snapshots.get("entry")
        best = track.snapshots.get("best")
        exit_img = track.snapshots.get("exit")

        if best is None and track.session_id:
            best = self._snapshot_path(track.session_id, "best", datetime.now(tz=timezone.utc))
        if entry is None:
            entry = best
        if exit_img is None:
            exit_img = best or entry

        return {
            "snapshot_entry_url": entry,
            "snapshot_best_url": best,
            "snapshot_exit_url": exit_img,
        }

    def flush_closed_sessions(self, now: Optional[datetime] = None) -> list[UVTPReport]:
        """
        Close stale tracks and emit final reports for ghost sessions.

        A track is stale when it has not been seen for `session_close_after_lost_frames`.
        """
        now = now or datetime.now(tz=timezone.utc)
        closed: list[UVTPReport] = []
        stale_track_ids = [
            track_id
            for track_id, track in self.active_tracks.items()
            if (self.frame_index - track.last_seen_frame) >= self.session_close_after_lost_frames
        ]

        for track_id in stale_track_ids:
            track = self.active_tracks.pop(track_id)
            if track.session_id is None:
                continue

            frames_tracked = max(0, track.last_seen_frame - track.first_seen_frame + 1)
            evidence = self._finalize_evidence(track)
            profile = self.profiler.profile(evidence["snapshot_best_url"] or "")

            report = UVTPReport(
                event_id=track.session_id,
                timestamp=now.isoformat(),
                camera_location=self.camera_location,
                violation_type="UNIDENTIFIABLE_VEHICLE",
                vehicle_profile={
                    "predicted_color": profile.predicted_color,
                    "predicted_make": profile.predicted_make,
                    "predicted_type": profile.predicted_type,
                    "orientation": profile.orientation,
                    "confidence_score": profile.confidence_score,
                },
                evidence=evidence,
                tracking_metadata={
                    "track_id": track.internal_track_id,
                    "duration_in_frames": frames_tracked,
                    "session_opened_at": (
                        track.session_opened_at.isoformat() if track.session_opened_at else None
                    ),
                    "session_closed_at": now.isoformat(),
                    "snapshot_jpeg_quality": self.snapshot_jpeg_quality,
                },
            )
            payload = report.to_dict()
            if self.report_dispatcher is not None:
                self.report_dispatcher.dispatch(payload)
            closed.append(report)

        return closed