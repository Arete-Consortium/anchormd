# Project Corrections Packet

This folder collects concrete correction notes and forward-looking suggestions for `anchormd`.

The goal is not to restate the whole codebase. The goal is to make follow-up work easier by splitting recommendations into focused documents that can be executed independently.

## Suggested Reading Order

1. `01-architecture.md`
2. `06-hardening.md`
3. `02-code-quality.md`
4. `03-tests.md`
5. `05-instructions-and-agent-surfaces.md`
6. `04-prompts-and-product-language.md`
7. `07-best-practices.md`

## Scope

These notes cover:

- architecture corrections
- code corrections and refactors
- test coverage and test strategy
- prompt and copy cleanup
- instruction surfaces (`CLAUDE.md`, skills, prompts, generated guidance)
- security hardening
- long-term engineering best practices

## High-Level Priorities

### Immediate

- Fail closed on license verification for Pro-only behavior
- Keep GitHub OAuth tokens out of browser-facing auth flows
- Restrict private scan access to the owning user
- Prevent secret leakage through clone failures and stored scan errors

### Near-Term

- Consolidate scan access and repo metadata handling in the web app
- Strengthen web-specific regression tests
- Reduce overlap between prompts, instructions, and product copy

### Follow-On

- Separate product concerns more clearly between CLI, web app, and license server
- Standardize guidance generation across prompts, templates, and skill docs
- Introduce clearer security and release checklists

## Implementation Style

Each document below uses the same pattern:

- current issue
- correction
- suggested implementation direction
- practical follow-up tasks

Use these files as planning inputs, not as rigid specs.
