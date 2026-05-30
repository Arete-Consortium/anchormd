# Best Practices For Ongoing Development

## Product Best Practices

- Keep the CLI trustworthy even when offline, but never use offline trust as a billing shortcut
- Treat private repo support as a privacy feature, not just a convenience feature
- Align marketing claims with tested behavior

## Engineering Best Practices

- Put trust-boundary logic behind helpers, not route-local conditionals
- Add a regression test whenever a fix closes an access or entitlement gap
- Prefer small, named policy helpers over inline authorization checks
- Keep sensitive text sanitized before storage or display

## Documentation Best Practices

- Update `CLAUDE.md` when security or workflow assumptions change
- Keep prompt docs, skill docs, and product docs aligned on terminology
- Record architectural decisions when they affect privacy or monetization

## Testing Best Practices

- Build at least one test at the helper level and one at the route level for security fixes
- Use explicit fixtures for verified entitlements instead of magic-looking keys
- Keep a small smoke-test suite for auth, licensing, and scan privacy

## Release Best Practices

- review auth changes before deploy
- review schema changes before deploy
- run targeted security regression tests before merge
- rotate tokens that get exposed during debugging or support

## Team Best Practices

- treat copied secrets as compromised immediately
- prefer reversible, low-risk rollout steps for auth or licensing changes
- use branch-based delivery for security fixes unless an emergency hotfix is required

## Practical Next Tasks

- add a short release checklist doc for auth and billing changes
- define a “security-sensitive files” list in docs
- add a lightweight changelog section for trust-boundary changes
