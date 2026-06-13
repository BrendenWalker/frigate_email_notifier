from __future__ import annotations

import pytest

from app.config import Config


@pytest.fixture
def env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MQTT_HOST", "mqtt.example.com")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASS", "secret")
    monkeypatch.setenv("SMTP_FROM", "alerts@example.com")
    monkeypatch.setenv("SMTP_TO", "you@example.com,other@example.com")


@pytest.fixture
def minimal_config(env_vars: None) -> Config:
    config = Config.from_env()
    config.validate()
    return config
