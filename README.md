# AnchorMD

> Generate optimized CLAUDE.md files for AI coding agents in seconds.

Stop hand-rolling CLAUDE.md. Let Forge analyze your codebase and generate
a production-grade configuration file that makes Claude Code, Cursor,
Windsurf, Codex, and OpenCode actually understand your project.

## Why?

AI coding agents are only as good as the context you give them. A well-crafted
CLAUDE.md is the difference between an agent that writes idiomatic code and one
that fights your conventions on every change.

AnchorMD:
- **Scans** your codebase to detect languages, frameworks, and patterns
- **Generates** a complete CLAUDE.md with coding standards, commands, and anti-patterns
- **Audits** existing CLAUDE.md files and scores them against best practices
- **Framework-aware** presets for React, FastAPI, Rust, Django, Next.js, and more

## Install

```bash
pip install anchormd
```

## Quick Start

```bash
# Generate a CLAUDE.md for your project
anchormd generate .

# Audit an existing CLAUDE.md
anchormd audit ./CLAUDE.md

# Interactive setup
anchormd init .

# See what would change
anchormd diff .

# List available presets
anchormd presets

# List framework-specific presets
anchormd frameworks
```

## Example Output

Running `anchormd generate .` on a FastAPI project produces:

```markdown
# CLAUDE.md — my-api

## Project Overview
my-api — FastAPI service for account and billing workflows.

## Current State
- **Version**: 0.4.0
- **Language**: Python
- **Files**: 47 across 2 languages
- **Lines**: 3,204

## Tech Stack
- **Language**: Python
- **Framework**: fastapi
- **Package Manager**: pip
- **Linters**: ruff
- **Test Frameworks**: pytest
- **CI/CD**: GitHub Actions

## Coding Standards
- **Naming**: snake_case
- **Type Hints**: present
- **Docstrings**: google style
- **Imports**: absolute

## Common Commands
...

## Anti-Patterns (Do NOT Do)
- Do NOT use synchronous database calls in async endpoints
- Do NOT return raw dicts — use Pydantic response models
- Do NOT use `os.path` — use `pathlib.Path` everywhere
...
```

## GitHub Action

Add automated CLAUDE.md auditing to your CI pipeline:

```yaml
# .github/workflows/claudemd-audit.yml
name: Audit CLAUDE.md
on: [pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/checkout@v6
      - uses: Arete-Consortium/anchormd@v0.5.0
        with:
          fail-below: 40     # Minimum passing score (0-100)
          comment: true       # Post results as PR comment
```

The action posts a formatted comment on your PR with score, findings, and recommendations.

## Free vs Pro vs Strict

| Feature | Free | Pro $8/mo | Strict $49/seat/mo |
|---------|:----:|:---------:|:------------------:|
| `generate` — scan and produce CLAUDE.md | Yes | Yes | Yes |
| `audit` — score existing CLAUDE.md | Yes | Yes | Yes |
| `verify`, `harvest`, `patch` | Yes | Yes | Yes |
| 11 community presets | Yes | Yes | Yes |
| `init` — interactive setup | - | Yes | Yes |
| `diff` — detect drift | - | Yes | Yes |
| 6 premium presets | - | Yes | Yes |
| `tech-debt`, `github-health`, `cleanup` | - | Yes | Yes |
| Fail-closed validation (`ANCHORMD_STRICT=1`) | - | - | Yes |
| CI integration (PR comment automation) | - | - | Yes |
| Drift detection (`generate`, `fix`, LLM judge, HTML) | - | - | Yes |
| Fleet audit `--json` + history | - | - | Yes |
| Team seats (one key → N machines) | - | - | Yes |
| Audit log (1yr retention, CSV/JSON export) | - | - | Yes |
| 99.5% license server SLA | - | - | Yes |

**Get Pro:** [Monthly ($8/mo)](https://buy.stripe.com/dRm6oH0KD64P9xq13VgrS00) | [Yearly ($69/yr)](https://buy.stripe.com/00w00j64X2SDaBu5kbgrS01)

**Get Strict** (for CI / teams / procurement-driven buyers): visit [anchormd.dev/?page=strict](https://anchormd.dev/?page=strict) — Seat Monthly $49/seat, Team-5 Annual $399, Team-25 Annual $1,490. Full feature documentation: [docs/strict.md](docs/strict.md).

**All 5 Tools Bundle:** [Monthly ($29/mo)](https://buy.stripe.com/7sY9AT9h90Kv5ha27ZgrS0a) | [Yearly ($199/yr)](https://buy.stripe.com/9B6fZh9h98cX24YfYPgrS0b) — includes anchormd, agent-lint, ai-spend, promptctl, context-hygiene

**Activate:**
```bash
export ANCHORMD_LICENSE=ANMD-XXXX-XXXX-XXXX
```

> **Breaking in v0.6.0**: `ci_integration` and advanced drift commands (`drift generate`, `drift fix`, `drift report --ci`, `drift report --html`, `--judge-model`) moved from Pro to Strict. Existing Pro subscribers on those features should subscribe to Strict or pin `anchormd==0.5.0`. See [CHANGELOG](CHANGELOG.md#060---2026-05-17) for the migration guide.

### Strict Mode (CI / Unattended)

`anchormd` fails open by default: if the license server is unreachable and no cache exists, a valid-format key grants Pro so a transient network blip does not break a working install. Strict subscribers can set `ANCHORMD_STRICT=1` to reverse that — any validation failure (missing key, server unreachable with no cache, revoked or expired key) exits non-zero instead of degrading.

```bash
export ANCHORMD_LICENSE=ANMD-XXXX-XXXX-XXXX
export ANCHORMD_STRICT=1
```

Recommended for CI jobs, release pipelines, and any unattended run where silent unlicensed fallback is worse than a hard fail. See [docs/strict.md](docs/strict.md) for CI recipes (GitHub Actions, GitLab, CircleCI).

## Framework Presets

| Preset | Description |
|--------|-------------|
| `python-fastapi` | FastAPI + async patterns |
| `python-cli` | Python CLI with typer/click |
| `react-typescript` | React + TypeScript + hooks |
| `nextjs` | Next.js App Router conventions |
| `django` | Django with ORM patterns |
| `rust` | Rust with clippy + proper error handling |
| `go` | Go with standard project layout |
| `node-express` | Express.js backend |

## Audit Scoring

Forge scores your CLAUDE.md on:
- **Section coverage** — does it have the essentials?
- **Accuracy** — does it match your actual codebase?
- **Specificity** — are instructions actionable or vague?
- **Anti-patterns** — does it prevent common mistakes?
- **Freshness** — is it up to date?

## Development

```bash
# Clone and install
git clone https://github.com/Arete-Consortium/anchormd.git
cd anchormd
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

## Community

[Discord](https://discord.gg/fdzQkrt8) — Join the community

## License

Business Source License 1.1 (BSL-1.1). See [`LICENSE`](LICENSE) for terms and the MIT change date.
