import requests
from config import REQUEST_TIMEOUT, USER_AGENT

API_URL = "https://en.wikipedia.org/w/api.php"


def lookup_company(name: str) -> dict:
    """
    Free, no-key Wikipedia summary lookup. Only useful for companies notable
    enough to have an article - silently returns empty for the long tail,
    which is most leads. That's fine, it's a bonus source, not primary.
    """
    out = {"summary": None, "url": None, "ok": False}
    if not name:
        return out
    try:
        resp = requests.get(
            API_URL,
            params={
                "action": "query", "list": "search", "srsearch": f"{name} company",
                "format": "json", "srlimit": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        results = resp.json().get("query", {}).get("search", [])
        if not results:
            return out
        title = results[0]["title"]

        resp2 = requests.get(
            API_URL,
            params={
                "action": "query", "prop": "extracts", "exintro": True,
                "explaintext": True, "titles": title, "format": "json",
            },
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        pages = resp2.json().get("query", {}).get("pages", {})
        for page in pages.values():
            extract = page.get("extract")
            if extract:
                out["ok"] = True
                out["summary"] = extract[:600]
                out["url"] = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                break
    except (requests.RequestException, ValueError, KeyError):
        pass
    return out
