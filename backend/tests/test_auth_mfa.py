from uuid import uuid4

from app.api.v1.routes.auth import verify_user_mfa
from app.core.security import generate_mfa_secret, generate_totp_code, hash_token, verify_totp_code
from app.domain.models import User


def test_totp_generation_matches_rfc_6238_sha1_vector() -> None:
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"

    assert generate_totp_code(secret, for_time=59, digits=8) == "94287082"
    assert verify_totp_code("94287082", secret, for_time=59, digits=8)


def test_verify_totp_rejects_non_numeric_codes() -> None:
    secret = generate_mfa_secret()

    assert verify_totp_code("abc123", secret) is False


def test_verify_user_mfa_allows_accounts_without_mfa() -> None:
    user = User(
        tenant_id=uuid4(),
        email="analyst@example.com",
        full_name="SOC Analyst",
        password_hash="hash",
        is_mfa_enabled=False,
        mfa_recovery_codes=[],
    )

    assert verify_user_mfa(user, None) is True


def test_verify_user_mfa_accepts_totp_code() -> None:
    secret = generate_mfa_secret()
    code = generate_totp_code(secret)
    user = User(
        tenant_id=uuid4(),
        email="analyst@example.com",
        full_name="SOC Analyst",
        password_hash="hash",
        is_mfa_enabled=True,
        mfa_secret=secret,
        mfa_recovery_codes=[],
    )

    assert verify_user_mfa(user, code) is True


def test_verify_user_mfa_consumes_recovery_code_once() -> None:
    user = User(
        tenant_id=uuid4(),
        email="analyst@example.com",
        full_name="SOC Analyst",
        password_hash="hash",
        is_mfa_enabled=True,
        mfa_recovery_codes=[hash_token("backup-code")],
    )

    assert verify_user_mfa(user, "backup-code") is True
    assert user.mfa_recovery_codes == []
    assert verify_user_mfa(user, "backup-code") is False
