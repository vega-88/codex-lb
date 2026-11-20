from __future__ import annotations

import hashlib
import json
from typing import cast

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.usage.logs import RequestLogLike, calculated_cost_from_log
from app.core.utils.time import utcnow
from app.db.models import Account, RequestLog
from app.db.session import sqlite_writer_section
from app.modules.router_control.schemas import RequestEvent


class EventConflictError(Exception):
    pass


class RouterControlRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ingest(self, event_id: str, event: RequestEvent) -> bool:
        """Return duplicate flag. Receipt and append commit atomically, including across workers."""
        key = "zcr:" + event_id
        canonical = json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        fingerprint = "router_event_sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
        async with sqlite_writer_section():
            try:
                if self.session.get_bind().dialect.name == "sqlite":
                    await self.session.execute(text("BEGIN IMMEDIATE"))
                else:
                    # A hash collision only serializes unrelated events; identity is still the full key below.
                    lock = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big", signed=True)
                    await self.session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
                previous = (
                    await self.session.execute(select(RequestLog).where(RequestLog.request_id == key).limit(1))
                ).scalar_one_or_none()
                if previous is not None:
                    if previous.source != "zed-router" or previous.failure_detail != fingerprint:
                        raise EventConflictError
                    await self.session.rollback()
                    return True
                account = await self.session.get(Account, event.account_id)
                if account is None:
                    raise LookupError("Unknown event account")
                # Ingestion time keeps delayed outbox events above already-completed rollup watermarks.
                log = RequestLog(
                    account_id=account.id,
                    request_id=key,
                    archive_request_id=key,
                    model=event.model,
                    plan_type=account.plan_type,
                    source="zed-router",
                    useragent_group="zed-router",
                    status=event.status,
                    error_code=event.error_code,
                    transport="http" if event.transport == "compact" else event.transport,
                    upstream_transport="http" if event.transport == "compact" else event.transport,
                    latency_ms=event.latency_ms,
                    input_tokens=event.input_tokens,
                    output_tokens=event.output_tokens,
                    cached_input_tokens=event.cached_input_tokens,
                    reasoning_tokens=event.reasoning_tokens,
                    session_id=event.session_id,
                    requested_at=utcnow(),
                    failure_detail=fingerprint,
                    upstream_proxy_route_mode="account_bound",
                    upstream_proxy_fallback_used=False,
                )
                log.cost_usd = calculated_cost_from_log(cast(RequestLogLike, log))
                self.session.add(log)
                await self.session.commit()
                return False
            except BaseException:
                await self.session.rollback()
                raise
