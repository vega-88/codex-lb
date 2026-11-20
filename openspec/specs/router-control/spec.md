# router-control Specification

## Purpose

Provide an optional local boundary for access-only credentials, shared routing policy and reliable dashboard accounting while LB retains OAuth ownership.

## Requirements

### Requirement: Protected local credential broker
LB SHALL provide account/settings snapshots and access-only credentials to an owner-authenticated loopback router. Missing credentials, browser Origin headers and remote peers SHALL be rejected. OAuth refresh SHALL remain owned by LB and its existing coordination.

#### Scenario: Router obtains an access token
- **WHEN** a configured local router authenticates and requests an eligible account
- **THEN** LB returns current access credentials with no-store headers
- **AND** no refresh token or encryption key is included

#### Scenario: Browser or unauthenticated caller
- **WHEN** a caller sends an Origin header or lacks the control bearer token
- **THEN** LB denies the request before exposing account or credential data

### Requirement: Idempotent external request accounting
LB SHALL atomically deduplicate terminal events by namespaced event ID, reject changed duplicate payloads, and expose accepted usage in existing dashboard logs. Events SHALL contain metadata only.

#### Scenario: An acknowledgement is lost
- **WHEN** Router retries the same terminal event after an interrupted acknowledgement
- **THEN** only one dashboard request row is recorded

#### Scenario: Concurrent deliveries
- **WHEN** multiple deliveries carry the same event ID
- **THEN** receipt and append are serialized in one database transaction

### Requirement: Shared policy with isolated transport ownership
Router SHALL use LB account policies and primary budget settings, keep routing state and a durable delivery outbox separately, and use the mandatory proxy for every OpenAI call. Telemetry failure SHALL NOT replay model requests.

#### Scenario: Dashboard policy changes
- **WHEN** a new selection fetches a current snapshot
- **THEN** Router applies the shared account policy and budget threshold

#### Scenario: Control-plane outage after generation
- **WHEN** a completed request event cannot reach LB
- **THEN** Router retains it for later delivery without repeating the model request
