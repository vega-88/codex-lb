from __future__ import annotations

import ipaddress
import os
import secrets
import stat
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.refresh import RefreshError
from app.core.config.settings import get_settings
from app.db.session import get_background_session, get_session
from app.dependencies import AccountsContext, get_accounts_context
from app.modules.accounts.auth_manager import AuthManager
from app.modules.accounts.repository import AccountsRepository
from app.modules.router_control.repository import EventConflictError, RouterControlRepository
from app.modules.router_control.schemas import AccessCredential, CredentialRequest, EventReceipt, RequestEvent, Snapshot
from app.modules.router_control.service import AccountUnavailableError, RouterControlService
from app.modules.settings.repository import SettingsRepository
from app.modules.usage.repository import UsageRepository


def authenticate(request: Request, response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    if request.headers.get("origin") is not None or request.client is None:
        raise HTTPException(403, "local_router_only")
    try:
        local = ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        local = False
    if not local:
        raise HTTPException(403, "local_router_only")
    path = get_settings().data_dir / "router-control.key"
    try:
        info = path.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISREG(info.st_mode):
            raise HTTPException(503, "control_key_permissions")
        if info.st_size > 4096:
            raise HTTPException(503, "control_key_invalid")
        expected = path.read_text().strip()
    except FileNotFoundError:
        raise HTTPException(404, "router_control_disabled") from None
    supplied = request.headers.get("authorization", "")
    if len(expected) < 32 or not secrets.compare_digest(
        supplied.encode("utf-8"), ("Bearer " + expected).encode("utf-8")
    ):
        raise HTTPException(401, "invalid_router_credentials", headers={"Cache-Control": "no-store"})


router = APIRouter(prefix="/internal/router/v1", tags=["local-router"], dependencies=[Depends(authenticate)])


@asynccontextmanager
async def refresh_repository() -> AsyncIterator[AccountsRepository]:
    async with get_background_session() as session:
        yield AccountsRepository(session)


def service(context: AccountsContext) -> RouterControlService:
    return RouterControlService(
        context.repository,
        UsageRepository(context.session),
        SettingsRepository(context.session),
        AuthManager(context.repository, refresh_repo_factory=refresh_repository),
    )


@router.get("/snapshot", response_model=Snapshot)
async def snapshot(context: AccountsContext = Depends(get_accounts_context)) -> Snapshot:
    return await service(context).snapshot()


@router.post("/accounts/{account_id}/credential", response_model=AccessCredential)
async def credential(
    account_id: str, body: CredentialRequest, context: AccountsContext = Depends(get_accounts_context)
) -> AccessCredential:
    try:
        return await service(context).credential(account_id, body)
    except LookupError:
        raise HTTPException(404, "account_not_found") from None
    except AccountUnavailableError:
        raise HTTPException(409, "account_unavailable") from None
    except ValueError:
        raise HTTPException(400, "refresh_digest_required") from None
    except RefreshError:
        raise HTTPException(503, "credential_refresh_failed") from None


@router.post("/events/{event_id}", response_model=EventReceipt)
async def event(event_id: UUID, body: RequestEvent, session: AsyncSession = Depends(get_session)) -> EventReceipt:
    try:
        duplicate = await RouterControlRepository(session).ingest(event_id.hex, body)
        return EventReceipt(duplicate=duplicate)
    except EventConflictError:
        raise HTTPException(409, "event_payload_conflict") from None
    except LookupError:
        raise HTTPException(404, "account_not_found") from None
