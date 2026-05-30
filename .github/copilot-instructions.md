# Copilot Instructions — anchormd

Start by reading `CLAUDE.md`; this repo has strict product and monetization constraints.

## Project Focus
- CLI + web tooling to generate/audit `CLAUDE.md` files.
- Python package in `src/anchormd`.
- License server in `license_server`.

## Guardrails
- Do not modify pricing/monetization flows unless explicitly requested.
- Keep CLI behavior backward-compatible where practical.
- Preserve API contract and webhook safety in license server routes.
- Never commit secrets or live credentials.

## Preferred Commands
- `python -m pip install -e ".[dev]"`
- `ruff check .`
- `ruff format .`
- `mypy src`
- `pytest -q`

## Validation Expectations
- Add/update tests for changed behavior.
- If touching licensing or Stripe webhook logic, include failure-path test coverage.
