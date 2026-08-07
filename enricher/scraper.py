import re
import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?\(?\d{2,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4}")

SOCIAL_PATTERNS = {
    "linkedin_url": r"linkedin\.com/(?:company|in)/[\w-]+",
    "twitter_url": r"(?:twitter\.com|x\.com)/[\w]+",
    "facebook_url": r"facebook\.com/[\w.]+",
    "instagram_url": r"instagram\.com/[\w.]+",
    "github_url": r"github\.com/[\w-]+",
}

TECH_SIGNATURES = {
    "WordPress": ["wp-content", "wp-includes"],
    "Shopify": ["cdn.shopify.com", "Shopify.theme"],
    "Wix": ["wix.com", "wixstatic.com"],
    "Squarespace": ["squarespace.com", "squarespace-cdn"],
    "Webflow": ["webflow.com", "webflow.js"],
    "React": ["__next_data__", "react-dom", "_app.js"],
    "Vue.js": ["vue.js", "__vue__"],
    "Angular": ["ng-version", "ng-app"],
    "Google Analytics": ["googletagmanager.com", "gtag(", "google-analytics.com"],
    "Hotjar": ["static.hotjar.com"],
    "HubSpot": ["js.hs-scripts.com", "hs-analytics"],
    "Mailchimp": ["list-manage.com", "mailchimp"],
    "Stripe": ["js.stripe.com"],
    "Salesforce": ["force.com", "salesforce.com"],
    "Intercom": ["widget.intercom.io"],
    "Zendesk": ["zdassets.com", "zendesk.com"],
    "Cloudflare": ["cloudflare.com/cdn-cgi", "__cf_bm"],
}


def _fetch(url: str):
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return None


def scrape_company_site(domain: str) -> dict:
    """
    Best-effort scrape of the company homepage. Returns a dict of whatever
    was found; missing fields are simply absent, never fabricated.
    """
    out = {
        "company_name": None,
        "company_description": None,
        "company_logo": None,
        "contact_email": None,
        "contact_phone": None,
        "tech_stack": [],
        "linkedin_url": None,
        "twitter_url": None,
        "facebook_url": None,
        "instagram_url": None,
        "github_url": None,
        "ok": False,
    }

    html = _fetch(f"https://{domain}") or _fetch(f"http://{domain}")
    if not html:
        return out

    out["ok"] = True
    soup = BeautifulSoup(html, "html.parser")

    # Name: og:site_name > <title> > <h1>
    og_site_name = soup.find("meta", property="og:site_name")
    if og_site_name and og_site_name.get("content"):
        out["company_name"] = og_site_name["content"].strip()
    elif soup.title and soup.title.string:
        out["company_name"] = soup.title.string.strip().split("|")[0].split("-")[0].strip()

    # Description: og:description > meta description
    og_desc = soup.find("meta", property="og:description")
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if og_desc and og_desc.get("content"):
        out["company_description"] = og_desc["content"].strip()
    elif meta_desc and meta_desc.get("content"):
        out["company_description"] = meta_desc["content"].strip()

    # Logo: og:image
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        out["company_logo"] = og_image["content"].strip()

    # Contact email / phone from visible text + mailto/tel links
    text = soup.get_text(" ", strip=True)
    mailtos = [a["href"].replace("mailto:", "").split("?")[0]
               for a in soup.find_all("a", href=True) if a["href"].startswith("mailto:")]
    emails = mailtos or EMAIL_RE.findall(text)
    generic_prefixes = ("info@", "contact@", "hello@", "support@", "sales@")
    preferred = [e for e in emails if e.lower().startswith(generic_prefixes)]
    if preferred:
        out["contact_email"] = preferred[0]
    elif emails:
        out["contact_email"] = emails[0]

    tels = [a["href"].replace("tel:", "") for a in soup.find_all("a", href=True)
            if a["href"].startswith("tel:")]
    if tels:
        out["contact_phone"] = tels[0]
    else:
        phone_match = PHONE_RE.search(text)
        if phone_match:
            out["contact_phone"] = phone_match.group(0)

    # Social links
    html_lower = html.lower()
    for field, pattern in SOCIAL_PATTERNS.items():
        m = re.search(pattern, html_lower)
        if m:
            out[field] = "https://" + m.group(0)

    # Tech stack signatures
    detected = []
    for tech, signatures in TECH_SIGNATURES.items():
        if any(sig.lower() in html_lower for sig in signatures):
            detected.append(tech)
    out["tech_stack"] = detected

    return out


def scrape_about_page_for_funding(domain: str) -> dict:
    """
    Best-effort only. We deliberately do NOT scrape Crunchbase or LinkedIn --
    both actively block scraping and doing so risks the source IP getting
    banned. Instead we check the company's own about/press pages for
    funding-related keywords, which is far more reliable to reach.
    """
    out = {"funding_mentioned": False, "snippet": None}
    for path in ("/about", "/about-us", "/press", "/news"):
        html = _fetch(f"https://{domain}{path}")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        for kw in ("raised $", "funding round", "series a", "series b", "series c",
                   "seed round", "venture capital", "investors include"):
            idx = text.lower().find(kw)
            if idx != -1:
                out["funding_mentioned"] = True
                out["snippet"] = text[max(0, idx - 80):idx + 160].strip()
                return out
    return out
