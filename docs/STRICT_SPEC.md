# anchormd Strict — Enterprise/CI Tier Spec

**Status:** LOCKED — Day 1 begins on operator signal
**Spec mode:** specification (decision made, build it)
**Target ship:** 7 working days from kickoff
**Repo:** `~/projects/anchormd` v0.5.0 → v0.6.0
**Author:** ARETE
**Locked:** 2026-05-17

## Locked decisions

| # | Decision | Value |
|---|---|---|
| 1 | Pricing | **$49/seat/mo · $399/yr team-of-5 · $1,490/yr team-of-25** |
| 2 | Grandfather existing Pro customers? | **NO** — CI + drift move out of Pro at v0.6.0 launch for all subs, existing and new |
| 3 | Audit log retention on Strict | **1 year** |
| 4 | Launch order | **Strict (7d) → memboot Cloud (14d)** |

## Goal

Convert the existing `ANCHORMD_STRICT=1` security flag (one boolean in `licensing.py:255`) into a positioned **Enterprise/CI tier** above the current $8/mo Pro, sold on **fail-closed license validation + team licensing + audit trail**. The work is mostly wiring; the value is positioning.

## Non-goals

- Net-new generation/audit features (those continue on Pro roadmap)
- Modifying free or Pro pricing
- GitHub App build-out (separate spec; Strict ships without it)
- Adding new MCP/agent surface (memboot Cloud territory)

## User stories

1. **CI operator at a 50-dev shop**: "Our `anchormd audit` step has to fail-closed if the license server is unreachable. Pro fails open. We need Strict."
2. **Team lead**: "Five engineers, one license key gets shared via env var. I want five seats, one bill, an admin page to revoke."
3. **Security review at a regulated buyer**: "Show me the audit log for who ran what scan and when. No log = no purchase."
4. **Solo dev who never needs this**: Free + Pro unchanged in feel. No upsell pressure in the existing CLI.

## What already exists (don't rebuild)

| Component | Path | State |
|---|---|---|
| Strict-mode gate | `src/anchormd/licensing.py:255-265, 426-433` | Working — drops to FREE + `strict_refused: true` metadata |
| `@require_pro` / tier gating | `src/anchormd/gates.py:30-76` | Working — needs `@require_strict` sibling |
| License server | `license_server/` (Fly: `cmdf-license.fly.dev`) | Working — Litestream HA, Stripe webhooks, SMTP delivery |
| Stripe Payment Links | `scripts/stripe_setup.py` | Working — re-run with new prices |
| Machine-ID binding | `src/anchormd/machine_id.py` | Hostname+username hash — sufficient for seat binding |
| Telemetry | `src/anchormd/telemetry.py` | `track_pro_gate` exists — extend with `track_strict_event` |
| CI integration | `src/anchormd/ci.py` | Currently labeled Pro — re-label as Strict-only |
| Fleet command | `anchormd fleet [root]` | Already Pro — bump to Strict (JSON output + history) |
| Drift command | `src/anchormd/drift/` | Already Pro — bump to Strict (procurement story) |

## Tier matrix

| Feature | Free | Pro $8/mo | Strict $49/seat/mo |
|---|:---:|:---:|:---:|
| `generate`, `audit` | ✓ | ✓ | ✓ |
| `verify`, `harvest`, `patch` | ✓ | ✓ | ✓ |
| `init`, `diff`, premium presets | | ✓ | ✓ |
| `tech-debt`, `github-health`, `cleanup` | | ✓ | ✓ |
| Fail-closed license validation (`ANCHORMD_STRICT=1`) | | | ✓ |
| CI integration (`ci.py` PR comments) | | | ✓ (moved from Pro) |
| Drift detection (`drift/`) | | | ✓ (moved from Pro) |
| Fleet audit — JSON output + history | | | ✓ |
| Team seats (1 key → N machine-IDs) | | | ✓ |
| Audit log (every scan logged, 1yr retention, exportable) | | | ✓ |
| SLA: 99.5% license-server uptime | | | ✓ |

## Architecture changes

```
license_server/
├── routes/
│   ├── seats.py        # NEW — POST /v1/seats/claim, /seats/release, /seats/list
│   └── audit.py        # NEW — POST /v1/audit/log, GET /v1/audit/export
├── models.py           # +Seat, +AuditEvent
└── migrations/
    └── 003_seats_audit.sql  # NEW — seats table, audit_events table
src/anchormd/
├── licensing.py        # extend get_license_info() → Tier.STRICT
├── gates.py            # +require_strict() decorator
├── audit_logger.py     # NEW — fire-and-forget POST to /v1/audit/log
└── seats.py            # NEW — first-run binds machine_id to seat slot
```

`Tier` enum extended: `FREE | PRO | STRICT`.

## Implementation steps (7 days)

### Day 1 — Tier plumbing
- Add `Tier.STRICT` to `licensing.py`; update `TIER_DEFINITIONS` features list
- Add `@require_strict` decorator in `gates.py` (mirror of `require_pro`)
- Update `get_license_info()` to read `tier` from server response
- Re-gate `ci.py`, `drift/`, and `fleet` JSON output behind `@require_strict`
- Tests: 8 unit tests covering tier resolution edge cases

### Day 2 — License server: seats
- Migration `003_seats_audit.sql` — seats table (license_key, machine_id, claimed_at, last_seen_at)
- `routes/seats.py` — claim (insert if room, else 409), release (delete), list (admin)
- Server enforces seat cap from license metadata (`metadata.seats`)
- `validate.py` returns `seats_used`, `seats_total` in response
- Client `seats.py` claims a seat on first successful validation; cache claim 24h
- Tests: 6 server tests + 4 client tests

### Day 3 — Audit log
- Migration adds `audit_events` table (license_key, machine_id, event_type, command, repo, scanned_at, metadata JSON)
- `routes/audit.py` — `POST /v1/audit/log` (fire-and-forget, 5xx never blocks CLI), `GET /v1/audit/export` (CSV, admin Bearer)
- 1-year retention cron in license server (delete rows older than 365 days)
- Client `audit_logger.py` — async best-effort POST after every `generate`/`audit`/`scan`. Failure never blocks
- CLI flag `--no-audit` for paranoid environments
- Tests: 5 server + 3 client

### Day 4 — Stripe + email
- Run `scripts/stripe_setup.py` with new SKUs:
  - `STRICT_SEAT_MONTHLY` = $49/seat/mo
  - `STRICT_TEAM_5_ANNUAL` = $399/yr (5 seats)
  - `STRICT_TEAM_25_ANNUAL` = $1,490/yr (25 seats)
- Update `stripe_webhooks.py` to map new Stripe price IDs → `Tier.STRICT` with `seats` metadata
- New email template in `email_delivery.py` — Strict welcome (CI setup snippet, seat-management URL)
- **NEW: Pro downgrade email** — auto-fire to all active Pro subs on v0.6.0 launch day announcing CI + drift move to Strict (see §Customer comms below)
- Tests: 4 webhook tests with Strict price IDs

### Day 5 — Web frontend
- Landing page section: "Strict — for teams and CI" with three bullets
- `/strict` route with comparison table and Stripe Payment Link
- Update `/pricing` to show three tiers
- Screencast (~5 min): CI integration failing closed under network outage
- Tests: snapshot tests for new components

### Day 6 — Docs + launch surfaces
- `docs/strict.md` — full feature doc + CI setup recipes (GitHub Actions, GitLab, CircleCI)
- README block on Strict
- CHANGELOG `[0.6.0]` entry — must explicitly list the Pro tier change
- Substack draft: "We added a fail-closed license tier because Pro shouldn't be a CI fit"
- Show HN draft: "anchormd Strict: license validation that fails closed in CI"

### Day 7 — Ship + first-customer outreach
- Deploy server: `fly deploy --dockerfile license_server/Dockerfile --config license_server/fly.toml`
- Publish v0.6.0 to PyPI
- Send Pro downgrade comms email (see below)
- Post to r/ClaudeAI, r/cursor, Show HN
- Direct outreach: 10 GitHub repos that already use anchormd + appear to have CI (`gh search code anchormd path:.github/workflows`)

## Customer communications

**LOCKED 2026-05-17: hard cutover, no notice.** Operator accepted the chargeback risk explicitly.

- No T-7 email
- No 30-day trial
- CHANGELOG `[0.6.0]` entry will still explicitly list the Pro tier change (standard release-notes hygiene, not a comms campaign)
- No in-CLI deprecation notice — Pro license attempting CI/drift gets the standard `@require_strict` upgrade prompt on launch day

Stripe dispute exposure window: ~60 days from each Pro charge. If disputes spike, fall back to issuing refunds on request rather than fighting them.

## Acceptance criteria (binary, testable)

1. `ANCHORMD_LICENSE=<strict-key> anchormd audit ./CLAUDE.md` succeeds; `get_license_info().tier == Tier.STRICT`
2. With license server down and no cache + `ANCHORMD_STRICT=1`: CLI exits non-zero on any Pro/Strict command (regression test)
3. Five activations from five distinct machine-IDs against a 5-seat key succeed; sixth gets HTTP 409 "seat cap reached"
4. `POST /v1/audit/log` records an event; `GET /v1/audit/export` returns CSV with that row; rows older than 365 days are auto-deleted
5. Stripe checkout for `STRICT_TEAM_5_ANNUAL` triggers webhook → license generated with `metadata.seats=5` → welcome email sent
6. CI workflow on a public anchormd-using repo: license server unreachable → workflow fails → log shows `strict_refused: true`
7. Full test suite passes: target ≥420 tests. No mypy regressions.
8. Server-side: `/v1/health` returns 200 with `litestream_status` field
9. Pro downgrade email delivered to all active Pro subs ≥7 days before launch (or skipped per explicit operator override)

## Risks + mitigations

| Risk | Mitigation |
|---|---|
| Pro subs churn or chargeback on hard cutover | T-7 day comms email + 30-day Strict trial. If operator skips comms, accept brand risk explicitly |
| Audit log SQLite write contention | Litestream is on; SQLite WAL handles it; cap audit POSTs to 30/min via existing `rate_limit.py` |
| 7-day window slips against swing shift + FDE pipeline | If Day 4 slips, ship Day 1-3 as v0.5.5 ("Strict beta — fail-closed only") and complete seats/audit in v0.6.0 |
| First-customer count is zero in 30 days | Strict is sold on CI/procurement; cycle is longer than self-serve Pro. 90-day target = 3 paying teams, not 30 |
| Stripe disputes from no-grandfather move | Comms email + 30d trial + clear CHANGELOG reduce dispute likelihood. Document refund policy: 30d full refund on Pro if customer formally objects to Strict move |

## Out of scope (deferred to later versions)

- GitHub App (OAuth-based seat assignment) — v0.7.0
- SSO/SAML for Enterprise contracts — v1.0.0
- Slack/Discord audit-log webhooks — v0.7.0
- Per-repo policy bundles (Strict + ruleset.yml) — v0.7.0
- Self-hosted license server option — Enterprise-tier contract only, not in this release
