# Architecture Corrections And Suggestions

## Current Shape

The repo currently spans several concerns:

- CLI generation and audit logic in `src/anchormd/`
- a web application in `web/`
- a license server in `license_server/`
- prompt and skill artifacts in `prompts/` and `skills/`

This is workable, but several trust boundaries and ownership lines are still too soft.

## Main Corrections

### 1. Make trust boundaries explicit

The biggest architectural correction is to keep these three roles separate:

- the CLI may validate and cache entitlements
- the web app may manage web sessions and scan ownership
- the license server remains the source of truth for paid entitlements and quotas

Correction:

- do not let client-side checksum validation act as entitlement proof
- do not let browser-facing sessions double as upstream GitHub credentials
- do not let scan records act like globally readable cache entries when the underlying repo is private

### 2. Centralize scan ownership and visibility rules

The web app currently does a lot in route handlers. A small internal access layer would reduce repeated mistakes.

Suggested direction:

- create a scan repository module for DB reads/writes
- create a scan access policy module with helpers like:
  - `load_scan(scan_id)`
  - `can_view_scan(user, scan)`
  - `can_reuse_cached_scan(user, repo_url, private)`
  - `normalize_repo_metadata(repo_url, token)`

This keeps policy out of route bodies and makes tests more focused.

### 3. Reduce cross-surface coupling

The CLI, web app, and license server all depend on overlapping concepts:

- license validation
- quota enforcement
- repo scanning
- prompt or instruction generation

Suggested direction:

- move shared repo analysis primitives into library code under `src/anchormd/`
- keep transport-specific behavior in:
  - `web/` for HTTP and session handling
  - `license_server/` for entitlement and usage service behavior

That reduces drift between products and keeps security fixes from needing to be duplicated.

## Recommended Structure Improvements

### Introduce explicit service seams

Suggested internal modules:

- `src/anchormd/services/licensing_service.py`
- `src/anchormd/services/scan_service.py`
- `src/anchormd/services/repo_service.py`

Even if they only wrap existing logic at first, the separation will pay off quickly.

### Distinguish public vs authenticated repo flows

The web app should treat these as different cases:

- public repo scan
- authenticated public repo scan
- authenticated private repo scan
- paid deep scan for public repo

Keeping them explicit avoids future cache or access regressions.

## Practical Next Tasks

- extract scan loading and authorization into helper modules
- add a single source of truth for repo visibility normalization
- document the trust model in `docs/ARCHITECTURE.md`
- add a short data-flow diagram for:
  - GitHub OAuth
  - scan creation
  - deep scan fulfillment
  - license verification
