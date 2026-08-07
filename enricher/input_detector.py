import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"^[\w.+-]+@([\w-]+\.[\w.-]+)$")
DOMAIN_RE = re.compile(r"^(?:https?://)?(?:www\.)?([\w-]+(?:\.[\w-]+)+)(?:/.*)?$")
LINKEDIN_RE = re.compile(r"linkedin\.com/(in|company)/([\w-]+)")

FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "aol.com", "protonmail.com", "live.com",
}


def normalize_domain(raw: str) -> str:
    raw = raw.strip().lower()
    raw = re.sub(r"^https?://", "", raw)
    raw = re.sub(r"^www\.", "", raw)
    raw = raw.split("/")[0]
    return raw


def detect(input_data: dict) -> dict:
    """
    input_data: any combination of {email, domain, name, company, linkedin}
    Returns a normalized dict with a resolved `domain` when derivable, and
    flags describing what we have to work with.
    """
    result = {
        "email": (input_data.get("email") or "").strip() or None,
        "domain": None,
        "name": (input_data.get("name") or "").strip() or None,
        "company": (input_data.get("company") or "").strip() or None,
        "linkedin": None,
        "linkedin_type": None,  # "in" (person) or "company"
        "is_free_email": False,
    }

    # LinkedIn URL
    li = input_data.get("linkedin", "")
    m = LINKEDIN_RE.search(li) if li else None
    if m:
        result["linkedin"] = f"https://www.linkedin.com/{m.group(1)}/{m.group(2)}/"
        result["linkedin_type"] = "person" if m.group(1) == "in" else "company"

    # Email -> domain
    if result["email"]:
        m = EMAIL_RE.match(result["email"])
        if m:
            domain = m.group(1).lower()
            result["is_free_email"] = domain in FREE_EMAIL_DOMAINS
            if not result["is_free_email"]:
                result["domain"] = domain

    # Explicit domain field, or a company field that looks like a domain
    raw_domain = input_data.get("domain") or ""
    if raw_domain and DOMAIN_RE.match(raw_domain):
        result["domain"] = normalize_domain(raw_domain)
    elif not result["domain"] and result["company"] and DOMAIN_RE.match(result["company"]) \
            and "." in result["company"]:
        result["domain"] = normalize_domain(result["company"])

    return result
