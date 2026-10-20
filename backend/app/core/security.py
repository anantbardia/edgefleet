"""Security utilities: password hashing, standard JWT tokens, and RBAC."""

import base64
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    import bcrypt
except ImportError:
    bcrypt = None

from app.config import settings

logger = logging.getLogger("edgefleet.security")
ALGORITHM = "HS256"


class JWTError(Exception):
    """Base JWT error."""
    pass


def hash_password(password: str) -> str:
    """Hash a password using bcrypt (with PBKDF2 fallback)."""
    pw_bytes = password.encode("utf-8")[:72]
    if bcrypt is not None:
        try:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")
        except Exception as e:
            logger.warning("Bcrypt hashing failed (%s), falling back to PBKDF2", e)

    salt = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
    key = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt.encode("utf-8"), 100000)
    return f"pbkdf2${salt}${key.hex()}"


get_password_hash = hash_password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash (supports both bcrypt and pbkdf2)."""
    try:
        pw_bytes = plain_password.encode("utf-8")[:72]
        if hashed_password.startswith(("$2b$", "$2a$", "$2y$")):
            if bcrypt is not None:
                hash_bytes = hashed_password.encode("utf-8")
                return bcrypt.checkpw(pw_bytes, hash_bytes)
        elif hashed_password.startswith("pbkdf2$"):
            parts = hashed_password.split("$")
            if len(parts) == 3:
                salt, expected_hex = parts[1], parts[2]
                key = hashlib.pbkdf2_hmac("sha256", pw_bytes, salt.encode("utf-8"), 100000)
                return hmac.compare_digest(key.hex(), expected_hex)
        return False
    except Exception as exc:
        logger.error("Error verifying password: %s", exc)
        return False


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(s: str) -> bytes:
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a standard HS256 JWT access token."""
    to_encode = data.copy()
    expire_epoch = int(
        (
            datetime.now(timezone.utc)
            + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        ).timestamp()
    )
    to_encode.update({"exp": expire_epoch, "type": "access"})

    header = {"alg": "HS256", "typ": "JWT"}
    h_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_b64 = _b64_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    sig = _b64_encode(
        hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    )
    return f"{h_b64}.{p_b64}.{sig}"


def create_refresh_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a standard HS256 JWT refresh token."""
    to_encode = data.copy()
    expire_epoch = int(
        (
            datetime.now(timezone.utc)
            + (expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
        ).timestamp()
    )
    to_encode.update({"exp": expire_epoch, "type": "refresh"})

    header = {"alg": "HS256", "typ": "JWT"}
    h_b64 = _b64_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    p_b64 = _b64_encode(json.dumps(to_encode, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    sig = _b64_encode(
        hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    )
    return f"{h_b64}.{p_b64}.{sig}"


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a HS256 JWT token. Returns None on failure."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        h_b64, p_b64, sig = parts
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        expected_sig = _b64_encode(
            hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected_sig):
            return None
        payload = json.loads(_b64_decode(p_b64).decode("utf-8"))
        if "exp" in payload and payload["exp"] < int(time.time()):
            return None
        return payload
    except Exception:
        return None


# ── RBAC ─────────────────────────────────────────────────────────────────────

ROLE_HIERARCHY = {"admin": 3, "operator": 2, "viewer": 1}


def has_role(user_role: str, required_role: str) -> bool:
    """Check if user_role meets or exceeds the required_role level."""
    return ROLE_HIERARCHY.get(user_role, 0) >= ROLE_HIERARCHY.get(required_role, 0)
