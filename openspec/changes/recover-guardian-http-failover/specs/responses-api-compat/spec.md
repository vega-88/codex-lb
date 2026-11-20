## ADDED Requirements

### Requirement: Native unanchored Guardian HTTP requests remain independent
The service SHALL use the ordinary Responses stream for an anonymous native
Codex or explicitly marked Guardian `codex-auto-review` HTTP request only when
it has no explicit response/conversation anchor and contains complete inline
text review history. SDK-marked requests SHALL retain existing routing.

#### Scenario: Review falls back after the former owner exhausts its quota
- **GIVEN** a native Guardian HTTP request contains the complete review context
- **AND** its headers carry a stale session or turn-state affinity
- **WHEN** neither an explicit response nor conversation anchor is present
- **THEN** the service uses ordinary account selection without the stale affinity
- **AND** it forwards the complete review body to the selected account
- **AND** it preserves inline encrypted reasoning instead of discarding it

### Requirement: Guardian context validation preserves the original body
The service SHALL preserve eligible requests exactly, including inline IDs,
validated provenance, local function/custom namespaces and complete encrypted
reasoning. Hosted tools, stored references, files, pending calls, unfinished
reasoning and unknown shapes SHALL be ineligible. Malformed JSON discriminators
SHALL make classification fail without raising a classification exception.

#### Scenario: Unknown state retains continuity processing
- **GIVEN** an unanchored Guardian request includes hosted tools or unknown state
- **WHEN** the inline-context validator examines the request
- **THEN** the request remains on its existing continuity path
- **AND** classification does not change the original body

### Requirement: Independent reviews retain accounting without stale affinity
Independent Guardian requests SHALL omit `x-codex-turn-state`. Session/thread
labels SHALL remain for accounting and upstream cache identity without creating
a hard local owner. Model/account eligibility, file ownership checks and normal
accounting SHALL remain enforced.

#### Scenario: Old turn state does not pin a fresh review
- **GIVEN** an eligible complete Guardian HTTP review has a stale turn-state token
- **WHEN** the service selects the independent stream
- **THEN** the upstream request omits that token and retains session/thread labels
- **AND** the existing exhausted bridge remains intact

### Requirement: Anchored and unrelated requests preserve existing routing
API-key traffic, explicitly anchored requests, non-native public requests and
other models SHALL retain their existing continuity and routing behavior.

#### Scenario: Explicit ownership and unrelated requests remain unchanged
- **WHEN** a Guardian request supplies an explicit response or conversation anchor
- **OR** the request uses another model or a public non-native route
- **THEN** existing continuity ownership and routing behavior remain in force
