"""Comprehensive tests for Cryptographic Integrity, Tamper Detection, and Field Encryption."""

import pytest
from datetime import datetime, timezone
from fastapi import status
from sqlalchemy import select

from app.core.encryption import encrypt_data, decrypt_data
from app.database.models.environmental_measurement import EnvironmentalMeasurement


def setup_measurement_for_integrity(client):
    """Helper to seed user, region, device, and an initial measurement."""
    # 1. Admin
    client.post("/api/v1/auth/register", json={
        "email": "admin_integ@agroforestry.gov.in",
        "username": "admin_integ",
        "full_name": "Integrity Admin",
        "password": "Password12345!",
        "role": "ADMIN",
    })
    token = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_integ",
        "password": "Password12345!",
    }).json()["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 2. Region
    region_resp = client.post(
        "/api/v1/regions",
        json={
            "region_id": "REG-KA-INTEG",
            "name": "Integrity Test Reserve",
            "boundary_geojson": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [75.50, 13.90],
                        [75.60, 13.90],
                        [75.60, 14.00],
                        [75.50, 14.00],
                        [75.50, 13.90],
                    ]
                ],
            },
        },
        headers=user_headers,
    )

    # 3. Device
    dev_reg = client.post(
        "/api/v1/devices",
        json={"device_id": "DEV-INTEG-01", "name": "Integrity Test Node", "assigned_region_id": region_resp.json().get("id")},
        headers=user_headers,
    )
    api_key = dev_reg.json()["api_key"]
    dev_headers = {"X-Device-ID": "DEV-INTEG-01", "X-Device-Key": api_key}

    # 4. Ingest Telemetry
    ingest_resp = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": "REG-KA-INTEG",
            "latitude": 13.9500,
            "longitude": 75.5500,
            "temperature": 27.5,
            "humidity": 68.0,
            "soil_moisture": 45.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=dev_headers,
    )
    measurement_uid = ingest_resp.json()["measurement_uid"]

    return user_headers, dev_headers, "REG-KA-INTEG", measurement_uid


def test_encryption_and_decryption_roundtrip():
    """Test symmetric AES encryption and decryption utility."""
    secret_text = "Sensitive-Device-Secret-Credential-2026!#%"
    encrypted = encrypt_data(secret_text)
    assert encrypted != secret_text
    assert len(encrypted) > 20

    decrypted = decrypt_data(encrypted)
    assert decrypted == secret_text


def test_unmodified_measurement_integrity_verification(client):
    """Test that an unmodified ingested record passes cryptographic verification."""
    user_headers, _, _, measurement_uid = setup_measurement_for_integrity(client)

    # Verify integrity
    resp = client.post(
        f"/api/v1/measurements/{measurement_uid}/verify-integrity",
        headers=user_headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["is_valid"] is True
    assert data["status"] == "VERIFIED_AUTHENTIC"
    assert data["stored_hash"] is not None
    assert data["stored_hash"] == data["computed_hash"]


def test_tamper_detection_on_modified_record(client, db_session):
    """
    Zero Trust Tamper Detection Test:
    Simulate an unauthorized attacker or rogue script modifying database records
    (e.g. altering temperature from 27.5°C to 48.0°C).
    The verification engine must detect the mismatch, return TAMPERED_DETECTED,
    and flag the record as is_tampered = True.
    """
    user_headers, _, _, measurement_uid = setup_measurement_for_integrity(client)

    # 1. Modify the record directly in the database
    stmt = select(EnvironmentalMeasurement).where(
        EnvironmentalMeasurement.measurement_uid == measurement_uid
    )
    measurement = db_session.execute(stmt).scalar_one()
    measurement.temperature = 48.0  # Tampered field!
    db_session.commit()

    # 2. Run integrity verification endpoint
    resp = client.post(
        f"/api/v1/measurements/{measurement_uid}/verify-integrity",
        headers=user_headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["is_valid"] is False
    assert data["status"] == "TAMPERED_DETECTED"
    assert data["stored_hash"] != data["computed_hash"]

    # 3. Verify that the is_tampered flag is now True in the database
    db_session.refresh(measurement)
    assert measurement.is_tampered is True


def test_bulk_integrity_audit_scan(client, db_session):
    """Test scanning all stored measurements for tampering."""
    user_headers, _, region_id, measurement_uid = setup_measurement_for_integrity(client)

    # Tamper with the record
    stmt = select(EnvironmentalMeasurement).where(
        EnvironmentalMeasurement.measurement_uid == measurement_uid
    )
    m = db_session.execute(stmt).scalar_one()
    m.humidity = 10.0  # Tampered!
    db_session.commit()

    # Run bulk audit scan
    scan_resp = client.post(
        f"/api/v1/measurements/integrity/audit-scan?region_id={region_id}",
        headers=user_headers,
    )
    assert scan_resp.status_code == status.HTTP_200_OK
    data = scan_resp.json()
    assert data["total_scanned"] >= 1
    assert data["tampered_count"] >= 1
    assert measurement_uid in data["tampered_uids"]
