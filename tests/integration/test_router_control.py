from __future__ import annotations

import asyncio
import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.modules.router_control.api as control_api
from app.core.crypto import TokenEncryptor
from app.core.utils.time import utcnow
from app.db.models import Account, AccountStatus, RequestLog
from app.db.session import SessionLocal
from app.modules.accounts.auth_manager import AuthManager
from app.modules.settings.repository import SettingsRepository
from app.modules.usage.repository import UsageRepository

pytestmark = pytest.mark.integration
BASE = "/internal/router/v1"
TOKEN = "synthetic-local-router-key-1234567890"
AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def broker(tmp_path, monkeypatch):
    key = tmp_path / "router-control.key"
    key.write_text(TOKEN)
    key.chmod(0o600)
    monkeypatch.setattr(control_api, "get_settings", lambda: SimpleNamespace(data_dir=tmp_path))
    return key


async def account():
    encryptor = TokenEncryptor()
    async with SessionLocal() as session:
        row = Account(
            id="router-team",
            chatgpt_account_id="workspace",
            email="synthetic@example.com",
            plan_type="team",
            routing_policy="burn_first",
            access_token_encrypted=encryptor.encrypt("synthetic-access-token"),
            refresh_token_encrypted=encryptor.encrypt("synthetic-refresh-token"),
            id_token_encrypted=encryptor.encrypt("synthetic-id-token"),
            last_refresh=utcnow(),
            status=AccountStatus.ACTIVE,
        )
        session.add(row)
        await session.commit()
    return row.id


def event(account_id):
    return {
        "account_id": account_id,
        "model": "gpt-6.1-sol",
        "transport": "websocket",
        "status": "success",
        "latency_ms": 1000,
        "input_tokens": 30,
        "output_tokens": 5,
        "cached_input_tokens": 10,
    }


@pytest.mark.asyncio
async def test_control_rejects_missing_auth_origin_and_remote(async_client, app_instance, broker):
    for headers in [{}, {"Authorization": "Bearer wrong"}, {**AUTH, "Origin": "http://localhost"}]:
        response = await async_client.get(BASE + "/snapshot", headers=headers)
        assert response.status_code in {401, 403}
    async with AsyncClient(
        transport=ASGITransport(app=app_instance, client=("203.0.113.1", 123)), base_url="http://test"
    ) as remote:
        response = await remote.get(BASE + "/snapshot", headers=AUTH)
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_control_disabled_without_key_and_rejects_open_permissions(async_client, broker):
    broker.unlink()
    assert (await async_client.get(BASE + "/snapshot", headers=AUTH)).status_code == 404
    broker.write_text(TOKEN)
    broker.chmod(0o644)
    assert (await async_client.get(BASE + "/snapshot", headers=AUTH)).status_code == 503


@pytest.mark.asyncio
async def test_snapshot_has_shared_settings_usage_and_no_credentials(async_client, broker):
    account_id = await account()
    async with SessionLocal() as session:
        settings = await SettingsRepository(session).get_or_create()
        settings.sticky_reallocation_primary_budget_threshold_pct = 90
        await session.commit()
        await UsageRepository(session).add_entry(
            account_id=account_id, used_percent=25, window="primary", reset_at=2000000000, window_minutes=300
        )
    response = await async_client.get(BASE + "/snapshot", headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["primary_budget_threshold_pct"] == 90
    assert data["accounts"][0]["primary_used"] == 25
    assert data["accounts"][0]["quota_recorded_at"].endswith("Z")
    assert "token" not in response.text and "synthetic-access" not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_credential_access_only_and_forced_refresh_digest(async_client, broker, monkeypatch):
    account_id = await account()
    forces = []

    async def ensure(self, row, *, force=False):
        forces.append(force)
        return row

    monkeypatch.setattr(AuthManager, "ensure_fresh", ensure)
    response = await async_client.post(BASE + f"/accounts/{account_id}/credential", json={}, headers=AUTH)
    assert response.status_code == 200
    assert set(response.json()) == {"account_id", "access_token", "upstream_id", "installation_id"}
    assert "synthetic-refresh" not in response.text and "synthetic-id-token" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert forces == [False]
    response = await async_client.post(
        BASE + f"/accounts/{account_id}/credential", json={"force_refresh": True}, headers=AUTH
    )
    assert response.status_code == 400
    response = await async_client.post(
        BASE + f"/accounts/{account_id}/credential",
        json={
            "force_refresh": True,
            "previous_token_digest": hashlib.sha256(b"synthetic-access-token").hexdigest(),
        },
        headers=AUTH,
    )
    assert response.status_code == 200 and forces[-1] is True


@pytest.mark.asyncio
async def test_paused_account_does_not_export_credentials(async_client, broker):
    account_id = await account()
    async with SessionLocal() as session:
        row = await session.get(Account, account_id)
        row.status = AccountStatus.PAUSED
        await session.commit()
    response = await async_client.post(BASE + f"/accounts/{account_id}/credential", json={}, headers=AUTH)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_concurrent_event_retries_are_deduplicated_and_visible(async_client, broker):
    account_id = await account()
    event_id = uuid4().hex
    results = await asyncio.gather(
        *[async_client.post(BASE + f"/events/{event_id}", json=event(account_id), headers=AUTH) for _ in range(4)]
    )
    assert all(r.status_code == 200 for r in results)
    assert sum(not r.json()["duplicate"] for r in results) == 1
    async with SessionLocal() as session:
        rows = (await session.execute(select(RequestLog).where(RequestLog.source == "zed-router"))).scalars().all()
        assert len(rows) == 1
        assert rows[0].input_tokens == 30 and rows[0].cached_input_tokens == 10
    dashboard = await async_client.get("/api/accounts")
    summary = next(a for a in dashboard.json()["accounts"] if a["accountId"] == account_id)
    assert summary["requestUsage"]["requestCount"] == 1
    assert summary["requestUsage"]["totalTokens"] == 35


@pytest.mark.asyncio
async def test_changed_duplicate_event_is_conflict(async_client, broker):
    account_id = await account()
    event_id = uuid4().hex
    body = event(account_id)
    assert (await async_client.post(BASE + f"/events/{event_id}", json=body, headers=AUTH)).status_code == 200
    body["input_tokens"] = 40
    assert (await async_client.post(BASE + f"/events/{event_id}", json=body, headers=AUTH)).status_code == 409


@pytest.mark.asyncio
async def test_event_schema_rejects_payload_text_and_boolean_usage(async_client, broker):
    for extra in [{"prompt": "private"}, {"input_tokens": True}]:
        response = await async_client.post(
            BASE + f"/events/{uuid4().hex}", json={**event("unknown"), **extra}, headers=AUTH
        )
        assert response.status_code == 422
