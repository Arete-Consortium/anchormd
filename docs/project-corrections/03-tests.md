# Test Corrections And Suggestions

## Current Strength

The repo already has a healthy test surface, which is a real asset.

## Main Corrections

### 1. Treat security regressions as first-class tests

The new `tests/test_web_security.py` style should be extended.

Tests worth keeping permanent:

- private scan cannot be viewed anonymously
- private scan cannot be viewed by another user
- public scan remains viewable without auth
- cached private scan is only reusable by the owner
- OAuth callback rejects missing or invalid state
- browser-facing token is not the raw GitHub token
- clone error sanitization removes secrets

### 2. Update entitlement assumptions in test fixtures

Tests should no longer assume:

- “valid-looking key” automatically means Pro

Instead, tests should model Pro status through:

- server-validated license responses
- cached verified license records

This makes the suite reflect real production trust rules.

### 3. Add route-level tests for every new access policy

Whenever access rules change, add both:

- helper-level tests
- endpoint-level tests

That combination catches both logic drift and integration drift.

## Suggested Test Additions

### Web app

- deep scan report access for private repos
- fix report access for private repos
- Cursor rules export access for private repos
- push PR route cannot reuse another user’s private scan result

### Licensing

- unverified key stays free even if checksum passes
- cached verified Pro still works when server is unavailable
- expired cache sets degraded metadata but keeps verified tier

### Prompt and instruction generation

- generated instruction docs do not leak premium-only guidance into free flows unless intended
- generated output for web and CLI stays consistent for shared repo-analysis logic

## Test Execution Guidance

Recommended test layers:

- unit tests for sanitizers, access helpers, and token/session helpers
- route tests for web auth and scan access
- integration tests for CLI + licensing interaction

## Practical Next Tasks

- expand `tests/test_web_security.py`
- add helper fixtures for verified Pro licenses
- add regression tests for any future auth/session changes
- document a minimal “security smoke test” command set in the repo
