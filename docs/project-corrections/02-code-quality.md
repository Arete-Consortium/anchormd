# Code Corrections And Suggestions

## Main Themes

The strongest improvements are not about style polish. They are about reducing accidental security and policy regressions.

## Corrections To Preserve

### 1. Fail closed for paid features

`src/anchormd/licensing.py` should continue to treat server verification or cached prior verification as the gate for Pro behavior.

Why this matters:

- local format validation is useful
- local checksum validation is useful
- neither should be treated as proof of payment

### 2. Keep app sessions separate from GitHub tokens

`web/app.py` should continue using:

- stored GitHub token for server-side GitHub API calls
- separate opaque app session token for browser auth

This separation should remain a hard rule.

### 3. Sanitize sensitive operational errors

`web/generator.py` and related web scan code should continue to treat upstream command stderr as untrusted output.

Rule:

- never persist raw credential-bearing errors without sanitization

## Suggestions For Refactor

### Simplify route bodies

Several route handlers are still too large. When a handler both:

- loads DB state
- normalizes repo metadata
- authorizes access
- transforms response payloads

it becomes easy to reintroduce bugs during feature work.

Suggested extraction targets:

- repo metadata fetcher
- scan record loader
- scan access policy
- deep scan report serializer

### Reduce ad hoc JSON column parsing

`languages`, `recommendations`, and nested report payloads are parsed repeatedly.

Suggested direction:

- add small parsing helpers
- normalize empty/default handling in one place

This makes future format changes safer.

### Avoid “policy by convention”

Whenever a field name like `scan_type` or `repo_private` controls access, wrap it in helper functions instead of checking raw field values everywhere.

## Style Guidance

- prefer narrow helpers over long route functions
- keep security-sensitive logic near tests
- avoid repeating SQL fragments for security-relevant reads
- use explicit names like `session_token_hash`, `repo_private`, `user_id`

## Practical Next Tasks

- extract access helpers from `web/app.py`
- add parsing helpers for scan payload JSON fields
- add docstrings on security-sensitive helpers
- keep error sanitization logic unit-tested
