"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import logger
from app.database.database import init_db, SessionLocal
from app.database.seed import seed_initial_data
from app.core.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.mqtt import mqtt_subscriber
from app.middleware import AuthenticationMiddleware, ZeroTrustRequestVerificationMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle events management."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")
    init_db()
    seed_demo = settings.APP_ENV.lower() != "production" and settings.SEED_DEMO_DATA
    try:
        with SessionLocal() as db:
            if seed_demo:
                seed_initial_data(db)
            else:
                logger.info("Demo seed skipped (production or SEED_DEMO_DATA=false)")
    except Exception as e:
        logger.warning(f"Initial seeder skipped: {e}")

    try:
        with SessionLocal() as db:
            from app.services.detection_service import DetectionService
            moved = DetectionService.migrate_legacy_registered_trees_to_detections(db)
            if moved:
                logger.info(f"Startup migration: {moved} legacy trees → unassigned detections")
    except Exception as e:
        logger.warning(f"Detection migration skipped: {e}")

    try:
        mqtt_subscriber.start()
    except Exception as e:
        logger.warning(f"MQTT subscriber startup note: {e}")

    try:
        from app.services.tree_environment_scheduler import tree_environment_scheduler
        tree_environment_scheduler.start()
    except Exception as e:
        logger.warning(f"Tree environment scheduler startup note: {e}")

    yield

    try:
        from app.services.tree_environment_scheduler import tree_environment_scheduler
        tree_environment_scheduler.stop()
    except Exception:
        pass

    try:
        mqtt_subscriber.stop()
    except Exception:
        pass
    logger.info(f"Shutting down {settings.APP_NAME}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    docs_url = "/docs" if settings.DEBUG else None
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Zero Trust IoT Security Framework for GPS-Based Agroforestry Monitoring and Sandalwood Tree Registration",
        docs_url=docs_url,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Middlewares (Executed in reverse order of registration)
    from fastapi.middleware.gzip import GZipMiddleware
    application.add_middleware(GZipMiddleware, minimum_size=500)
    application.add_middleware(ZeroTrustRequestVerificationMiddleware)
    application.add_middleware(AuthenticationMiddleware)

    # CORS configuration
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception Handlers
    application.add_exception_handler(AppException, app_exception_handler)
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, generic_exception_handler)

    @application.get("/health", tags=["Health"], summary="System Health Check")
    async def health_check():
        """Health check endpoint to verify service availability and subsystem diagnostics."""
        db_healthy = True
        try:
            from sqlalchemy import text
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
        except Exception:
            db_healthy = False

        from app.ai.model import detector
        ai_healthy = detector.is_fitted
        # Public health is intentionally minimal to avoid recon leakage.
        return {
            "status": "ok" if db_healthy else "degraded",
        }


    @application.get("/", tags=["Root"], summary="Root API Information")
    async def root():
        """Root endpoint returning basic service metadata."""
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "docs_url": "/docs",
            "health_url": "/health",
        }

    # Mount API v1 Routes
    from app.api.router import api_router
    from app.api.routes.map import router as map_router
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)
    application.include_router(map_router)

    return application


app = create_app()
