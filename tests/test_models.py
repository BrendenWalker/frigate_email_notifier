from __future__ import annotations

from app.models import Event, EventPhase


def test_event_phase_from_dict_full() -> None:
    phase = EventPhase.from_dict(
        {
            "id": "abc123",
            "camera": "front_door",
            "label": "person",
            "start_time": 1700000000.0,
            "end_time": 1700000010.5,
            "score": 0.92,
            "has_clip": True,
            "has_snapshot": True,
        }
    )

    assert phase.id == "abc123"
    assert phase.camera == "front_door"
    assert phase.label == "person"
    assert phase.start_time == 1700000000.0
    assert phase.end_time == 1700000010.5
    assert phase.score == 0.92
    assert phase.has_clip is True
    assert phase.has_snapshot is True


def test_event_phase_from_dict_minimal() -> None:
    phase = EventPhase.from_dict({})

    assert phase.id is None
    assert phase.start_time == 0.0
    assert phase.end_time is None
    assert phase.has_clip is False


def test_event_from_dict() -> None:
    event = Event.from_dict(
        {
            "type": "end",
            "before": {
                "camera": "driveway",
                "label": "car",
                "start_time": 1.0,
            },
            "after": {
                "camera": "driveway",
                "label": "car",
                "end_time": 2.0,
                "has_snapshot": True,
            },
        }
    )

    assert event.type == "end"
    assert event.before is not None
    assert event.before.label == "car"
    assert event.after is not None
    assert event.after.has_snapshot is True


def test_event_from_dict_missing_phases() -> None:
    event = Event.from_dict({"type": "new"})

    assert event.before is None
    assert event.after is None
