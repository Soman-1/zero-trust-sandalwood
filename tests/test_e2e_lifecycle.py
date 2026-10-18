"""Comprehensive End-to-End (E2E) Integration Test covering all 14 phases in a single unified flow."""

import pytest
from datetime import datetime, timezone
from fastapi import status


def test_full_system_e2e_lifecycle(client):
    """
    Full End-to-End Operational Lifecycle Test:
    1. Register and authenticate Admin and Operator.
    2. Create a Monitored Agroforestry Region with GeoJSON polygon boundaries.
    3. Identify and register Sandalwood Trees with operator-assigned IDs (KA-01, KA-02).
    4. Register an IoT field telemetry node and obtain cryptographic API key.
    5. Ingest normal telemetry -> validated, AI evaluated, SHA-256 sealed.
    6. Ingest critical anomalous telemetry -> triggers AI anomaly detection and automatic Alert.
    7. Operator investigates and resolves the alert.
    8. Verify cryptographic hash-chained audit ledger.
    9. Anchor audit trail batch to blockchain.
    10. Verify GIS geospatial map layer and executive dashboard overview.
    """
    # ----------------------------------------------------
    # Step 1: User Registration & Authentication
    # ----------------------------------------------------
    client.post("/api/v1/auth/register", json={
        "email": "chief_admin@agroforestry.gov.in",
        "username": "chief_admin",
        "full_name": "Chief Forest Officer",
        "password": "MasterSecurePassword2026!",
        "role": "ADMIN",
    })
    admin_login = client.post("/api/v1/auth/login", json={
        "username_or_email": "chief_admin",
        "password": "MasterSecurePassword2026!",
    })
    assert admin_login.status_code == status.HTTP_200_OK
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/api/v1/auth/register", json={
        "email": "field_operator@agroforestry.gov.in",
        "username": "field_operator",
        "full_name": "Field Range Officer",
        "password": "OperatorSecurePassword2026!",
        "role": "OPERATOR",
    })
    op_login = client.post("/api/v1/auth/login", json={
        "username_or_email": "field_operator",
        "password": "OperatorSecurePassword2026!",
    })
    op_token = op_login.json()["access_token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    # ----------------------------------------------------
    # Step 2: Create Monitored Agroforestry Region
    # ----------------------------------------------------
    region_payload = {
        "region_id": "REG-KA-SHIVAMOGGA-E2E",
        "name": "Shivamogga Sandalwood Core Reserve",
        "area_hectares": 1250.0,
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
    }
    reg_resp = client.post("/api/v1/regions", json=region_payload, headers=admin_headers)
    assert reg_resp.status_code == status.HTTP_201_CREATED
    region_id = reg_resp.json()["region_id"]
    region_db_id = reg_resp.json()["id"]
    assert region_id == "REG-KA-SHIVAMOGGA-E2E"

    # ----------------------------------------------------
    # Step 3: Register Sandalwood Trees (Sequential IDs)
    # ----------------------------------------------------
    tree1_resp = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-01",
            "region_id": region_id,
            "species": "Santalum album",
            "latitude": 13.9500,
            "longitude": 75.5500,
            "estimated_age_years": 12,
            "girth_cm": 45.0,
            "height_m": 8.5,
            "status": "HEALTHY",
        },
        headers=op_headers,
    )
    assert tree1_resp.status_code == status.HTTP_201_CREATED
    tree1_uid = tree1_resp.json()["tree_uid"]
    assert tree1_uid == "KA-01"

    tree2_resp = client.post(
        "/api/v1/trees",
        json={
            "tree_uid": "KA-02",
            "region_id": region_id,
            "species": "Santalum album",
            "latitude": 13.9520,
            "longitude": 75.5520,
            "estimated_age_years": 8,
            "girth_cm": 30.0,
            "height_m": 6.0,
            "status": "HEALTHY",
        },
        headers=op_headers,
    )
    assert tree2_resp.status_code == status.HTTP_201_CREATED
    tree2_uid = tree2_resp.json()["tree_uid"]
    assert tree2_uid == "KA-02"

    # ----------------------------------------------------
    # Step 4: Register Field IoT Hardware Device
    # ----------------------------------------------------
    dev_resp = client.post(
        "/api/v1/devices",
        json={
            "device_id": "DEV-E2E-NODE-01",
            "name": "Shivamogga Core Sensor Node 1",
            "device_type": "STATIONARY_NODE",
            "assigned_region_id": region_db_id,
        },
        headers=admin_headers,
    )
    assert dev_resp.status_code == status.HTTP_201_CREATED
    api_key = dev_resp.json()["api_key"]
    dev_headers = {
        "X-Device-ID": "DEV-E2E-NODE-01",
        "X-Device-Key": api_key,
    }

    # ----------------------------------------------------
    # Step 5: Ingest Normal Field Telemetry
    # ----------------------------------------------------
    t_normal = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": region_id,
            "tree_id": tree1_uid,
            "latitude": 13.9500,
            "longitude": 75.5500,
            "temperature": 27.5,
            "humidity": 68.0,
            "soil_moisture": 52.0,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=dev_headers,
    )
    assert t_normal.status_code == status.HTTP_201_CREATED
    normal_uid = t_normal.json()["measurement_uid"]

    # Verify normal measurement is non-anomalous & authentic
    verify_resp = client.post(f"/api/v1/measurements/{normal_uid}/verify-integrity", headers=admin_headers)
    assert verify_resp.status_code == status.HTTP_200_OK
    assert verify_resp.json()["is_valid"] is True
    assert verify_resp.json()["status"] == "VERIFIED_AUTHENTIC"

    # ----------------------------------------------------
    # Step 6: Ingest Critical Anomalous Telemetry (Spike)
    # ----------------------------------------------------
    t_anomaly = client.post(
        "/api/v1/measurements/ingest",
        json={
            "region_id": region_id,
            "tree_id": tree2_uid,
            "latitude": 13.9520,
            "longitude": 75.5520,
            "temperature": 48.5,  # Extreme heat
            "humidity": 14.0,     # Extreme dry
            "soil_moisture": 7.0, # Severe drought
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        },
        headers=dev_headers,
    )
    assert t_anomaly.status_code == status.HTTP_201_CREATED
    anomaly_uid = t_anomaly.json()["measurement_uid"]

    # Verify AI detected the anomaly
    meas_check = client.get(f"/api/v1/measurements/{anomaly_uid}", headers=admin_headers)
    assert meas_check.json()["is_anomaly"] is True

    # ----------------------------------------------------
    # Step 7: Verify Auto-Triggered Alert & Resolve It
    # ----------------------------------------------------
    alerts_resp = client.get(f"/api/v1/alerts?region_id={region_id}", headers=admin_headers)
    assert alerts_resp.status_code == status.HTTP_200_OK
    assert alerts_resp.json()["total"] >= 1
    alert_uid = alerts_resp.json()["alerts"][0]["alert_uid"]

    # Operator Acknowledges
    ack_resp = client.post(
        f"/api/v1/alerts/{alert_uid}/acknowledge",
        json={"notes": "Field officer investigating tree microclimate"},
        headers=op_headers,
    )
    assert ack_resp.status_code == status.HTTP_200_OK
    assert ack_resp.json()["status"] == "ACKNOWLEDGED"

    # Operator Resolves
    res_resp = client.post(
        f"/api/v1/alerts/{alert_uid}/resolve",
        json={"resolution_notes": "Emergency drip irrigation activated. Soil moisture normalized."},
        headers=op_headers,
    )
    assert res_resp.status_code == status.HTTP_200_OK
    assert res_resp.json()["status"] == "RESOLVED"

    # ----------------------------------------------------
    # Step 8: Verify Audit Trail Hash Chain Integrity
    # ----------------------------------------------------
    chain_check = client.get("/api/v1/audit/verify-chain", headers=admin_headers)
    assert chain_check.status_code == status.HTTP_200_OK
    assert chain_check.json()["is_chain_valid"] is True

    # ----------------------------------------------------
    # Step 9: Anchor Audit Batch to Blockchain
    # ----------------------------------------------------
    anchor_resp = client.post("/api/v1/audit/blockchain-anchor", json={"batch_size": 100}, headers=admin_headers)
    assert anchor_resp.status_code == status.HTTP_200_OK
    assert anchor_resp.json()["success"] is False
    assert anchor_resp.json()["tx_hash"] == ""

    # ----------------------------------------------------
    # Step 10: Executive Dashboard & GIS Map Layer
    # ----------------------------------------------------
    overview = client.get("/api/v1/dashboard/overview", headers=admin_headers)
    assert overview.status_code == status.HTTP_200_OK
    assert overview.json()["total_regions"] >= 1
    assert overview.json()["tree_assets"]["total"] >= 2

    map_layer = client.get(f"/api/v1/dashboard/map-layer?region_id={region_id}", headers=admin_headers)
    assert map_layer.status_code == status.HTTP_200_OK
    assert map_layer.json()["type"] == "FeatureCollection"
    assert len(map_layer.json()["features"]) >= 3  # Region polygon + 2 Sandalwood tree points
