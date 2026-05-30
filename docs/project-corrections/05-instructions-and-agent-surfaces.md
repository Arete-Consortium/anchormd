# Instructions Corrections And Suggestions

## Relevant Surfaces

The project has multiple instruction-bearing files:

- root `CLAUDE.md`
- skill docs under `skills/`
- prompt files under `prompts/`
- generated CLAUDE.md documents

These surfaces overlap in purpose but should not duplicate each other blindly.

## Main Corrections

### 1. Distinguish canonical instructions from generated instructions

Recommended split:

- repo `CLAUDE.md` explains how contributors or agents should work on `anchormd`
- generated output explains how an agent should work on some target repo

Those should inform each other, but not mirror each other word-for-word.

### 2. Keep security instructions explicit

Security-sensitive guidance should not be left implicit in prompts.

Examples:

- never expose upstream credentials to browser clients
- never trust client-side checksum validation for billing entitlements
- never treat private scan artifacts as globally cacheable

These belong in contributor-facing instructions and in tests, not only in review notes.

### 3. Avoid instruction drift

When root instructions, prompt files, and tests disagree, the system quietly degrades.

Suggested practice:

- treat `CLAUDE.md` and selected docs as the canonical source
- periodically check prompts and skills against those canonical rules

## Suggested Instruction Improvements

- add a short section in root `CLAUDE.md` for auth/session boundaries
- add a short section for web scan privacy rules
- note that paid entitlements require server verification or cached verified state
- list security-sensitive files explicitly:
  - `src/anchormd/licensing.py`
  - `web/app.py`
  - `web/generator.py`
  - `license_server/routes/validate.py`

## Practical Next Tasks

- update root `CLAUDE.md` with a “Security Boundaries” section
- add a “Web Privacy Rules” section
- add a “License Trust Model” section
- review skill docs for consistency with those rules
