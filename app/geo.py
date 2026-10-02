"""IP -> geolocation enrichment with a provider fallback chain.

Tries provider A first, then provider B on any failure (timeout, non-2xx,
unparseable body). If both are unavailable, returns (None, None, None) so the
caller can still store the submission without geo data -- enrichment must
degrade, never block, the write path.

Each provider can be disabled via settings (GEO_PROVIDER_A_DISABLED /
GEO_PROVIDER_B_DISABLED) to make the fallback deterministic for the
acceptance probe, without depending on the real provider actually being down.
"""

import httpx

from app.config import settings

TIMEOUT = httpx.Timeout(3.0)


def _call_provider_a(ip: str) -> tuple[str | None, str | None]:
    url = settings.geo_provider_a_url.format(ip=ip)
    resp = httpx.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") == "fail":
        raise ValueError(body.get("message", "provider A failed"))
    return body.get("country"), body.get("city")


def _call_provider_b(ip: str) -> tuple[str | None, str | None]:
    url = settings.geo_provider_b_url.format(ip=ip)
    resp = httpx.get(url, timeout=TIMEOUT)
    resp.raise_for_status()
    body = resp.json()
    if body.get("error"):
        raise ValueError(body.get("reason", "provider B failed"))
    return body.get("country_name"), body.get("city")


def enrich_ip(ip: str) -> tuple[str | None, str | None, str | None]:
    """Returns (country, city, provider_name_used) -- provider_name_used is
    None when every provider failed or is disabled."""
    if not ip or ip in ("127.0.0.1", "testclient", "localhost"):
        return None, None, None

    if not settings.geo_provider_a_disabled:
        try:
            country, city = _call_provider_a(ip)
            return country, city, "provider_a"
        except Exception:
            pass

    if not settings.geo_provider_b_disabled:
        try:
            country, city = _call_provider_b(ip)
            return country, city, "provider_b"
        except Exception:
            pass

    return None, None, None
