# AnchorMD Strict

A tier above Pro for CI environments, team licensing, and procurement-driven buyers.

Free and Pro continue to work as before. Strict is opt-in.

## When to subscribe to Strict

Subscribe to Strict if **any** of these match your environment:

1. **Your CI workflow runs `anchormd audit` or `anchormd drift`** and you need it to fail closed when the license server is unreachable. Pro silently degrades to Free under that condition. Strict refuses.
2. **You have a team and want one license to cover N machines** on one bill. Pro is single-seat by design.
3. **A security or procurement reviewer has asked who ran what scan and when.** Strict logs every CLI invocation server-side with 1-year retention and CSV/JSON export.
4. **You use drift detection in CI.** `drift generate`, `drift fix`, `drift report --ci`, `drift report --html`, and the `--judge-model` LLM judge path are Strict-only in v0.6.0+.
5. **You need the GitHub Action that auto-comments audit findings on PRs.** That CI integration is Strict-only in v0.6.0+.

If none of those apply, Pro at $8/mo is the right tier.

## Pricing

| SKU | Price | Seats |
|-----|-------|-------|
| Seat Monthly | $49 / seat / month | Adjustable 1-100 at checkout |
| Team-5 Annual | $399 / year | 5 seats |
| Team-25 Annual | $1,490 / year | 25 seats |

Subscribe at <https://anchormd.dev/?page=strict>.

For larger seat counts (50+), self-hosted license server, MSA, DPA, or SOC 2 inquiries: `strict@anchormd.dev`.

## Strict-only features

### 1. Fail-closed validation

Set `ANCHORMD_STRICT=1` to make any license-validation failure exit non-zero.

| Failure mode | Pro behavior | Strict behavior with `ANCHORMD_STRICT=1` |
|---|---|---|
| No license key configured | Free tier (silent) | Free tier + warning in logs |
| Server unreachable, no cache | Pro tier (fail-open) | Exit non-zero, `strict_refused: true` in metadata |
| License revoked | Free tier (silent) | Exit non-zero |
| License expired | Free tier (silent) | Exit non-zero |
| Server returns 5xx, expired cache exists | Cached Pro (degraded) | Cached Pro (degraded) — operator decision: degraded > broken |
| Server returns 5xx, no cache | Pro tier (fail-open) | Exit non-zero |

### 2. Team seats

One license key supports up to `seats_total` machine activations. The server tracks each `machine_id` that successfully validates and rejects new claims with HTTP 409 once the cap is reached.

The client auto-claims a seat on the first successful server validation per machine. Subsequent CLI invocations hit a 24-hour local cache. When the cap is reached, the client logs a warning but does not block — server validation remains valid for licensed machines, and the operator gets visibility into the overflow.

### 3. Audit log

Every Strict CLI invocation posts to `/v1/audit/log` (fire-and-forget, 2s timeout, never blocks the CLI). The server records: `license_id`, `machine_id`, `event_type`, `command`, `repo_fingerprint`, `metadata` JSON, `created_at`.

Retention: 365 days. Enforced at server startup by `prune_old_events()`.

Opt out per environment by setting `ANCHORMD_NO_AUDIT=1`. (Also opts out of the seat claim.)

Admin export:

```bash
# CSV (default)
curl -H "Authorization: Bearer $ANMD_ADMIN_SECRET" \
  "https://cmdf-license.fly.dev/v1/audit/export?license_key=ANMD-XXXX-XXXX-XXXX" \
  > audit.csv

# JSON
curl -H "Authorization: Bearer $ANMD_ADMIN_SECRET" \
  "https://cmdf-license.fly.dev/v1/audit/export?license_key=ANMD-XXXX-XXXX-XXXX&format=json"
```

### 4. Drift detection (advanced)

Strict-only drift commands and flags:

| Command | What it does |
|---|---|
| `anchormd drift generate --model <m>` | Generate benchmarks from a CLAUDE.md using a model |
| `anchormd drift fix --model <m>` | Suggest CLAUDE.md fixes for failing benchmarks |
| `anchormd drift run --judge-model <m>` | Use a second model as LLM judge for soft checks |
| `anchormd drift report --ci` | CI mode: exit non-zero on critical drift |
| `anchormd drift report --html report.html` | Write an HTML report |

`anchormd drift init`, `drift run`, `drift report` (terminal output), `drift baseline`, and `drift trend` remain in Free.

### 5. Fleet audit with JSON output + history

Strict adds `--json` output and persistent history to `anchormd fleet`. The basic terminal report remains in Free.

### 6. CI integration

The `anchormd ci-setup` command generates a GitHub Action workflow that auto-comments audit findings on pull requests. Moved from Pro to Strict in v0.6.0.

## Environment variables

| Variable | What |
|---|---|
| `ANCHORMD_LICENSE` | The license key (`ANMD-XXXX-XXXX-XXXX`). Required for Pro and Strict. |
| `ANCHORMD_LICENSE_SERVER` | Override the license-server URL. Defaults to `https://cmdf-license.fly.dev` in production builds. |
| `ANCHORMD_STRICT` | Set to `1` to enable fail-closed validation. Strict-only feature. |
| `ANCHORMD_NO_AUDIT` | Set to `1` to skip the audit-log POST and the seat-claim POST. For paranoid environments where outbound HTTPS to the license server is undesirable. |

## CI recipes

### GitHub Actions

```yaml
# .github/workflows/anchormd-audit.yml
name: Audit CLAUDE.md (anchormd Strict)

on:
  pull_request:
    paths:
      - "CLAUDE.md"
      - "src/**"
      - "pyproject.toml"

permissions:
  contents: read
  pull-requests: write

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install anchormd
        run: pip install anchormd

      - name: Audit CLAUDE.md
        env:
          ANCHORMD_LICENSE: ${{ secrets.ANCHORMD_LICENSE }}
          ANCHORMD_STRICT: "1"
        run: anchormd audit ./CLAUDE.md --fail-below 60
```

### GitLab CI

```yaml
# .gitlab-ci.yml
anchormd-audit:
  image: python:3.12
  variables:
    ANCHORMD_STRICT: "1"
  before_script:
    - pip install anchormd
  script:
    - anchormd audit ./CLAUDE.md --fail-below 60
  only:
    changes:
      - CLAUDE.md
      - src/**/*
      - pyproject.toml
```

Add `ANCHORMD_LICENSE` to your project's CI/CD variables (Settings → CI/CD → Variables, masked).

### CircleCI

```yaml
# .circleci/config.yml
version: 2.1

jobs:
  audit:
    docker:
      - image: cimg/python:3.12
    environment:
      ANCHORMD_STRICT: "1"
    steps:
      - checkout
      - run:
          name: Install anchormd
          command: pip install anchormd
      - run:
          name: Audit CLAUDE.md
          command: anchormd audit ./CLAUDE.md --fail-below 60

workflows:
  audit-on-pr:
    jobs:
      - audit:
          filters:
            branches:
              ignore: main
```

Add `ANCHORMD_LICENSE` as a context or project environment variable.

## API reference

### Seat management

```http
POST /v1/seats/claim
Content-Type: application/json

{"license_key": "ANMD-XXXX-XXXX-XXXX", "machine_id": "<machine-id>"}
```

Response:

```json
{
  "claimed": true,
  "seats_used": 3,
  "seats_total": 5,
  "machine_id": "<machine-id>",
  "license_key_masked": "ANMD-****-****-XXXX"
}
```

On `seats_used >= seats_total`: HTTP 409 with `detail: "Seat cap reached: 5/5. Release a seat or upgrade."`.

```http
POST /v1/seats/release
Content-Type: application/json

{"license_key": "ANMD-XXXX-XXXX-XXXX", "machine_id": "<machine-id>"}
```

Idempotent; releasing an unclaimed machine returns `released: false` without erroring.

```http
GET /v1/seats/list?license_key=ANMD-XXXX-XXXX-XXXX
Authorization: Bearer <admin-secret>
```

Admin-only. Returns all seats claimed under the license with `machine_id`, `claimed_at`, `last_seen_at`.

### Audit log

```http
POST /v1/audit/log
Content-Type: application/json

{
  "license_key": "ANMD-XXXX-XXXX-XXXX",
  "machine_id": "<machine-id>",
  "event_type": "scan",
  "command": "audit",
  "repo_fingerprint": "abc123",
  "metadata": {}
}
```

Fire-and-forget from the client perspective. Unknown licenses return HTTP 404 so the client can stop retrying. Network errors are swallowed and never propagate.

```http
GET /v1/audit/export?license_key=...&format=csv
Authorization: Bearer <admin-secret>
```

`format=csv` (default) or `format=json`. CSV is `attachment; filename="audit_<masked>.csv"`.

## FAQ

**Q. Does the audit log work if my network is air-gapped?**

No. The audit log is server-side. If you have no outbound HTTPS to `cmdf-license.fly.dev`, set `ANCHORMD_NO_AUDIT=1` and audit posts will be silently skipped. The CLI keeps working.

**Q. What happens to my Pro subscription when v0.6.0 ships?**

`init`, `diff`, premium presets, `tech-debt`, `github-health`, `cleanup`, basic drift commands, and basic fleet are unchanged. `ci_integration`, `drift generate`, `drift fix`, `drift report --ci`, `drift report --html`, and `drift --judge-model` move to Strict. There is no grandfather period. See the [CHANGELOG](../CHANGELOG.md#060---2026-05-17) migration guide.

**Q. Can I host the license server myself?**

The license server (FastAPI + SQLite + Litestream) is in `license_server/` of the source repo. The current license model is built around the hosted instance at `cmdf-license.fly.dev`. Self-hosted is available under an Enterprise contract — contact `strict@anchormd.dev`.

**Q. Is the audit log encrypted at rest?**

The license server's SQLite database is replicated to a private Litestream destination. The database itself is not encrypted at rest. If your compliance regime requires at-rest encryption, contact `strict@anchormd.dev` for a self-hosted deployment with SQLCipher.

**Q. What's the SLA?**

99.5% monthly uptime on `cmdf-license.fly.dev`. Status published at `cmdf-license.fly.dev/v1/health`. Outages > 1 hour notified via the email on file for the license.
