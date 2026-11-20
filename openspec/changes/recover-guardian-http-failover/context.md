# Context and evidence

Codex 0.170.0's native HTTP executor builds the complete Responses prompt, while
its WebSocket path may send a delta. Guardian calls can therefore fall back to
HTTP with all prior inline messages and encrypted reasoning even after the main
agent has switched accounts. Reattaching such a fresh HTTP review to the old
bridge owner creates repeated 502/503 failures.

The existing generic account-neutral replay classifier deliberately rejects
modern inline IDs, provenance, namespaces and encrypted reasoning. This change
keeps that classifier unchanged. A separate bounded native Guardian HTTP check
validates ordinary text, local declarations and controls using a validation-only
view. The entire original body is forwarded; this view is never serialized.

For example, an unanchored review with complete prior messages, encrypted
reasoning and a completed verdict can select a usable reserve account even when
its turn-state token identifies an exhausted bridge owner. A stored-item
reference, hosted tool or unfinished reasoning retains the continuity path.
Unknown shapes and malformed discriminators are ineligible for the new path.

OpenAI documents encrypted reasoning as inline stateless state:
https://developers.openai.com/api/docs/guides/conversation-state
The native HTTP executor constructs its full prompt:
https://github.com/openai/codex/blob/main/codex-rs/core/src/client.rs

Verification on v1.24.0: 250 focused Guardian/replay tests pass, including the
seeded exhausted-owner route and exact-body preservation. The production code
and tests match the independently reviewed patch. The full suite recorded
8764 passed, 38 skipped and one pre-existing failure in
`test_proxy_responses_repeated_401_after_refresh_fails_over` (gpt-5.4), also
reproduced on a fresh unmodified v1.24.0 snapshot. The full suite is not claimed
all-green. Strict validation of this change passes; main-spec strict validation
has pre-existing placeholder/long-requirement warnings in 55 specifications.

An upstream validation or decryption failure still fails the review; it never
approves the action. No real credentials, account databases or captured private
review histories are included in these fixtures.
