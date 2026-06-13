from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.config import Config
from app.email_sender import send_alert_email
from app.models import Event

logger = logging.getLogger(__name__)


class FrigateHandler:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._last_event: Event | None = None
        self._last_event_json: str | None = None

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

        end_time = _unix_to_local(after.end_time)
        if end_time is None:
            logger.warning("Snapshot received without event end time")
            return

        subject = (
            f"{after.label} detected.  "
            f"{_unix_to_local(event.before.start_time)} {end_time}"
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
            except Exception:
                logger.exception("Failed to send alert email")
        else:
            logger.debug("Outside alert window: %s", subject)

    @property
    def last_event(self) -> Event | None:
        return self._last_event


def _unix_to_local(unix_time: float | None) -> datetime | None:
    if unix_time is None:
        return None
    return datetime.fromtimestamp(unix_time, tz=timezone.utc).astimezone()


def _is_night(event_end: datetime, start_hour: int, end_hour: int) -> bool:
    event_time = event_end.time()
    start = event_end.replace(hour=start_hour, minute=0, second=0, microsecond=0).time()
    end = event_end.replace(hour=end_hour, minute=0, second=0, microsecond=0).time()
    return event_time >= start or event_time < end

