- [x] Reproduce new-thread process preference bypassing burn_first.
- [x] Preserve unavailable/scoped/capped account, existing thread and required-owner boundaries.
- [x] Apply the narrow initial candidate-pool correction.
- [x] Run affected suites, lint, types and strict change validation.
- [x] Publish only to the personal fork and deploy with independent rollback.

Verification:
- The original selector failed the available-primary regression; the other nine boundaries passed.
- Focused selector, refresh, replay, Guardian, sticky and WebSocket suites: 912 passed, 3 skipped.
- Full suite: 8774 passed, 38 skipped; the sole failure was the metrics logging assertion because this invocation disabled app.main logging. The whole metrics file subsequently passed without that flag.
- Additional HTTP Responses/compact regression and complete sticky/metrics files: 52 passed.
- Ruff formatting/lint, targeted ty check and strict change validation passed.
- Installed candidate: two real native WebSocket requests completed through the mandatory account-bound proxy. A new thread chose burn_first Team despite an inherited Plus seed; an existing sibling stayed on Plus, with both mappings and the process preference verified.
- Failed-start canary exercised independent rollback before activation.
- Pinned personal-fork runtime deployed; registered LaunchAgent PID matched the listener, code hashes and mandatory proxy environment matched, real Guardian completed, and a fresh quota snapshot was recorded. Temporary diagnostic jobs were removed; rollback remains available through the active deployment manifest.
- After spec synchronization, strict account-routing validation retains only the pre-existing placeholder-purpose and long-requirement warnings; the added requirements introduce no new warning.
