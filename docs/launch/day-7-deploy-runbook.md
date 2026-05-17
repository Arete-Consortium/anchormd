# Day 7 Deploy Runbook — anchormd v0.6.0 + Strict launch

**Author:** ARETE
**Purpose:** Step-by-step runbook for the non-reversible launch day. Each step has expected output and a rollback procedure.
**Estimated wall time:** 90–120 minutes if everything goes well; budget 3 hours.
**Pre-condition:** Last commit on `origin/main` is `5758f97` or later. All 811 tests passing.

> **Stop reading and DO NOT START** if any of these are true:
> - You are inside the 60-minute window after a Fly.io status incident
> - You have a meeting / call / interview in the next 3 hours
> - You have not had food and water in the last 2 hours
>
> This is irreversible work. Do it tired or distracted and you will spend the next week unwinding it.

---

## Phase 0 — Pre-flight verification (5 min)

Confirm the launch state before doing anything irreversible.

```bash
cd ~/projects/anchormd

# Make flyctl reachable (installed at ~/.fly/bin/flyctl, not in default PATH).
export PATH="$HOME/.fly/bin:$PATH"

# Confirm clean working tree, on main, in sync with origin.
git status --short --branch
# EXPECTED: "## main...origin/main" with no listed files
# IF NOT: stash or commit local changes before continuing

# Confirm last commit is at least Day 6 + runbook
git log --oneline -2
# EXPECTED: dad8844 docs(launch): Day 7 deploy runbook …
#           5758f97 docs: launch surfaces for v0.6.0 — Day 6 of v0.6.0

# Confirm test suite green
.venv/bin/python -m pytest tests/ -q | tail -3
# EXPECTED: 811 passed (or more if you added during prep)

# Confirm version is still 0.5.0 in BOTH places (you'll bump them in Phase 6)
grep '^version' pyproject.toml
grep '__version__' src/anchormd/__init__.py
# EXPECTED:
#   version = "0.5.0"
#   __version__ = "0.5.0"

# Confirm Fly auth — REQUIRED, the access token expires periodically
flyctl auth whoami
# EXPECTED: your fly account email
# IF "no access token available": run `flyctl auth login`, then retry

# Confirm license server project is reachable
flyctl status --config license_server/fly.toml
# EXPECTED: machines healthy, latest deploy timestamp visible

# Confirm PyPI credentials are ready for Phase 7
# Modern PyPI requires an API token, NOT password auth.
# Have these ready as env vars (do not commit them):
#   TWINE_USERNAME=__token__
#   TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcCJ...  (your pypi.org API token)
# If you don't have a token: pypi.org → Account → API tokens → Add token
# (scope to "anchormd" project only, not account-wide)

# Confirm build + twine are installed in .venv (NOT default deps)
.venv/bin/python -m build --version 2>/dev/null || .venv/bin/pip install build twine
# EXPECTED: build N.N.N (CPython ...)
```

If any of these fail: STOP. Fix it before proceeding.

---

## Phase 1 — Deploy license server to Fly.io (15 min)

This applies migrations `005_seats.sql` and `006_audit_events.sql` to production.

```bash
cd ~/projects/anchormd

flyctl deploy \
  --dockerfile license_server/Dockerfile \
  --config license_server/fly.toml
```

**EXPECTED OUTPUT:**
```
==> Verifying app config
==> Building image
...
--> Image: registry.fly.io/cmdf-license:deployment-XXXXXX
==> Creating release
--> release v<N> created
==> Monitoring deployment
v<N> deployed successfully
```

**Smoke test:**
```bash
# Health check
curl -sS https://cmdf-license.fly.dev/v1/health | jq .
# EXPECTED: {"status":"ok","version":"...","total_licenses":<N>,"active_licenses":<N>}

# Verify migrations ran — query one of YOUR OWN existing Pro license keys
# (do NOT use the literal ANMD-XXXX-XXXX-XXXX placeholder — pull from
# 1Password / your ~/.config/anchormd/license / your Stripe-receipt email)
MY_KEY="ANMD-..."  # ← substitute your real Pro license key here
curl -sS -X POST https://cmdf-license.fly.dev/v1/validate \
  -H "Content-Type: application/json" \
  -d "{\"license_key\":\"$MY_KEY\"}" | jq .
# EXPECTED: response includes seats_used and seats_total fields
#           (both null on legacy Pro keys — proves the schema migration ran)
```

**ROLLBACK:**
```bash
# If migrations failed or the server returns 500:
flyctl releases --config license_server/fly.toml
flyctl deploy --image registry.fly.io/cmdf-license:deployment-<PREVIOUS_SHA> \
  --config license_server/fly.toml
# Then: investigate Sentry / fly logs to understand the failure
```

The migrations are **additive only** (CREATE TABLE IF NOT EXISTS). They cannot corrupt existing data. If a previous-version client hits the new server, the seats/audit fields simply go ignored.

---

## Phase 2 — Stripe test-mode setup (20 min)

Generate test Payment Links before touching live mode.

```bash
# Confirm you have the TEST key, not the live key
echo "$STRIPE_SECRET_KEY" | head -c 10
# EXPECTED: sk_test_...
# IF sk_live_: STOP, source the test key first

cd ~/projects/anchormd
python scripts/stripe_setup.py 2>&1 | tee /tmp/stripe-test-output.txt
```

**EXPECTED:** stdout printed at end of run:
```
── Payment Links ──
AnchorMD Pro Monthly:    https://buy.stripe.com/...
AnchorMD Pro Yearly:     https://buy.stripe.com/...
Bundle Monthly ($29):    https://buy.stripe.com/...
Bundle Yearly ($199):    https://buy.stripe.com/...
Strict Seat Monthly:     https://buy.stripe.com/test_XXXXX
Strict Team-5 Annual:    https://buy.stripe.com/test_XXXXX
Strict Team-25 Annual:   https://buy.stripe.com/test_XXXXX
```

> WARNING: This script is **non-idempotent**. Each run creates new Stripe products. If you accidentally run it twice you'll have duplicate products. Run once per environment.

**Capture the three Strict test URLs in a scratch file:**

```bash
grep 'Strict' /tmp/stripe-test-output.txt > /tmp/strict-test-urls.txt
cat /tmp/strict-test-urls.txt
```

---

## Phase 3 — Substitute test URLs into web pages (10 min)

Edit `web/frontend/src/StrictPage.jsx` and `web/frontend/src/PricingPage.jsx` to replace the placeholder URLs with the test URLs from Phase 2.

Files to edit:
1. `web/frontend/src/StrictPage.jsx` — top of file, three constants:
   - `STRICT_SEAT_MONTHLY_URL`
   - `STRICT_TEAM_5_URL`
   - `STRICT_TEAM_25_URL`
2. `web/frontend/src/PricingPage.jsx` — top of file, four constants:
   - `PRO_MONTHLY_URL` (use the Pro Monthly link from Phase 2 stdout — already live, but the script may have generated a new test one)
   - `PRO_YEARLY_URL`
   - `STRICT_SEAT_MONTHLY_URL`
   - `STRICT_TEAM_5_URL`

**Verify the substitution by building locally:**

```bash
cd ~/projects/anchormd/web/frontend
npm run build 2>&1 | tail -10
# EXPECTED: ✓ built in ~1s, no errors
```

**Commit but do NOT push yet** (test smoke test goes first):

```bash
cd ~/projects/anchormd
git add web/frontend/src/StrictPage.jsx web/frontend/src/PricingPage.jsx
git commit -m "chore(web): substitute Stripe test Payment Link URLs"
```

---

## Phase 4 — Webhook smoke test ($0.50) (20 min)

Make a $0.50 test purchase to confirm the entire pipeline works end-to-end before flipping to live mode.

First, deploy the web with test URLs:

```bash
cd ~/projects/anchormd
git push origin main
# Vercel auto-deploys from main. Watch for the green check.
gh run watch
# Or visit https://vercel.com/<your-team>/anchormd-web/deployments
```

Once Vercel green:

```bash
cd ~/projects/anchormd
git push origin main
# Vercel auto-deploys from main. Vercel deploys are NOT visible in `gh run` —
# watch them at https://vercel.com/<your-team>/anchormd-web/deployments
# or via the Vercel CLI: `vercel ls anchormd-web` if you have it linked.
#
# The Fly anchormd-web backend does NOT need to redeploy for this launch —
# StrictPage / PricingPage are static frontend changes proxied by Vercel.
```

Once Vercel shows green for the latest commit:

```bash
# Visit anchormd.dev/?page=strict in browser (NOT localhost — you want
# to exercise the real Vercel → Stripe → Fly path)
# Click "Subscribe" on the Team-5 Annual card
# Stripe checkout opens (test mode banner visible)
# Use Stripe test card: 4242 4242 4242 4242, any future expiry, any CVC
# Email: yourname+stripe-test@gmail.com  (Gmail "+" alias trick — works for
#        Gmail and many other providers. If yours doesn't support +, use a
#        second mailbox.)
# Complete checkout
```

**Verify the webhook fired:**

```bash
# Check Fly logs for the webhook handler
flyctl logs --config license_server/fly.toml | grep -E "stripe|license|strict" | head -20
# EXPECTED: "License created for yourname+stripe-test@gmail.com (product=anchormd, tier=strict)"
# EXPECTED: "Strict license emailed to yourname+stripe-test@gmail.com (5 seats)"

# Check your email — should have a Strict welcome email with:
# - subject: "Your AnchorMD Strict License — 5 seats"
# - body containing your test ANMD-XXXX-XXXX-XXXX license key
# - GitHub Actions snippet with ANCHORMD_STRICT="1"
```

**Verify the license works:**

```bash
export ANCHORMD_LICENSE="ANMD-XXXX-XXXX-XXXX"  # from your test email
export ANCHORMD_LICENSE_SERVER="https://cmdf-license.fly.dev"
.venv/bin/anchormd status
# EXPECTED: Tier: Strict (cyan border), 5 seats total
```

**Verify seat claim fires:**

```bash
# Wipe local seat cache to force a fresh claim
rm -f ~/.anchormd/seat_claim.json
.venv/bin/anchormd audit ./CLAUDE.md
# EXPECTED: command runs, no errors
# Then check the server:
curl -sS https://cmdf-license.fly.dev/v1/validate \
  -X POST -H "Content-Type: application/json" \
  -d "{\"license_key\":\"$ANCHORMD_LICENSE\"}" | jq .
# EXPECTED: seats_used=1, seats_total=5
```

**Verify audit log entry:**

```bash
# Admin export
curl -sS -H "Authorization: Bearer $ANMD_ADMIN_SECRET" \
  "https://cmdf-license.fly.dev/v1/audit/export?license_key=$ANCHORMD_LICENSE&format=json" | jq .
# EXPECTED: events array with at least one entry (the audit command you just ran)
```

If ANY of these fail: **STOP. Do not proceed to live mode.** Debug, fix, redeploy, retest.

**No refund needed for the $0.50 test charge.** Stripe test-mode "charges" never settle to real money. The test transaction sits in the Stripe dashboard with a "Test mode" banner. When you flip to live mode in Phase 5, the test products and test transactions remain visible but are clearly separated by the toggle in the Stripe UI. For your future actual launch reference: in *live* mode, you would refund a $0.50 smoke test via Payments → Refund.

---

## Phase 5 — Stripe LIVE mode (15 min)

> WARNING: This is the irreversible step. Live Stripe products cannot be cleanly deleted once they have been associated with even one customer.

```bash
# Source the LIVE Stripe secret key
export STRIPE_SECRET_KEY="sk_live_..."

# Confirm live mode
echo "$STRIPE_SECRET_KEY" | head -c 10
# EXPECTED: sk_live_...

cd ~/projects/anchormd
python scripts/stripe_setup.py --live 2>&1 | tee /tmp/stripe-live-output.txt
```

The script enforces `--live` for live keys — this is the secondary safety check.

**Capture the live URLs:**

```bash
grep 'Strict' /tmp/stripe-live-output.txt > /tmp/strict-live-urls.txt
cat /tmp/strict-live-urls.txt
```

---

## Phase 6 — Substitute live URLs + version bump + commit (10 min)

```bash
# Substitute live URLs the same way as Phase 3
# Edit StrictPage.jsx and PricingPage.jsx with the LIVE buy.stripe.com URLs
# (not test_XXXXX)

# Bump version in BOTH places — pyproject.toml AND src/anchormd/__init__.py
# Both must match or `anchormd --version` will lie about the wheel contents.
sed -i 's/^version = "0.5.0"/version = "0.6.0"/' pyproject.toml
sed -i 's/__version__ = "0.5.0"/__version__ = "0.6.0"/' src/anchormd/__init__.py
# Verify both bumped
grep '^version' pyproject.toml
grep '__version__' src/anchormd/__init__.py
# EXPECTED: both show 0.6.0

# Verify build
cd ~/projects/anchormd/web/frontend
npm run build 2>&1 | tail -5
cd ~/projects/anchormd
.venv/bin/python -m pytest tests/ -q | tail -3
# EXPECTED: 811 passed (no test changes from earlier)

# Commit
git add web/frontend/src/StrictPage.jsx web/frontend/src/PricingPage.jsx \
  pyproject.toml src/anchormd/__init__.py
git commit -m "release: v0.6.0 — Strict tier live"

git tag -a v0.6.0 -m "v0.6.0 — Strict tier"

# Push main FIRST, then the tag — order matters because GitHub validates the
# tag's commit exists on the branch.
git push origin main
git push origin v0.6.0

# Vercel auto-deploys from the main push.
```

After pushing the tag, the draft release at
<https://github.com/Arete-Consortium/anchormd/releases> automatically
associates with tag `v0.6.0`. To publish:

```bash
gh release edit v0.6.0 --draft=false
# OR via the web UI: open the release, click "Publish release"
# (the button is direct — no Edit-then-Publish two-step needed)
```

---

## Phase 7 — PyPI publish (10 min)

```bash
cd ~/projects/anchormd

# Clean any old build artifacts.
# `rm` is aliased to a `trash` reminder in your shell, so use `trash` directly
# (or invoke real rm via `\rm -rf`). Both work.
trash dist build 2>/dev/null
trash $(find . -maxdepth 2 -name "*.egg-info" -type d) 2>/dev/null

# Build
.venv/bin/python -m build
# EXPECTED: dist/anchormd-0.6.0-py3-none-any.whl and dist/anchormd-0.6.0.tar.gz
# IF "No module named 'build'": run `.venv/bin/pip install build twine` first

# Verify the wheel installs cleanly in a fresh venv (catches missing manifest
# files, broken entry points, etc. BEFORE the upload makes them permanent)
python -m venv /tmp/anchormd-verify
/tmp/anchormd-verify/bin/pip install dist/anchormd-0.6.0-py3-none-any.whl
/tmp/anchormd-verify/bin/anchormd --version
# EXPECTED: anchormd 0.6.0
# IF version reads 0.5.0: STOP — the __init__.py bump in Phase 6 didn't land.
# Re-do Phase 6, rebuild, re-test.

# Upload to PyPI — credentials come from env vars set in Phase 0:
#   TWINE_USERNAME=__token__
#   TWINE_PASSWORD=pypi-...
.venv/bin/twine upload dist/*
# EXPECTED: "Uploading dist/anchormd-0.6.0-py3-none-any.whl"
#           "Uploading dist/anchormd-0.6.0.tar.gz"
#           "View at: https://pypi.org/project/anchormd/0.6.0/"
```

**Verify PyPI:**

```bash
# PyPI CDN propagation is usually 1-5 minutes. Don't panic if the first
# `pip install` doesn't see it instantly.
sleep 120
pip index versions anchormd 2>&1 | head -3
# EXPECTED: lists 0.6.0 (may need to wait longer if it doesn't appear)

# Once visible, install in a fresh venv to confirm end-to-end:
python -m venv /tmp/anchormd-pypi
/tmp/anchormd-pypi/bin/pip install --upgrade anchormd
/tmp/anchormd-pypi/bin/anchormd --version
# EXPECTED: anchormd 0.6.0
```

**If twine fails with `403 Invalid or non-existent authentication`:**
- Token might be account-scoped instead of project-scoped — PyPI accepts both, but check the token is for "anchormd" or all projects.
- Token might have been rotated. Generate a fresh one at pypi.org/manage/account/token/.

**If twine fails with `400 Filename has already been used`:**
- A previous partial upload of v0.6.0 succeeded. PyPI never allows re-uploading the same filename. Bump to v0.6.1, retag, and retry. (This is why the wheel-install verification step exists — to catch problems before uploading.)

---

## Phase 8 — Post-launch monitoring (1 hour active, 24 hour passive)

**Immediate (next 60 minutes):**

- [ ] Watch `flyctl logs --config license_server/fly.toml` for the first real Strict purchase
- [ ] Watch Stripe dashboard for any failed checkouts (declined cards, abandoned carts)
- [ ] Refresh `https://cmdf-license.fly.dev/v1/health` every 15 min — verify uptime
- [ ] Refresh `https://anchormd.dev/?page=strict` — verify page renders, Subscribe buttons go to live Stripe

**Show HN posting:**

If launch time is Tue/Wed morning Pacific (best HN engagement window):
- Open `docs/launch/show-hn-strict.md` in editor
- Run `/content-scrubber` on the body
- Copy the scrubbed body verbatim into HN's submission form
- Title: use option 1 ("Show HN: anchormd Strict – license validation that fails closed in CI")
- URL: `https://anchormd.dev/?page=strict`
- Submit
- Reply to every comment within 4 hours for the first 12 hours

If launch time is wrong window (Fri/Sat/Sun, or right after a major model release):
- HOLD the Show HN post until next Tue/Wed AM PT
- The deploy is done. Show HN can wait.

**Substack post:**

- Open `substack-drafts/2026-05-anchormd-strict-fail-closed.md` in editor
- Run `/content-scrubber` on the post body (NOT the frontmatter)
- Copy into Substack editor, schedule for Wednesday 9am PT for max engagement
- Tag: AI infrastructure, indie developer, SaaS

**Stripe dispute watch:**

This is the no-grandfather risk. Check the Stripe dashboard Disputes tab:
- T+24 hours: zero disputes expected (Pro subs may not have run their CI yet)
- T+1 week: any disputes likely surface here as Pro subs hit their first failed CI run
- T+30 days: dispute window closes for the most recent charge
- T+60 days: full dispute window closes for all pre-launch charges

If disputes appear:
1. Don't fight them. The refund offer is in the CHANGELOG.
2. Process the refund through Stripe (Customer → Refund).
3. Email the customer offering a complimentary 30-day Strict trial as a goodwill gesture.

---

## Rollback procedures (per phase)

| Phase | Failure mode | Rollback |
|---|---|---|
| 0 | flyctl auth expired | `flyctl auth login`, then retry. |
| 0 | `build` / `twine` missing | `.venv/bin/pip install build twine`. Note: NOT in dev deps because PyPI publishing is operator-only, not CI. |
| 0 | PyPI token missing | Generate at pypi.org/manage/account/token/, set `TWINE_USERNAME=__token__` + `TWINE_PASSWORD=pypi-...`. |
| 1 | Migration failed | Roll back Fly release to previous SHA. Migrations are additive (CREATE TABLE IF NOT EXISTS), so partial application is safe; full rollback restores prior schema. |
| 2 | Stripe script crashed mid-run | Inspect Stripe dashboard for partially-created products; manually **archive** (not delete) any orphans before retry. Stripe products with any customer history cannot be deleted. |
| 3 | Web build failed | Revert the StrictPage/PricingPage commit. Site stays on Day 6 state. |
| 4 | Webhook test failed | Do not proceed to Phase 5. Fix the webhook handler, redeploy Fly, retry. Common: webhook signing secret stale after Fly env var rotation. |
| 5 | Live Stripe script crashed | Same as Phase 2 rollback. Manually archive orphans. |
| 6 | Version mismatch between pyproject.toml and __init__.py | Wheel-install in Phase 7 catches this. Fix the missed bump, re-commit, re-tag (delete + recreate the tag locally + force-push if not yet pushed). |
| 6 | Version bump push failed | Investigate (likely CI failed on the release commit). Revert if necessary. |
| 7 | PyPI upload failed (auth) | See troubleshooting block in Phase 7. |
| 7 | PyPI upload failed (filename used) | Bump to v0.6.1, retag, retry. PyPI never allows re-uploading the same filename. |
| 8 | Show HN post deleted by moderator | Wait 24 hours, repost with adjusted title. |

---

## Acceptance criteria — Day 7 complete when

- [ ] `cmdf-license.fly.dev/v1/health` returns 200 with migrations 005 + 006 applied
- [ ] 3 live Stripe Strict Payment Links exist and route to live Stripe checkout
- [ ] `anchormd.dev/?page=strict` loads with working Subscribe buttons
- [ ] `pip install anchormd==0.6.0` succeeds and the binary reports v0.6.0
- [ ] One $0.50 test purchase has completed the full pipeline (Stripe → webhook → license created → email sent → CLI activates → seat claimed → audit log entry created)
- [ ] Show HN posted (or scheduled for next Tue/Wed AM PT)
- [ ] Substack post scheduled (or posted)
- [ ] Stripe dispute monitoring cadence set on calendar (check daily for 7 days, then weekly for 60)

---

## What I (the assistant) need from you AFTER Day 7

- **The actual Stripe live URLs.** Send them back to me and I'll prep the substack-draft scrubbing pass with concrete CTAs.
- **First customer signal.** When the first paying Strict customer activates, that is the data point that validates the wedge.
- **Any Pro chargebacks.** I'll help you draft refund-with-goodwill emails if needed.
- **First Show HN front-page if it happens.** I'll help you prep follow-up posts that capitalize on the traffic spike.

If a critical step breaks and you need help debugging, paste the error and the phase number. I can read Fly logs, Stripe dashboard exports, or PyPI errors and triage from those.

---

**Last reminder before you start:** this runbook is your future self's memory. If you finish a phase and have to walk away, mark it complete in this file before closing the laptop. Future-you will thank present-you.
