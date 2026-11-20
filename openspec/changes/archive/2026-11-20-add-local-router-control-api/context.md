# Context
The control API is enabled by an owner-only data-dir/router-control.key. It rejects browser Origin headers and non-loopback peers. LB alone refreshes OAuth credentials, using existing refresh coordination and separate refresh sessions. Only access tokens leave LB. Router authenticates locally without an outbound proxy; all OpenAI traffic still requires the configured upstream proxy.

Snapshots carry routing policy, account status, quota freshness and the existing primary/secondary budget settings. Unsupported router strategies fail clearly. Request events contain bounded metadata and usage, never prompts or credentials. A durable router outbox retries delivery. LB serializes receipt check and append in one database transaction (SQLite BEGIN IMMEDIATE; PostgreSQL transaction advisory lock), uses a namespaced event ID and rejects changed payloads for the same ID. Dashboard requested_at is ingestion time to avoid inserting below a completed usage-rollup watermark after an outage; latency retains actual elapsed time. Existing LB proxy paths remain available during migration.

Example: Router selects Team from a snapshot, obtains its current access token, sends Responses through the required SOCKS proxy, then submits one terminal event. A lost acknowledgement causes a duplicate delivery with the same ID and no extra dashboard row.

## Operations

The optional Zed profile is zed-codex-router-prototype. Existing codex-acp and LB
proxy routes remain available for old chats; old response owners are not imported.
LB stays on 2455, Router on 2460 under local.zed-codex-router. The control key
~/.codex-lb/router-control.key is secret and must not be logged or committed.
All OpenAI traffic loads the existing protected upstream-proxy.env.

Read ~/.codex-lb/active-deployment.json for the pinned LB runtime, verification
and independent rollback command. Read ~/.local/share/zed-codex-router/active-deployment.json
for the packaged Router runtime and verification. Router config/state live under
~/.config/zed-codex-router and ~/.local/state/zed-codex-router. launchd must run
the packaged runtime outside Desktop because of macOS TCC restrictions.

Expected Router /status values are control_plane=lb_api, fresh account quota
timestamps and pending_dashboard_events=0. Dashboard source is zed-router.
An outbox backlog calls for checking control delivery, never inference replay.
Never dump raw LB startup logs: they can include a bootstrap token. If one is
exposed, revoke it through the official LB token service without printing its replacement.
