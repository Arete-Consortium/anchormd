---
title: "Why we added a fail-closed license tier to anchormd"
subtitle: "Pro was the wrong shape for CI. Here is how we fixed it without grandfathering."
draft: true
pre_publish:
  - run /content-scrubber before publish (mandatory per Arete CLAUDE.md)
  - re-verify Stripe Payment Link URLs are live (placeholder fall-through removed)
  - re-verify PyPI shows 0.6.0
---

A customer wrote in last week. They run anchormd on every pull request. Their CI workflow had been quiet for two months, which is exactly what you want a license-validation step to be. Then their build broke. They dug into it expecting a billing problem and found the opposite: their license server connection had been silently failing for six weeks, the CI step had been falling back to Free tier, and nothing had blocked the PR. The premium presets they pay for had stopped applying.

That is the fail-open problem. It is the right default for solo developers. A flaky home wifi at 11 PM should not break `anchormd generate` on a side project. So we ship Pro with fail-open and that is the right call.

But it is the wrong default for CI.

In CI, the license-validation step has one job: refuse to run if the license is not valid. Falling back to Free quietly is worse than crashing the build. A build that crashes gets seen. A build that silently swaps tier produces output that looks correct and is not.

We could have shipped a flag. `ANCHORMD_STRICT=1`. Done in an afternoon. We did ship it, in v0.5.0, as a Pro feature.

Two weeks later it became obvious that flag did not solve the actual problem. The procurement reviewer at a larger prospect sent a security questionnaire. Question 14: "show us the audit log of who ran what scan and when." We had nothing. Question 19: "the license is shared across five engineers. What happens if the sixth engineer activates it on their machine?" Nothing happened. The license worked everywhere. Their CFO had no visibility into how many machines were using it. That was a deal-breaker.

So the gap was not "should the CLI fail closed in CI." That was already done. The gap was "what shape of license does a procurement department want to buy?" The answer is roughly:

1. **Fail-closed validation.** (We had it.)
2. **A bounded seat count.** (We did not.)
3. **An audit log they can export.** (We did not.)
4. **An SLA on the license server.** (We had it informally.)
5. **A documented retention policy.** (We did not.)

That is a real tier, not a flag. So this month we built it.

## The shape of the new tier

The tier is called Strict. It costs $49 per seat per month, or $399 a year for a team of five, or $1,490 a year for a team of twenty-five.

The core technical change is that one license key now maps to N machine activations. When the sixth engineer at a five-seat shop tries to claim a seat, the server returns 409 and the CLI logs a warning. The license still works for the five engineers who already claimed. The team lead sees the warning in their CI logs and either releases a seat or upgrades. No one's pipeline breaks at midnight because their teammate added themselves to the license without telling them.

The audit log is the procurement answer. Every CLI invocation by a Strict user posts to `/v1/audit/log` fire-and-forget. The server keeps records for one year and exports CSV or JSON via an admin endpoint. We picked one year because that is what the buyers we surveyed said they needed to satisfy their internal review cycles. Indefinite retention is available on Enterprise contracts; we did not want to default to it because storage cost compounds and most buyers do not actually want everything forever.

`ANCHORMD_STRICT=1` continues to work the same way. Setting it makes the CLI exit non-zero when the license server is unreachable instead of silently degrading. We left the Pro fail-open behavior alone. Strict subscribers opt in.

## The decision we did not make

I considered a grandfather period. The clean version was: every existing Pro subscriber keeps CI integration and full drift detection for ninety days after the v0.6.0 release; the gate flips after that.

I did not do this.

The reason is mostly that grandfather periods are a tax on the next decision. The next time we move a feature between tiers, the precedent says we have to do this song-and-dance again. The product gets harder to move because every move has to be wrapped in a transition program. And the buyers I am building Strict for are the buyers who would never be on Pro in the first place. The friction is on the wrong side.

The honest cost is some chargebacks. Pro subscribers who depended on CI integration on v0.5.0 can either subscribe to Strict, pin their workflow to `anchormd==0.5.0`, or accept a full refund on their most recent Pro charge if they object in writing within thirty days. That is in the changelog and the in-CLI upgrade prompt routes to that policy.

It is the right call for an early-stage tool with maybe a hundred Pro subscribers. It would be the wrong call at a million.

## What I did not build

Two things did not make v0.6.0 that probably should have:

**A self-hosted license server option.** Some of the procurement reviewers want to run the validation server inside their VPC. I have the code; the license server is a FastAPI app with SQLite. Packaging it for self-hosted distribution is its own product and I did not want to ship a half-version of it. It is available as an Enterprise contract item.

**SSO for the admin endpoint.** Right now the audit-log export and the seat list use a shared admin bearer token. Single-customer use is fine; multi-tenant procurement teams want SAML. Same answer: Enterprise contract.

Both will come if the demand shape supports them. I am not going to build SOC 2 infrastructure speculatively.

## What it actually cost

I am running this as a one-person shop. I track build effort in a spec doc and the commit log. v0.6.0 took roughly twenty-five hours of focused build time over five days, split:

- Day 1: Tier plumbing (two hours)
- Day 2: Server-side seats (two hours)
- Day 3: Audit log + retention (two hours)
- Day 4: Stripe wiring + welcome email (two hours)
- Day 5: Web frontend pages (two hours)
- Day 6: Documentation + changelog + this post (variable)
- Day 7: Stripe-live, PyPI publish, outreach (will be variable)

Plus about three hours of review and gap-closing after Day 5, which caught two real bugs I had shipped without noticing. The audit logger module existed but was never called from any CLI command. The client-side seat claim was specced but never built. Both are now real. The lesson is to review your own work after the fact even when the tests pass.

That is the post. If you read this far and you have a CI workflow that runs anchormd, take a look at `?page=strict` on the site. If you do not, Pro at $8 is still the right tier and nothing changes for you.

— Arete

(I run [anchormd](https://anchormd.dev), an audit and generation tool for CLAUDE.md files. The code is on [GitHub](https://github.com/Arete-Consortium/anchormd). v0.6.0 ships this week.)
