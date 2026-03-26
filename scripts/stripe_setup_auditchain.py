#!/usr/bin/env python3
"""Create AuditChain Stripe products, prices, and payment links.

Prerequisites:
    pip install stripe
    export STRIPE_SECRET_KEY=sk_live_...

Usage:
    python scripts/stripe_setup_auditchain.py           # Test mode
    python scripts/stripe_setup_auditchain.py --live    # Confirm live mode

Creates:
    - Product: "AuditChain Pro" ($29/mo or $249/yr)
    - Payment Links for both (printed to stdout)

IMPORTANT: Payment link metadata.product is read by the webhook at
POST /v1/webhooks/stripe to determine which license key to generate.
"""

import argparse
import os
import sys

try:
    import stripe
except ImportError:
    print("Install stripe: pip install stripe", file=sys.stderr)  # noqa: T201
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set up Stripe for AuditChain Pro"
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

    # ── AuditChain Pro ────────────────────────────────────────

    product = stripe.Product.create(
        name="AuditChain Pro",
        description=(
            "AI agent compliance platform on Base L2. "
            "Unlimited on-chain audit logs, compliance reports, "
            "EU AI Act mappings, and agent tracking. "
            "Includes Pro access to agent-lint, ai-spend, and context-hygiene."
        ),
        metadata={"product": "auditchain", "tier": "pro"},
    )
    print(f"Product: {product.id}")  # noqa: T201

    monthly = stripe.Price.create(
        product=product.id,
        unit_amount=2900,  # $29.00
        currency="usd",
        recurring={"interval": "month"},
    )
    print(f"  Monthly price: {monthly.id} ($29/mo)")  # noqa: T201

    yearly = stripe.Price.create(
        product=product.id,
        unit_amount=24900,  # $249.00
        currency="usd",
        recurring={"interval": "year"},
    )
    print(f"  Yearly price: {yearly.id} ($249/yr)")  # noqa: T201

    monthly_link = stripe.PaymentLink.create(
        line_items=[{"price": monthly.id, "quantity": 1}],
        metadata={"product": "auditchain"},
    )
    print(f"  Monthly link: {monthly_link.url}")  # noqa: T201

    yearly_link = stripe.PaymentLink.create(
        line_items=[{"price": yearly.id, "quantity": 1}],
        metadata={"product": "auditchain"},
    )
    print(f"  Yearly link:  {yearly_link.url}")  # noqa: T201

    # ── Founding Member ($19/mo locked) ───────────────────────

    founding = stripe.Price.create(
        product=product.id,
        unit_amount=1900,  # $19.00
        currency="usd",
        recurring={"interval": "month"},
        nickname="Founding Member",
    )
    print(f"\n  Founding price: {founding.id} ($19/mo)")  # noqa: T201

    founding_link = stripe.PaymentLink.create(
        line_items=[{"price": founding.id, "quantity": 1}],
        metadata={"product": "auditchain"},
    )
    print(f"  Founding link: {founding_link.url}")  # noqa: T201

    # ── Summary ───────────────────────────────────────────────

    print("\n── AuditChain Payment Links ──")  # noqa: T201
    print(f"Pro Monthly ($29):     {monthly_link.url}")  # noqa: T201
    print(f"Pro Yearly ($249):     {yearly_link.url}")  # noqa: T201
    print(f"Founding Member ($19): {founding_link.url}")  # noqa: T201
    print(  # noqa: T201
        "\nWebhook reads metadata.product='auditchain' to route key generation."
        "\nEnsure webhook is configured at: "
        "https://cmdf-license.fly.dev/v1/webhooks/stripe"
    )


if __name__ == "__main__":
    main()
