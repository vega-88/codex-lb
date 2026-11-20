- [x] Implement protected snapshots/access-only credentials and coordinated refresh.
- [x] Implement atomic idempotent event ingestion into existing dashboard logs.
- [x] Update Router to use the broker and shared settings with a durable event outbox.
- [x] Verify auth boundaries, concurrency, offline delivery, HTTP/WebSocket and actual ACP.
- [x] Publish fork changes and stage/deploy with independent recovery; provide a separate Zed profile.

Verification before deployment:
- 8 API integration cases passed, including concurrent deduplication and dashboard totals.
- Final API + existing Guardian helper suites: 39 passed.
- Router: 26 tests passed, lint/format and targeted type checks passed.
- Isolated real HTTP/WS and installed ACP adapter completed through the mandatory SOCKS proxy with credentials obtained from the candidate LB API. Terminal usage arrived in its dashboard; outbox drained.
- First broad run was interrupted after 8145 passed / 38 skipped / 12 timeouts, all in unchanged Helm dependency-download tests. Runtime rerun excludes only tests/unit/test_helm_external_secrets.py; see final result below.
- No schema migration was introduced. Existing proxy routes remain available for old chats during adoption of the separate Zed profile.
- Completed broad rerun: 8730 passed, 38 skipped, one unrelated timeout in test_helm_replica_artifacts.py::test_grafana_dashboard_titles_can_be_overridden while helm dependency build downloaded external artifacts. Full suite is not claimed green. All new API/Router scenarios and targeted Guardian checks passed.
- Corrected SSE token accounting also passed against real application/octet-stream responses and an installed ACP session; final candidate rows had non-null input/output usage.

Deployment completion:
- Fork implementation published at 07e87b636ae265483a6a0fee8f7b3a2b46368f5f and installed from its pinned wheel, with dashboard assets and independent rollback.
- Final registered LB/Router listener ownership, installed hashes and both protected proxy environments verified. Real production HTTP, WS and installed ACP completed; four unique dashboard rows contain terminal usage, and the durable outbox is empty.
- Both account quota snapshots are fresh; shared soft reserve is 10%. Existing Zed settings/profile remain, with zed-codex-router-prototype added separately.
- Router launchd runtime was packaged outside Desktop to avoid macOS TCC. Temporary deployment jobs were removed after successful verification.
- Zed interface selection remains a manual check; the actual installed adapter was exercised by protocol. Complex-state and general Guardian migration remain outside this prototype.
