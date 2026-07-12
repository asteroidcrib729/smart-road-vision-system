from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Protocol


class SnapshotStorage(Protocol):
    def save_snapshot_bytes(self, image_bytes: bytes, destination_path: str, jpeg_quality: int = 80) -> str:
        ...


class ReportDispatcher(Protocol):
    def dispatch(self, payload: Dict[str, Any]) -> None:
        ...


@dataclass
class LocalSnapshotStorage:
    """Writes pre-encoded JPEG bytes to disk under the provided destination path."""

    def save_snapshot_bytes(self, image_bytes: bytes, destination_path: str, jpeg_quality: int = 80) -> str:
        _ = jpeg_quality  # bytes are expected to already be JPEG-encoded by upstream pipeline.
        path = Path(destination_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image_bytes)
        return str(path)


@dataclass
class JsonlReportDispatcher:
    """Appends one JSON payload per line to a local `.jsonl` file."""

    output_path: str = "uvtp_reports.jsonl"

    def dispatch(self, payload: Dict[str, Any]) -> None:
        path = Path(self.output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")


@dataclass
class InMemoryReportDispatcher:
    """Test helper dispatcher that stores dispatched payloads in memory."""

    sent_payloads: List[Dict[str, Any]] = field(default_factory=list)

    def dispatch(self, payload: Dict[str, Any]) -> None:
        self.sent_payloads.append(payload)