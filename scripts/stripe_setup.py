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
    - Product: "AnchorMD Strict" — Seat Monthly ($49/seat/mo), Team-5 ($399/yr),
      Team-25 ($1,490/yr)
    - Payment Links for all 7 (printed to stdout)

IMPORTANT: Payment link metadata is read by the webhook at
POST /v1/webhooks/stripe — metadata.product routes the license generation,
metadata.tier sets the tier, metadata.seats (Strict only) sets the seat cap.
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
    parser = argparse.ArgumentParser(description="Set up Stripe for AnchorMD Pro + Bundle")
    parser.add_argument("--live", action="store_true", help="Confirm live mode (not test)")
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

    # ── AnchorMD Strict (CI/team tier) ─────────────────────────

    strict_product = stripe.Product.create(
        name="AnchorMD Strict",
        description=(
            "Fail-closed license validation, team seats, and audit log for CI "
            "and procurement environments. Includes everything in Pro plus "
            "CI integration and full drift detection."
        ),
        metadata={"product": "anchormd", "tier": "strict"},
    )
    print(f"\nStrict Product: {strict_product.id}")  # noqa: T201

    strict_seat_monthly = stripe.Price.create(
        product=strict_product.id,
        unit_amount=4900,  # $49.00 per seat
        currency="usd",
        recurring={"interval": "month"},
    )
    print(f"  Seat Monthly price: {strict_seat_monthly.id} ($49/seat/mo)")  # noqa: T201

    strict_team5_annual = stripe.Price.create(
        product=strict_product.id,
        unit_amount=39900,  # $399.00
        currency="usd",
        recurring={"interval": "year"},
        nickname="Strict Team-5 Annual",
    )
    print(f"  Team-5 Annual price: {strict_team5_annual.id} ($399/yr)")  # noqa: T201

    strict_team25_annual = stripe.Price.create(
        product=strict_product.id,
        unit_amount=149000,  # $1,490.00
        currency="usd",
        recurring={"interval": "year"},
        nickname="Strict Team-25 Annual",
    )
    print(f"  Team-25 Annual price: {strict_team25_annual.id} ($1,490/yr)")  # noqa: T201

    # Strict seat-monthly: each unit = 1 seat. Quantity at checkout sets seat count.
    # Webhook reads metadata.seats from the payment link.
    strict_seat_monthly_link = stripe.PaymentLink.create(
        line_items=[
            {
                "price": strict_seat_monthly.id,
                "quantity": 1,
                "adjustable_quantity": {
                    "enabled": True,
                    "minimum": 1,
                    "maximum": 100,
                },
            }
        ],
        metadata={"product": "anchormd", "tier": "strict", "seats": "1"},
    )
    print(f"  Seat Monthly link: {strict_seat_monthly_link.url}")  # noqa: T201

    strict_team5_link = stripe.PaymentLink.create(
        line_items=[{"price": strict_team5_annual.id, "quantity": 1}],
        metadata={"product": "anchormd", "tier": "strict", "seats": "5"},
    )
    print(f"  Team-5 link: {strict_team5_link.url}")  # noqa: T201

    strict_team25_link = stripe.PaymentLink.create(
        line_items=[{"price": strict_team25_annual.id, "quantity": 1}],
        metadata={"product": "anchormd", "tier": "strict", "seats": "25"},
    )
    print(f"  Team-25 link: {strict_team25_link.url}")  # noqa: T201

    # ── Summary ────────────────────────────────────────────────

    print("\n── Payment Links ──")  # noqa: T201
    print(f"AnchorMD Pro Monthly:    {monthly_link.url}")  # noqa: T201
    print(f"AnchorMD Pro Yearly:     {yearly_link.url}")  # noqa: T201
    print(f"Bundle Monthly ($29):    {bundle_monthly_link.url}")  # noqa: T201
    print(f"Bundle Yearly ($199):    {bundle_yearly_link.url}")  # noqa: T201
    print(f"Strict Seat Monthly:     {strict_seat_monthly_link.url}")  # noqa: T201
    print(f"Strict Team-5 Annual:    {strict_team5_link.url}")  # noqa: T201
    print(f"Strict Team-25 Annual:   {strict_team25_link.url}")  # noqa: T201
    print(  # noqa: T201
        "\nWebhook reads metadata.product + metadata.tier + metadata.seats."
        "\nEnsure webhook is configured at: "
        "https://cmdf-license.fly.dev/v1/webhooks/stripe"
    )


if __name__ == "__main__":
    main()
