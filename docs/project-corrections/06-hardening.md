# Hardening Corrections And Suggestions

## Highest-Value Hardening Areas

### 1. Entitlement hardening

Keep the current correction:

- Pro access must come from server verification or cached prior verification

Future improvement:

- include a clearer verified-state marker in logs and diagnostics
- consider explicit cache invalidation or max-staleness policy for degraded mode

### 2. Session hardening

The web app should continue to:

- issue opaque app session tokens
- store only hashed session tokens in the DB
- validate OAuth `state`

Future improvement:

- add session expiry and rotation
- add logout/invalidation support

### 3. Repo privacy hardening

Private repo scans must continue to be:

- created only when the server can actually access the repo
- visible only to the owning user
- excluded from anonymous or cross-user cache reuse

Future improvement:

- add explicit audit logging for private scan access denials

### 4. Operational secret hardening

Continue to treat:

- git stderr
- webhook payload-derived strings
- upstream API errors

as tainted text.

Future improvement:

- add a shared secret-redaction utility
- use it in both web and license-server contexts

## Additional Suggestions

### Webhook handling

- keep signature verification mandatory
- avoid duplicate exception lines or confusing unreachable branches
- add idempotency expectations to webhook docs

### Database migrations

- document startup migrations clearly
- prefer small, explicit migrations for security-relevant schema changes

### Security review checklist

Before shipping auth or billing changes, answer:

- does this expose a new credential to the browser
- does this allow access to another user’s private output
- does this fail open for paid or protected behavior
- does this persist tainted external output without sanitization

## Practical Next Tasks

- add session expiry policy
- add security checklist to release flow
- centralize redaction helpers
- extend webhook and auth tests
