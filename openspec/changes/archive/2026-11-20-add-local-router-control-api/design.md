# Design

## Context

See proposal.md for motivation. Existing LB clients and this chat must keep working
while an optional Router takes over transport for a separate Zed profile. Both
accounts require the existing outbound proxy. LB remains the only OAuth writer.

## Goals / Non-Goals

The boundary gives Router current account policy and access credentials without
sharing the encryption key, refresh tokens or LB database. Terminal usage reaches
existing dashboard storage after interruption. No schema migration is needed.
General Guardian/history migration, file ownership migration and replacement of
existing LB proxy routes are outside this change.

## Decisions

- An opt-in loopback API with an owner-only bearer-key file replaces direct
  database/key sharing. Origin-bearing and remote callers are rejected, responses
  are no-store, and absent configuration leaves the feature disabled.
- Credential issuance reuses AuthManager and separate refresh sessions. A digest
  of a rejected access token prevents refreshing a newer token unnecessarily;
  Router does not replay the model request after a 401.
- Snapshots carry policies, quota freshness and shared budget settings. Router
  rejects unsupported settings explicitly instead of silently changing semantics.
- A durable Router outbox commits terminal metadata with local request state.
  LB serializes receipt-check and append using SQLite BEGIN IMMEDIATE under its
  writer lock or a PostgreSQL transaction advisory lock. A namespaced event ID
  and fingerprint reject payload changes; no new receipt table is required.
- Dashboard ingestion uses delivery time so delayed events cannot land below a
  completed rollup watermark. Actual generation latency remains in its own field.
- Model traffic uses the mandatory proxy. Authenticated local control traffic
  bypasses environment proxies only for the configured loopback address.

## Risks / Trade-offs

- LB/control-plane outage prevents fresh credential selection; completed usage
  stays in the local outbox. Telemetry never triggers a second inference.
- Lost HTTP/WebSocket transport has ambiguous dispatch; it does not trigger a
  replay. Hard owners remain enforced. This limits seamless account migration.
- PostgreSQL locking is implemented but was not live-tested; deployed storage
  is SQLite, whose concurrent idempotency path has integration coverage.
- Desktop LaunchAgent access is restricted by macOS TCC; the installed Router
  uses a packaged wheel outside Desktop, with source and runtime kept distinct.

## Migration Plan

Build and stage the pinned fork wheel including dashboard assets. Verify an
isolated candidate with real proxied HTTP/WS and installed ACP. Cut over LB only
with an independent controller and prepared rollback; retain old proxy routes.
Install Router separately on 2460 and add an experimental custom Zed profile.
Verify registered listener ownership, runtime hashes, both proxy environments,
real model requests, fresh quota timestamps and unique dashboard accounting.
The old profile is the immediate client fallback. The LB active-deployment
manifest retains the independent runtime rollback command.
