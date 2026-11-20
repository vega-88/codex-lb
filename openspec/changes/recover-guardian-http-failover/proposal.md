# Recover native Guardian HTTP fallback after account exhaustion

Native Codex sends its complete Guardian request when falling back to HTTP.
The HTTP session bridge can reattach this unanchored request to the exhausted
account used by a previous review, returning 502/503 while main-agent requests
already succeed on a reserve account.

For eligible anonymous native codex-auto-review HTTP requests without an
explicit response/conversation anchor, use ordinary account selection without
inferring the previous review owner. Preserve the complete original request
body, session accounting labels, account eligibility and normal finalization.
Explicit owners, API-key/SDK traffic and unknown or hosted state retain their
existing paths. No settings or client history changes are required.

The change is deliberately narrower than relaxing generic replay classification.
It preserves the approval review and does not reinterpret a technical review
failure as permission to execute an action.
