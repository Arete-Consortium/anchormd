# Release Runbook — anchormd

Reproducible steps to cut a release. The goal is that anyone (not just the
original maintainer's laptop) can ship the CLI and deploy the services.

## Components & how they ship

| Component | Target | Trigger |
|-----------|--------|---------|
| CLI (`anchormd`) | PyPI | GitHub Release published → `publish.yml` (OIDC trusted publishing) |
| License server | Fly.io `cmdf-license` | Push to `main` touching `license_server/**` → `deploy-license-server.yml` (approval gated) |
| Web app | Fly.io `anchormd-web` | Push to `main` touching `web/**` → `deploy-web.yml` (approval gated) |
| Landing page | GitHub Pages | Push to `main` touching `docs/**` → `pages.yml` |

## 1. Pre-flight (local)

```bash
.venv/bin/python -m pytest tests/ -v
ruff check src/ tests/ license_server/
ruff format --check src/ tests/ license_server/
mypy src/
```

All green before tagging. CI re-runs these on the PR; do not rely on CI alone.

## 2. Version bump

- Bump `version` in `pyproject.toml`.
- Update `CLAUDE.md` "Current State → Version" and the README badge.
- Commit on a `release/x.y.z` branch, open a PR, let CI + the AI Quality Gate
  pass, merge to `main`.

## 3. Publish the CLI

- Draft a GitHub Release with tag `vX.Y.Z` (conventional changelog in the body).
- Publishing the release triggers `publish.yml`, which builds and pushes to PyPI
  via OIDC. No API token is stored — the `pypi` environment provides identity.
- Verify: `pip index versions anchormd` (or install in a clean venv).

## 4. Deploy the services

Deploys run automatically on merge to `main` for the relevant paths, but pause
for approval on the `production` environment.

- Approve the **Deploy License Server** run (Actions → run → Review deployments)
  when `license_server/**` changed.
- Approve the **Deploy Web** run when `web/**` changed.
- Manual fallback (from project root):

  ```bash
  fly deploy --config license_server/fly.toml --dockerfile license_server/Dockerfile
  fly deploy --config fly.web.toml
  ```

## 5. Post-deploy verification

```bash
curl https://cmdf-license.fly.dev/v1/health    # license counts + 200 OK
```

- Smoke-test a web scan against the live `anchormd-web` URL.
- Confirm a test Stripe webhook still fulfills (staging/test-mode key) if the
  webhook or fulfillment path changed.

## Required secrets / config

| Secret | Where | Used by |
|--------|-------|---------|
| `FLY_API_TOKEN` | Repo secret | `deploy-*.yml` |
| `pypi` environment | Repo environment (OIDC) | `publish.yml` |
| `production` environment | Repo environment (add required reviewers) | `deploy-*.yml` approval gate |

## Rollback

- **Fly**: `fly releases --app <app>` then `fly deploy --image <previous>` or
  `fly releases rollback` (per app).
- **PyPI**: cannot delete/overwrite a version — yank with
  `pip` maintainers tooling and ship a fixed patch release.
