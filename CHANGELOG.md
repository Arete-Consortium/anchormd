# Changelog

All notable changes to anchormd are documented here. This project follows [Semantic Versioning](https://semver.org/).

## [0.6.0] - 2026-05-17

### Breaking changes for existing Pro subscribers

Two features that shipped under Pro in v0.5.x have moved to the new Strict tier in v0.6.0. **There is no grandfather period.** Pro subscribers on active subscriptions lose access to these features on the v0.6.0 release. Customers who depend on either feature should subscribe to Strict at <https://anchormd.dev/?page=strict>.

- `ci_integration` (PR-comment automation) — moved to Strict
- Advanced drift features — `drift generate`, `drift fix`, `drift report --ci`, `drift report --html`, and the `--judge-model` LLM judge path — moved to Strict
- `drift run` and `drift report` (terminal output) remain in Free
- `drift init`, `drift baseline`, `drift trend` remain free utility commands

Refund policy: 30-day full refund on Pro if a customer formally objects to this change.

### Added — Strict tier ($49/seat/mo · $399/yr team-5 · $1,490/yr team-25)

A new tier above Pro that targets CI environments and procurement-driven buyers. Strict is opt-in; Free and Pro continue to work as before for everyone else.

- **Fail-closed license validation** — `ANCHORMD_STRICT=1` env var. Any license-validation failure (server unreachable, key revoked, expired, no cache) exits the CLI non-zero instead of silently degrading to Free. The Pro fail-open behavior remains unchanged for Pro subscribers; Strict subscribers opt into fail-closed.
- **Team seats** — one license key supports N machine activations. Server enforces the cap at claim time (HTTP 409 over `seats_total`). Seat-Monthly Stripe Payment Link uses `adjustable_quantity` for flexible team sizing.
- **Audit log** — every Strict CLI invocation posts to `/v1/audit/log`. Server-side retention enforced at FastAPI lifespan startup; default 365 days. Admin export via `GET /v1/audit/export` in CSV (default) or JSON.
- **Fleet `--json` output + history** — moved from Pro to Strict.
- **CI integration + advanced drift detection** — moved from Pro to Strict (see breaking changes above).
- **Procurement footer** on `anchormd.dev/?page=strict` for MSA / DPA / SOC 2 / self-hosted inquiries.

### Added — client + server infrastructure

- `Tier.STRICT` enum + `TIER_DEFINITIONS[Tier.STRICT]` config in `src/anchormd/licensing.py`.
- `@require_strict` decorator in `src/anchormd/gates.py` mirroring `@require_pro`.
- `is_strict()` and `tier_at_least(Tier)` helpers.
- `track_strict_gate(feature)` telemetry sibling to `track_pro_gate`.
- `LicenseInfo.seats_used` / `LicenseInfo.seats_total` carried through the validation pipeline (server response → cache → expired cache).
- `src/anchormd/audit_logger.py` — fire-and-forget POST to `/v1/audit/log`. Honors `ANCHORMD_NO_AUDIT=1` opt-out. Strict-only: free/pro users skip the POST entirely (no overhead).
- `src/anchormd/seats.py` — `claim_seat_on_startup()` called once per successful Strict server validation. 24-hour on-disk cache prevents re-POSTing. 409 from the server logs a warning but does not block the CLI.
- License server: `/v1/seats/claim`, `/v1/seats/release`, `/v1/seats/list` (admin Bearer).
- License server: `/v1/audit/log`, `/v1/audit/export` (admin Bearer).
- Migrations `005_seats.sql` and `006_audit_events.sql`.
- `scripts/stripe_setup.py` extended with three Strict SKUs: Seat Monthly ($49/seat/mo, `adjustable_quantity`), Team-5 Annual ($399/yr), Team-25 Annual ($1,490/yr).
- `license_server/stripe_webhooks.py` — Strict checkout branch: extracts seat count from `metadata.seats` or line-item quantity, persists into license metadata, fires `send_strict_license_email` instead of the standard welcome.
- `license_server/email_delivery.py` — `send_strict_license_email` with CI setup snippet (GitHub Actions block), seat count, audit log mention.
- Web: `web/frontend/src/StrictPage.jsx` (hero, three feature bullets, 3 plan cards, GitHub Actions CI snippet, 11-row comparison table, procurement contact).
- Web: `web/frontend/src/PricingPage.jsx` (three-tier card grid, annual savings, 5-scenario decision flow).
- Web: `?page=strict` / `?page=pricing` URL routing; home callout linking to `?page=strict`; footer nav for Pricing + Strict-for-CI.

### Fixed

- Three pre-existing tier-display sites in `src/anchormd/cli.py` (`status`, `stats`, `license-info`) now route Strict subscribers to a cyan border + "Strict" label instead of falling back to "Pro" or "Free".
- Drift CLI upgrade messages route through `get_upgrade_message()` so the URL and price label reflect the actual gating tier (Strict for moved features).

### Infrastructure

- 49 new tests across `test_strict_tier.py` (18), `test_seats.py` (10), `test_audit.py` (7), `test_audit_logger.py` (6 with wire-up regressions), `test_seats_client.py` (11), `test_stripe_webhooks.py::TestCheckoutStrict` (5). Full suite: 811 passing (was 765 in v0.5.0).
- New documentation: `docs/strict.md`, `docs/STRICT_SPEC.md`.
- New launch surfaces: `substack-drafts/2026-05-anchormd-strict-fail-closed.md`, `docs/launch/show-hn-strict.md`.

### Changed

- Version bumped 0.5.0 → 0.6.0.

### Migration guide (for Pro subscribers)

If your CI workflow runs `anchormd audit --ci` or any `drift generate` / `drift fix` / `drift report --html` / `drift report --ci` / `drift --judge-model` command, your Pro license stops authorizing those commands on v0.6.0. The CLI exits with an upgrade prompt pointing at <https://anchormd.dev/?page=strict>. Options:

1. Subscribe to Strict (recommended for CI use). The license server preserves your existing subscription history; emailing `hello@anchormd.dev` from your Pro-on-file email gets you a 20% upgrade credit for the first year.
2. Pin your CI workflow to `anchormd==0.5.0` until you decide. The 0.5.x server-validation behavior remains supported via the legacy mapping path.
3. Cancel Pro and switch to Free for the commands that are still free.

If neither option fits and you formally object to this change in writing within 30 days of your most recent Pro charge, contact `hello@anchormd.dev` for a full refund on that charge.

## [0.5.0] - 2026-04-17

### Added
- `anchormd verify <CLAUDE.md>` — cross-checks claims against reality. Verifies file paths in architecture blocks, project version vs `pyproject.toml`/`package.json`, and dependencies vs the manifest. Complements `audit` (structure scoring) with a truth score.
- `anchormd fleet [root]` — walks a root directory for every `CLAUDE.md`, audits each in parallel, and emits a ranked report (lowest score first). Prunes heavy directories (`.venv`, `node_modules`, `.flatpak-builder`, etc.) during descent. Optional `--reality` for two-column scoring, `--min-score`, `--limit`, `--json`.
- `anchormd harvest [project]` — parses `~/.claude/projects/<slug>/*.jsonl` transcripts, extracts tool errors, normalizes them (strips paths/hex/numbers), and surfaces recurring gotchas by tool + signature. Reveals patterns like repeated Edit-before-Read failures or file-too-large Reads.
- `anchormd patch <CLAUDE.md>` — harvests gotchas and splices matching anti-patterns into the file's `## Anti-Patterns` section. Case-insensitive dedupe by bullet title, diff preview, `--dry-run` / `-y` flags.
- Gotcha → anti-pattern suggestion library (`analyzers/suggestions.py`) with rules for Edit/Write without Read, Read token-limit overflow, Edit on stale read, WebFetch status failures, `command not found`, `rm → trash` aliasing, and user-denied tool uses.
- `ANCHORMD_STRICT=1` — opt-in strict licensing mode that closes the fail-open path. Any validation failure (missing key, server unreachable with no cache, revoked or expired key) drops to Free and exits non-zero on Pro commands. Recommended for CI and unattended pipelines.
- `tech-debt --source-only` flag to restrict scanning to source directories, plus `--include-path` and `--exclude` filters for finer control over which files are audited.

### Changed
- Version bumped 0.4.1 → 0.5.0.
- CLAUDE.md updated to reflect the new command set and correct the `api/core/generator.py` → `web/generator.py` path.

### Infrastructure
- 19 new tests across `test_reality.py`, `test_harvest.py`, `test_suggestions.py`, `test_patcher.py`. Full suite: 374 passing.
