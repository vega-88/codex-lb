# Local router control API

## Why
A dedicated local Codex router needs current credentials and shared dashboard settings without reading the LB database/key or rotating refresh tokens. Its request statistics must reach the existing dashboard reliably.

## What Changes
Add an opt-in loopback bearer-authenticated control API for account/settings snapshots, access-only credentials and idempotent terminal request events. Keep existing proxy routes for existing clients. A separate router owns selection, transport, bindings and an event outbox. No schema migration, frontend change or upstream PR.
