"""AUTH-09, AUTH-10 integration tests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from cryptography.fernet import Fernet

from app.auth.context import SYSTEM_USER_ID, OperationContext, system_operation_context
from app.dependencies import session_with_rls
from app.encryption import _reset_fernet_cache_for_tests
from app.services.provider_keys import (
    MissingProviderKey,
    ProviderKeyResponse,
    resolve_key,
    set_provider_key,
)

pytestmark = [pytest.mark.auth, pytest.mark.integration]


def _user_ctx(uid: uuid.UUID) -> OperationContext:
    return OperationContext(
        user_id=uid,
        role="user",
        transport="cli",
        remote=False,
        client_name="test",
        request_id="test-providerkeys",
    )


@pytest.fixture(autouse=True)
def _fernet_key(monkeypatch):
    from app import settings as settings_mod

    monkeypatch.setattr(
        settings_mod.settings,
        "smartcopilot_fernet_key",
        Fernet.generate_key().decode(),
    )
    _reset_fernet_cache_for_tests()
    yield
    _reset_fernet_cache_for_tests()


def test_encrypted_key_excluded_from_responses() -> None:
    """D-28: schema-level exclusion. Pydantic model_dump() must not include encrypted_key."""
    resp = ProviderKeyResponse(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="openai",
        key_hint="abcd",
        created_at=datetime.now(UTC),
        encrypted_key=b"\x00\x01\x02",
    )
    dumped = resp.model_dump()
    assert "encrypted_key" not in dumped, (
        f"encrypted_key leaked into response: {dumped.keys()}"
    )
    # Also test JSON shape
    assert "encrypted_key" not in resp.model_dump_json()


async def test_user_key_takes_precedence_over_shared(
    seed_basic_user: uuid.UUID,
) -> None:
    # System places a shared key
    async for s_sys in session_with_rls(system_operation_context()):
        await set_provider_key(
            s_sys, system_operation_context(), provider="openai", plaintext="sk-system"
        )
        await s_sys.commit()
    # User places their own key
    ctx = _user_ctx(seed_basic_user)
    async for s_user in session_with_rls(ctx):
        await set_provider_key(s_user, ctx, provider="openai", plaintext="sk-user")
        await s_user.commit()
    # Resolve: user wins
    async for s_resolve in session_with_rls(ctx):
        resolved = await resolve_key(s_resolve, ctx, provider="openai")
        assert resolved == "sk-user"
    # Cleanup
    async for s_cleanup_user in session_with_rls(ctx):
        from sqlalchemy import delete as sa_delete

        from app.models.provider_key import ProviderKey

        await s_cleanup_user.execute(
            sa_delete(ProviderKey).where(ProviderKey.user_id == seed_basic_user)
        )
        await s_cleanup_user.commit()
    async for s_cleanup_sys in session_with_rls(system_operation_context()):
        from sqlalchemy import delete as sa_delete

        from app.models.provider_key import ProviderKey

        await s_cleanup_sys.execute(
            sa_delete(ProviderKey).where(ProviderKey.user_id == SYSTEM_USER_ID)
        )
        await s_cleanup_sys.commit()


async def test_shared_key_fallback_when_no_user_key(seed_basic_user: uuid.UUID) -> None:
    async for s_sys in session_with_rls(system_operation_context()):
        await set_provider_key(
            s_sys,
            system_operation_context(),
            provider="anthropic",
            plaintext="sk-shared",
        )
        await s_sys.commit()
    ctx = _user_ctx(seed_basic_user)
    # User has no key for anthropic; system fallback resolves
    async for s in session_with_rls(ctx):
        assert await resolve_key(s, ctx, provider="anthropic") == "sk-shared"
    # Cleanup
    async for s_cleanup in session_with_rls(system_operation_context()):
        from sqlalchemy import delete as sa_delete

        from app.models.provider_key import ProviderKey

        await s_cleanup.execute(
            sa_delete(ProviderKey).where(ProviderKey.user_id == SYSTEM_USER_ID)
        )
        await s_cleanup.commit()


async def test_missing_provider_key_error(seed_basic_user: uuid.UUID) -> None:
    ctx = _user_ctx(seed_basic_user)
    async for s in session_with_rls(ctx):
        with pytest.raises(MissingProviderKey) as excinfo:
            await resolve_key(s, ctx, provider="openrouter")
        assert excinfo.value.provider == "openrouter"
