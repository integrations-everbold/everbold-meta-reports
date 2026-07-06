import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).parent
DATA_FILE = ROOT / "data" / "report.json"
TEMPLATE_DIR = ROOT / "templates"
ASSETS_DIR = ROOT / "assets"
OUTPUT_DIR = ROOT / "reports"
OUTPUT_DIR.mkdir(exist_ok=True)

def safe_float(v):
    try: return float(v)
    except Exception: return 0.0

def euro(v): return f"€{safe_float(v):,.2f}"
def integer(v):
    try: return f"{int(float(v)):,}"
    except Exception: return "0"
def percent(v): return f"{safe_float(v):.2f}%"

def score(summary):
    s = 100
    if safe_float(summary.get("ctr")) < 1: s -= 24
    elif safe_float(summary.get("ctr")) < 1.5: s -= 14
    elif safe_float(summary.get("ctr")) < 2: s -= 6
    if safe_float(summary.get("cpc")) > 2: s -= 18
    elif safe_float(summary.get("cpc")) > 1: s -= 8
    if safe_float(summary.get("cost_per_conversion")) > 50: s -= 18
    elif safe_float(summary.get("cost_per_conversion")) > 30: s -= 8
    return max(0, min(100, round(s)))

def health(s):
    if s >= 88: return "Excellent"
    if s >= 74: return "Strong"
    if s >= 60: return "Stable"
    return "Needs Attention"

def build_kpis(summary, conversion_name):
    return [
        {"key":"spend","label":"Spend","value":euro(summary.get("spend",0)),"note":"Meta ad spend"},
        {"key":"conversions","label":conversion_name,"value":integer(summary.get("conversions",0)),"note":"Primary conversion"},
        {"key":"cost_per_conversion","label":f"Cost / {conversion_name}","value":euro(summary.get("cost_per_conversion",0)),"note":"Acquisition cost"},
        {"key":"ctr","label":"CTR","value":percent(summary.get("ctr",0)),"note":"Click-through rate"},
        {"key":"cpc","label":"CPC","value":euro(summary.get("cpc",0)),"note":"Cost per click"},
        {"key":"reach","label":"Reach","value":integer(summary.get("reach",0)),"note":"Unique reach"},
        {"key":"impressions","label":"Impressions","value":integer(summary.get("impressions",0)),"note":"Ad impressions"},
        {"key":"clicks","label":"Clicks","value":integer(summary.get("clicks",0)),"note":"Total clicks"},
    ]

def executive_summary(client, summary, conversion_name):
    return f"{client['name']} generated {integer(summary.get('conversions',0))} {conversion_name} from {euro(summary.get('spend',0))} in Meta spend. The average cost per {conversion_name.lower()} was {euro(summary.get('cost_per_conversion',0))}, with a CTR of {percent(summary.get('ctr',0))}."

def recommendations(summary, campaigns, conversion_name):
    # initial only; JS updates dynamically from selected time range
    return ["Use the date selector above to review performance by period.", "Prioritise spend towards campaigns with the strongest cost per conversion.", "Refresh creatives regularly to maintain CTR and reduce fatigue.", "Review campaigns with spend but limited conversion volume."]

def copy_assets():
    dest = OUTPUT_DIR / "assets"
    if dest.exists(): shutil.rmtree(dest)
    if ASSETS_DIR.exists(): shutil.copytree(ASSETS_DIR, dest)

def main():
    report = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("dashboard.html")
    copy_assets()
    index_links = []

    for client in report.get("clients", []):
        conversion_name = client.get("conversion_name", "Conversions")
        summary = client.get("summary", {})
        perf_score = score(summary)

        chart_data = {
            "daily": client.get("daily", []),
            "campaigns": client.get("campaigns", []),
            "campaignDaily": client.get("campaign_daily", []),
            "creatives": client.get("creatives", []),
            "creativeDaily": client.get("creative_daily", []),
            "conversionName": conversion_name,
            "clientName": client.get("name")
        }

        html = template.render(
            client=client, generated_date=datetime.now().strftime("%d %B %Y"), conversion_name=conversion_name,
            summary=summary, kpis=build_kpis(summary, conversion_name),
            executive_summary=executive_summary(client, summary, conversion_name),
            recommendations=recommendations(summary, client.get("campaigns", []), conversion_name),
            performance_score=perf_score, performance_health=health(perf_score),
            campaigns=client.get("campaigns", []), creatives=client.get("creatives", [])[:12],
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
