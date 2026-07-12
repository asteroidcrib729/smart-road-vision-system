from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class SessionIdGenerator:
    camera_id: str
    _counter: int = 0

    def next_id(self, now: datetime | None = None) -> str:
        now = now or datetime.now(tz=timezone.utc)
        self._counter += 1
        return f"UID-{now:%Y%m%d}-{self.camera_id}-{self._counter:04d}"