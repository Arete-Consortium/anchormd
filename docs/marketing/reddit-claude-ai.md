# r/ClaudeAI Post Draft

**Title:** I built a tool that generates CLAUDE.md files for any GitHub repo — paste a URL, get a context file in 30 seconds

**Body:**

I've been using Claude Code daily for months and noticed the same problem: CLAUDE.md files are either missing, outdated, or poorly written. So I built **anchormd** — a tool that scans any codebase and generates a complete CLAUDE.md automatically.

**Try it now:** [anchormd.dev](https://anchormd.dev) — paste a GitHub URL, get results in ~30 seconds. No signup required for public repos. Sign in with GitHub to scan private repos and batch-scan your entire account.

**What it generates:**
- Project overview, architecture tree, tech stack
- Coding standards (detected from your actual code — naming conventions, quote style, import patterns)
- Common commands (test, lint, format, build — auto-detected)
- Anti-patterns to avoid
- Domain context (key classes, API endpoints, enums)
- Quality score (0-100) with specific improvement recommendations

**New: Fix Report download** — if your score is under 100, download a markdown file with the exact gap analysis, copy-paste section templates, and a Claude Code prompt to auto-fix everything.

**Batch scan** — sign in with GitHub, hit "Scan All", and it scans every repo you own. Repos that already scored 100 and haven't changed are cached automatically so re-scans are fast.

**Also available as a CLI:** `pip install anchormd` — run `anchormd generate .` in any project directory.

**Why this matters:** A good CLAUDE.md is the difference between Claude Code understanding your project and hallucinating. I've seen it go from ~60% useful suggestions to ~90%+ with a proper context file.

Built with FastAPI + React, ~700 tests. Open source CLI, Pro tier for advanced features.

Feedback welcome — what would make this more useful for your workflow?
