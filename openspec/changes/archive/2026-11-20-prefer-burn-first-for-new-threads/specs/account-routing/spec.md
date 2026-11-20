## ADDED Requirements

### Requirement: New thread seeding respects manual burn-first priority
For a previously unmapped Codex thread, strategies honoring manual routing
priority SHALL consider eligible burn_first accounts before inheriting a normal
or preserved process preference. Existing health, quota, scope and cap gates
SHALL remain enforced. Only the new thread mapping SHALL be persisted.

#### Scenario: Primary account recovers before a new thread
- **GIVEN** a process preference names a normal account
- **AND** an eligible burn_first account is available
- **WHEN** a new unmapped thread selects its account
- **THEN** ordinary account selection considers the burn_first account
- **AND** the process preference remains unchanged

#### Scenario: Primary account is unavailable or outside scope
- **GIVEN** the burn_first account fails quota, scope or local cap checks
- **WHEN** the new thread selects its account
- **THEN** the inherited selectable preference remains usable
- **AND** no eligibility gate is bypassed

### Requirement: Existing ownership and strategy boundaries remain intact
Existing thread mappings and required response/file/turn-state ownership SHALL
retain their existing selection behavior. Fixed-order strategies SHALL preserve
their existing process-seeding semantics.

#### Scenario: Existing thread or required owner names the reserve account
- **WHEN** a thread already has a selectable mapping or requires an account owner
- **THEN** burn_first priority does not override that existing ownership path

#### Scenario: Fixed-order routing strategy seeds a new thread
- **WHEN** the strategy is sequential_drain, reset_drain or single_account
- **THEN** the existing inherited-preference behavior is preserved
