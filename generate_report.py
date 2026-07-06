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

def euro(value):
    try:
        return f"€{float(value):,.2f}"
    except Exception:
        return "€0.00"

def integer(value):
    try:
        return f"{int(float(value)):,}"
    except Exception:
        return "0"

def percent(value):
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "0.00%"

def safe_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0

def score(summary):
    s = 100
    ctr = safe_float(summary.get("ctr"))
    cpc = safe_float(summary.get("cpc"))
    cpa = safe_float(summary.get("cost_per_conversion"))
    if ctr < 1: s -= 24
    elif ctr < 1.5: s -= 14
    elif ctr < 2: s -= 6
    if cpc > 2: s -= 18
    elif cpc > 1: s -= 8
    if cpa > 50: s -= 18
    elif cpa > 30: s -= 8
    return max(0, min(100, round(s)))

def health(score_value):
    if score_value >= 88:
        return "Excellent"
    if score_value >= 74:
        return "Strong"
    if score_value >= 60:
        return "Stable"
    return "Needs Attention"

def build_kpis(summary, conversion_name):
    return [
        {"label": "Spend", "value": euro(summary.get("spend", 0)), "note": "Meta ad spend"},
        {"label": conversion_name, "value": integer(summary.get("conversions", 0)), "note": "Primary conversion"},
        {"label": f"Cost / {conversion_name}", "value": euro(summary.get("cost_per_conversion", 0)), "note": "Acquisition cost"},
        {"label": "CTR", "value": percent(summary.get("ctr", 0)), "note": "Click-through rate"},
        {"label": "CPC", "value": euro(summary.get("cpc", 0)), "note": "Cost per click"},
        {"label": "Reach", "value": integer(summary.get("reach", 0)), "note": "Unique reach"},
        {"label": "Impressions", "value": integer(summary.get("impressions", 0)), "note": "Ad impressions"},
        {"label": "Clicks", "value": integer(summary.get("clicks", 0)), "note": "Total clicks"},
    ]

def executive_summary(client, summary, conversion_name):
    conv = int(safe_float(summary.get("conversions", 0)))
    spend = safe_float(summary.get("spend", 0))
    cpa = safe_float(summary.get("cost_per_conversion", 0))
    ctr = safe_float(summary.get("ctr", 0))
    return (
        f"{client['name']} generated {conv:,} {conversion_name} from {euro(spend)} in Meta spend. "
        f"The average cost per {conversion_name.lower()} was {euro(cpa)}, with a CTR of {ctr:.2f}%. "
        f"This report highlights the strongest campaigns, creative performance, and priority actions for the next period."
    )

def recommendations(summary, campaigns, conversion_name):
    items = []
    campaigns = campaigns or []
    active = [c for c in campaigns if safe_float(c.get("spend", 0)) > 0]
    if active:
        best = sorted(active, key=lambda c: (safe_float(c.get("conversions", 0)), -safe_float(c.get("cost_per_conversion", 999999))), reverse=True)[0]
        items.append(f"Scale the strongest campaign: {best.get('name','Campaign')} delivered {integer(best.get('conversions',0))} {conversion_name} at {euro(best.get('cost_per_conversion',0))}.")
        costly = sorted(active, key=lambda c: safe_float(c.get("cost_per_conversion", 0)), reverse=True)[0]
        if safe_float(costly.get("cost_per_conversion", 0)) > safe_float(summary.get("cost_per_conversion", 0)) and safe_float(costly.get("conversions", 0)) > 0:
            items.append(f"Review {costly.get('name','Campaign')} because its cost per {conversion_name.lower()} is above the account average.")
    if safe_float(summary.get("ctr", 0)) < 1.5:
        items.append("CTR is below the preferred benchmark. Prioritise creative testing and stronger opening hooks.")
    else:
        items.append("CTR is in a healthy range. Continue refreshing creative variations to avoid fatigue.")
    if safe_float(summary.get("conversions", 0)) == 0:
        items.append("No primary conversions were recorded in this period. Confirm conversion tracking and campaign objectives.")
    return items[:4]

def top_creatives(creatives, limit=12):
    creatives = creatives or []
    active = [c for c in creatives if safe_float(c.get("spend", 0)) > 0]
    return sorted(active, key=lambda c: (safe_float(c.get("conversions", 0)), safe_float(c.get("spend", 0))), reverse=True)[:limit]

def copy_assets():
    dest = OUTPUT_DIR / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, dest)

def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError("data/report.json not found. Run fetch_meta.py first.")

    report = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("dashboard.html")

    copy_assets()

    index_links = []

    for client in report.get("clients", []):
        slug = client["slug"]
        conversion_name = client.get("conversion_name", "Conversions")
        summary = client.get("summary", {})
        perf_score = score(summary)

        chart_data = {
            "daily": client.get("daily", []),
            "campaigns": client.get("campaigns", []),
            "conversionName": conversion_name
        }

        html = template.render(
            client=client,
            generated_date=datetime.now().strftime("%d %B %Y"),
            conversion_name=conversion_name,
            summary=summary,
            kpis=build_kpis(summary, conversion_name),
            executive_summary=executive_summary(client, summary, conversion_name),
            recommendations=recommendations(summary, client.get("campaigns", []), conversion_name),
            performance_score=perf_score,
            performance_health=health(perf_score),
            campaigns=client.get("campaigns", []),
            creatives=top_creatives(client.get("creatives", [])),
            organic=client.get("organic", {"facebook": [], "instagram": []}),
            report_data_json=json.dumps(chart_data)
        )

        out = OUTPUT_DIR / slug
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(html, encoding="utf-8")
        index_links.append((client["name"], f"{slug}/"))

    index_html = "<!doctype html><html><head><meta charset='utf-8'><title>Everbold Reports</title><link rel='stylesheet' href='assets/css/styles.css'></head><body><main class='main standalone'><h1>Everbold Reports</h1><div class='link-list'>" + "".join([f"<a class='report-link' href='{href}'>{name}</a>" for name, href in index_links]) + "</div></main></body></html>"
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("Reports generated:", len(index_links))

if __name__ == "__main__":
    main()
