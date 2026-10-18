"""Comprehensive database foundation and core domain models test suite."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.database.base import Base
from app.database.models import (
    User,
    UserRole,
    UserStatus,
    UserSession,
    Device,
    DeviceStatus,
    Region,
    RegionStatus,
    Tree,
    TreeStatus,
    EnvironmentalMeasurement,
    Alert,
    AlertSeverity,
    AlertStatus,
    AuditLog,
)


def test_create_user_and_session(db_session):
    """Test user creation and session association."""
    user = User(
        email="admin@agroforestry.gov.in",
        username="admin_karnataka",
        full_name="Forest Admin",
        hashed_password="mock_argon2_hash_value",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.id is not None
    assert user.role == UserRole.ADMIN
    assert user.created_at is not None

    session = UserSession(
        user_id=user.id,
        token_jti="test-jwt-jti-001",
        ip_address="192.168.1.50",
        user_agent="Mozilla/5.0 TestClient",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=8),
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.is_active is True
    assert len(user.sessions) == 1
    assert user.sessions[0].token_jti == "test-jwt-jti-001"


def test_unique_user_constraints(db_session):
    """Test that email and username uniqueness is enforced."""
    user1 = User(
        email="operator@agroforestry.gov.in",
        username="operator1",
        full_name="Operator One",
        hashed_password="hash1",
        role=UserRole.OPERATOR,
    )
    db_session.add(user1)
    db_session.commit()

    user2 = User(
        email="operator@agroforestry.gov.in",  # Duplicate email
        username="operator2",
        full_name="Operator Two",
        hashed_password="hash2",
        role=UserRole.OPERATOR,
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_two_layer_architecture_region_and_trees(db_session):
    """Test the two major data layers: Region (Layer 1) and Trees (Layer 2)."""
    # 1. Create a Region
    region = Region(
        region_id="REG-KA-SHIVAMOGGA",
        name="Shivamogga Sandalwood Reserve",
        description="Protected agroforestry belt in Western Ghats",
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [
                [
                    [75.56, 13.92],
                    [75.58, 13.92],
                    [75.58, 13.94],
                    [75.56, 13.94],
                    [75.56, 13.92],
                ]
            ],
        },
        center_latitude=13.93,
        center_longitude=75.57,
        area_hectares=120.5,
        status=RegionStatus.ACTIVE,
    )
    db_session.add(region)
    db_session.commit()
    db_session.refresh(region)

    assert region.id is not None

    # 2. Register Sandalwood Trees within the Region
    tree1 = Tree(
        tree_uid="KA-00001",
        species="Santalum album",
        region_id=region.id,
        latitude=13.9310,
        longitude=75.5720,
        altitude=640.0,
        gps_accuracy=2.5,
        estimated_age_years=12.0,
        girth_cm=45.0,
        height_m=6.2,
        status=TreeStatus.HEALTHY,
    )
    tree2 = Tree(
        tree_uid="KA-00002",
        species="Santalum album",
        region_id=region.id,
        latitude=13.9315,
        longitude=75.5725,
        altitude=641.5,
        gps_accuracy=3.0,
        estimated_age_years=8.5,
        girth_cm=32.0,
        height_m=4.8,
        status=TreeStatus.HEALTHY,
    )
    db_session.add_all([tree1, tree2])
    db_session.commit()

    assert len(region.trees) == 2
    assert region.trees[0].tree_uid == "KA-00001"


def test_unique_tree_uid_constraint(db_session):
    """Test that tree_uid is strictly unique."""
    region = Region(region_id="REG-001", name="Test Region")
    db_session.add(region)
    db_session.commit()

    tree1 = Tree(tree_uid="KA-00001", region_id=region.id, latitude=12.0, longitude=77.0)
    db_session.add(tree1)
    db_session.commit()

    tree2 = Tree(tree_uid="KA-00001", region_id=region.id, latitude=12.1, longitude=77.1)
    db_session.add(tree2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_region_wide_vs_tree_specific_measurements(db_session):
    """
    Test that measurements can be:
    1. Region-wide (tree_id is None) - First-class regional environmental layer
    2. Tree-specific (tree_id is set) - Tree layer observation
    """
    # Create Region, Device, and Tree
    region = Region(region_id="REG-KA-COORG", name="Coorg Reserve")
    db_session.add(region)
    db_session.commit()

    device = Device(
        device_id="DEV-KA-001",
        name="Field Tower Node 1",
        device_type="STATIONARY_NODE",
        api_key_hash="mock_hashed_device_key",
        assigned_region_id=region.id,
        status=DeviceStatus.ACTIVE,
    )
    db_session.add(device)
    db_session.commit()

    tree = Tree(
        tree_uid="KA-00100",
        region_id=region.id,
        latitude=12.3375,
        longitude=75.8069,
    )
    db_session.add(tree)
    db_session.commit()

    # Case A: Region-wide measurement (tree_id is None)
    regional_reading = EnvironmentalMeasurement(
        region_id=region.id,
        tree_id=None,  # Region-level observation
        device_id=device.id,
        latitude=12.3350,
        longitude=75.8050,
        temperature=27.5,
        humidity=74.0,
        soil_moisture=52.0,
        additional_metrics={"rainfall_mm": 12.4, "solar_lux": 82000},
        integrity_hash="sha256_mock_hash_regional",
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add(regional_reading)

    # Case B: Tree-specific measurement (tree_id = tree.id)
    tree_reading = EnvironmentalMeasurement(
        region_id=region.id,
        tree_id=tree.id,  # Linked to specific sandalwood tree
        device_id=device.id,
        latitude=12.3375,
        longitude=75.8069,
        temperature=28.1,
        humidity=72.5,
        soil_moisture=48.0,
        additional_metrics={"soil_ph": 6.8},
        integrity_hash="sha256_mock_hash_tree",
        is_anomaly=False,
        anomaly_score=-0.12,
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add(tree_reading)
    db_session.commit()

    # Verify relationships
    db_session.refresh(region)
    db_session.refresh(tree)

    assert len(region.measurements) == 2
    assert len(tree.measurements) == 1
    assert tree.measurements[0].tree_id == tree.id
    assert regional_reading.tree_id is None
    assert regional_reading.additional_metrics["rainfall_mm"] == 12.4


def test_alert_and_audit_log_entities(db_session):
    """Test Alert creation and AuditLog event tracking with integrity hash."""
    region = Region(region_id="REG-KA-MYSORE", name="Mysore Belt")
    db_session.add(region)
    db_session.commit()

    # Create Alert
    alert = Alert(
        region_id=region.id,
        alert_type="ANOMALY_RAPID_TEMPERATURE_SURGE",
        severity=AlertSeverity.HIGH,
        message="Temperature jumped by 9°C in 15 minutes",
        anomaly_score=0.88,
        status=AlertStatus.ACTIVE,
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)

    assert alert.id is not None
    assert alert.severity == AlertSeverity.HIGH
    assert alert.status == AlertStatus.ACTIVE

    # Create AuditLog
    audit = AuditLog(
        event_type="DEVICE_AUTHENTICATION_FAILURE",
        actor_device_id=None,
        region_id=region.id,
        description="Device DEV-UNKNOWN attempted connection with invalid key",
        event_payload={"attempted_device_id": "DEV-UNKNOWN", "ip": "10.0.0.1"},
        event_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        blockchain_status="LOCAL_ONLY",
    )
    db_session.add(audit)
    db_session.commit()
    db_session.refresh(audit)

    assert audit.id is not None
    assert audit.event_hash is not None
    assert audit.recorded_at is not None
