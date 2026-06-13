from __future__ import annotations

import os
from dataclasses import dataclass


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Required environment variable {name} is not set")
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return int(raw)


def _csv(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


@dataclass(frozen=True)
class Config:
    mqtt_host: str
    mqtt_port: int
    mqtt_user: str
    mqtt_pass: str
    mqtt_topic_prefix: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    smtp_from: str
    smtp_to: list[str]
    smtp_use_tls: bool
    alert_start_hour: int
    alert_end_hour: int
    excluded_labels: frozenset[str]

    @property
    def events_topic(self) -> str:
        return f"{self.mqtt_topic_prefix}/events"

    @property
    def subscribe_topic(self) -> str:
        return f"{self.mqtt_topic_prefix}/#"

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            mqtt_host=_require("MQTT_HOST"),
            mqtt_port=_int("MQTT_PORT", 1883),
            mqtt_user=_optional("MQTT_USER"),
            mqtt_pass=_optional("MQTT_PASS"),
            mqtt_topic_prefix=_optional("MQTT_TOPIC_PREFIX", "frigate"),
            smtp_host=_require("SMTP_HOST"),
            smtp_port=_int("SMTP_PORT", 587),
            smtp_user=_require("SMTP_USER"),
            smtp_pass=_require("SMTP_PASS"),
            smtp_from=_require("SMTP_FROM"),
            smtp_to=_csv("SMTP_TO", ""),
            smtp_use_tls=_bool("SMTP_USE_TLS", True),
            alert_start_hour=_int("ALERT_START_HOUR", 19),
            alert_end_hour=_int("ALERT_END_HOUR", 7),
            excluded_labels=frozenset(label.lower() for label in _csv("EXCLUDED_LABELS", "bird")),
        )

    def validate(self) -> None:
        if not self.smtp_to:
            raise ValueError("SMTP_TO must contain at least one recipient")
        if not (0 <= self.alert_start_hour <= 23 and 0 <= self.alert_end_hour <= 23):
            raise ValueError("ALERT_START_HOUR and ALERT_END_HOUR must be between 0 and 23")
