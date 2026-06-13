from __future__ import annotations

import logging
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt

from app.config import Config
from app.frigate_handler import FrigateHandler

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def run() -> int:
    configure_logging()

    try:
        config = Config.from_env()
        config.validate()
    except ValueError as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    handler = FrigateHandler(config)
    stop_event = threading.Event()

    def on_connect(client: mqtt.Client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code != 0:
            logger.error("MQTT connect failed with code %s", reason_code)
            return
        logger.info(
            "Connected to MQTT broker %s:%s, subscribing to %s",
            config.mqtt_host,
            config.mqtt_port,
            config.subscribe_topic,
        )
        client.subscribe(config.subscribe_topic)

    def on_message(_client: mqtt.Client, _userdata, message: mqtt.MQTTMessage) -> None:
        handler.handle_message(message.topic, message.payload)

    def on_disconnect(_client: mqtt.Client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code != 0 and not stop_event.is_set():
            logger.warning("Unexpected MQTT disconnect (code=%s)", reason_code)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if config.mqtt_user:
        client.username_pw_set(config.mqtt_user, config.mqtt_pass or None)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    def shutdown(_signum, _frame) -> None:
        logger.info("Shutdown requested")
        stop_event.set()
        client.disconnect()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    logger.info("Starting Frigate email notifier")
    try:
        client.connect(config.mqtt_host, config.mqtt_port, keepalive=60)
    except OSError as exc:
        logger.error(
            "Failed to connect to MQTT broker %s:%s: %s",
            config.mqtt_host,
            config.mqtt_port,
            exc,
        )
        return 1

    client.loop_start()

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    finally:
        client.loop_stop()
        client.disconnect()
        logger.info("Stopped")

    return 0


if __name__ == "__main__":
    sys.exit(run())
