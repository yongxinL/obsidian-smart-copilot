"""Unit tests for auth/core.py — transport-neutral validators (D-17, D-18).

Tests validate:
  - validate_jwt returns AuthResult on success and error on failure
  - validate_jwt never raises HTTPException
  - validate_jwt parses optional sid claim into AuthResult.session_id
  - validate_refresh and validate_bearer return AuthResult (unit-level contract)
  - No fastapi/starlette imports in auth/core module
"""
from __future__ import annotations

import inspect
import uuid

import pytest

pytestmark = [pytest.mark.auth]

# Signing key used for test tokens — must match what settings.jwt_signing_key is patched to
_TEST_SIGNING_KEY = "test-signing-key-min-32-bytes-for-hs256-aaaaaaaa"


class TestValidateJwtContract:
    """validate_jwt returns AuthResult dataclass — never raises."""

    def test_missing_auth_on_none_token(self) -> None:
        from app.auth.context import AuthResult
        from app.auth.core import validate_jwt

        result = validate_jwt(None)
        assert isinstance(result, AuthResult)
        assert result.error == "missing_auth"
        assert result.user_id is None

    def test_missing_auth_on_empty_string(self) -> None:
        from app.auth.context import AuthResult
        from app.auth.core import validate_jwt

        result = validate_jwt("")
        assert isinstance(result, AuthResult)
        assert result.error == "missing_auth"

    def test_invalid_token_on_garbage(self) -> None:
        from app.auth.context import AuthResult
        from app.auth.core import validate_jwt

        result = validate_jwt("garbage.token.string")
        assert isinstance(result, AuthResult)
        assert result.error == "invalid_token"
        assert result.user_id is None

    def test_never_raises_http_exception(self) -> None:
        """validate_jwt must NEVER raise HTTPException (D-17)."""
        from app.auth.core import validate_jwt

        # Should not raise — returns AuthResult
        result = validate_jwt("not.a.valid.jwt")
        assert result.error is not None

    def test_valid_jwt_returns_auth_result_with_user_id_and_role(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.settings as _settings
        monkeypatch.setattr(_settings.settings, "jwt_signing_key", _TEST_SIGNING_KEY)

        from app.auth.context import AuthResult
        from app.auth.core import validate_jwt
        from app.auth.tokens import issue_access_jwt

        user_id = uuid.uuid4()
        token = issue_access_jwt(
            user_id=user_id,
            role="user",
            signing_key=_TEST_SIGNING_KEY,
            ttl_seconds=900,
        )
        result = validate_jwt(token)
        assert isinstance(result, AuthResult)
        assert result.error is None
        assert result.user_id == user_id
        assert result.role == "user"

    def test_valid_jwt_with_sid_claim_sets_session_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """validate_jwt parses optional sid claim into AuthResult.session_id."""
        import app.settings as _settings
        monkeypatch.setattr(_settings.settings, "jwt_signing_key", _TEST_SIGNING_KEY)

        from app.auth.context import AuthResult
        from app.auth.core import validate_jwt
        from app.auth.tokens import issue_access_jwt

        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        token = issue_access_jwt(
            user_id=user_id,
            role="user",
            signing_key=_TEST_SIGNING_KEY,
            ttl_seconds=900,
            session_id=session_id,
        )
        result = validate_jwt(token)
        assert isinstance(result, AuthResult)
        assert result.error is None
        assert result.session_id == session_id

    def test_valid_jwt_without_sid_has_none_session_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.settings as _settings
        monkeypatch.setattr(_settings.settings, "jwt_signing_key", _TEST_SIGNING_KEY)

        from app.auth.core import validate_jwt
        from app.auth.tokens import issue_access_jwt

        user_id = uuid.uuid4()
        token = issue_access_jwt(
            user_id=user_id,
            role="admin",
            signing_key=_TEST_SIGNING_KEY,
            ttl_seconds=900,
        )
        result = validate_jwt(token)
        assert result.error is None
        assert result.session_id is None

    def test_invalid_role_returns_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A JWT with a non-standard role is rejected."""
        import app.settings as _settings
        monkeypatch.setattr(_settings.settings, "jwt_signing_key", _TEST_SIGNING_KEY)

        from jose import jwt

        from app.auth.core import validate_jwt

        claims = {
            "sub": str(uuid.uuid4()),
            "role": "superuser",  # not in ("admin", "user")
            "jti": str(uuid.uuid4()),
            "iat": 1700000000,
            "nbf": 1700000000,
            "exp": 9999999999,
        }
        token = jwt.encode(claims, _TEST_SIGNING_KEY, algorithm="HS256")
        result = validate_jwt(token)
        assert result.error == "invalid_token"


class TestNoFastAPIImport:
    """D-17: auth/core.py must NOT import fastapi or starlette."""

    def test_no_fastapi_import_in_core_module(self) -> None:
        import app.auth.core as core_module

        source = inspect.getsource(core_module)
        # Check for import statements (not comments)
        import_lines = [
            line for line in source.splitlines()
            if line.strip().startswith(("from fastapi", "import fastapi",
                                        "from starlette", "import starlette"))
        ]
        assert import_lines == [], f"D-17 violated: {import_lines}"


class TestValidateRefreshAndBearerContract:
    """Smoke-test that validate_refresh and validate_bearer are async and return AuthResult."""

    def test_validate_refresh_is_async_coroutine(self) -> None:
        import asyncio

        from app.auth.core import validate_refresh

        assert asyncio.iscoroutinefunction(validate_refresh)

    def test_validate_bearer_is_async_coroutine(self) -> None:
        import asyncio

        from app.auth.core import validate_bearer

        assert asyncio.iscoroutinefunction(validate_bearer)

    @pytest.mark.asyncio
    async def test_validate_refresh_missing_token_returns_missing_auth(self) -> None:
        from app.auth.context import AuthResult
        from app.auth.core import validate_refresh

        result = await validate_refresh(None)
        assert isinstance(result, AuthResult)
        assert result.error == "missing_auth"

    @pytest.mark.asyncio
    async def test_validate_bearer_missing_token_returns_missing_auth(self) -> None:
        from app.auth.context import AuthResult
        from app.auth.core import validate_bearer

        result = await validate_bearer(None)
        assert isinstance(result, AuthResult)
        assert result.error == "missing_auth"
