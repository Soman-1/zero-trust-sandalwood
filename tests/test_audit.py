"""Comprehensive tests for Cryptographic Audit Ledger, Hash Chaining, and Blockchain Anchoring."""

import pytest
from datetime import datetime, timezone
from fastapi import status
from sqlalchemy import select

from app.database.models.audit_log import AuditLog
from app.services.audit_service import AuditService, GENESIS_PREVIOUS_HASH


def setup_audit_users(client):
    """Helper to setup admin and viewer users."""
    # 1. Admin
    client.post("/api/v1/auth/register", json={
        "email": "admin_chain@agroforestry.gov.in",
        "username": "admin_chain",
        "full_name": "Audit Admin",
        "password": "Password12345!",
        "role": "ADMIN",
    })
    admin_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "admin_chain",
        "password": "Password12345!",
    }).json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Viewer
    client.post("/api/v1/auth/register", json={
        "email": "viewer_chain@agroforestry.gov.in",
        "username": "viewer_chain",
        "full_name": "Audit Viewer",
        "password": "Password12345!",
        "role": "VIEWER",
    })
    view_token = client.post("/api/v1/auth/login", json={
        "username_or_email": "viewer_chain",
        "password": "Password12345!",
    }).json()["access_token"]
    view_headers = {"Authorization": f"Bearer {view_token}"}

    return admin_headers, view_headers


def test_hash_chained_audit_log_creation(client, db_session):
    """Test that sequential audit events are cryptographically hash-chained."""
    admin_headers, _ = setup_audit_users(client)

    # 1. Record event 1
    log1 = AuditService.record_event(
        db=db_session,
        event_type="SYSTEM_BOOT",
        action="BOOT",
        description="Zero Trust backend started",
        actor_type="SYSTEM",
    )
    assert log1.previous_hash == GENESIS_PREVIOUS_HASH
    assert len(log1.event_hash) == 64

    # 2. Record event 2
    log2 = AuditService.record_event(
        db=db_session,
        event_type="TREE_REGISTERED",
        action="REGISTER",
        description="Sandalwood tree SW-KA-00001 registered",
        actor_type="USER",
        actor_id="admin_chain",
    )
    assert log2.previous_hash == log1.event_hash
    assert len(log2.event_hash) == 64

    # 3. Record event 3
    log3 = AuditService.record_event(
        db=db_session,
        event_type="DEVICE_REGISTERED",
        action="REGISTER",
        description="IoT Device DEV-01 registered",
        actor_type="USER",
        actor_id="admin_chain",
    )
    assert log3.previous_hash == log2.event_hash


def test_verify_unbroken_audit_chain(client, db_session):
    """Test cryptographic chain verification endpoint on untampered ledger."""
    admin_headers, _ = setup_audit_users(client)

    # Seed 3 audit entries
    AuditService.record_event(db=db_session, event_type="E1", action="A1", description="Event 1")
    AuditService.record_event(db=db_session, event_type="E2", action="A2", description="Event 2")
    AuditService.record_event(db=db_session, event_type="E3", action="A3", description="Event 3")

    resp = client.get("/api/v1/audit/verify-chain", headers=admin_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["is_chain_valid"] is True
    assert data["total_verified"] >= 3
    assert data["broken_link_index"] is None


def test_tamper_detection_on_audit_ledger(client, db_session):
    """
    Zero Trust Audit Tampering Test:
    Simulate an attacker modifying a historical audit record in the database.
    The verification engine must immediately detect the broken hash chain.
    """
    admin_headers, _ = setup_audit_users(client)

    # Seed 3 events
    AuditService.record_event(db=db_session, event_type="SEC1", action="INIT", description="Initial event")
    log2 = AuditService.record_event(db=db_session, event_type="SEC2", action="CHANGE", description="Critical change")
    AuditService.record_event(db=db_session, event_type="SEC3", action="FINAL", description="Final event")

    # Attacker alters description of log2 in database
    log2.description = "Tampered description trying to hide unauthorized change"
    db_session.commit()

    # Run verification endpoint
    resp = client.get("/api/v1/audit/verify-chain", headers=admin_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["is_chain_valid"] is False
    assert data["broken_link_index"] is not None
    assert "tampered" in data["message"] or "mismatch" in data["message"]


def test_blockchain_anchoring_batch(client, db_session):
    """Test anchoring pending audit logs to simulated blockchain transaction."""
    admin_headers, _ = setup_audit_users(client)

    # Seed unanchored events
    AuditService.record_event(db=db_session, event_type="BC1", action="OP1", description="Blockchain test 1")
    AuditService.record_event(db=db_session, event_type="BC2", action="OP2", description="Blockchain test 2")

    resp = client.post(
        "/api/v1/audit/blockchain-anchor",
        json={"batch_size": 20},
        headers=admin_headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["success"] is False
    assert data["anchored_records"] == 0
    assert data["tx_hash"] == ""
    assert len(data["merkle_root"]) == 64
    assert "LOCAL_ONLY" in data["message"] or "unavailable" in data["message"].lower() or "Chain" in data["message"]


def test_audit_rbac_restrictions(client):
    """Test that VIEWER role is blocked from accessing the audit ledger."""
    _, view_headers = setup_audit_users(client)

    # Viewer queries logs -> 403 Forbidden
    r1 = client.get("/api/v1/audit/logs", headers=view_headers)
    assert r1.status_code == status.HTTP_403_FORBIDDEN

    # Viewer tries to trigger blockchain anchor -> 403 Forbidden
    r2 = client.post("/api/v1/audit/blockchain-anchor", json={"batch_size": 10}, headers=view_headers)
    assert r2.status_code == status.HTTP_403_FORBIDDEN
