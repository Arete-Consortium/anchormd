---
name: anchormd-generate
description: Generate a CLAUDE.md file for the current project. Use when setting up a new project for AI-assisted development, when a project lacks a CLAUDE.md, when the user asks to create project context for Claude Code, or when onboarding a codebase for agent use. Scans the codebase to detect languages, frameworks, testing patterns, build commands, and conventions, then produces a structured CLAUDE.md with coding standards, anti-patterns, and project-specific instructions.
license: BSL-1.1
---

# Generate CLAUDE.md

Generate a production-grade CLAUDE.md for the current project using anchormd.

## Prerequisites

anchormd must be installed: `pip install anchormd`

## Workflow

1. Run the generator against the project root:
   ```bash
   anchormd generate .
   ```

2. Review the generated CLAUDE.md output. The generator scans for:
   - Programming languages and frameworks in use
   - Build systems and package managers
   - Testing frameworks and patterns
   - CI/CD configuration
   - Code style and linting setup
   - Project structure and architecture

3. If the output needs refinement, iterate:
   ```bash
   anchormd generate . --preset python-fastapi  # Explicit framework preset
   anchormd generate . --preset minimal         # Fewer sections
   ```

4. Audit the generated file for quality:
   ```bash
   anchormd audit CLAUDE.md
   ```

## Available Presets

Community presets (free): default, minimal, full, python-fastapi, python-cli, django, react-typescript, nextjs, rust, go, node-express

Pro presets (license required): monorepo, library, react-native, data-science, devops, mobile

## When NOT to Use

- If a well-maintained CLAUDE.md already exists, prefer manual updates over regeneration
- For monorepos, run per-package rather than at the root
