"""POST /v1/webhooks/stripe — Stripe webhook endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request

from license_server.config import get_stripe_webhook_secret
from license_server.rate_limit import limiter
from license_server.stripe_webhooks import EVENT_HANDLERS

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/webhooks/stripe")
@limiter.limit("30/minute")
async def stripe_webhook(request: Request) -> dict:
    """Receive and process Stripe webhook events.

    Verifies the webhook signature using the Stripe SDK, then
    dispatches to the appropriate handler based on event type.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    webhook_secret = get_stripe_webhook_secret()
    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Verify signature
    try:
        import stripe

        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ImportError as exc:
        logger.error("stripe package not installed")
        raise HTTPException(status_code=500, detail="Stripe SDK not available") from exc
    except stripe.error.SignatureVerificationError as exc:
        logger.warning("Invalid webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature") from exc
    except Exception as exc:
        logger.error("Webhook verification failed: %s", exc)
        raise HTTPException(status_code=400, detail="Verification failed") from exc

    event_type = event.get("type", "")
    event_id = event.get("id", "unknown")

    handler = EVENT_HANDLERS.get(event_type)
    if handler is None:
        logger.debug("Ignoring unhandled event type: %s", event_type)
        return {"received": True, "event_type": event_type, "handled": False}

    logger.info("Processing %s (event=%s)", event_type, event_id)
    result = handler(event)

    return {"received": True, "event_type": event_type, "handled": True, **result}
