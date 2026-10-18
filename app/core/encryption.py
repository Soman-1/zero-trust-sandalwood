import base64
import functools
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings


def _require_encryption_key() -> bytes:
    """Return ENCRYPTION_KEY material. Never fall back to JWT_SECRET."""
    raw = (settings.ENCRYPTION_KEY or "").strip()
    if not raw:
        raise RuntimeError("ENCRYPTION_KEY must be set; refusing to fall back to JWT_SECRET")
    return raw.encode("utf-8")


@functools.lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Derive and cache a valid 32-byte URL-safe base64 key and Fernet instance from configuration."""
    derived_32 = hashlib.sha256(_require_encryption_key()).digest()
    key = base64.urlsafe_b64encode(derived_32)
    return Fernet(key)


def _get_fernet_key() -> bytes:
    """Derive a valid 32-byte URL-safe base64 key from configuration (for backward compatibility)."""
    derived_32 = hashlib.sha256(_require_encryption_key()).digest()
    return base64.urlsafe_b64encode(derived_32)


def encrypt_data(plaintext: str) -> str:
    """
    Encrypt sensitive plaintext using AES authenticated encryption (Fernet).
    Returns a URL-safe base64 ciphertext string.
    """
    if not plaintext:
        return ""
    fernet = _get_fernet()
    encrypted_bytes = fernet.encrypt(plaintext.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")


def decrypt_data(ciphertext: str) -> str:
    """
    Decrypt authenticated ciphertext back to original plaintext.
    """
    if not ciphertext:
        return ""
    fernet = _get_fernet()
    decrypted_bytes = fernet.decrypt(ciphertext.encode("utf-8"))
    return decrypted_bytes.decode("utf-8")
