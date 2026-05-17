"""Tests for Stripe webhook handlers (business logic, no Stripe SDK needed)."""

from __future__ import annotations

import json
import sqlite3

import pytest

from license_server.database import run_migrations
from license_server.stripe_webhooks import (
    handle_checkout_completed,
    handle_payment_failed,
    handle_subscription_deleted,
)


@pytest.fixture
def db():
    """In-memory SQLite database with migrations applied."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn)
    return conn


@pytest.fixture(autouse=True)
def _patch_db(db, monkeypatch):
    """Patch get_connection to return the test DB."""
    monkeypatch.setattr("license_server.stripe_webhooks.get_connection", lambda *a, **kw: db)


@pytest.fixture(autouse=True)
def _patch_email(monkeypatch):
    """Stub out email delivery."""
    monkeypatch.setattr("license_server.stripe_webhooks.send_license_email", lambda *a, **kw: True)
    monkeypatch.setattr("license_server.stripe_webhooks.send_bundle_email", lambda *a, **kw: True)
    monkeypatch.setattr(
        "license_server.stripe_webhooks.send_strict_license_email", lambda *a, **kw: True
    )


def _checkout_event(
    email: str = "buyer@example.com",
    customer_id: str = "cus_test123",
    subscription_id: str = "sub_test456",
    tier: str = "pro",
    event_id: str = "evt_test789",
) -> dict:
    """Build a minimal checkout.session.completed event."""
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer_details": {"email": email},
                "customer": customer_id,
                "subscription": subscription_id,
                "metadata": {"tier": tier},
            }
        },
    }


def _subscription_deleted_event(
    subscription_id: str = "sub_test456",
    event_id: str = "evt_cancel",
) -> dict:
    """Build a minimal customer.subscription.deleted event."""
    return {
        "id": event_id,
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": subscription_id,
            }
        },
    }


def _payment_failed_event(
    subscription_id: str = "sub_test456",
    email: str = "buyer@example.com",
) -> dict:
    return {
        "id": "evt_fail",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "subscription": subscription_id,
                "customer_email": email,
            }
        },
    }


class TestCheckoutCompleted:
    """Tests for checkout.session.completed handler."""

    def test_creates_license(self, db):
        result = handle_checkout_completed(_checkout_event())

        assert "license_key_masked" in result
        assert result["email"] == "buyer@example.com"
        assert result["tier"] == "pro"
        assert result["stripe_customer_id"] == "cus_test123"
        assert result["stripe_subscription_id"] == "sub_test456"

        # Verify DB row
        row = db.execute(
            "SELECT * FROM licenses WHERE email = ?", ("buyer@example.com",)
        ).fetchone()
        assert row is not None
        assert row["active"] == 1
        assert row["tier"] == "pro"
        assert row["stripe_customer_id"] == "cus_test123"
        assert row["stripe_subscription_id"] == "sub_test456"

    def test_key_is_valid(self, db):
        result = handle_checkout_completed(_checkout_event())

        masked = result["license_key_masked"]
        assert masked.startswith("ANMD-****-****-")
        assert len(masked) == 19

    def test_missing_email_returns_error(self, db):
        event = _checkout_event()
        event["data"]["object"]["customer_details"]["email"] = None
        event["data"]["object"].pop("customer_email", None)

        result = handle_checkout_completed(event)
        assert result["error"] == "missing_email"

    def test_customer_email_fallback(self, db):
        """Falls back to customer_email if customer_details.email is missing."""
        event = _checkout_event()
        event["data"]["object"]["customer_details"]["email"] = None
        event["data"]["object"]["customer_email"] = "fallback@example.com"

        result = handle_checkout_completed(event)
        assert result["email"] == "fallback@example.com"

    def test_default_tier_is_pro(self, db):
        event = _checkout_event()
        event["data"]["object"]["metadata"] = {}

        result = handle_checkout_completed(event)
        assert result["tier"] == "pro"

    def test_stores_event_metadata(self, db):
        handle_checkout_completed(_checkout_event(event_id="evt_abc"))

        row = db.execute(
            "SELECT metadata FROM licenses WHERE email = ?",
            ("buyer@example.com",),
        ).fetchone()
        meta = json.loads(row["metadata"])
        assert meta["source"] == "stripe_checkout"
        assert meta["event_id"] == "evt_abc"

    def test_multiple_purchases_create_separate_licenses(self, db):
        handle_checkout_completed(_checkout_event(subscription_id="sub_1"))
        handle_checkout_completed(_checkout_event(subscription_id="sub_2"))

        count = db.execute(
            "SELECT COUNT(*) FROM licenses WHERE email = ?",
            ("buyer@example.com",),
        ).fetchone()[0]
        assert count == 2


class TestSubscriptionDeleted:
    """Tests for customer.subscription.deleted handler."""

    def test_revokes_license(self, db):
        handle_checkout_completed(_checkout_event())

        result = handle_subscription_deleted(_subscription_deleted_event())

        assert result["revoked"] is True
        assert result["email"] == "buyer@example.com"
        assert result["subscription_id"] == "sub_test456"

        row = db.execute(
            "SELECT active FROM licenses WHERE stripe_subscription_id = ?",
            ("sub_test456",),
        ).fetchone()
        assert row["active"] == 0

    def test_logs_revocation_audit(self, db):
        handle_checkout_completed(_checkout_event())
        handle_subscription_deleted(_subscription_deleted_event())

        log = db.execute(
            "SELECT result FROM validation_log WHERE result = 'revoked_subscription_cancelled'"
        ).fetchone()
        assert log is not None

    def test_missing_subscription_returns_error(self, db):
        result = handle_subscription_deleted(
            _subscription_deleted_event(subscription_id="sub_nonexistent")
        )
        assert result["error"] == "license_not_found"

    def test_already_revoked_returns_not_found(self, db):
        handle_checkout_completed(_checkout_event())
        handle_subscription_deleted(_subscription_deleted_event())

        result = handle_subscription_deleted(_subscription_deleted_event())
        assert result["error"] == "license_not_found"

    def test_missing_subscription_id_field(self, db):
        event = {
            "id": "evt_bad",
            "type": "customer.subscription.deleted",
            "data": {"object": {}},
        }
        result = handle_subscription_deleted(event)
        assert result["error"] == "missing_subscription_id"


class TestPaymentFailed:
    """Tests for invoice.payment_failed handler."""

    def test_logs_warning(self, db):
        result = handle_payment_failed(_payment_failed_event())

        assert result["logged"] is True
        assert result["email"] == "buyer@example.com"
        assert result["subscription_id"] == "sub_test456"

    def test_does_not_revoke(self, db):
        handle_checkout_completed(_checkout_event())
        handle_payment_failed(_payment_failed_event())

        row = db.execute(
            "SELECT active FROM licenses WHERE stripe_subscription_id = ?",
            ("sub_test456",),
        ).fetchone()
        assert row["active"] == 1


# ---------------------------------------------------------------------------
# Bundle tests
# ---------------------------------------------------------------------------


def _bundle_checkout_event(
    products: str = "anchormd,agent-lint,promptctl",
    subscription_id: str = "sub_bundle_789",
    event_id: str = "evt_bundle_001",
) -> dict:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer_details": {"email": "bundle@example.com"},
                "customer": "cus_bundle",
                "subscription": subscription_id,
                "metadata": {
                    "product": "bundle",
                    "bundle_products": products,
                    "tier": "pro",
                },
            }
        },
    }


class TestBundleCheckout:
    """Tests for bundle checkout handling."""

    def test_creates_multiple_licenses(self, db):
        result = handle_checkout_completed(_bundle_checkout_event())
        assert "bundle_id" in result
        assert len(result["licenses"]) == 3

        count = db.execute(
            "SELECT COUNT(*) FROM licenses WHERE email = ?",
            ("bundle@example.com",),
        ).fetchone()[0]
        assert count == 3

    def test_all_products_have_correct_prefix(self, db):
        result = handle_checkout_completed(_bundle_checkout_event())
        prefixes = {lic["masked"][:4] for lic in result["licenses"]}
        assert prefixes == {"ANMD", "ALNT", "PCTL"}

    def test_all_licenses_share_bundle_id(self, db):
        result = handle_checkout_completed(_bundle_checkout_event())
        bundle_id = result["bundle_id"]

        rows = db.execute(
            "SELECT bundle_id FROM licenses WHERE email = ?",
            ("bundle@example.com",),
        ).fetchall()
        assert all(row["bundle_id"] == bundle_id for row in rows)

    def test_default_bundle_products_when_empty(self, db):
        result = handle_checkout_completed(_bundle_checkout_event(products=""))
        # Should fall back to BUNDLE_PRODUCTS (all 6, including auditchain)
        assert len(result["licenses"]) == 6

    def test_bundle_revocation_revokes_all(self, db):
        handle_checkout_completed(_bundle_checkout_event(subscription_id="sub_bundle_rev"))

        result = handle_subscription_deleted(
            _subscription_deleted_event(subscription_id="sub_bundle_rev")
        )

        assert result["revoked"] is True
        assert result["revoked_count"] == 3

        active = db.execute(
            "SELECT COUNT(*) FROM licenses WHERE email = ? AND active = 1",
            ("bundle@example.com",),
        ).fetchone()[0]
        assert active == 0


def _strict_checkout_event(
    *,
    email: str = "team@example.com",
    seats: str | None = "5",
    quantity: int | None = None,
    customer_id: str = "cus_strict",
    subscription_id: str = "sub_strict",
    event_id: str = "evt_strict",
) -> dict:
    """Build a checkout.session.completed for a Strict purchase.

    seats: metadata.seats string (None to omit and rely on line_item quantity).
    quantity: when set, builds a line_items array with this quantity.
    """
    metadata: dict[str, str] = {"product": "anchormd", "tier": "strict"}
    if seats is not None:
        metadata["seats"] = seats

    session: dict[str, object] = {
        "customer_details": {"email": email},
        "customer": customer_id,
        "subscription": subscription_id,
        "metadata": metadata,
    }
    if quantity is not None:
        session["line_items"] = {"data": [{"quantity": quantity}]}

    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {"object": session},
    }


class TestCheckoutStrict:
    """Tests for the Strict tier checkout path (Day 4 of v0.6.0)."""

    def test_strict_seat_monthly_creates_license_with_1_seat(self, db):
        """Default seat-monthly link carries metadata.seats=1."""
        result = handle_checkout_completed(_strict_checkout_event(seats="1"))
        assert result["tier"] == "strict"
        assert result["seats"] == 1

        row = db.execute(
            "SELECT tier, metadata FROM licenses WHERE email = ?",
            ("team@example.com",),
        ).fetchone()
        assert row["tier"] == "strict"
        meta = json.loads(row["metadata"])
        assert meta["seats"] == 1

    def test_strict_team_5_creates_license_with_5_seats(self, db):
        result = handle_checkout_completed(_strict_checkout_event(seats="5"))
        assert result["seats"] == 5

        row = db.execute(
            "SELECT metadata FROM licenses WHERE email = ?",
            ("team@example.com",),
        ).fetchone()
        meta = json.loads(row["metadata"])
        assert meta["seats"] == 5

    def test_strict_team_25_creates_license_with_25_seats(self, db):
        result = handle_checkout_completed(_strict_checkout_event(seats="25"))
        assert result["seats"] == 25

        row = db.execute(
            "SELECT metadata FROM licenses WHERE email = ?",
            ("team@example.com",),
        ).fetchone()
        meta = json.loads(row["metadata"])
        assert meta["seats"] == 25

    def test_strict_falls_back_to_line_item_quantity(self, db):
        """When metadata.seats is absent, derive from buyer's quantity slider."""
        result = handle_checkout_completed(_strict_checkout_event(seats=None, quantity=8))
        assert result["seats"] == 8

        row = db.execute(
            "SELECT metadata FROM licenses WHERE email = ?",
            ("team@example.com",),
        ).fetchone()
        meta = json.loads(row["metadata"])
        assert meta["seats"] == 8

    def test_strict_sends_strict_email_not_standard(self, db, monkeypatch):
        """Strict checkout fires send_strict_license_email, never send_license_email."""
        strict_calls = []
        standard_calls = []
        monkeypatch.setattr(
            "license_server.stripe_webhooks.send_strict_license_email",
            lambda *a, **kw: strict_calls.append(a) or True,
        )
        monkeypatch.setattr(
            "license_server.stripe_webhooks.send_license_email",
            lambda *a, **kw: standard_calls.append(a) or True,
        )

        handle_checkout_completed(_strict_checkout_event(seats="5"))

        assert len(strict_calls) == 1
        assert len(standard_calls) == 0
        # send_strict_license_email signature: (email, key, seats)
        email_arg, key_arg, seats_arg = strict_calls[0]
        assert email_arg == "team@example.com"
        assert key_arg.startswith("ANMD-")
        assert seats_arg == 5
