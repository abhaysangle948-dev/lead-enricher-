# Lead Enricher

Works with **zero API keys**. Takes an email, domain, name+company, or LinkedIn
URL and enriches it using free, no-signup sources. Add free API keys later to
get more/better data — nothing needs to change in the code.

## What it uses (no key required)

- **Website scraping** (primary source) — company name, description, logo,
  contact email/phone, social links, and tech-stack fingerprinting, all
  pulled from the company's own homepage.
- **WHOIS** — domain registration country/date.
- **Wikipedia API** — free-text company summary, for companies notable
  enough to have an article.
- **Own-site funding scan** — checks the company's `/about` and `/press`
  pages for funding keywords. (Deliberately does **not** scrape LinkedIn or
  Crunchbase — both actively block scrapers and you risk getting your IP
  banned; scraping LinkedIn while logged into a personal account can also
  get that account restricted.)

## Optional: add free keys later

Copy `.env.example` to `.env`. Every key is optional — leave it blank and
that source is skipped automatically (you'll see `"skipped_no_key"` in the
lead's data-source list), no errors, no code changes.

- **Hunter.io** — free forever, ~25-50 credits/month, no card:
  https://hunter.io/users/sign_up
- **Apollo.io** — has a free tier (client stub included for you to fill in
  once you have a key — see note below).

> Note on Clearbit: it no longer has a free tier as of 2025 (HubSpot
> acquired it and folded it into paid "Breeze Intelligence"), so it's not
> included here. Hunter.io + scraping cover the same ground for free.

## Setup

```bash
cd lead-enricher
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env         # optional, only if you're adding Hunter.io etc.
python app.py
```

Open http://localhost:5000

## How enrichment runs

Submitting the form returns instantly (202) and enrichment runs in a
background thread — the UI polls `/api/leads/<id>` every 1.5s and updates
the status badge from `pending` → `partial` → `complete`/`failed`. This
avoids the browser hanging for 10+ seconds while several network calls and
scrapes run in sequence.

## Project structure

```
lead-enricher/
├── app.py                  # Flask routes
├── config.py                # env/config loading
├── database/
│   ├── db.py                # schema + connection
│   └── lead_repo.py         # CRUD
├── enricher/
│   ├── input_detector.py    # figures out what you gave it
│   ├── scraper.py           # website scrape: the main data source
│   ├── whois_client.py      # free WHOIS
│   ├── wikipedia_client.py  # free Wikipedia summary
│   ├── hunter_client.py     # optional, self-disables with no key
│   └── pipeline.py          # orchestrates + merges + writes to DB
├── templates/                # index / lead detail / history pages
└── static/                   # css + js
```

## Extending it

- **Add Apollo or another provider**: copy `hunter_client.py`'s pattern —
  check `is_configured()`, return `None` cleanly if no key, add it as a
  step in `pipeline.py`.
- **Swap threading for Celery** if you need to enrich many leads at once
  reliably (the current background-thread approach is fine for one user
  clicking "Enrich" at a time, but doesn't queue/retry under load).
- **Bulk upload**: add a CSV upload endpoint that loops `lead_repo.create_pending`
  + `pipeline.run` per row — the pipeline function already takes a plain dict.
