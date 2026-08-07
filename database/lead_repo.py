import json
from database.db import get_conn, row_to_dict

FIELDS = [
    "input_email", "input_domain", "input_name", "input_company", "input_linkedin",
    "company_name", "company_domain", "company_description", "company_industry",
    "company_location", "company_founded_year", "company_logo",
    "contact_name", "contact_title", "contact_email", "contact_phone",
    "linkedin_url", "twitter_url", "facebook_url", "instagram_url", "github_url",
    "tech_stack", "funding_info", "data_sources",
    "enrichment_status", "error_message",
]


def create_pending(input_data: dict) -> int:
    """Insert a bare row immediately so the UI has an id to poll while enrichment runs."""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO leads (input_email, input_domain, input_name, input_company,
               input_linkedin, enrichment_status)
               VALUES (?, ?, ?, ?, ?, 'pending')""",
            (
                input_data.get("email"), input_data.get("domain"),
                input_data.get("name"), input_data.get("company"),
                input_data.get("linkedin"),
            ),
        )
        conn.commit()
        return cur.lastrowid


def update_lead(lead_id: int, data: dict):
    data = dict(data)
    for json_field in ("tech_stack", "funding_info", "data_sources"):
        if json_field in data and not isinstance(data[json_field], str):
            data[json_field] = json.dumps(data[json_field])

    fields = [f for f in FIELDS if f in data]
    if not fields:
        return
    set_clause = ", ".join(f"{f} = ?" for f in fields)
    values = [data[f] for f in fields] + [lead_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE leads SET {set_clause} WHERE id = ?", values)
        conn.commit()


def get_lead(lead_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return row_to_dict(row) if row else None


def list_leads(search: str = None):
    query = "SELECT * FROM leads"
    params = ()
    if search:
        query += """ WHERE company_name LIKE ? OR contact_name LIKE ?
                      OR company_industry LIKE ? OR input_domain LIKE ?"""
        like = f"%{search}%"
        params = (like, like, like, like)
    query += " ORDER BY created_at DESC"
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [row_to_dict(r) for r in rows]


def delete_lead(lead_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
        conn.commit()
