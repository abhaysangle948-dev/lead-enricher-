import sqlite3
import json
from contextlib import contextmanager

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    input_email TEXT,
    input_domain TEXT,
    input_name TEXT,
    input_company TEXT,
    input_linkedin TEXT,

    company_name TEXT,
    company_domain TEXT,
    company_description TEXT,
    company_industry TEXT,
    company_location TEXT,
    company_founded_year TEXT,
    company_logo TEXT,

    contact_name TEXT,
    contact_title TEXT,
    contact_email TEXT,
    contact_phone TEXT,

    linkedin_url TEXT,
    twitter_url TEXT,
    facebook_url TEXT,
    instagram_url TEXT,
    github_url TEXT,

    tech_stack TEXT,       -- JSON array
    funding_info TEXT,     -- JSON object, best-effort/scraped

    data_sources TEXT,     -- JSON object: {source_name: "ok"|"skipped"|"failed"}
    enrichment_status TEXT DEFAULT 'pending',  -- pending | complete | partial | failed
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS api_usage (
    source TEXT PRIMARY KEY,
    period_start TIMESTAMP,
    calls_used INTEGER DEFAULT 0,
    monthly_limit INTEGER DEFAULT 0
);
"""


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def row_to_dict(row):
    d = dict(row)
    for json_field in ("tech_stack", "funding_info", "data_sources"):
        if d.get(json_field):
            try:
                d[json_field] = json.loads(d[json_field])
            except (TypeError, json.JSONDecodeError):
                pass
    return d
