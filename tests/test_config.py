from __future__ import annotations

import pytest

from app.config import Config


def test_from_env_required_and_defaults(env_vars: None) -> None:
    config = Config.from_env()

    assert config.mqtt_host == "mqtt.example.com"
    assert config.mqtt_port == 1883
    assert config.mqtt_topic_prefix == "frigate"
    assert config.smtp_port == 587
    assert config.smtp_use_tls is True
    assert config.alert_start_hour == 19
    assert config.alert_end_hour == 7
    assert config.excluded_labels == frozenset({"bird"})
    assert config.smtp_to == ["you@example.com", "other@example.com"]


def test_topic_properties(minimal_config: Config) -> None:
    assert minimal_config.events_topic == "frigate/events"
    assert minimal_config.subscribe_topic == "frigate/#"


def test_from_env_missing_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MQTT_HOST", raising=False)

    with pytest.raises(ValueError, match="MQTT_HOST"):
        Config.from_env()


def test_validate_empty_smtp_to(env_vars: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_TO", "")
    config = Config.from_env()

    with pytest.raises(ValueError, match="SMTP_TO"):
        config.validate()


def test_validate_invalid_alert_hours(env_vars: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALERT_START_HOUR", "25")
    config = Config.from_env()

    with pytest.raises(ValueError, match="ALERT_START_HOUR"):
        config.validate()


def test_excluded_labels_case_insensitive(env_vars: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EXCLUDED_LABELS", "Bird, CAT")
    config = Config.from_env()

    assert config.excluded_labels == frozenset({"bird", "cat"})
