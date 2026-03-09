"""Stripe webhook handlers for automated license fulfillment.

Handles:
- checkout.session.completed → generate + activate license, email key
- customer.subscription.deleted → revoke license
- invoice.payment_failed → log warning (grace period handled by Stripe)

Multi-product: Stripe metadata must include "product" (e.g. "claudemd-forge", "agent-lint").
Defaults to "claudemd-forge" for backward compatibility.
"""

from __future__ import annotations

import json
import logging
import uuid

from license_server.database import get_connection
from license_server.email_delivery import send_license_email
from license_server.key_gen import generate_key, hash_key, mask_key, validate_key_checksum

logger = logging.getLogger(__name__)


def handle_checkout_completed(event: dict) -> dict:
    """Process checkout.session.completed — create license and email key.

    Returns dict with license_key_masked and email on success.
    """
    session = event.get("data", {}).get("object", {})
    customer_email = session.get("customer_details", {}).get("email") or session.get(
        "customer_email"
    )
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not customer_email:
        logger.error("checkout.session.completed missing customer email: %s", event.get("id"))
        return {"error": "missing_email", "event_id": event.get("id")}

    # Extract product and tier from metadata
    metadata = session.get("metadata", {})
    product = metadata.get("product", "claudemd-forge")
    tier = metadata.get("tier", "pro")

    # Generate key with product-specific prefix and salt
    key = generate_key(product)
    if not validate_key_checksum(key, product):
        logger.error("Generated key failed checksum — should never happen")
        return {"error": "key_generation_failed"}

    key_h = hash_key(key)
    masked = mask_key(key)
    license_id = str(uuid.uuid4())

    conn = get_connection()
    conn.execute(
        "INSERT INTO licenses "
        "(id, key_hash, license_key_masked, tier, email, active, product, "
        "stripe_customer_id, stripe_subscription_id, metadata) "
        "VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?)",
        (
            license_id,
            key_h,
            masked,
            tier,
            customer_email,
            product,
            customer_id,
            subscription_id,
            json.dumps({"source": "stripe_checkout", "event_id": event.get("id")}),
        ),
    )
    conn.commit()

    logger.info(
        "License created for %s (product=%s, tier=%s, sub=%s)",
        customer_email,
        product,
        tier,
        subscription_id,
    )

    # Email the key (best-effort — don't fail the webhook)
    send_license_email(customer_email, key, tier, product)

    return {
        "license_key_masked": masked,
        "email": customer_email,
        "product": product,
        "tier": tier,
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
    }


def handle_subscription_deleted(event: dict) -> dict:
    """Process customer.subscription.deleted — revoke associated license."""
    subscription = event.get("data", {}).get("object", {})
    subscription_id = subscription.get("id")

    if not subscription_id:
        logger.error("subscription.deleted missing subscription id: %s", event.get("id"))
        return {"error": "missing_subscription_id", "event_id": event.get("id")}

    conn = get_connection()
    row = conn.execute(
        "SELECT id, license_key_masked, email, product FROM licenses "
        "WHERE stripe_subscription_id = ? AND active = 1",
        (subscription_id,),
    ).fetchone()

    if not row:
        logger.warning("No active license found for subscription %s", subscription_id)
        return {"error": "license_not_found", "subscription_id": subscription_id}

    conn.execute("UPDATE licenses SET active = 0 WHERE id = ?", (row["id"],))
    conn.execute(
        "INSERT INTO validation_log (key_hash, machine_id, result, ip_address) "
        "SELECT key_hash, NULL, 'revoked_subscription_cancelled', 'stripe_webhook' "
        "FROM licenses WHERE id = ?",
        (row["id"],),
    )
    conn.commit()

    logger.info(
        "License revoked for %s (product=%s, sub=%s cancelled)",
        row["email"],
        row["product"],
        subscription_id,
    )

    return {
        "revoked": True,
        "license_key_masked": row["license_key_masked"],
        "email": row["email"],
        "product": row["product"],
        "subscription_id": subscription_id,
    }


def handle_payment_failed(event: dict) -> dict:
    """Process invoice.payment_failed — log warning.

    Stripe handles retry logic and dunning emails.
    We log it for visibility but don't revoke — Stripe will send
    customer.subscription.deleted if all retries fail.
    """
    invoice = event.get("data", {}).get("object", {})
    subscription_id = invoice.get("subscription")
    customer_email = invoice.get("customer_email")

    logger.warning(
        "Payment failed for %s (sub=%s). Stripe will retry.",
        customer_email,
        subscription_id,
    )

    return {
        "logged": True,
        "email": customer_email,
        "subscription_id": subscription_id,
    }


# Map event types to handlers
EVENT_HANDLERS: dict[str, object] = {
    "checkout.session.completed": handle_checkout_completed,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.payment_failed": handle_payment_failed,
}
