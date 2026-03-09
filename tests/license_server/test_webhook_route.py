"""Tests for the POST /v1/webhooks/stripe endpoint."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from license_server import main as main_module
from license_server.database import run_migrations
from license_server.main import app
from license_server.rate_limit import limiter


@pytest.fixture
def db(tmp_path):
    import sqlite3

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn)
    return conn


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(main_module, "_db_path_override", ":memory:")

    def _get_test_conn(db_path=None):
        return db

    monkeypatch.setattr("license_server.main.get_connection", _get_test_conn)
    monkeypatch.setattr("license_server.database._connection", db)

    limiter.enabled = False
    with TestClient(app) as c:
        yield c
    limiter.enabled = True


def _checkout_payload(email: str = "buyer@example.com") -> dict:
    return {
        "id": "evt_test",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer_details": {"email": email},
                "customer": "cus_test",
                "subscription": "sub_test",
                "metadata": {"tier": "pro"},
            }
        },
    }


class TestWebhookEndpoint:
    """Tests for /v1/webhooks/stripe route."""

    def test_missing_webhook_secret_returns_500(self, client, monkeypatch):
        monkeypatch.setattr("license_server.routes.webhook.get_stripe_webhook_secret", lambda: None)
        resp = client.post(
            "/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "t=123,v1=abc"},
        )
        assert resp.status_code == 500
        assert "not configured" in resp.json()["detail"]

    def test_invalid_signature_returns_400(self, client, monkeypatch):
        monkeypatch.setattr(
            "license_server.routes.webhook.get_stripe_webhook_secret", lambda: "whsec_test"
        )

        mock_stripe = MagicMock()
        mock_stripe.error.SignatureVerificationError = type(
            "SignatureVerificationError", (Exception,), {}
        )
        mock_stripe.Webhook.construct_event.side_effect = (
            mock_stripe.error.SignatureVerificationError("bad sig")
        )

        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            resp = client.post(
                "/v1/webhooks/stripe",
                content=json.dumps(_checkout_payload()).encode(),
                headers={"stripe-signature": "t=123,v1=bad"},
            )
        assert resp.status_code == 400

    def test_successful_checkout_webhook(self, client, db, monkeypatch):
        monkeypatch.setattr(
            "license_server.routes.webhook.get_stripe_webhook_secret", lambda: "whsec_test"
        )
        monkeypatch.setattr(
            "license_server.stripe_webhooks.send_license_email", lambda *a, **kw: True
        )
        # Patch get_connection in stripe_webhooks to use test db
        monkeypatch.setattr("license_server.stripe_webhooks.get_connection", lambda *a, **kw: db)

        event_data = _checkout_payload()
        mock_stripe = MagicMock()
        mock_stripe.error.SignatureVerificationError = type(
            "SignatureVerificationError", (Exception,), {}
        )
        mock_stripe.Webhook.construct_event.return_value = event_data

        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            resp = client.post(
                "/v1/webhooks/stripe",
                content=json.dumps(event_data).encode(),
                headers={"stripe-signature": "t=123,v1=valid"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["received"] is True
        assert body["handled"] is True
        assert body["email"] == "buyer@example.com"

        # Verify license was created in DB
        row = db.execute(
            "SELECT * FROM licenses WHERE email = ?", ("buyer@example.com",)
        ).fetchone()
        assert row is not None
        assert row["active"] == 1

    def test_unhandled_event_type_returns_ok(self, client, monkeypatch):
        monkeypatch.setattr(
            "license_server.routes.webhook.get_stripe_webhook_secret", lambda: "whsec_test"
        )

        event_data = {"id": "evt_x", "type": "charge.refunded", "data": {"object": {}}}
        mock_stripe = MagicMock()
        mock_stripe.error.SignatureVerificationError = type(
            "SignatureVerificationError", (Exception,), {}
        )
        mock_stripe.Webhook.construct_event.return_value = event_data

        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            resp = client.post(
                "/v1/webhooks/stripe",
                content=json.dumps(event_data).encode(),
                headers={"stripe-signature": "t=123,v1=valid"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["handled"] is False

    def test_stripe_sdk_not_installed(self, client, monkeypatch):
        monkeypatch.setattr(
            "license_server.routes.webhook.get_stripe_webhook_secret", lambda: "whsec_test"
        )

        # Simulate stripe not installed by making import fail
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "stripe":
                raise ImportError("No module named 'stripe'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        resp = client.post(
            "/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "t=123,v1=abc"},
        )
        assert resp.status_code == 500
        assert "not available" in resp.json()["detail"]
