import csv
import io
import threading

from flask import Flask, render_template, request, jsonify, Response

from database.db import init_db
from database import lead_repo
from enricher import pipeline

app = Flask(__name__)
init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/history")
def history():
    return render_template("history.html")


@app.route("/lead/<int:lead_id>")
def lead_detail(lead_id):
    lead = lead_repo.get_lead(lead_id)
    if not lead:
        return "Lead not found", 404
    return render_template("lead_detail.html", lead=lead)


@app.route("/api/enrich", methods=["POST"])
def api_enrich():
    payload = request.get_json(force=True, silent=True) or {}
    if not any(payload.get(k) for k in ("email", "domain", "name", "company", "linkedin")):
        return jsonify({"error": "Provide at least one of: email, domain, name, company, linkedin"}), 400

    lead_id = lead_repo.create_pending(payload)

    # Run enrichment in a background thread so the request returns instantly
    # and the frontend polls /api/leads/<id> for progress instead of blocking
    # on 4-6 chained network calls.
    thread = threading.Thread(target=pipeline.run, args=(lead_id, payload), daemon=True)
    thread.start()

    return jsonify({"id": lead_id, "status": "pending"}), 202


@app.route("/api/leads", methods=["GET"])
def api_list_leads():
    search = request.args.get("q")
    return jsonify(lead_repo.list_leads(search=search))


@app.route("/api/leads/<int:lead_id>", methods=["GET"])
def api_get_lead(lead_id):
    lead = lead_repo.get_lead(lead_id)
    if not lead:
        return jsonify({"error": "not found"}), 404
    return jsonify(lead)


@app.route("/api/leads/<int:lead_id>", methods=["DELETE"])
def api_delete_lead(lead_id):
    lead_repo.delete_lead(lead_id)
    return jsonify({"deleted": lead_id})


CSV_COLUMNS = [
    "id", "created_at", "input_email", "input_domain", "input_name", "input_company",
    "company_name", "company_domain", "company_description", "company_industry",
    "company_location", "company_founded_year", "contact_name", "contact_title",
    "contact_email", "contact_phone", "linkedin_url", "twitter_url", "facebook_url",
    "github_url", "tech_stack", "funding_info", "enrichment_status",
]


def _leads_to_csv(leads):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        row = dict(lead)
        for f in ("tech_stack", "funding_info"):
            if isinstance(row.get(f), (list, dict)):
                row[f] = str(row[f])
        writer.writerow(row)
    return buf.getvalue()


@app.route("/api/export", methods=["GET"])
def api_export_all():
    csv_data = _leads_to_csv(lead_repo.list_leads())
    return Response(csv_data, mimetype="text/csv",
                     headers={"Content-Disposition": "attachment; filename=leads.csv"})


@app.route("/api/export/<int:lead_id>", methods=["GET"])
def api_export_one(lead_id):
    lead = lead_repo.get_lead(lead_id)
    if not lead:
        return jsonify({"error": "not found"}), 404
    csv_data = _leads_to_csv([lead])
    return Response(csv_data, mimetype="text/csv",
                     headers={"Content-Disposition": f"attachment; filename=lead_{lead_id}.csv"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
