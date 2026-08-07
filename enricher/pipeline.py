from enricher import input_detector, scraper, whois_client, wikipedia_client, hunter_client
from database import lead_repo


def run(lead_id: int, raw_input: dict):
    """
    Runs synchronously and writes progressive updates to the lead row so the
    frontend can poll /api/leads/<id> and watch status move
    pending -> partial -> complete/failed.
    """
    sources = {}
    result = {}

    try:
        detected = input_detector.detect(raw_input)
        domain = detected["domain"]

        if not domain and not detected["company"]:
            lead_repo.update_lead(lead_id, {
                "enrichment_status": "failed",
                "error_message": "Could not determine a domain or company name from the input.",
            })
            return

        # --- Website scrape (primary source, no key needed) ---
        if domain:
            site = scraper.scrape_company_site(domain)
            sources["website_scrape"] = "ok" if site["ok"] else "failed"
            if site["ok"]:
                result.update({
                    "company_name": site["company_name"],
                    "company_description": site["company_description"],
                    "company_logo": site["company_logo"],
                    "contact_email": site["contact_email"],
                    "contact_phone": site["contact_phone"],
                    "tech_stack": site["tech_stack"],
                    "linkedin_url": site["linkedin_url"],
                    "twitter_url": site["twitter_url"],
                    "facebook_url": site["facebook_url"],
                    "instagram_url": site["instagram_url"],
                    "github_url": site["github_url"],
                })
            lead_repo.update_lead(lead_id, {**result, "enrichment_status": "partial",
                                             "data_sources": sources})
        else:
            sources["website_scrape"] = "skipped_no_domain"

        # --- WHOIS (free, no key) ---
        if domain:
            wi = whois_client.lookup(domain)
            sources["whois"] = "ok" if wi["ok"] else "failed"
            if wi["ok"]:
                result["company_location"] = wi.get("country")
                result["company_founded_year"] = (wi.get("created") or "")[:4] or None

        # --- Wikipedia (free, no key, best-effort for known companies) ---
        name_to_search = result.get("company_name") or detected.get("company")
        if name_to_search:
            wiki = wikipedia_client.lookup_company(name_to_search)
            sources["wikipedia"] = "ok" if wiki["ok"] else "not_found"
            if wiki["ok"] and not result.get("company_description"):
                result["company_description"] = wiki["summary"]

        # --- About/press page funding check (best-effort, own-site only) ---
        if domain:
            funding = scraper.scrape_about_page_for_funding(domain)
            sources["funding_scan"] = "found" if funding["funding_mentioned"] else "not_found"
            if funding["funding_mentioned"]:
                result["funding_info"] = funding

        # --- Hunter.io (optional - only runs if HUNTER_API_KEY is set) ---
        if domain:
            if hunter_client.is_configured():
                hunter = hunter_client.domain_search(domain)
                if hunter and "error" not in hunter:
                    sources["hunter_io"] = "ok"
                    people = hunter.get("people") or []
                    if people and not result.get("contact_email"):
                        result["contact_name"] = people[0]["name"]
                        result["contact_title"] = people[0]["title"]
                        result["contact_email"] = people[0]["email"]
                else:
                    sources["hunter_io"] = (hunter or {}).get("error", "failed")
            else:
                sources["hunter_io"] = "skipped_no_key"

        # Carry forward whatever the user typed in that we didn't already fill
        result.setdefault("company_name", detected.get("company"))
        result.setdefault("contact_name", detected.get("name"))
        if detected.get("linkedin"):
            result.setdefault("linkedin_url", detected["linkedin"])

        result["data_sources"] = sources
        any_data = any(v for k, v in result.items() if k != "data_sources")
        result["enrichment_status"] = "complete" if any_data else "failed"
        if not any_data:
            result["error_message"] = "No public data found for this input. Try a different domain or email."

        lead_repo.update_lead(lead_id, result)

    except Exception as exc:  # keep the pipeline from ever crashing the request thread
        lead_repo.update_lead(lead_id, {
            "enrichment_status": "failed",
            "error_message": f"Unexpected error: {exc}",
            "data_sources": sources,
        })
