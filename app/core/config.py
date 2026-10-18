"""Application configuration management via Pydantic Settings."""

from functools import lru_cache
from typing import List, Union, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
import warnings

# Suppress known external library compatibility warnings in Python 3.14/NumPy 2.x
warnings.filterwarnings("ignore", category=DeprecationWarning, module="joblib")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="starlette")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application
    APP_NAME: str = "Zero Trust Agroforestry Monitoring API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    # Demo users/regions. Forced off when APP_ENV=production.
    SEED_DEMO_DATA: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite:///./zero_trust_agroforestry.db"
    DB_ECHO: bool = False

    # Security & JWT — never ship real secrets as defaults.
    # Development may set ALLOW_INSECURE_DEFAULTS=true for local demos only.
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ENCRYPTION_KEY: str = ""
    ALLOW_INSECURE_DEFAULTS: bool = False
    # Self-service accounts are off unless an operator turns this on for a local demo.
    ALLOW_PUBLIC_REGISTRATION: bool = False
    # Reject measurement recorded_at older than this (hours).
    MAX_MEASUREMENT_AGE_HOURS: int = 72
    # Seed passwords (required when SEED_DEMO_DATA=true). Never hardcode.
    SEED_ADMIN_PASSWORD: Optional[str] = None
    SEED_OPERATOR_PASSWORD: Optional[str] = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # MQTT Broker Configuration
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_KEEPALIVE: int = 60
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_USE_TLS: bool = False
    MQTT_TOPIC_PREFIX: str = "agroforestry"

    # Blockchain & Audit Evidence Configuration
    BLOCKCHAIN_RPC: str = "http://127.0.0.1:8545"
    BLOCKCHAIN_CONTRACT_ADDRESS: str = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
    BLOCKCHAIN_CHAIN_ID: int = 31337
    # Never default to a well-known Hardhat key. Set explicitly in .env for local anchoring.
    BLOCKCHAIN_PRIVATE_KEY: Optional[str] = None

    # Optional Redis for shared nonce / rate-limit state. In-memory if unset.
    REDIS_URL: Optional[str] = None

    # Zero Trust Security Parameters
    ZERO_TRUST_MAX_CLOCK_SKEW_SECONDS: int = 900  # 15 minutes replay protection window

    # Live area weather refresh (Open-Meteo → environmental_measurements per tree)
    ENV_REFRESH_ENABLED: bool = True
    ENV_REFRESH_INTERVAL_SECONDS: int = 900  # 15 minutes

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return v if isinstance(v, list) else [str(v)]

    def assert_production_secrets(self) -> None:
        """Refuse insecure secrets. Production/staging always fail closed; other envs need an explicit override."""
        env = (self.APP_ENV or "").lower()
        is_hardened = env in {"production", "staging"}
        known = {
            "agroforestry-zero-trust-super-secret-key-change-in-production-2026",
            "production-secret-key-replace-in-env-2026-sandalwood",
            "zero-trust-agroforestry-super-secret-development-key-32bytes",
            "x5B7n8r6v8y/B?E(H+MbQeThWmZq4t7w9z$C&F)J@Nc=",
            "change-me",
            "changeme",
            "replace-with-a-unique-32-plus-character-secret",
            "replace-with-a-unique-encryption-key",
        }
        jwt = (self.JWT_SECRET or "").strip()
        enc = (self.ENCRYPTION_KEY or "").strip()

        def _secret_ok(value: str) -> bool:
            return bool(value) and value not in known and len(value) >= 32

        if is_hardened or not self.ALLOW_INSECURE_DEFAULTS:
            if not _secret_ok(jwt):
                raise RuntimeError(
                    "JWT_SECRET is missing, too short, or a known default. "
                    "Set a unique secret (≥32 chars), or set ALLOW_INSECURE_DEFAULTS=true for local demos only."
                )
            if not _secret_ok(enc):
                raise RuntimeError(
                    "ENCRYPTION_KEY is missing, too short, or a known default. "
                    "Set a unique key (≥32 chars), or set ALLOW_INSECURE_DEFAULTS=true for local demos only."
                )

        if is_hardened:
            if self.ALLOW_INSECURE_DEFAULTS:
                raise RuntimeError("ALLOW_INSECURE_DEFAULTS cannot be true when APP_ENV is production/staging.")
            if self.ALLOW_PUBLIC_REGISTRATION:
                raise RuntimeError("ALLOW_PUBLIC_REGISTRATION must be false when APP_ENV is production/staging.")
            if not self.REDIS_URL:
                raise RuntimeError("REDIS_URL is required when APP_ENV is production/staging (anti-replay).")
            if not self.MQTT_USE_TLS:
                raise RuntimeError("MQTT_USE_TLS must be true when APP_ENV is production/staging.")
            if any(bad in (self.DATABASE_URL or "") for bad in ("change-me", "changeme", "AgroSecure2026", "soman123")):
                raise RuntimeError("DATABASE_URL still uses a default or demo password. Set a unique database credential.")
            hardhat_dev_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
            if not self.BLOCKCHAIN_PRIVATE_KEY:
                raise RuntimeError("BLOCKCHAIN_PRIVATE_KEY is required when APP_ENV=production/staging.")
            if self.BLOCKCHAIN_PRIVATE_KEY == hardhat_dev_key:
                raise RuntimeError(
                    "BLOCKCHAIN_PRIVATE_KEY is using Hardhat default dev key. "
                    "Set a unique private key before APP_ENV=production/staging."
                )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()


settings = get_settings()
settings.assert_production_secrets()
