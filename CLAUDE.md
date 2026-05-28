# CLAUDE.md — anchormd

## Project Overview

Generate and audit AI-agent context files (CLAUDE.md, AGENTS.md) for AI coding agents. Freemium CLI + web UI with a Stripe-automated license server. Three paid tiers: Pro (individual), Strict (CI / procurement), and one-off web scans.

Commands: `generate`, `audit` (structure scoring), `verify` (reality check — claims vs filesystem), `fleet` (cross-repo audit), `harvest` (recurring gotchas from Claude Code transcripts), `patch` (splice harvested anti-patterns into existing CLAUDE.md), plus Pro: `init`, `diff`, `tech-debt`, `github-health`, `cleanup`, `drift`. Strict adds fail-closed validation, team seats, and a server-side audit log.

## Current State

- **Version**: 0.6.0 (shipped 2026-05-17; see CHANGELOG.md)
- **Language**: Python 3.11+
- **Tests**: 811 passing (client + license server combined)
- **License Server**: `https://cmdf-license.fly.dev` (Fly.io, SQLite + WAL, Litestream HA via `license_server/litestream.yml`)
- **Web UI**: `anchormd-web` on Fly.io (deployed from project root via `fly.web.toml`)
- **Stripe**: Live — automated checkout → key generation → email delivery for Pro and Strict SKUs

## Monetization

- **Free**: `generate`, `audit`, 11 community presets, AGENTS.md/Codex/CLAUDE.md exports, `drift run` / `drift report` (terminal)
- **Pro ($8/mo or $69/yr)**: `init`, `diff`, 6 premium presets, team templates, `tech-debt`, `github-health`, `cleanup`
- **Strict ($49/seat/mo · $399/yr team-5 · $1,490/yr team-25)**: Fail-closed license validation (`ANCHORMD_STRICT=1`), team seats, 365-day audit log, fleet `--json` + history, CI integration (PR-comment automation), advanced drift (`drift generate`, `drift fix`, `drift report --ci/--html`, `--judge-model`)
- **Template Packs**: Gumroad ($5–10 each)
- **One-time web scan**: $29 deep scan (planned)
- **Payment Links**: Stripe Payment Links → webhook → auto key + email
- **Do NOT modify pricing tiers without explicit approval** (the Pro→Strict feature moves in v0.6.0 were approved; future moves are not)

## Architecture

```
anchormd/
├── .github/workflows/
├── docs/
│   ├── strict.md                 # Strict tier docs
│   └── STRICT_SPEC.md            # Internal spec
├── license_server/               # FastAPI license server (separate deployable)
│   ├── migrations/               # 001..006 (latest: seats, audit_events)
│   ├── routes/
│   │   ├── activate.py           # POST /v1/activate (admin)
│   │   ├── validate.py           # POST /v1/validate
│   │   ├── revoke.py             # POST /v1/revoke (admin)
│   │   ├── usage.py              # POST /v1/usage{,/check}
│   │   ├── seats.py              # POST /v1/seats/{claim,release}, GET /v1/seats/list
│   │   ├── audit.py              # POST /v1/audit/log, GET /v1/audit/export
│   │   └── webhook.py            # POST /v1/webhooks/stripe
│   ├── stripe_webhooks.py        # Event handlers (Pro + Strict checkout, cancel, payment_failed)
│   ├── email_delivery.py         # SMTP delivery (welcome + Strict welcome with CI snippet)
│   ├── key_gen.py                # ANMD-XXXX-XXXX-XXXX generation + hashing
│   ├── config.py                 # Env var configuration
│   ├── database.py               # SQLite + migration runner
│   ├── models.py                 # Pydantic request/response models
│   ├── rate_limit.py             # slowapi rate limiter
│   ├── litestream.yml            # Litestream HA replication config
│   ├── scripts/restore.sh        # Restore-on-start wrapper
│   ├── Dockerfile, fly.toml, requirements.txt
│   └── pyproject.toml            # Server package metadata (kept in sync with root)
├── packs/                        # Gumroad template packs
├── prompts/
├── scripts/
│   ├── stripe_setup.py           # Create Stripe products/prices/payment links (supports --strict-only)
│   └── keygen.py                 # Manual key generation (legacy)
├── src/anchormd/                 # CLI package (PyPI: anchormd)
│   ├── cli.py                    # Typer CLI entrypoint
│   ├── licensing.py              # Key detection, validation, caching, Tier enum
│   ├── gates.py                  # @require_pro, @require_strict decorators
│   ├── seats.py                  # Client-side seat claim (Strict)
│   ├── audit_logger.py           # Fire-and-forget audit POST (Strict)
│   ├── telemetry.py              # Anonymous gate-event tracking
│   ├── machine_id.py             # Hostname+username hash
│   ├── scanner.py                # Repo introspection
│   ├── config.py, models.py, exceptions.py
│   ├── ci.py, cleanup.py
│   ├── analyzers/                # commands, domain, github, harvest, language,
│   │                             # opsec, patterns, reality, skills, suggestions, tech_debt
│   ├── generators/               # auditor, composer, patcher, sections, checkers/
│   ├── drift/                    # cli, generator, fixer, runner, scorer, reporter,
│   │                             # storage, trend, adapters/, templates/
│   └── templates/                # base, frameworks, presets
├── web/                          # Web UI (anchormd-web on Fly.io)
│   ├── app.py                    # FastAPI: POST /api/scan, GET /api/scan/{id}
│   ├── generator.py              # Wrapper around anchormd generation logic
│   ├── frontend/                 # React + Vite + Tailwind (dark theme; StrictPage, PricingPage)
│   └── Dockerfile                # Multi-stage build (Node + Python)
├── tests/                        # 811 tests; mirrors src/ + tests/license_server/
├── substack-drafts/              # Launch copy
├── skills/                       # Claude Code skill definitions
├── fly.web.toml, vercel.json, action.yml
└── pyproject.toml
```

## Tech Stack

- **Language**: Python, HTML, SQL, JavaScript (web frontend)
- **Package Manager**: pip
- **Linters / Formatters**: ruff
- **Type Checkers**: mypy (strict)
- **Test Frameworks**: pytest
- **CI/CD**: GitHub Actions
- **Hosting**: Fly.io (license server + web UI), PyPI (CLI)
- **Payments**: Stripe (webhooks + payment links)
- **Email**: SMTP (Gmail app password)
- **HA**: Litestream → S3-compatible storage for SQLite replication

## API Endpoints (License Server)

| Endpoint | Auth | Rate Limit | Purpose |
|----------|------|------------|---------|
| `GET /v1/health` | None | 120/min | Health check + license counts |
| `POST /v1/activate` | Admin Bearer | 10/min | Create license key |
| `POST /v1/validate` | None | 60/min | Validate license key (returns tier, seats_used/total) |
| `POST /v1/revoke` | Admin Bearer | 10/min | Revoke license key |
| `POST /v1/usage/check` | None | 60/min | Check scan quota remaining |
| `POST /v1/usage` | None | 30/min | Record a scan + return updated quota |
| `POST /v1/seats/claim` | None | 60/min | Strict: claim a seat for this machine |
| `POST /v1/seats/release` | None | 30/min | Strict: release a seat |
| `GET /v1/seats/list` | Admin Bearer | 30/min | Strict: list seats for a license |
| `POST /v1/audit/log` | None | 120/min | Strict: append a CLI invocation event |
| `GET /v1/audit/export` | Admin Bearer | 10/min | Strict: export audit events (CSV default, JSON optional) |
| `POST /v1/webhooks/stripe` | Stripe signature | 30/min | Automated fulfillment (Pro + Strict checkout) |

## License Key System

- **Format**: `ANMD-XXXX-XXXX-XXXX` (uppercase alphanumeric)
- **Checksum**: Segment 3 = first 4 hex chars of `SHA256("anchormd-v1:{seg1}-{seg2}")`
- **Storage**: SHA-256 hash only — plaintext never stored
- **Masking**: `ANMD-****-****-{last4}` for display
- **Client detection**: `ANCHORMD_LICENSE` env var → `.anchormd-license` → `~/.config/anchormd/license`
- **Pro validation**: Local checksum → server call (5s timeout) → 24h cache → **fail-open** to local-only
- **Strict validation** (`ANCHORMD_STRICT=1`): same path, but any validation failure (server unreachable, revoked, expired, no cache) → **fail-closed** non-zero exit
- **Seats** (Strict): first successful validation per machine triggers `claim_seat_on_startup()`; cap enforced server-side (HTTP 409 over `seats_total`); 24h on-disk claim cache

## Environment Variables

### License Server (Fly.io secrets)
- `ANMD_ADMIN_SECRET` — Bearer token for admin endpoints
- `ANMD_DB_PATH` — SQLite path (default: `/data/license_server.db`)
- `ANMD_RATE_LIMIT` — Optional rate-limit override
- `STRIPE_SECRET_KEY` — Stripe API key
- `STRIPE_WEBHOOK_SECRET` — Stripe webhook signing secret
- `ANMD_SMTP_USER` / `ANMD_SMTP_PASSWORD` — Gmail credentials
- `ANMD_SMTP_FROM` — From address for emails
- `ANMD_SMTP_HOST` / `ANMD_SMTP_PORT` — SMTP server (defaults: Gmail)

### Client (user-side)
- `ANCHORMD_LICENSE` — License key
- `ANCHORMD_LICENSE_SERVER` — Server URL (optional override)
- `ANCHORMD_STRICT` — Set to `1` to opt into fail-closed validation (Strict tier)
- `ANCHORMD_NO_AUDIT` — Set to `1` to opt out of Strict audit logging
- `ANCHORMD_TELEMETRY` — Set to `0` to disable anonymous gate-event tracking
- `ANCHORMD_DIR` — Override config dir (default: `~/.config/anchormd`)

## Common Commands

```bash
# test (all)
.venv/bin/python -m pytest tests/ -v
# test (license server only)
.venv/bin/python -m pytest tests/license_server/ -v
# lint
ruff check src/ tests/ license_server/ web/
# format
ruff format src/ tests/ license_server/ web/
# type check
mypy src/
# deploy license server
fly deploy --dockerfile license_server/Dockerfile --config license_server/fly.toml
# deploy web UI
fly deploy --config fly.web.toml
# health check
curl https://cmdf-license.fly.dev/v1/health
```

## Coding Standards

- **Naming**: snake_case
- **Quote Style**: double quotes
- **Type Hints**: present (mypy strict)
- **Imports**: absolute
- **Path Handling**: pathlib
- **Line Length**: 100 characters
- **Error Handling**: Custom exception classes, `from exc` in re-raises

## Anti-Patterns (Do NOT Do)

- Do NOT commit secrets, API keys, or credentials
- Do NOT skip writing tests for new code
- Do NOT use `os.path` — use `pathlib.Path` everywhere
- Do NOT use bare `except:` — catch specific exceptions
- Do NOT use mutable default arguments
- Do NOT use `print()` for diagnostics or server-side logging — use the `logging` module. (User-facing CLI output via `rich.console` / `typer.echo` is fine.)
- Do NOT store plaintext license keys in the database
- Do NOT modify pricing tiers without approval
- Do NOT add a grandfather/legacy code path for a tier move without approval

## Dependencies

### CLI (PyPI)
- typer, rich, pydantic, tomli, pyyaml, jinja2
- httpx (optional, for server validation — installed via `anchormd[server]`)

### License Server (Fly.io)
- fastapi, uvicorn, pydantic, slowapi, stripe

### Web UI (Fly.io)
- fastapi, uvicorn (backend) · React + Vite + Tailwind (frontend)

### Dev
- pytest, mypy, ruff, httpx — plus license-server runtime deps so `tests/license_server/` collects

## Web UI Roadmap

**Strategic context:** Every coding-agent user needs a CLAUDE.md (or AGENTS.md). Most write poor ones. anchormd is the tool that fixes that. The web UI is the top of funnel; the CLI is the power-user surface; Strict is the procurement-friendly tier.

### Shipped (April–May 2026)

- ✅ Phase 1 — Web MVP: GitHub URL → CLAUDE.md (FastAPI `/api/scan`, React landing, Fly.io)
- ✅ Phase 2 — Free-tier quota + scan-usage tracking (`/v1/usage`); category breakdown surfaced on free tier
- ✅ Litestream HA on the license server (restore-on-start)
- ✅ AGENTS.md / Codex / CLAUDE.md exports + agent-neutral copy
- ✅ Strict tier (v0.6.0, 2026-05-17): fail-closed validation, seats, audit log, three Strict SKUs

### Current focus

- Distribution: r/ClaudeAI, r/cursor, r/LocalLLaMA, Show HN, X/Twitter, Substack
- One-time $29 deep web scan with audit report (Stripe Checkout + email delivery)
- GitHub OAuth + multi-repo dashboard + PR creation (push generated CLAUDE.md directly to repo)

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| Web UI alongside CLI | CLI alone has a low monetization ceiling; web enables Stripe gate + casual users |
| Strict as a distinct tier (not a Pro add-on) | Procurement-driven buyers expect a CI-grade SKU with fail-closed + audit; Pro stays cheap for individuals |
| One-time $29 before subscription on web | Lowest-friction first purchase; validates willingness to pay |
| Fly.io for both server + web | Consistent infra, single ops surface |
| Litestream over Fly volumes alone | SQLite + S3 replication gives point-in-time restore without leaving Fly |

### IP Notes
- Core generation algorithm (repo structure → CLAUDE.md schema) is proprietary
- Audit ruleset (anti-patterns, gap detection) is proprietary
- Source is Business Source License 1.1 (converts to MIT 4 years after each release per the BSL change date). Web/API layer remains closed pending the change date.

---

## Git Conventions

- Commit messages: Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)
- Branch naming: `feat/description`, `fix/description`
- Run tests before committing
