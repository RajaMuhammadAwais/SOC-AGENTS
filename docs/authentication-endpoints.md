# Authentication Endpoints

The authentication API supports tenant registration, login, refresh-token rotation, logout acknowledgement, current-principal lookup, and MFA setup/enable/disable.

## Source Basis

- FastAPI OAuth2/JWT security tutorial, verified on 2026-06-11: the backend keeps bearer JWTs and password hashing in the existing FastAPI style.
- OWASP Multifactor Authentication Cheat Sheet, verified on 2026-06-11: MFA is required at login when enabled; OTP values are not logged; recovery codes are stored hashed and consumed once.
- RFC 6238, verified on 2026-06-11: TOTP generation uses the standard HMAC-SHA1 moving-factor algorithm.

## Endpoints

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/mfa/setup`
- `POST /auth/mfa/enable`
- `POST /auth/mfa/disable`

## MFA Behavior

MFA setup returns a shared TOTP secret and one-time recovery codes. Recovery codes are hashed before storage and removed after use. Accounts with MFA enabled must provide a valid TOTP or unused recovery code during login.

## Notes

`mfa_secret` is stored on the user model so local development and tests can verify TOTP. Production deployments should protect this field with database encryption or a managed secrets facility as part of the planned secrets-management and encryption tasks.
