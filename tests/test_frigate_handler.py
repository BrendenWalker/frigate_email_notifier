from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from app.config import Config
from app.frigate_handler import FrigateHandler


def _unix(dt: datetime) -> float:
    return dt.timestamp()


def _event_payload(
    *,
    camera: str = "front_door",
    label: str = "person",
    end_time: float,
    has_snapshot: bool = True,
    has_clip: bool = False,
) -> bytes:
    return json.dumps(
        {
            "type": "end",
            "before": {
                "camera": camera,
                "label": label,
                "start_time": end_time - 10,
            },
            "after": {
                "camera": camera,
                "label": label,
                "end_time": end_time,
                "has_snapshot": has_snapshot,
                "has_clip": has_clip,
            },
        }
    ).encode()


@pytest.fixture
def night_config(minimal_config: Config) -> Config:
    return minimal_config


def test_event_topic_stores_last_event(night_config: Config) -> None:
    handler = FrigateHandler(night_config)
    payload = _event_payload(end_time=_unix(datetime(2024, 1, 15, 20, 0)))

    handler.handle_message("frigate/events", payload)

    assert handler.last_event is not None
    assert handler.last_event.after is not None
    assert handler.last_event.after.label == "person"


def test_stats_topic_ignored(night_config: Config) -> None:
    handler = FrigateHandler(night_config)

    handler.handle_message("frigate/stats", b'{"cameras":{}}')

    assert handler.last_event is None


def test_malformed_event_does_not_crash(night_config: Config) -> None:
    handler = FrigateHandler(night_config)

    handler.handle_message("frigate/events", b"not-json")

    assert handler.last_event is None


@patch("app.frigate_handler.send_alert_email")
@patch("app.frigate_handler._unix_to_local")
def test_snapshot_sends_email_during_night_window(
    mock_unix_to_local: object,
    mock_send: object,
    night_config: Config,
) -> None:
    mock_unix_to_local.side_effect = lambda _t: datetime(2024, 1, 15, 20, 0)
    end_time = _unix(datetime(2024, 1, 15, 20, 0))
    handler = FrigateHandler(night_config)
    handler.handle_message("frigate/events", _event_payload(end_time=end_time))

    handler.handle_message(
        "frigate/front_door/person/snapshot",
        b"\xff\xd8\xff fake-jpeg",
    )

    mock_send.assert_called_once()
    args = mock_send.call_args[0]
    assert args[0] is night_config
    assert "person detected" in args[1]


@patch("app.frigate_handler.send_alert_email")
@patch("app.frigate_handler._unix_to_local")
def test_snapshot_skipped_outside_alert_window(
    mock_unix_to_local: object,
    mock_send: object,
    night_config: Config,
) -> None:
    mock_unix_to_local.side_effect = lambda _t: datetime(2024, 1, 15, 14, 0)
    end_time = _unix(datetime(2024, 1, 15, 14, 0))
    handler = FrigateHandler(night_config)
    handler.handle_message("frigate/events", _event_payload(end_time=end_time))

    handler.handle_message(
        "frigate/front_door/person/snapshot",
        b"\xff\xd8\xff fake-jpeg",
    )

    mock_send.assert_not_called()


@patch("app.frigate_handler.send_alert_email")
def test_snapshot_skipped_for_excluded_label(
    mock_send: object,
    env_vars: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EXCLUDED_LABELS", "bird")
    config = Config.from_env()
    end_time = _unix(datetime(2024, 1, 15, 20, 0))
    handler = FrigateHandler(config)
    handler.handle_message(
        "frigate/events",
        _event_payload(camera="yard", label="bird", end_time=end_time),
    )

    handler.handle_message("frigate/yard/bird/snapshot", b"jpeg")

    mock_send.assert_not_called()


@patch("app.frigate_handler.send_alert_email")
def test_snapshot_skipped_without_clip_or_snapshot(
    mock_send: object,
    night_config: Config,
) -> None:
    end_time = _unix(datetime(2024, 1, 15, 20, 0))
    handler = FrigateHandler(night_config)
    handler.handle_message(
        "frigate/events",
        _event_payload(end_time=end_time, has_snapshot=False, has_clip=False),
    )

    handler.handle_message(
        "frigate/front_door/person/snapshot",
        b"jpeg",
    )

    mock_send.assert_not_called()


@patch("app.frigate_handler.send_alert_email")
def test_snapshot_skipped_for_wrong_topic(
    mock_send: object,
    night_config: Config,
) -> None:
    end_time = _unix(datetime(2024, 1, 15, 20, 0))
    handler = FrigateHandler(night_config)
    handler.handle_message("frigate/events", _event_payload(end_time=end_time))

    handler.handle_message("frigate/front_door/person/thumbnail", b"jpeg")

    mock_send.assert_not_called()


@patch("app.frigate_handler.send_alert_email")
def test_snapshot_skipped_without_prior_event(
    mock_send: object,
    night_config: Config,
) -> None:
    handler = FrigateHandler(night_config)

    handler.handle_message(
        "frigate/front_door/person/snapshot",
        b"jpeg",
    )

    mock_send.assert_not_called()
