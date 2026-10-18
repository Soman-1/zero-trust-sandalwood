"""MQTT Client Manager for IoT field device telemetry and messaging."""

import json
from typing import Callable, Dict, Any, Optional, List
from app.core.config import settings
from app.core.logging import logger

try:
    import paho.mqtt.client as paho_mqtt
    HAS_PAHO = True
except ImportError:
    HAS_PAHO = False


class MQTTClientManager:
    """Manages MQTT broker connection, topic subscriptions, and message dispatching."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        keepalive: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: Optional[bool] = None,
    ):
        self.host = host or settings.MQTT_HOST
        self.port = port or settings.MQTT_PORT
        self.keepalive = keepalive or settings.MQTT_KEEPALIVE
        self.username = username or settings.MQTT_USERNAME
        self.password = password or settings.MQTT_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.MQTT_USE_TLS
        self.is_connected = False
        self.subscriptions: Dict[str, List[Callable[[str, bytes], None]]] = {}
        self._client = None

        if HAS_PAHO:
            self._client = paho_mqtt.Client()
            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)
            if self.use_tls:
                self._client.tls_set()
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
            logger.info(f"Connected to MQTT broker at {self.host}:{self.port}")
            # Resubscribe to all registered topics
            for topic in self.subscriptions:
                client.subscribe(topic)
                logger.info(f"Subscribed to MQTT topic: {topic}")
        else:
            self.is_connected = False
            logger.warning(f"Failed to connect to MQTT broker with result code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.is_connected = False
        logger.warning(f"Disconnected from MQTT broker (rc={rc})")

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        payload = msg.payload
        self.dispatch_message(topic, payload)

    def dispatch_message(self, topic: str, payload: bytes) -> None:
        """Dispatch incoming MQTT payload to registered topic handlers."""
        dispatched = False
        for sub_topic, handlers in self.subscriptions.items():
            if self._topic_matches(sub_topic, topic):
                for handler in handlers:
                    try:
                        handler(topic, payload)
                        dispatched = True
                    except Exception as e:
                        logger.error(f"Error executing MQTT handler for topic '{topic}': {e}")
        if not dispatched:
            logger.debug(f"No handlers matched MQTT topic: {topic}")

    @staticmethod
    def _topic_matches(pattern: str, topic: str) -> bool:
        """Check if an MQTT topic matches a subscription pattern with wildcards (+ and #)."""
        pattern_parts = pattern.split("/")
        topic_parts = topic.split("/")
        i = 0
        while i < len(pattern_parts) and i < len(topic_parts):
            if pattern_parts[i] == "#":
                return True
            if pattern_parts[i] != "+" and pattern_parts[i] != topic_parts[i]:
                return False
            i += 1
        if i < len(pattern_parts) and pattern_parts[i] == "#":
            return True
        return i == len(pattern_parts) and i == len(topic_parts)

    def connect(self) -> bool:
        """Connect to the MQTT broker."""
        if not HAS_PAHO or self._client is None:
            logger.info("Paho-MQTT client not active; running in virtual dispatch mode.")
            self.is_connected = True
            return True

        try:
            self._client.connect(self.host, self.port, self.keepalive)
            self._client.loop_start()
            return True
        except Exception as e:
            logger.warning(f"Could not connect to live MQTT broker at {self.host}:{self.port} ({e}). Falling back to local broker queue.")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the MQTT broker."""
        if HAS_PAHO and self._client and self.is_connected:
            self._client.loop_stop()
            self._client.disconnect()
            self.is_connected = False

    def subscribe(self, topic: str, handler: Callable[[str, bytes], None]) -> None:
        """Register a callback handler for a topic pattern."""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        self.subscriptions[topic].append(handler)

        if HAS_PAHO and self._client and self.is_connected:
            self._client.subscribe(topic)
            logger.info(f"Subscribed live to MQTT topic: {topic}")

    def publish(self, topic: str, payload: Any, qos: int = 1, retain: bool = False) -> bool:
        """Publish payload (dict, str, or bytes) to an MQTT topic."""
        if isinstance(payload, dict):
            payload_str = json.dumps(payload)
        elif isinstance(payload, bytes):
            payload_str = payload
        else:
            payload_str = str(payload)

        if HAS_PAHO and self._client and self.is_connected:
            info = self._client.publish(topic, payload_str, qos=qos, retain=retain)
            return info.rc == paho_mqtt.MQTT_ERR_SUCCESS
        else:
            # Self-dispatch in memory for local/test workflows
            raw_bytes = payload_str.encode("utf-8") if isinstance(payload_str, str) else payload_str
            self.dispatch_message(topic, raw_bytes)
            return True


# Default instance
mqtt_client = MQTTClientManager()
