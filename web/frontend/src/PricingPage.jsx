// PricingPage — the three-tier price + decision-flow page.
//
// PAYMENT LINK SUBSTITUTION: Same Stripe Payment Link substitution applies as
// StrictPage.jsx — replace the placeholder URLs below after running stripe_setup.py.
const PRO_MONTHLY_URL = "?page=pricing&plan=pro-monthly";
const PRO_YEARLY_URL = "?page=pricing&plan=pro-yearly";
const STRICT_SEAT_MONTHLY_URL = "?page=pricing&plan=strict-seat-monthly";
const STRICT_TEAM_5_URL = "?page=pricing&plan=strict-team-5";

function TierCard({ name, price, period, tagline, features, ctaLabel, ctaUrl, highlight = false }) {
  const ring = highlight ? "border-anchor-500 ring-2 ring-anchor-500/30" : "border-gray-700";
  return (
    <div className={`bg-gray-900 border ${ring} rounded-lg p-6 flex flex-col`}>
      <h3 className="text-white font-bold text-2xl mb-1">{name}</h3>
      <div className="flex items-baseline gap-2 mb-4">
        <span className="text-anchor-400 font-mono text-3xl">{price}</span>
        <span className="text-gray-500 text-sm">{period}</span>
      </div>
      <p className="text-gray-400 text-sm mb-5">{tagline}</p>
      <ul className="space-y-2 mb-6 flex-1">
        {features.map((f) => (
          <li key={f} className="flex items-start gap-2 text-gray-300 text-sm">
            <span className="text-anchor-400 mt-0.5">✓</span>
            <span>{f}</span>
          </li>
        ))}
      </ul>
      <a
        href={ctaUrl}
        className={`block text-center font-semibold px-4 py-2.5 rounded-md transition-colors text-sm
                    ${
                      highlight
                        ? "bg-anchor-500 hover:bg-anchor-600 text-white"
                        : "bg-gray-800 hover:bg-gray-700 text-white border border-gray-700"
                    }`}
      >
        {ctaLabel}
      </a>
    </div>
  );
}

export default function PricingPage() {
  return (
    <div className="pt-12 pb-16">
      <div className="text-center mb-12">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 tracking-tight">
          Pricing
        </h1>
        <p className="text-gray-400 text-lg max-w-2xl mx-auto">
          Three tiers. Free works forever. Pro for serious solo devs.
          Strict for CI and teams that need fail-closed validation + audit log.
        </p>
      </div>

      {/* Three tiers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-16">
        <TierCard
          name="Free"
          price="$0"
          period="forever"
          tagline="Generate, audit, verify. Everything you need to ship one good CLAUDE.md."
          features={[
            "anchormd generate",
            "anchormd audit + score",
            "verify, harvest, patch",
            "11 community presets",
          ]}
          ctaLabel="pip install anchormd"
          ctaUrl="https://pypi.org/project/anchormd/"
        />
        <TierCard
          name="Pro"
          price="$8"
          period="per month · $69/yr"
          tagline="The everyday Claude Code dev's toolkit. Interactive setup, diffs, presets."
          features={[
            "Everything in Free",
            "init (interactive setup)",
            "diff (preview changes)",
            "tech-debt, github-health, cleanup",
            "Premium presets (17 total)",
            "Priority updates",
          ]}
          ctaLabel="Subscribe to Pro"
          ctaUrl={PRO_MONTHLY_URL}
        />
        <TierCard
          name="Strict"
          price="$49"
          period="per seat · monthly"
          tagline="Fail-closed CI, team seats, audit log. The CI + procurement tier."
          features={[
            "Everything in Pro",
            "ANCHORMD_STRICT — fail-closed validation",
            "CI integration (PR comments)",
            "Full drift detection (generate, fix, judge, HTML)",
            "Fleet audit --json + history",
            "Team seats (1 key → N machines)",
            "Audit log (1yr retention, CSV/JSON export)",
            "99.5% SLA on license server",
          ]}
          ctaLabel="Subscribe to Strict"
          ctaUrl={STRICT_SEAT_MONTHLY_URL}
          highlight
        />
      </div>

      {/* Annual savings */}
      <div className="mb-12 bg-gray-900/60 border border-gray-800 rounded-lg p-6">
        <h2 className="text-white text-xl font-bold mb-3">Annual plans</h2>
        <p className="text-gray-400 text-sm mb-4">
          Pre-paid annual plans cost less per month and consolidate billing.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
          <a
            href={PRO_YEARLY_URL}
            className="bg-gray-900 border border-gray-700 hover:border-gray-600 rounded-lg p-4
                       transition-colors block"
          >
            <div className="text-white font-semibold mb-1">Pro Yearly</div>
            <div className="text-anchor-400 font-mono">$69 / yr</div>
            <div className="text-gray-500 text-xs mt-1">$5.75/mo effective</div>
          </a>
          <a
            href={STRICT_TEAM_5_URL}
            className="bg-gray-900 border border-gray-700 hover:border-gray-600 rounded-lg p-4
                       transition-colors block"
          >
            <div className="text-white font-semibold mb-1">Strict Team-5</div>
            <div className="text-anchor-400 font-mono">$399 / yr</div>
            <div className="text-gray-500 text-xs mt-1">$6.65/seat/mo · 5 seats</div>
          </a>
          <a
            href="?page=strict#team-25"
            className="bg-gray-900 border border-gray-700 hover:border-gray-600 rounded-lg p-4
                       transition-colors block"
          >
            <div className="text-white font-semibold mb-1">Strict Team-25</div>
            <div className="text-anchor-400 font-mono">$1,490 / yr</div>
            <div className="text-gray-500 text-xs mt-1">$4.97/seat/mo · 25 seats</div>
          </a>
        </div>
      </div>

      {/* Which tier? decision flow */}
      <div className="mb-12">
        <h2 className="text-white text-2xl font-bold mb-6">Which tier is right for me?</h2>
        <div className="space-y-3">
          <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-5">
            <h3 className="text-white font-semibold mb-2">
              I want to try anchormd on one project.
            </h3>
            <p className="text-gray-400 text-sm">
              <span className="text-anchor-300 font-semibold">Free.</span>{" "}
              <code className="text-anchor-300 text-xs">pip install anchormd</code> and
              run <code className="text-anchor-300 text-xs">anchormd generate</code>.
              The audit scorer is free too.
            </p>
          </div>
          <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-5">
            <h3 className="text-white font-semibold mb-2">
              I use anchormd daily across 5+ projects.
            </h3>
            <p className="text-gray-400 text-sm">
              <span className="text-anchor-300 font-semibold">Pro.</span>{" "}
              <code className="text-anchor-300 text-xs">init</code> /
              <code className="text-anchor-300 text-xs"> diff</code> /
              <code className="text-anchor-300 text-xs"> tech-debt</code> earn back
              their cost in saved time after the first non-trivial repo.
            </p>
          </div>
          <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-5">
            <h3 className="text-white font-semibold mb-2">
              My CI must fail when the license server is down.
            </h3>
            <p className="text-gray-400 text-sm">
              <span className="text-anchor-300 font-semibold">Strict.</span>{" "}
              Pro silently degrades to Free on outage — that's not what your CI wants.
              Strict honors <code className="text-anchor-300 text-xs">ANCHORMD_STRICT=1</code>
              {" "}and exits non-zero instead.
            </p>
          </div>
          <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-5">
            <h3 className="text-white font-semibold mb-2">
              Five engineers share one license via env var.
            </h3>
            <p className="text-gray-400 text-sm">
              <span className="text-anchor-300 font-semibold">Strict Team-5 Annual.</span>{" "}
              One key, five seat claims, one bill, one renewal.
            </p>
          </div>
          <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-5">
            <h3 className="text-white font-semibold mb-2">
              Security review asks who ran what scan and when.
            </h3>
            <p className="text-gray-400 text-sm">
              <span className="text-anchor-300 font-semibold">Strict.</span>{" "}
              Every command logged server-side, 1-year retention, CSV export. The
              procurement answer is built in.
            </p>
          </div>
        </div>
      </div>

      <div className="text-center">
        <p className="text-gray-500 text-sm">
          Questions about plans? <a href="mailto:hello@anchormd.dev" className="text-anchor-400 hover:text-anchor-300">hello@anchormd.dev</a>
        </p>
      </div>
    </div>
  );
}
