# Security review — 2026-10-17

The reviewed launch scope is the public visual editor, Python preview engine,
exports and optional Discord OAuth project saving. Hosted bot execution is an
experimental owner-only feature, disabled by default. This is a code review and
local validation record, not a guarantee against every vulnerability.

Checked boundaries:

- Escaped UI rendering: HTML-like reply content remains text in preview.
- 256 KiB limits include streamed/chunked request bodies, not just Content-Length.
- Strict bounded graph definitions, typed sample context and bounded execution.
- No user-provided Python execution, subprocess commands or server URL fetching.
- Origin checks, hashed sessions, CSRF, ownership, optimistic writes and safe errors.
- Mocked Discord OAuth tests cover state mismatch/replay, identify-only scope,
  token exchange, hashed session creation and session revocation on logout.
- Production prohibits development login; OAuth is optional but credentials must
  be configured as a pair. Hosting needs a separate explicit opt-in.
- Public browser CSP and security headers; process-local request throttling.
- Bot tokens are encrypted at rest, omitted from responses/exports and logs.
- Release/staged secret scans compare against local secrets without printing them.

Bun and pip-audit reported no known advisories for the checked locked dependency
versions. Re-run audits as advisories and dependencies change. Production uses a
separate server lock; test tools are not installed in the backend image.

The local checks passed 51 Python tests and ten browser checks on both dev and
production builds. The build-time public origin and fresh adapter output are
verified, rather than relying on Vite compilation alone.

Still requires the actual environment: Docker builds (CI configured), PostgreSQL
migrations and backup restoration, trusted proxy/client-address configuration,
HTTPS cookie behavior and real Discord OAuth. Runner isolation and recovery need
separate integration tests before enabling hosting. See deployment.md.
