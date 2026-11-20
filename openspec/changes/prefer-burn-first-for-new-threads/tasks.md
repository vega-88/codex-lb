- [x] Reproduce new-thread process preference bypassing burn_first.
- [x] Preserve unavailable/scoped/capped account, existing thread and required-owner boundaries.
- [x] Apply the narrow initial candidate-pool correction.
- [x] Run affected suites, lint, types and strict change validation.
- [ ] Publish only to the personal fork and deploy with independent rollback.

Verification:
- The original selector failed the available-primary regression; the other nine boundaries passed.
- Focused selector, refresh, replay, Guardian, sticky and WebSocket suites: 912 passed, 3 skipped.
- Full suite: 8774 passed, 38 skipped; the sole failure was the metrics logging assertion because this invocation disabled app.main logging. The whole metrics file subsequently passed without that flag.
- Additional HTTP Responses/compact regression and complete sticky/metrics files: 52 passed.
- Ruff formatting/lint, targeted ty check and strict change validation passed.
- Release activation and native candidate verification remain tracked by the final task.
