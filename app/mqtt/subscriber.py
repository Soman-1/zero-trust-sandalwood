"""MQTT Subscriber for registering and routing agroforestry telemetry topics."""

from typing import Optional
from app.core.config import settings
from app.core.logging import logger
from app.mqtt.client import MQTTClientManager, mqtt_client
from app.mqtt.handlers import handle_telemetry_message, handle_device_alert_message


class MQTTSubscriber:
    """Configures and runs background subscriptions to field device topics."""

    def __init__(self, client: Optional[MQTTClientManager] = None):
        self.client = client or mqtt_client
        self.prefix = settings.MQTT_TOPIC_PREFIX

    def setup_subscriptions(self) -> None:
        """Register Zero Trust topic patterns with their respective handlers."""
        # 1. Telemetry topic patterns
        telemetry_wildcard = f"{self.prefix}/+/telemetry"
        telemetry_direct = f"{self.prefix}/telemetry"

        self.client.subscribe(telemetry_wildcard, handle_telemetry_message)
        self.client.subscribe(telemetry_direct, handle_telemetry_message)
        logger.info(f"Registered MQTT handlers for telemetry topics: '{telemetry_wildcard}', '{telemetry_direct}'")

        # 2. Alert & distress topic pattern
        alert_wildcard = f"{self.prefix}/+/alerts"
        self.client.subscribe(alert_wildcard, handle_device_alert_message)
        logger.info(f"Registered MQTT handlers for alert topics: '{alert_wildcard}'")

    def start(self) -> bool:
        """Initialize subscriptions and connect to broker."""
        self.setup_subscriptions()
        return self.client.connect()

    def stop(self) -> None:
        """Disconnect and stop subscriber."""
        self.client.disconnect()


# Singleton instance
mqtt_subscriber = MQTTSubscriber()
