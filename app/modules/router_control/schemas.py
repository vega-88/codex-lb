from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class ControlModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountSnapshot(ControlModel):
    id: str
    label: str
    plan: str
    policy: str
    status: str
    reset_at: int | None
    primary_used: float | None
    secondary_used: float | None
    quota_recorded_at: datetime | None
    primary_window_minutes: int | None


class RouterSettings(ControlModel):
    routing_strategy: str
    primary_budget_threshold_pct: float
    secondary_budget_threshold_pct: float


class Snapshot(ControlModel):
    accounts: list[AccountSnapshot]
    settings: RouterSettings


class CredentialRequest(ControlModel):
    force_refresh: bool = False
    previous_token_digest: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class AccessCredential(ControlModel):
    account_id: str
    access_token: str = Field(repr=False)
    upstream_id: str | None
    installation_id: str


class RequestEvent(ControlModel):
    account_id: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    transport: Literal["http", "websocket", "compact"]
    status: Literal["success", "error", "cancelled"]
    latency_ms: StrictInt = Field(ge=0, le=604800000)
    input_tokens: StrictInt | None = Field(default=None, ge=0, le=10000000000)
    output_tokens: StrictInt | None = Field(default=None, ge=0, le=10000000000)
    cached_input_tokens: StrictInt | None = Field(default=None, ge=0, le=10000000000)
    reasoning_tokens: StrictInt | None = Field(default=None, ge=0, le=10000000000)
    error_code: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_.-]{1,100}$")
    session_id: str | None = Field(default=None, pattern=r"^zcr:[a-f0-9]{64}$")


class EventReceipt(ControlModel):
    accepted: bool = True
    duplicate: bool
