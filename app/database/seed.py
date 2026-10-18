"""Database seeder for operator accounts. Forest reserves and devices are not seeded."""

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import logger
from app.core.security import hash_password
from app.database.models.user import User, UserRole, UserStatus


def seed_initial_data(db: Session) -> None:
    """Seed operator accounts if the database has no users yet."""
    existing_user = db.execute(select(User)).first()
    if existing_user:
        return

    admin_password = (settings.SEED_ADMIN_PASSWORD or "").strip()
    operator_password = (settings.SEED_OPERATOR_PASSWORD or "").strip()
    if not admin_password or not operator_password:
        logger.warning(
            "Skipping user seed: set SEED_ADMIN_PASSWORD and SEED_OPERATOR_PASSWORD "
            "when SEED_DEMO_DATA is enabled."
        )
        return

    logger.info("Seeding operator accounts...")

    admin_user = User(
        email="admin@agroforestry.gov.in",
        username="admin",
        full_name="Forest Department Administrator",
        hashed_password=hash_password(admin_password),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    operator_user = User(
        email="operator@agroforestry.gov.in",
        username="operator",
        full_name="Field Forest Officer",
        hashed_password=hash_password(operator_password),
        role=UserRole.OPERATOR,
        status=UserStatus.ACTIVE,
    )
    db.add_all([admin_user, operator_user])
    db.commit()
    logger.info("Database seeded with users. Devices are registered from the console so their API keys can be saved.")
