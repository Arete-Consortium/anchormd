# Show HN draft: anchormd Strict

**Status:** draft. Run `/content-scrubber` before posting. Post when v0.6.0 is live on PyPI and the Stripe Payment Links point at live URLs (not placeholders).

## Title (80 chars max — HN limit)

```
Show HN: anchormd Strict – license validation that fails closed in CI
```

Alternative title (more controversial, higher click-through, factually defensible):

```
Show HN: I added a fail-closed license tier because Pro silently degrades to Free
```

## URL

```
https://anchormd.dev/?page=strict
```

## Body (HN strips most markdown; format for plaintext)

```
We ship anchormd (CLAUDE.md audit + generation tool for AI coding agents).
Pro fails open by default: if the license server is unreachable, a
valid-format key grants Pro tier so a transient network blip does not
break a developer's working install. That is the right default for
solo devs.

It is the wrong default for CI. A CI job that silently swaps to Free
tier produces output that looks correct and is not.

v0.6.0 ships a tier above Pro called Strict. Three concrete changes:

1. ANCHORMD_STRICT=1 exits non-zero on any license-validation failure
   (server unreachable / revoked / expired) instead of degrading.

2. One license supports N machine activations. The 6th machine on a
   5-seat license gets HTTP 409 from /v1/seats/claim but the CLI keeps
   working for the 5 seats already claimed — operator visibility
   without a midnight pipeline outage.

3. Every CLI invocation posts fire-and-forget to /v1/audit/log. Server
   keeps records for one year. Admin CSV/JSON export. The procurement
   answer to "who ran what scan and when."

Stripe SKUs: $49/seat/mo, $399/yr team-5, $1,490/yr team-25. Free and
Pro tiers continue to work as before — Strict is opt-in.

Built by one person over 5 days of focused work. Code: github.com/Arete-
Consortium/anchormd. Spec doc + CHANGELOG migration guide in the repo.

Two features moved from Pro to Strict (CI integration + advanced drift
detection). No grandfather period — rationale in the CHANGELOG. 30-day
refund offer for Pro subscribers who object.

Happy to answer questions about the no-grandfather decision, the seat-
claim design (200/409 instead of hard gate), or the audit log retention
choice (365 days rather than indefinite). What I would push back on:
suggestions to add SOC 2 speculatively before there's demand for it.
```

## Word count

~280 words. Under the 500-word soft HN ceiling. Body is plaintext-safe (no markdown, no smart quotes — paste verbatim into HN's body field).

## Comments seed

If the post lands and the first comment is the inevitable "but what about self-hosted":

```
Self-hosted is on the roadmap but I did not want to ship half a version
of it for v0.6.0. The license server is a FastAPI app with SQLite +
Litestream replication — the code is in license_server/ if you want to
read it. Available as an Enterprise contract today. I will not build the
SOC 2 wrapper around it speculatively; needs a buyer.
```

If the first comment is "this is just feature gating":

```
Yes. The interesting part is the seat-claim design. Strict server
validation is NOT seat-gated — the 6th machine still gets a valid
license response. The 409 only happens at /v1/seats/claim. Operator
gets a visible warning in their CLI logs without their CI breaking at
midnight. The discipline is in what you choose NOT to gate.
```

## When to post

Tuesday or Wednesday morning Pacific Time. Avoid:
- Monday mornings (HN front page is most competitive)
- Fri/Sat/Sun (low engineering audience)
- Immediately after a major model release (Claude / GPT) — your post gets buried
- Within 30 minutes of any Cloudflare or AWS outage (HN front page becomes outage takes)

## Post-launch

- Reply to every comment within 4 hours for the first 12 hours. After that, every 8 hours until thread dies.
- Do NOT delete negative comments. Engage them. Most negative HN comments are technically right about something specific.
- Watch the Stripe dashboard. If the Show HN drives any Strict signups, that is the validation.
- If the post hits front page: do NOT add a "thanks HN" comment. They will downvote it. Just keep replying to questions.

## Anti-patterns to avoid

- Do not link to the Substack post in the HN body. Multiple-link posts read as marketing. The repo URL is enough.
- Do not say "we are launching." HN sees "we" as a team and asks who; "I" with a one-person framing reads more honest.
- Do not include screenshots in the post body. HN strips images. If you want to show the diff, link to the CHANGELOG section directly.
- Do not pre-write a defense of the no-grandfather decision in the body. Let the question come; the answer is better received when prompted.
