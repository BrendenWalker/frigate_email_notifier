from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EventPhase:
    id: str | None = None
    camera: str | None = None
    label: str | None = None
    start_time: float = 0.0
    end_time: float | None = None
    score: float = 0.0
    has_clip: bool = False
    has_snapshot: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EventPhase:
        return cls(
            id=data.get("id"),
            camera=data.get("camera"),
            label=data.get("label"),
            start_time=float(data.get("start_time") or 0),
            end_time=_optional_float(data.get("end_time")),
            score=float(data.get("score") or 0),
            has_clip=bool(data.get("has_clip")),
            has_snapshot=bool(data.get("has_snapshot")),
        )


@dataclass
class Event:
    before: EventPhase | None = None
    after: EventPhase | None = None
    type: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        before = data.get("before")
        after = data.get("after")
        return cls(
            before=EventPhase.from_dict(before) if isinstance(before, dict) else None,
            after=EventPhase.from_dict(after) if isinstance(after, dict) else None,
            type=data.get("type"),
        )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
