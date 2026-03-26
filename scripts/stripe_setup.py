#!/usr/bin/env python3
"""Create AnchorMD Stripe products, prices, and payment links.

Prerequisites:
    pip install stripe
    export STRIPE_SECRET_KEY=sk_test_...  (or sk_live_...)

Usage:
    python scripts/stripe_setup.py           # Creates everything (test mode)
    python scripts/stripe_setup.py --live    # Confirm live mode

Creates:
    - Product: "AnchorMD Pro" ($8/mo or $69/yr)
    - Product: "Arete Dev Tools Bundle" ($29/mo or $199/yr)
    - Payment Links for all 4 (printed to stdout)

IMPORTANT: Payment link metadata.product is read by the webhook at
POST /v1/webhooks/stripe to determine which license key(s) to generate.
"""

import argparse
import os
import sys

try:
    import stripe
except ImportError:
    print("Install stripe: pip install stripe", file=sys.stderr)  # noqa: T201
    sys.exit(1)

BUNDLE_PRODUCTS = "anchormd,agent-lint,ai-spend,promptctl,context-hygiene,auditchain"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up Stripe for AnchorMD Pro + Bundle"
    )
    parser.add_argument(
        "--live", action="store_true", help="Confirm live mode (not test)"
    )
    args = parser.parse_args()

    key = os.environ.get("STRIPE_SECRET_KEY")
    if not key:
        print("Set STRIPE_SECRET_KEY environment variable", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    if key.startswith("sk_live_") and not args.live:
        print(  # noqa: T201
            "Live key detected. Pass --live to confirm.",
            file=sys.stderr,
        )
        sys.exit(1)

    stripe.api_key = key

    # ── AnchorMD Pro (individual) ──────────────────────────────

    product = stripe.Product.create(
        name="AnchorMD Pro",
        description=(
            "Premium features for AnchorMD: tech debt scanner, GitHub health, "
            "cleanup agent, drift detection, premium presets, and priority support."
        ),
        metadata={"product": "anchormd", "tier": "pro"},
    )
    print(f"Product: {product.id}")  # noqa: T201

    monthly = stripe.Price.create(
        product=product.id,
        unit_amount=800,  # $8.00
        currency="usd",
        recurring={"interval": "month"},
    )
    print(f"  Monthly price: {monthly.id} ($8/mo)")  # noqa: T201

    yearly = stripe.Price.create(
        product=product.id,
        unit_amount=6900,  # $69.00
        currency="usd",
        recurring={"interval": "year"},
    )
    print(f"  Yearly price: {yearly.id} ($69/yr)")  # noqa: T201

    monthly_link = stripe.PaymentLink.create(
        line_items=[{"price": monthly.id, "quantity": 1}],
        metadata={"product": "anchormd"},
    )
    print(f"  Monthly link: {monthly_link.url}")  # noqa: T201

    yearly_link = stripe.PaymentLink.create(
        line_items=[{"price": yearly.id, "quantity": 1}],
        metadata={"product": "anchormd"},
    )
    print(f"  Yearly link:  {yearly_link.url}")  # noqa: T201

    # ── Bundle (all 5 tools) ───────────────────────────────────

    bundle_product = stripe.Product.create(
        name="Arete Dev Tools Bundle",
        description=(
            "All 5 Pro tools: AnchorMD, agent-lint, ai-spend, "
            "promptctl, context-hygiene. One license, full access."
        ),
        metadata={"product": "bundle", "tier": "pro"},
    )
    print(f"\nBundle Product: {bundle_product.id}")  # noqa: T201

    bundle_monthly = stripe.Price.create(
        product=bundle_product.id,
        unit_amount=2900,  # $29.00
        currency="usd",
        recurring={"interval": "month"},
    )
    print(f"  Monthly price: {bundle_monthly.id} ($29/mo)")  # noqa: T201

    bundle_yearly = stripe.Price.create(
        product=bundle_product.id,
        unit_amount=19900,  # $199.00
        currency="usd",
        recurring={"interval": "year"},
    )
    print(f"  Yearly price: {bundle_yearly.id} ($199/yr)")  # noqa: T201

    bundle_monthly_link = stripe.PaymentLink.create(
        line_items=[{"price": bundle_monthly.id, "quantity": 1}],
        metadata={
            "product": "bundle",
            "bundle_products": BUNDLE_PRODUCTS,
        },
    )
    print(f"  Monthly link: {bundle_monthly_link.url}")  # noqa: T201

    bundle_yearly_link = stripe.PaymentLink.create(
        line_items=[{"price": bundle_yearly.id, "quantity": 1}],
        metadata={
            "product": "bundle",
            "bundle_products": BUNDLE_PRODUCTS,
        },
    )
    print(f"  Yearly link:  {bundle_yearly_link.url}")  # noqa: T201

    # ── Summary ────────────────────────────────────────────────

    print("\n── Payment Links ──")  # noqa: T201
    print(f"AnchorMD Pro Monthly:  {monthly_link.url}")  # noqa: T201
    print(f"AnchorMD Pro Yearly:   {yearly_link.url}")  # noqa: T201
    print(f"Bundle Monthly ($29):  {bundle_monthly_link.url}")  # noqa: T201
    print(f"Bundle Yearly ($199):  {bundle_yearly_link.url}")  # noqa: T201
    print(  # noqa: T201
        "\nWebhook reads metadata.product to route key generation."
        "\nEnsure webhook is configured at: "
        "https://cmdf-license.fly.dev/v1/webhooks/stripe"
    )


if __name__ == "__main__":
    main()
