"""Security helpers for password hashing, JWT tokens, and national ID tokenization."""

import hashlib  # noqa: I001
import os
from datetime import datetime, timedelta, timezone

import bcrypt # pyright: ignore[reportMissingImports]
from jose import JWTError, jwt # pyright: ignore[reportMissingModuleSource]

SECRET = os.getenv("PROTO_SECRET", "prototype-secret-change-me")
ALGO = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("PROTO_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(p: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(p: str, h: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(p.encode("utf-8"), h.encode("utf-8"))


def tokenize_national_id(nid: str) -> str:
    """Return a SHA-256 hex digest of a national ID (for storage lookup)."""
    return hashlib.sha256(nid.encode("utf-8")).hexdigest()


def make_token(member_id: str) -> str:
    """Create a JWT access token for a member."""
    now = datetime.now(timezone.utc)  # noqa: UP017
    payload = {
        "sub": member_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def decode_token(token: str) -> str:
    """Decode a JWT access token and return the member_id ('sub' claim)."""
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e
    sub = payload.get("sub")
    if not sub:
        raise ValueError("Token missing 'sub' claim")
    return sub