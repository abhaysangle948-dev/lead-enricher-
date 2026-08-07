import whois as pywhois


def lookup(domain: str) -> dict:
    """Free WHOIS lookup, no key required. Best-effort - many registrars redact data."""
    out = {"registrar": None, "created": None, "country": None, "ok": False}
    try:
        w = pywhois.whois(domain)
        if w:
            out["ok"] = True
            out["registrar"] = w.get("registrar")
            created = w.get("creation_date")
            if isinstance(created, list):
                created = created[0] if created else None
            out["created"] = str(created) if created else None
            out["country"] = w.get("country")
    except Exception:
        pass
    return out
