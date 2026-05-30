// StrictPage — landing for the Strict tier (CI + procurement positioning).
//
// PAYMENT LINK SUBSTITUTION:
// After running `python scripts/stripe_setup.py --live`, replace the three
// STRICT_* URLs below with the live Stripe Payment Link URLs printed to stdout.
// Until then they fall through to the pricing page with a TODO marker.
const STRICT_SEAT_MONTHLY_URL = "?page=pricing&plan=strict-seat-monthly";
const STRICT_TEAM_5_URL = "?page=pricing&plan=strict-team-5";
const STRICT_TEAM_25_URL = "?page=pricing&plan=strict-team-25";

const CI_SNIPPET = `# .github/workflows/anchormd-audit.yml
name: Audit CLAUDE.md (anchormd Strict)

on:
  pull_request:
    paths:
      - "CLAUDE.md"
      - "src/**"

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install anchormd
      - name: Audit CLAUDE.md
        env:
          ANCHORMD_LICENSE: \${{ secrets.ANCHORMD_LICENSE }}
          ANCHORMD_STRICT: "1"          # ← fails closed
        run: anchormd audit ./CLAUDE.md`;

function FeatureBullet({ title, body }) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-6">
      <h3 className="text-white font-semibold mb-2 text-lg">{title}</h3>
      <p className="text-gray-400 text-sm leading-relaxed">{body}</p>
    </div>
  );
}

function PlanCard({ title, price, tagline, url, highlight = false, seats }) {
  const ring = highlight
    ? "border-anchor-500 ring-2 ring-anchor-500/30"
    : "border-gray-700";
  return (
    <div
      className={`bg-gray-900 border ${ring} rounded-lg p-6 flex flex-col`}
    >
      <h3 className="text-white font-bold text-xl mb-1">{title}</h3>
      <div className="text-anchor-400 font-mono text-2xl mb-1">{price}</div>
      {seats && (
        <div className="text-gray-500 text-xs uppercase tracking-wide mb-3">
          {seats}
        </div>
      )}
      <p className="text-gray-400 text-sm mb-5 flex-1">{tagline}</p>
      <a
        href={url}
        className="block text-center bg-anchor-500 hover:bg-anchor-600 text-white
                   font-semibold px-4 py-2.5 rounded-md transition-colors text-sm"
      >
        Subscribe
      </a>
    </div>
  );
}

export default function StrictPage() {
  return (
    <div className="pt-12 pb-16">
      {/* Hero */}
      <div className="text-center mb-12">
        <span className="inline-block bg-anchor-600/20 text-anchor-300 text-xs font-semibold
                         px-3 py-1 rounded-full border border-anchor-500/40 uppercase tracking-wide
                         mb-4">
          Strict — for teams and CI
        </span>
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4 tracking-tight">
          License validation that <span className="text-anchor-400">fails closed.</span>
        </h1>
        <p className="text-gray-400 text-lg max-w-2xl mx-auto">
          Pro is great for solo devs. Strict is for the CI run that has to fail
          when the license server is unreachable, the team that needs five seats
          on one bill, and the procurement reviewer who wants an audit log.
        </p>
      </div>

      {/* Three bullets */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
        <FeatureBullet
          title="Fail-closed validation"
          body={
            "ANCHORMD_STRICT=1 exits non-zero on any license-validation failure: " +
            "server unreachable, key revoked, expired, no cache. Pro silently " +
            "degrades to Free. Strict refuses."
          }
        />
        <FeatureBullet
          title="Team seats"
          body={
            "One license, N machine activations. Sliders on the monthly plan, " +
            "fixed 5- and 25-seat annual tiers. Seat management is built in — " +
            "claim and release through the API."
          }
        />
        <FeatureBullet
          title="Audit log"
          body={
            "Every scan recorded server-side with a 1-year retention window. " +
            "CSV or JSON export. The procurement answer to 'show me who ran what.'"
          }
        />
      </div>

      {/* Pricing tiles */}
      <h2 className="text-white text-2xl font-bold mb-6 text-center">
        Pick a plan
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-12">
        <PlanCard
          title="Seat Monthly"
          price="$49"
          seats="per seat / month"
          tagline="Solo or small team. Slide the seat count at checkout — bill scales with your team."
          url={STRICT_SEAT_MONTHLY_URL}
        />
        <PlanCard
          title="Team-5 Annual"
          price="$399"
          seats="5 seats / year"
          tagline="Five seats, one bill, one annual renewal. ~$6.65/seat/month effective."
          url={STRICT_TEAM_5_URL}
          highlight
        />
        <PlanCard
          title="Team-25 Annual"
          price="$1,490"
          seats="25 seats / year"
          tagline="Enterprise-shaped pricing for larger orgs. ~$4.97/seat/month effective."
          url={STRICT_TEAM_25_URL}
        />
      </div>

      {/* CI snippet */}
      <div className="mb-12">
        <h2 className="text-white text-2xl font-bold mb-4">CI setup</h2>
        <p className="text-gray-400 text-sm mb-4 max-w-2xl">
          Drop this into <code className="text-anchor-300 text-xs">.github/workflows/</code>.
          The <code className="text-anchor-300 text-xs">ANCHORMD_STRICT=&quot;1&quot;</code>{" "}
          env var is what makes the audit step fail closed.
        </p>
        <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
          <pre className="p-6 text-sm text-gray-300 font-mono whitespace-pre overflow-x-auto">
{CI_SNIPPET}
          </pre>
        </div>
      </div>

      {/* Comparison table */}
      <div className="mb-12">
        <h2 className="text-white text-2xl font-bold mb-4">What you get with Strict</h2>
        <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-800">
              <tr>
                <th className="text-left text-gray-300 font-semibold px-4 py-3">Feature</th>
                <th className="text-center text-gray-300 font-semibold px-4 py-3">Free</th>
                <th className="text-center text-gray-300 font-semibold px-4 py-3">Pro</th>
                <th className="text-center text-anchor-300 font-semibold px-4 py-3">Strict</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {[
                ["generate, audit", true, true, true],
                ["verify, harvest, patch", true, true, true],
                ["init, diff, premium presets", false, true, true],
                ["tech-debt, github-health, cleanup", false, true, true],
                ["Fail-closed validation (ANCHORMD_STRICT)", false, false, true],
                ["CI integration (PR comments)", false, false, true],
                ["Drift detection (generate, fix, judge, HTML)", false, false, true],
                ["Fleet audit --json + history", false, false, true],
                ["Team seats (1 key → N machines)", false, false, true],
                ["Audit log (1yr retention, CSV/JSON export)", false, false, true],
                ["SLA — 99.5% license server uptime", false, false, true],
              ].map(([label, free, pro, strict]) => (
                <tr key={label}>
                  <td className="text-gray-300 px-4 py-2.5">{label}</td>
                  <td className="text-center px-4 py-2.5">
                    {free ? <span className="text-green-400">✓</span> : <span className="text-gray-600">·</span>}
                  </td>
                  <td className="text-center px-4 py-2.5">
                    {pro ? <span className="text-green-400">✓</span> : <span className="text-gray-600">·</span>}
                  </td>
                  <td className="text-center px-4 py-2.5">
                    {strict ? <span className="text-anchor-300">✓</span> : <span className="text-gray-600">·</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-gray-500 text-xs mt-3">
          v0.6.0 (released {new Date().getFullYear()}): CI integration and advanced drift
          detection moved from Pro to Strict. Existing Pro subscribers — see CHANGELOG.
        </p>
      </div>

      {/* Procurement footer */}
      <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-6 text-center">
        <h3 className="text-white font-bold text-lg mb-2">Procurement / security review?</h3>
        <p className="text-gray-400 text-sm max-w-2xl mx-auto mb-4">
          Strict includes audit-log export, fail-closed CI, signed license keys, and a
          documented data-retention policy. Need MSA / DPA / SOC 2 / self-hosted server?
        </p>
        <a
          href="mailto:strict@anchormd.dev?subject=Strict%20enterprise%20inquiry"
          className="inline-block bg-gray-800 hover:bg-gray-700 border border-gray-700
                     text-white text-sm px-5 py-2 rounded-md transition-colors"
        >
          Contact us
        </a>
      </div>
    </div>
  );
}
