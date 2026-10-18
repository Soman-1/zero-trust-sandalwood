"""Tests for MQTT ingestion and Zero Trust message handlers."""

import json
import pytest
from app.mqtt.client import MQTTClientManager
from app.mqtt.handlers import handle_telemetry_message, handle_device_alert_message
from app.database.models.device import Device, DeviceStatus
from app.database.models.region import Region, RegionStatus
from app.core.security import generate_device_api_key, hash_device_api_key


def test_mqtt_client_local_dispatch():
    """Test MQTTClientManager local publish-subscribe dispatch."""
    client = MQTTClientManager()
    received = []

    def sample_handler(topic, payload):
        received.append((topic, payload.decode("utf-8")))

    client.subscribe("agroforestry/test/data", sample_handler)
    client.publish("agroforestry/test/data", {"sensor": "active"})

    assert len(received) == 1
    assert received[0][0] == "agroforestry/test/data"
    assert '"sensor": "active"' in received[0][1]


def test_mqtt_telemetry_handler_zero_trust_ingestion(db_session):
    """Test full telemetry ingestion over MQTT with device auth and integrity seal."""
    # Setup Region & Device
    region = Region(
        region_id="REG-KA-MQTT-01",
        name="MQTT Test Region",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[75.0, 13.0], [76.0, 13.0], [76.0, 14.0], [75.0, 14.0], [75.0, 13.0]]]
        },
        center_latitude=13.5,
        center_longitude=75.5,
        area_hectares=100.0,
        status=RegionStatus.ACTIVE,
    )
    db_session.add(region)
    db_session.commit()

    raw_key = generate_device_api_key()
    device = Device(
        device_id="DEV-MQTT-NODE-01",
        name="Field MQTT Node",
        device_type="STATIONARY_NODE",
        api_key_hash=hash_device_api_key(raw_key),
        status=DeviceStatus.ACTIVE,
        assigned_region_id=region.id,
    )
    db_session.add(device)
    db_session.commit()

    payload = {
        "device_id": "DEV-MQTT-NODE-01",
        "device_key": raw_key,
        "region_id": "REG-KA-MQTT-01",
        "latitude": 13.5,
        "longitude": 75.5,
        "temperature": 27.5,
        "humidity": 65.0,
        "soil_moisture": 52.0,
    }

    result = handle_telemetry_message(
        topic="agroforestry/DEV-MQTT-NODE-01/telemetry",
        payload_bytes=json.dumps(payload).encode("utf-8"),
        db=db_session,
    )

    assert result["success"] is True
    assert "measurement_uid" in result
    assert "integrity_hash" in result


def test_mqtt_telemetry_handler_rejects_unauthorized_device(db_session):
    """Test that unauthorized/forged device MQTT telemetry is rejected."""
    payload = {
        "device_id": "DEV-UNKNOWN-99",
        "device_key": "fake-key",
        "region_id": "REG-KA-MQTT-01",
        "latitude": 13.5,
        "longitude": 75.5,
        "temperature": 27.5,
        "humidity": 65.0,
        "soil_moisture": 52.0,
    }

    result = handle_telemetry_message(
        topic="agroforestry/DEV-UNKNOWN-99/telemetry",
        payload_bytes=json.dumps(payload).encode("utf-8"),
        db=db_session,
    )

    assert result["success"] is False


def test_mqtt_telemetry_handler_anti_replay_defense(db_session):
    """Test that replayed MQTT telemetry messages with identical nonces are rejected."""
    import time
    from app.core.security import generate_device_api_key, hash_device_api_key

    region = Region(
        region_id="REG-KA-REPLAY-01",
        name="MQTT Replay Test Region",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[75.0, 13.0], [76.0, 13.0], [76.0, 14.0], [75.0, 14.0], [75.0, 13.0]]]
        },
        center_latitude=13.5,
        center_longitude=75.5,
        area_hectares=100.0,
        status=RegionStatus.ACTIVE,
    )
    db_session.add(region)
    db_session.commit()

    raw_key = generate_device_api_key()
    device = Device(
        device_id="DEV-MQTT-REPLAY-01",
        name="Field Node Replay Test",
        device_type="STATIONARY_NODE",
        api_key_hash=hash_device_api_key(raw_key),
        status=DeviceStatus.ACTIVE,
        assigned_region_id=region.id,
    )
    db_session.add(device)
    db_session.commit()

    nonce = "mqtt-unique-nonce-12345"
    payload = {
        "device_id": "DEV-MQTT-REPLAY-01",
        "device_key": raw_key,
        "region_id": "REG-KA-REPLAY-01",
        "latitude": 13.5,
        "longitude": 75.5,
        "temperature": 27.5,
        "humidity": 65.0,
        "soil_moisture": 52.0,
        "nonce": nonce,
        "timestamp": time.time(),
    }

    # First attempt: succeeds
    res1 = handle_telemetry_message(
        topic="agroforestry/DEV-MQTT-REPLAY-01/telemetry",
        payload_bytes=json.dumps(payload).encode("utf-8"),
        db=db_session,
    )
    assert res1["success"] is True

    # Second attempt with same nonce: rejected as replay attack
    res2 = handle_telemetry_message(
        topic="agroforestry/DEV-MQTT-REPLAY-01/telemetry",
        payload_bytes=json.dumps(payload).encode("utf-8"),
        db=db_session,
    )
    assert res2["success"] is False
    assert res2["error"] == "REPLAY_ATTACK_DETECTED"
