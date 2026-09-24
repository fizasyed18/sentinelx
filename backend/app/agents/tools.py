"""External tool/API integrations used by the agent graph.

Two independent external integrations are implemented here:
  1. Slack Web API / Incoming Webhook -- real-time human alerting.
  2. Threat-intel / IP geolocation lookup (ipapi.co) -- context enrichment.

Both fail soft: if the network call fails or no credentials are configured,
they log a warning and return a safe fallback so the pipeline never breaks.
"""
import requests

from app.config import settings
from app.logging_conf import get_logger

log = get_logger("tools")


def send_slack_alert(text: str) -> bool:
    """Post an incident alert to Slack via an Incoming Webhook."""
    if not settings.SLACK_WEBHOOK_URL:
        log.warning("slack_alert_skipped", reason="SLACK_WEBHOOK_URL not configured", preview=text[:120])
        return False
    try:
        resp = requests.post(settings.SLACK_WEBHOOK_URL, json={"text": text}, timeout=5)
        resp.raise_for_status()
        log.info("slack_alert_sent")
        return True
    except requests.RequestException as exc:
        log.error("slack_alert_failed", error=str(exc))
        return False


def lookup_ip_reputation(ip_address: str | None) -> dict:
    """Enrich an event with geolocation / network context for a source IP.

    Uses the free ipapi.co endpoint (no key required). Falls back to a
    neutral, clearly-labeled mock result if the lookup fails or no IP is
    present, so downstream agents always receive a well-formed dict.
    """
    fallback = {
        "ip": ip_address,
        "source": "fallback",
        "country": "unknown",
        "org": "unknown",
        "is_private_or_unresolvable": True,
    }
    if not ip_address:
        return fallback
    try:
        resp = requests.get(f"https://ipapi.co/{ip_address}/json/", timeout=settings.THREAT_INTEL_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return {
            "ip": ip_address,
            "source": "ipapi.co",
            "country": data.get("country_name", "unknown"),
            "org": data.get("org", "unknown"),
            "is_private_or_unresolvable": False,
        }
    except requests.RequestException as exc:
        log.warning("ip_lookup_failed", ip=ip_address, error=str(exc))
        return fallback
