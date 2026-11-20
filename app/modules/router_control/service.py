from __future__ import annotations

import base64
import hashlib
import json
import time
from datetime import timezone

from app.core.crypto import TokenEncryptor
from app.db.models import AccountStatus
from app.modules.accounts.auth_manager import AuthManager
from app.modules.accounts.repository import AccountsRepository
from app.modules.router_control.schemas import (
    AccessCredential,
    AccountSnapshot,
    CredentialRequest,
    RouterSettings,
    Snapshot,
)
from app.modules.settings.repository import SettingsRepository
from app.modules.usage.repository import UsageRepository


def _expires_soon(token: str) -> bool:
    try:
        segment = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))
        expiry = claims.get("exp")
        return isinstance(expiry, (int, float)) and not isinstance(expiry, bool) and expiry < time.time() + 60
    except (ValueError, IndexError, AttributeError):
        return False


class AccountUnavailableError(Exception):
    pass


class RouterControlService:
    def __init__(
        self, accounts: AccountsRepository, usage: UsageRepository, settings: SettingsRepository, auth: AuthManager
    ):
        self.accounts, self.usage, self.settings, self.auth = accounts, usage, settings, auth

    async def snapshot(self) -> Snapshot:
        accounts = [a for a in await self.accounts.list_accounts() if a.delete_requested_at is None]
        primary = await self.usage.latest_by_account(window="primary")
        secondary = await self.usage.latest_by_account(window="secondary")
        settings = await self.settings.get_or_create()
        return Snapshot(
            settings=RouterSettings(
                routing_strategy=settings.routing_strategy,
                primary_budget_threshold_pct=settings.sticky_reallocation_primary_budget_threshold_pct,
                secondary_budget_threshold_pct=settings.sticky_reallocation_secondary_budget_threshold_pct,
            ),
            accounts=[
                AccountSnapshot(
                    id=a.id,
                    label=a.alias or a.plan_type,
                    plan=a.plan_type,
                    policy=a.routing_policy,
                    status=a.status.value,
                    reset_at=a.reset_at,
                    primary_used=primary[a.id].used_percent if a.id in primary else None,
                    secondary_used=secondary[a.id].used_percent if a.id in secondary else None,
                    quota_recorded_at=(
                        primary[a.id].recorded_at.replace(tzinfo=timezone.utc) if a.id in primary else None
                    ),
                    primary_window_minutes=primary[a.id].window_minutes if a.id in primary else None,
                )
                for a in accounts
            ],
        )

    async def credential(self, account_id: str, request: CredentialRequest) -> AccessCredential:
        account = await self.accounts.get_by_id_fresh(account_id)
        if account is None or account.delete_requested_at is not None:
            raise LookupError("Unknown account")
        if account.status not in {AccountStatus.ACTIVE, AccountStatus.RATE_LIMITED, AccountStatus.QUOTA_EXCEEDED}:
            raise AccountUnavailableError
        encryptor = TokenEncryptor()
        current = encryptor.decrypt(account.access_token_encrypted)
        if request.force_refresh and request.previous_token_digest is None:
            raise ValueError("Forced refresh requires the previously rejected access-token digest")
        force = request.force_refresh and hashlib.sha256(current.encode()).hexdigest() == request.previous_token_digest
        account = await self.auth.ensure_fresh(account, force=force or _expires_soon(current))
        # Re-read after refresh; do not serve credentials for an account paused/deleted during refresh.
        latest = await self.accounts.get_by_id_fresh(account_id)
        if latest is None or latest.delete_requested_at is not None:
            raise LookupError("Unknown account")
        if latest.status not in {AccountStatus.ACTIVE, AccountStatus.RATE_LIMITED, AccountStatus.QUOTA_EXCEEDED}:
            raise AccountUnavailableError
        return AccessCredential(
            account_id=latest.id,
            access_token=encryptor.decrypt(latest.access_token_encrypted),
            upstream_id=latest.chatgpt_account_id,
            installation_id=latest.codex_installation_id,
        )
