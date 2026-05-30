"""Email delivery for license keys via SMTP."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from license_server.config import (
    get_smtp_from,
    get_smtp_host,
    get_smtp_password,
    get_smtp_port,
    get_smtp_user,
)

logger = logging.getLogger(__name__)

# Product display names and env var names for activation instructions
PRODUCT_INFO: dict[str, dict[str, str]] = {
    "anchormd": {
        "display": "AnchorMD",
        "env_var": "ANCHORMD_LICENSE",
        "file": "~/.anchormd-license",
        "issues": "https://github.com/Arete-Consortium/anchormd/issues",
    },
    "agent-lint": {
        "display": "Agent Lint",
        "env_var": "AGENT_LINT_LICENSE",
        "file": "~/.agent-lint-license",
        "issues": "https://github.com/AreteDriver/agent-lint/issues",
    },
    "ai-spend": {
        "display": "AI Spend",
        "env_var": "AI_SPEND_LICENSE",
        "file": "~/.ai-spend-license",
        "issues": "https://github.com/AreteDriver/ai-spend/issues",
    },
    "promptctl": {
        "display": "PromptCTL",
        "env_var": "PROMPTCTL_LICENSE",
        "file": "~/.promptctl-license",
        "issues": "https://github.com/AreteDriver/promptctl/issues",
    },
    "context-hygiene": {
        "display": "Context Hygiene",
        "env_var": "CONTEXT_HYGIENE_LICENSE",
        "file": "~/.context-hygiene-license",
        "issues": "https://github.com/AreteDriver/context-hygiene/issues",
    },
}


def send_license_email(
    email: str, license_key: str, tier: str = "pro", product: str = "anchormd"
) -> bool:
    """Send a license key to the customer via SMTP.

    Returns True on success, False on failure (never raises).
    """
    smtp_user = get_smtp_user()
    smtp_password = get_smtp_password()

    if not smtp_user or not smtp_password:
        logger.warning("SMTP not configured — skipping email to %s", email)
        return False

    info = PRODUCT_INFO.get(product, PRODUCT_INFO["anchormd"])

    msg = EmailMessage()
    msg["Subject"] = f"Your {info['display']} {tier.title()} License Key"
    msg["From"] = get_smtp_from()
    msg["To"] = email
    msg.set_content(_build_body(license_key, tier, product))

    try:
        with smtplib.SMTP(get_smtp_host(), get_smtp_port(), timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("License key emailed to %s for %s", email, product)
        return True
    except Exception:
        logger.exception("Failed to email license key to %s", email)
        return False


def send_strict_license_email(email: str, license_key: str, seats: int) -> bool:
    """Send a Strict-tier welcome email with CI setup snippet + seat info.

    Returns True on success, False on failure (never raises).
    """
    smtp_user = get_smtp_user()
    smtp_password = get_smtp_password()

    if not smtp_user or not smtp_password:
        logger.warning("SMTP not configured — skipping Strict email to %s", email)
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Your AnchorMD Strict License — {seats} seat{'s' if seats != 1 else ''}"
    msg["From"] = get_smtp_from()
    msg["To"] = email
    msg.set_content(_build_strict_body(license_key, seats))

    try:
        with smtplib.SMTP(get_smtp_host(), get_smtp_port(), timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("Strict license emailed to %s (%d seats)", email, seats)
        return True
    except Exception:
        logger.exception("Failed to email Strict license to %s", email)
        return False


def send_bundle_email(
    email: str,
    licenses: list[tuple[str, str]],
    tier: str = "pro",
    bundle_id: str | None = None,
) -> bool:
    """Send multiple license keys in a single email.

    licenses: list of (product, plaintext_key) tuples.
    Returns True on success, False on failure (never raises).
    """
    smtp_user = get_smtp_user()
    smtp_password = get_smtp_password()

    if not smtp_user or not smtp_password:
        logger.warning("SMTP not configured — skipping bundle email to %s", email)
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Your Pro Bundle License Keys ({len(licenses)} products)"
    msg["From"] = get_smtp_from()
    msg["To"] = email
    msg.set_content(_build_bundle_body(licenses, tier, bundle_id))

    try:
        with smtplib.SMTP(get_smtp_host(), get_smtp_port(), timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("Bundle email sent to %s (%d keys)", email, len(licenses))
        return True
    except Exception:
        logger.exception("Failed to email bundle keys to %s", email)
        return False


def send_aicards_email(
    email: str,
    pack_type: str,
    success: bool = True,
    cards: list[dict] | None = None,
) -> bool:
    """Send an AI Cards pack purchase confirmation email.

    Returns True on success, False on failure (never raises).
    """
    smtp_user = get_smtp_user()
    smtp_password = get_smtp_password()

    if not smtp_user or not smtp_password:
        logger.warning("SMTP not configured — skipping aicards email to %s", email)
        return False

    pack_label = pack_type.upper().replace("EXE", ".EXE").replace("SYS", ".SYS")
    msg = EmailMessage()
    msg["From"] = get_smtp_from()
    msg["To"] = email

    if success and cards:
        msg["Subject"] = f"AI Cards — Your {pack_label} pack has been minted!"
        card_lines = []
        for c in cards:
            name = c.get("card_name", c.get("card_id", "Unknown"))
            rarity = c.get("rarity", "")
            card_lines.append(f"    {rarity:10s}  {name}")
        body = (
            f"Your {pack_label} pack ({len(cards)} cards) has been minted on Sui!\n\n"
            "Cards received:\n" + "\n".join(card_lines) + "\n\n"
            "View your collection at https://aicards.fun\n\n"
            "— AI Cards TCG"
        )
    else:
        msg["Subject"] = f"AI Cards — Issue with your {pack_label} pack purchase"
        body = (
            f"We received your payment for a {pack_label} pack, but there was an "
            "issue minting your cards.\n\n"
            "This usually means we couldn't find your Sui wallet address. "
            "Please reply to this email with your Sui address (0x...) and we'll "
            "mint your cards manually.\n\n"
            "— AI Cards TCG"
        )

    msg.set_content(body)

    try:
        with smtplib.SMTP(get_smtp_host(), get_smtp_port(), timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("Aicards email sent to %s (pack=%s, success=%s)", email, pack_type, success)
        return True
    except Exception:
        logger.exception("Failed to email aicards confirmation to %s", email)
        return False


def _build_bundle_body(
    licenses: list[tuple[str, str]], tier: str, bundle_id: str | None = None
) -> str:
    """Build the plain-text email body for a bundle purchase."""
    lines = [f"Thanks for purchasing the Pro Bundle ({tier.title()})!\n"]
    lines.append(f"Bundle ID: {bundle_id or 'N/A'}\n")
    lines.append("Your license keys:\n")

    for product, key in licenses:
        info = PRODUCT_INFO.get(product, PRODUCT_INFO["anchormd"])
        lines.append(f"  {info['display']}:")
        lines.append(f"    Key: {key}")
        lines.append(f'    Activate: export {info["env_var"]}="{key}"')
        lines.append(f'    Or save: echo "{key}" > {info["file"]}\n')

    lines.append("These keys are shown once — save them somewhere safe.\n")
    lines.append("If you have questions, reply to this email.\n")
    lines.append("— Arete Consortium")
    return "\n".join(lines)


def _build_strict_body(license_key: str, seats: int) -> str:
    """Build the plain-text welcome email body for a Strict license."""
    seat_word = "seat" if seats == 1 else "seats"
    return f"""Thanks for purchasing AnchorMD Strict!

Your license: {license_key}
Seats: {seats} {seat_word}

── 1. Activate the license ──

    export ANCHORMD_LICENSE="{license_key}"

Or save it to a file:

    echo "{license_key}" > ~/.anchormd-license

── 2. Enable fail-closed validation in CI ──

Strict's headline feature is fail-closed license validation. Add this to your
GitHub Actions workflow (or equivalent for your CI):

    env:
      ANCHORMD_LICENSE: ${{{{ secrets.ANCHORMD_LICENSE }}}}
      ANCHORMD_STRICT: "1"

With ANCHORMD_STRICT=1, the CLI exits non-zero on any license validation
failure (server unreachable, key revoked, expired) — your CI fails closed
instead of silently downgrading to Free.

── 3. Strict-only features ──

    * Fail-closed license validation (ANCHORMD_STRICT)
    * CI integration (PR comment automation)
    * Drift detection — generate, fix, LLM judge, CI mode, HTML reports
    * Fleet audit with --json export + history
    * Team seats ({seats} machine activations on this license)
    * Audit log (every scan recorded, 1-year retention, CSV export)

── 4. Seat management ──

This license supports {seats} concurrent machines. Each device that runs
anchormd claims one seat automatically on first use. Manage seats at:
https://anchormd.dev/strict/seats (admin) or contact support to release a
stuck seat.

── 5. Need help? ──

CI setup recipes, audit log export, and procurement docs:
https://anchormd.dev/strict/docs

This key is shown once — save it somewhere safe.

— Arete Consortium
"""


def _build_body(license_key: str, tier: str, product: str = "anchormd") -> str:
    """Build the plain-text email body."""
    info = PRODUCT_INFO.get(product, PRODUCT_INFO["anchormd"])
    return f"""Thanks for purchasing {info["display"]} {tier.title()}!

Your license key:

    {license_key}

To activate, set the environment variable:

    export {info["env_var"]}="{license_key}"

Or save it to a file:

    echo "{license_key}" > {info["file"]}

This key is shown once — save it somewhere safe.

If you have questions, reply to this email or open an issue:
{info["issues"]}

— Arete Consortium
"""
