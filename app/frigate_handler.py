from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timezone, tzinfo
from zoneinfo import ZoneInfo

from app.config import Config
from app.email_sender import send_alert_email
from app.models import Event

logger = logging.getLogger(__name__)

_EMAILED_EVENT_HISTORY_SIZE = 1024


class FrigateHandler:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._timezone = ZoneInfo(config.timezone_name)
        self._last_event: Event | None = None
        self._last_event_json: str | None = None
        self._emailed_event_ids: set[str] = set()
        self._emailed_event_history: deque[str] = deque()

    def handle_message(self, topic: str, payload: bytes) -> None:
        if topic == self._config.events_topic:
            self._handle_event(payload)
            return

        stats_topic = f"{self._config.mqtt_topic_prefix}/stats"
        if topic == stats_topic:
            logger.debug("Stats message: %s", payload.decode("utf-8", errors="replace"))
            return

        if topic.endswith("/snapshot"):
            self._handle_snapshot(topic, payload)

    def _handle_event(self, payload: bytes) -> None:
        try:
            raw = payload.decode("utf-8")
            data = json.loads(raw)
            self._last_event = Event.from_dict(data)
            self._last_event_json = raw
            before = self._last_event.before
            if before and before.label is not None:
                logger.info(
                    "Object %s found. Score: %.0f%%",
                    before.label,
                    before.score * 100,
                )
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
            logger.exception("Failed to parse event message: %s", exc)

    def _handle_snapshot(self, topic: str, payload: bytes) -> None:
        event = self._last_event
        if event is None or event.after is None or event.before is None:
            return

        after = event.after
        if not (after.has_clip or after.has_snapshot):
            return

        label = (after.label or "").lower()
        if label in self._config.excluded_labels:
            logger.debug("Skipping excluded label snapshot: %s", after.label)
            return

        expected_topic = (
            f"{self._config.mqtt_topic_prefix}/{after.camera}/{after.label}/snapshot"
        )
        if topic != expected_topic:
            return

        event_id = _event_id(event)
        if event_id in self._emailed_event_ids:
            logger.debug("Skipping already emailed event: %s", event_id)
            return

        end_time = _unix_to_local(after.end_time, self._timezone)
        if end_time is None:
            logger.warning("Snapshot received without event end time")
            return

        start_time = _unix_to_local(event.before.start_time, self._timezone)
        subject = (
            f"{after.label} detected.  "
            f"{_format_event_time(start_time)} - {_format_event_time(end_time)}"
        )

        if _is_night(
            end_time,
            self._config.alert_start_hour,
            self._config.alert_end_hour,
        ):
            try:
                send_alert_email(
                    self._config,
                    subject,
                    payload,
                    self._last_event_json or "",
                )
                self._remember_emailed_event(event_id)
            except Exception:
                logger.exception("Failed to send alert email")
        else:
            logger.debug("Outside alert window: %s", subject)

    def _remember_emailed_event(self, event_id: str) -> None:
        if len(self._emailed_event_history) >= _EMAILED_EVENT_HISTORY_SIZE:
            expired_id = self._emailed_event_history.popleft()
            self._emailed_event_ids.remove(expired_id)
        self._emailed_event_history.append(event_id)
        self._emailed_event_ids.add(event_id)

    @property
    def last_event(self) -> Event | None:
        return self._last_event


def _event_id(event: Event) -> str:
    before = event.before
    after = event.after
    assert before is not None and after is not None
    return after.id or before.id or (
        f"{after.camera}:{after.label}:{before.start_time}:{after.end_time}"
    )


def _unix_to_local(
    unix_time: float | None,
    local_timezone: tzinfo,
) -> datetime | None:
    if unix_time is None:
        return None
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).astimezone(local_timezone)


def _format_event_time(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    return value.strftime("%Y-%m-%d %H:%M:%S %Z")


def _is_night(event_end: datetime, start_hour: int, end_hour: int) -> bool:
    event_time = event_end.time()
    start = event_end.replace(hour=start_hour, minute=0, second=0, microsecond=0).time()
    end = event_end.replace(hour=end_hour, minute=0, second=0, microsecond=0).time()
    return event_time >= start or event_time < end

