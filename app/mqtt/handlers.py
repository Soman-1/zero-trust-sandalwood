"""Zero Trust MQTT message handlers for field telemetry and registration."""

import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.core.errors import AppException, DeviceAuthError, ValidationError
from app.database.database import SessionLocal
from app.database.models.device import Device, DeviceStatus
from app.schemas.measurement import MeasurementIngestRequest
from app.services.device_service import DeviceService
from app.services.measurement_service import MeasurementService
from app.services.audit_service import AuditService

_SENSITIVE_MQTT_KEYS = {
    "device_key", "api_key", "password", "token", "secret", "authorization"
}

def _redact_mqtt_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove credential fields before persisting MQTT payloads to audit logs."""
    if not isinstance(data, dict):
        return {}
    return {
        k: ("***REDACTED***" if k.lower() in _SENSITIVE_MQTT_KEYS else v)
        for k, v in data.items()
    }



def handle_telemetry_message(topic: str, payload_bytes: bytes, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Zero Trust MQTT Telemetry Handler:
    Validates device authenticity, payload schema, physical sensor bounds,
    and processes measurement ingestion into the secure database ledger.
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    try:
        try:
            payload_str = payload_bytes.decode("utf-8")
            data = json.loads(payload_str)
        except Exception as e:
            logger.error(f"MQTT invalid JSON payload on {topic}: {e}")
            AuditService.record_event(
                db=db,
                event_type="UNAUTHORIZED_ACCESS",
                action="INVALID_MQTT_JSON",
                description=f"Malformed JSON payload received on MQTT topic {topic}",
                actor_type="DEVICE",
                event_payload={"topic": topic, "error": str(e)},
            )
            return {"success": False, "error": "INVALID_JSON_PAYLOAD"}

        device_id = data.get("device_id")
        device_key = data.get("device_key") or data.get("api_key")

        if not device_id or not device_key:
            logger.warning(f"MQTT telemetry rejected: missing device credentials on {topic}")
            AuditService.record_event(
                db=db,
                event_type="UNAUTHORIZED_ACCESS",
                action="MISSING_MQTT_CREDENTIALS",
                actor_type="DEVICE",
                actor_id=device_id or "UNKNOWN_DEVICE",
                description="MQTT telemetry rejected: missing device identity or API key credentials",
                event_payload={"topic": topic, "device_id": device_id},
            )
            return {"success": False, "error": "MISSING_DEVICE_CREDENTIALS"}

        # Authenticate Device
        device = DeviceService.authenticate_device(db, device_id=device_id, raw_api_key=device_key)

        # Parse and validate schema
        recorded_at_raw = data.get("timestamp") or data.get("recorded_at")
        recorded_at = None
        if recorded_at_raw:
            try:
                recorded_at = datetime.fromisoformat(str(recorded_at_raw).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        # Zero Trust Anti-Replay & Freshness Validation
        from app.core.anti_replay import anti_replay_validator
        import app.core.runtime as runtime
        import time

        nonce = data.get("nonce")
        req_ts = None
        if recorded_at:
            req_ts = recorded_at.timestamp()
        elif recorded_at_raw:
            try:
                req_ts = float(recorded_at_raw)
            except (ValueError, TypeError):
                req_ts = time.time()
        elif nonce:
            req_ts = time.time()

        if runtime.require_ingest_freshness and not nonce:
            logger.warning(f"MQTT telemetry rejected: missing nonce from device '{device_id}'")
            AuditService.record_event(
                db=db,
                event_type="UNAUTHORIZED_ACCESS",
                action="MISSING_NONCE",
                actor_type="DEVICE",
                actor_id=device_id,
                description="MQTT telemetry rejected: missing nonce in strict Zero Trust mode",
                event_payload={"topic": topic, "device_id": device_id},
            )
            return {"success": False, "error": "MISSING_NONCE", "message": "Zero Trust ingestion requires a unique nonce"}

        if req_ts is not None or nonce is not None:
            ts_to_check = req_ts if req_ts is not None else time.time()
            is_valid, replay_err = anti_replay_validator.validate_request(
                request_timestamp=ts_to_check,
                nonce=nonce,
                caller_id=device_id,
            )
            if not is_valid:
                logger.warning(f"MQTT telemetry rejected by Anti-Replay validator: {replay_err}")
                AuditService.record_event(
                    db=db,
                    event_type="UNAUTHORIZED_ACCESS",
                    action="REPLAY_ATTACK_DETECTED",
                    actor_type="DEVICE",
                    actor_id=device_id,
                    description=f"MQTT telemetry replay detected: {replay_err}",
                    event_payload={"topic": topic, "device_id": device_id, "nonce": nonce},
                )
                return {"success": False, "error": "REPLAY_ATTACK_DETECTED", "message": replay_err}

        try:
            latitude = float(data["latitude"])
            longitude = float(data["longitude"])
            temperature = float(data["temperature"])
            humidity = float(data["humidity"])
            soil_moisture = float(data["soil_moisture"])
        except (KeyError, ValueError, TypeError) as parse_err:
            logger.warning(f"MQTT telemetry invalid payload format from device '{device_id}': {parse_err}")
            AuditService.record_event(
                db=db,
                event_type="VALIDATION_FAILURE",
                action="INVALID_MQTT_PAYLOAD",
                actor_type="DEVICE",
                actor_id=device_id,
                description=f"Invalid or missing numeric telemetry fields: {parse_err}",
                event_payload={"topic": topic, "raw_data": _redact_mqtt_payload(data)},
            )
            return {"success": False, "error": "INVALID_SENSOR_DATA", "message": str(parse_err)}

        ingest_payload = MeasurementIngestRequest(
            region_id=data.get("region_id"),
            tree_id=data.get("tree_id"),
            latitude=latitude,
            longitude=longitude,
            temperature=temperature,
            humidity=humidity,
            soil_moisture=soil_moisture,
            additional_metrics=data.get("additional_metrics"),
            recorded_at=recorded_at,
        )

        # Execute Ingestion Pipeline
        measurement = MeasurementService.ingest_single_measurement(
            db=db,
            request=ingest_payload,
            device=device,
        )

        logger.info(f"MQTT telemetry successfully ingested for device {device_id}, tree {measurement.tree_id or 'N/A'}")
        return {
            "success": True,
            "measurement_uid": measurement.measurement_uid,
            "integrity_hash": measurement.integrity_hash,
            "is_anomaly": measurement.is_anomaly,
        }

    except AppException as ae:
        logger.warning(f"MQTT Ingestion Zero Trust rejection: {ae.message}")
        return {"success": False, "error": ae.error_code, "message": ae.message}
    except Exception as exc:
        logger.error(f"MQTT Ingestion unhandled exception: {exc}")
        return {"success": False, "error": "INTERNAL_INGESTION_ERROR", "message": str(exc)}
    finally:
        if should_close_db:
            db.close()


def handle_device_alert_message(topic: str, payload_bytes: bytes, db: Optional[Session] = None) -> Dict[str, Any]:
    """Handle device hardware distress or tampering alert broadcasts."""
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    try:
        payload_str = payload_bytes.decode("utf-8")
        data = json.loads(payload_str)

        device_id = data.get("device_id")
        device_key = data.get("device_key") or data.get("api_key")
        alert_type = data.get("alert_type", "HARDWARE_TAMPER_ALERT")
        description = data.get("description", "Device emitted distress beacon")

        if not device_id or not device_key:
            logger.warning(f"MQTT alert rejected: missing device credentials on {topic}")
            return {"success": False, "error": "MISSING_DEVICE_CREDENTIALS"}

        DeviceService.authenticate_device(db, device_id=device_id, raw_api_key=device_key)

        AuditService.record_event(
            db=db,
            event_type="TAMPER_DETECTED",
            action="DEVICE_DISTRESS_BEACON",
            actor_type="DEVICE",
            actor_id=device_id or "UNKNOWN_DEVICE",
            description=f"Device broadcast distress alert: {description}",
            event_payload={"topic": topic, "alert_type": alert_type, "raw_data": _redact_mqtt_payload(data)},
        )
        return {"success": True, "recorded": True}
    except Exception as e:
        logger.error(f"Failed to process device alert MQTT message: {e}")
        return {"success": False, "error": str(e)}
    finally:
        if should_close_db:
            db.close()
