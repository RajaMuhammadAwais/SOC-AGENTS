import hashlib
import hmac
import secrets
from base64 import b32decode, b32encode
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext

from app.core.config import Settings

password_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(
    *,
    subject: str,
    tenant_id: str,
    permissions: list[str],
    settings: Settings,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": subject,
        "tenant_id": tenant_id,
        "permissions": permissions,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.access_token_ttl_seconds)).timestamp()),
        "typ": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_mfa_secret() -> str:
    return b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def generate_totp_code(
    secret: str,
    *,
    for_time: int | None = None,
    interval_seconds: int = 30,
    digits: int = 6,
) -> str:
    timestamp = for_time if for_time is not None else int(datetime.now(UTC).timestamp())
    counter = timestamp // interval_seconds
    key = _decode_mfa_secret(secret)
    digest = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    ) % (10**digits)
    return str(code).zfill(digits)


def verify_totp_code(
    code: str,
    secret: str,
    *,
    for_time: int | None = None,
    window: int = 1,
    interval_seconds: int = 30,
    digits: int = 6,
) -> bool:
    if not code.isdigit() or len(code) != digits:
        return False

    timestamp = for_time if for_time is not None else int(datetime.now(UTC).timestamp())
    for offset in range(-window, window + 1):
        candidate_time = timestamp + (offset * interval_seconds)
        candidate = generate_totp_code(
            secret,
            for_time=candidate_time,
            interval_seconds=interval_seconds,
            digits=digits,
        )
        if hmac.compare_digest(candidate, code):
            return True
    return False


def generate_recovery_codes(count: int = 10) -> list[str]:
    return [secrets.token_urlsafe(10) for _ in range(count)]


def hash_recovery_codes(codes: list[str]) -> list[str]:
    return [hash_token(code) for code in codes]


def _decode_mfa_secret(secret: str) -> bytes:
    padding = "=" * ((8 - len(secret) % 8) % 8)
    return b32decode(f"{secret}{padding}", casefold=True)
