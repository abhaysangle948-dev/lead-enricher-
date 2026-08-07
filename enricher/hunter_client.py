import requests
from config import HUNTER_API_KEY, REQUEST_TIMEOUT

BASE_URL = "https://api.hunter.io/v2"


def is_configured() -> bool:
    return bool(HUNTER_API_KEY)


def domain_search(domain: str) -> dict:
    """
    Free tier: ~25-50 credits/month depending on current Hunter plan terms.
    Returns None (not an error) if no key is configured, so callers can
    just skip this source cleanly.
    """
    if not is_configured():
        return None
    try:
        resp = requests.get(
            f"{BASE_URL}/domain-search",
            params={"domain": domain, "api_key": HUNTER_API_KEY, "limit": 5},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            emails = data.get("emails", [])
            return {
                "organization": data.get("organization"),
                "pattern": data.get("pattern"),
                "people": [
                    {
                        "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
                        "email": e.get("value"),
                        "title": e.get("position"),
                        "confidence": e.get("confidence"),
                    }
                    for e in emails[:5]
                ],
            }
        if resp.status_code == 429:
            return {"error": "quota_exceeded"}
    except requests.RequestException:
        pass
    return {"error": "request_failed"}
