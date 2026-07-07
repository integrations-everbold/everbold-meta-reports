import json
import shutil
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "report.json"
TEMPLATE_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
OUTPUT_DIR = ROOT / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0

def euro(v):
    return f"€{safe_float(v):,.2f}"

def integer(v):
    try:
        return f"{int(float(v)):,}"
    except Exception:
        return "0"

def percent(v):
    return f"{safe_float(v):.2f}%"

def build_kpis(summary, conversion_name):
    return [
        {"label":"Spend","value":euro(summary.get("spend",0)),"note":"Meta ad spend"},
        {"label":conversion_name,"value":integer(summary.get("conversions",0)),"note":"Primary conversion"},
        {"label":f"Cost / {conversion_name}","value":euro(summary.get("cost_per_conversion",0)),"note":"Acquisition cost"},
        {"label":"CTR","value":percent(summary.get("ctr",0)),"note":"Click-through rate"},
        {"label":"CPC","value":euro(summary.get("cpc",0)),"note":"Cost per click"},
        {"label":"Reach","value":integer(summary.get("reach",0)),"note":"Unique reach"},
        {"label":"Impressions","value":integer(summary.get("impressions",0)),"note":"Ad impressions"},
        {"label":"Clicks","value":integer(summary.get("clicks",0)),"note":"Total clicks"},
    ]

def executive_summary(client, summary, conversion_name):
    return f"{client['name']} generated {integer(summary.get('conversions',0))} {conversion_name} from {euro(summary.get('spend',0))} in Meta spend. The average cost per {conversion_name.lower()} was {euro(summary.get('cost_per_conversion',0))}, with a CTR of {percent(summary.get('ctr',0))}."

def recommendations(summary, campaigns, creatives, conversion_name):
    recs = []
    lead_campaigns = [c for c in campaigns if safe_float(c.get("conversions", 0)) > 0]
    if lead_campaigns:
        best = sorted(lead_campaigns, key=lambda c: (safe_float(c.get("conversions",0)), -safe_float(c.get("cost_per_conversion",999999))), reverse=True)[0]
        recs.append(f"Prioritise budget towards {best.get('name')}, as it generated {integer(best.get('conversions',0))} {conversion_name} at {euro(best.get('cost_per_conversion',0))}.")
    costly = sorted(lead_campaigns, key=lambda c: safe_float(c.get("cost_per_conversion",0)), reverse=True)[0] if lead_campaigns else None
    if costly and safe_float(costly.get("cost_per_conversion",0)) > safe_float(summary.get("cost_per_conversion",0)):
        recs.append(f"Review {costly.get('name')}; its cost per {conversion_name.lower()} is above the account average.")
    if creatives:
        top = creatives[0]
        recs.append(f"Use {top.get('ad_name')} as the creative benchmark, as it produced the strongest conversion volume in this period.")
    if safe_float(summary.get("ctr",0)) < 1.5:
        recs.append("CTR is below the preferred benchmark. Test stronger opening hooks, clearer creative contrast and more direct lead-focused messaging.")
    else:
        recs.append("CTR is in a healthy range. Continue refreshing creative variations to avoid fatigue.")
    if safe_float(summary.get("cpc",0)) > 1:
        recs.append("CPC is elevated. Review audience overlap, placement mix and creative relevance.")
    return recs[:4]

def copy_assets():
    dest = OUTPUT_DIR / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, dest)

def main():
    report = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("dashboard.html")
    copy_assets()

    index_links = []

    for client in report.get("clients", []):
        conversion_name = client.get("conversion_name", "Conversions")
        summary = client.get("summary", {})
        campaigns = client.get("campaigns", [])
        creatives = client.get("creatives", [])

        chart_data = {
            "campaigns": campaigns,
            "creatives": creatives,
            "conversionName": conversion_name,
            "clientName": client.get("name")
        }

        html = template.render(
            client=client,
            generated_date=datetime.now().strftime("%d %B %Y"),
            conversion_name=conversion_name,
            summary=summary,
            kpis=build_kpis(summary, conversion_name),
            executive_summary=executive_summary(client, summary, conversion_name),
            recommendations=recommendations(summary, campaigns, creatives, conversion_name),
            campaigns=campaigns,
            creatives=creatives,
            report_data_json=json.dumps(chart_data)
        )

        out = OUTPUT_DIR / client["slug"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(html, encoding="utf-8")
        index_links.append((client["name"], f"{client['slug']}/"))

    index_html = "<!doctype html><html><head><meta charset='utf-8'><title>Everbold Reports</title><link rel='stylesheet' href='assets/css/styles.css'></head><body><main class='main standalone'><h1>Everbold Reports</h1><div class='link-list'>" + "".join([f"<a class='report-link' href='{href}'>{name}</a>" for name, href in index_links]) + "</div></main></body></html>"
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("Reports generated:", len(index_links))

if __name__ == "__main__":
    main()
