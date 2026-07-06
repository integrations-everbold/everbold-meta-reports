import json
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader

# ==========================================================
# EVERBOLD REPORTING
# REPORT GENERATOR
# PART 1
# ==========================================================

ROOT = Path(__file__).parent

DATA_DIR = ROOT / "data"

OUTPUT_DIR = ROOT / "reports"

TEMPLATE_DIR = ROOT / "templates"

OUTPUT_DIR.mkdir(exist_ok=True)

REPORT_FILE = DATA_DIR / "report.json"

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True
)

template = env.get_template("dashboard.html")

# ----------------------------------------------------------
# LOAD REPORT JSON
# ----------------------------------------------------------

with open(REPORT_FILE, "r", encoding="utf-8") as f:

    REPORT = json.load(f)

# ----------------------------------------------------------
# HELPERS
# ----------------------------------------------------------

def euro(value):

    return f"€{float(value):,.2f}"

def integer(value):

    return f"{int(value):,}"

def percentage(value):

    return f"{float(value):.2f}%"

# ----------------------------------------------------------
# KPI CARD
# ----------------------------------------------------------

def kpi_card(title, value, subtitle, colour="orange"):

    return f"""
    <div class="kpi-card">

        <div class="kpi-top">

            <div class="kpi-title">{title}</div>

            <div class="kpi-dot {colour}"></div>

        </div>

        <div class="kpi-value">

            {value}

        </div>

        <div class="kpi-subtitle">

            {subtitle}

        </div>

    </div>
    """

# ----------------------------------------------------------
# EXECUTIVE SUMMARY
# ----------------------------------------------------------

def build_summary(summary):

    cpl = summary["cost_per_conversion"]

    ctr = summary["ctr"]

    spend = summary["spend"]

    conversions = summary["conversions"]

    text = []

    text.append(
        f"Meta advertising generated {int(conversions)} conversions "
        f"from €{spend:,.2f} in ad spend."
    )

    text.append(
        f"The average cost per conversion was €{cpl:.2f} "
        f"with a click-through rate of {ctr:.2f}%."
    )

    if ctr >= 2:

        text.append(
            "Campaign engagement remains healthy and indicates that "
            "creative messaging is resonating with the target audience."
        )

    else:

        text.append(
            "CTR remains below the desired benchmark and creative testing "
            "should be prioritised."
        )

    return " ".join(text)

print("Generating reports...")
# ==========================================================
# BUILD KPI SECTION
# ==========================================================

def build_kpis(summary):

    cards = []

    cards.append(
        kpi_card(
            "Spend",
            euro(summary["spend"]),
            "Meta advertising spend"
        )
    )

    cards.append(
        kpi_card(
            "Conversions",
            integer(summary["conversions"]),
            "Primary conversion"
        )
    )

    cards.append(
        kpi_card(
            "Cost / Conversion",
            euro(summary["cost_per_conversion"]),
            "Average acquisition cost"
        )
    )

    cards.append(
        kpi_card(
            "CTR",
            percentage(summary["ctr"]),
            "Click Through Rate"
        )
    )

    cards.append(
        kpi_card(
            "CPC",
            euro(summary["cpc"]),
            "Cost Per Click"
        )
    )

    cards.append(
        kpi_card(
            "Reach",
            integer(summary["reach"]),
            "Accounts reached"
        )
    )

    cards.append(
        kpi_card(
            "Impressions",
            integer(summary["impressions"]),
            "Ad impressions"
        )
    )

    cards.append(
        kpi_card(
            "Clicks",
            integer(summary["clicks"]),
            "Link clicks"
        )
    )

    return "\n".join(cards)


# ==========================================================
# BUILD CHART DATA
# ==========================================================

def build_chart_data(daily):

    return {

        "labels": [
            row["date"] for row in daily
        ],

        "spend": [
            row["spend"] for row in daily
        ],

        "conversions": [
            row["conversions"] for row in daily
        ],

        "cpc": [
            row["cpc"] for row in daily
        ],

        "ctr": [
            row["ctr"] for row in daily
        ],

        "cost_per_conversion": [
            row["cost_per_conversion"] for row in daily
        ]

    }


# ==========================================================
# BUILD CAMPAIGN TABLE
# ==========================================================

def build_campaign_table(campaigns):

    rows = []

    for campaign in campaigns:

        rows.append(f"""
<tr>

<td>{campaign['name']}</td>

<td>{campaign['status']}</td>

<td>{euro(campaign['spend'])}</td>

<td>{integer(campaign['conversions'])}</td>

<td>{euro(campaign['cost_per_conversion'])}</td>

<td>{percentage(campaign['ctr'])}</td>

<td>{euro(campaign['cpc'])}</td>

<td>{integer(campaign['reach'])}</td>

</tr>
""")

    return "\n".join(rows)
    # ==========================================================
# BUILD CREATIVE GALLERY
# ==========================================================

def build_creatives(creatives):

    html = []

    for creative in creatives:

        thumb = creative.get("thumbnail") or ""

        html.append(f"""
<div class="creative-card">

    <div class="creative-image">

        <img src="{thumb}" loading="lazy">

    </div>

    <div class="creative-body">

        <div class="creative-title">

            {creative["ad_name"]}

        </div>

        <div class="creative-metrics">

            <div><strong>Spend</strong><br>{euro(creative["spend"])}</div>

            <div><strong>Conversions</strong><br>{integer(creative["conversions"])}</div>

            <div><strong>CTR</strong><br>{percentage(creative["ctr"])}</div>

            <div><strong>CPC</strong><br>{euro(creative["cpc"])}</div>

        </div>

    </div>

</div>
""")

    return "\n".join(html)


# ==========================================================
# BUILD ORGANIC POSTS
# ==========================================================

def build_organic(posts):

    cards = []

    for platform in ["facebook", "instagram"]:

        for post in posts.get(platform, []):

            cards.append(f"""
<div class="organic-card">

    <div class="organic-platform">
        {platform.title()}
    </div>

    <div class="organic-message">
        {post.get("message","")}
    </div>

    <div class="organic-metrics">

        <span>👍 {post.get("likes",0)}</span>

        <span>💬 {post.get("comments",0)}</span>

        <span>↗ {post.get("shares",0)}</span>

        <span>👁 {post.get("reach",0)}</span>

    </div>

</div>
""")

    return "\n".join(cards)


# ==========================================================
# BUILD CLIENT REPORT
# ==========================================================

for client in REPORT["clients"]:

    summary = client["summary"]

    html = template.render(

        generated=datetime.now().strftime("%d %B %Y"),

        client_name=client["name"],

        brand_colour=client["brand_color"],

        executive_summary=build_summary(summary),

        kpis=build_kpis(summary),

        chart_data=json.dumps(build_chart_data(client["daily"])),

        campaign_rows=build_campaign_table(client["campaigns"]),

        creative_cards=build_creatives(client["creatives"]),

        organic_cards=build_organic(client["organic"])

    )

    output = OUTPUT_DIR / f'{client["slug"]}.html'

    output.write_text(html, encoding="utf-8")

    print("Generated:", output)

print()
print("All reports generated successfully.")
        # ==========================================================
# PERFORMANCE SCORE
# ==========================================================

def performance_score(summary):

    score = 100

    ctr = summary.get("ctr", 0)
    cpc = summary.get("cpc", 0)
    cpa = summary.get("cost_per_conversion", 0)

    if ctr < 1:
        score -= 25
    elif ctr < 1.5:
        score -= 15
    elif ctr < 2:
        score -= 5

    if cpc > 2:
        score -= 20
    elif cpc > 1:
        score -= 10

    if cpa > 50:
        score -= 20
    elif cpa > 30:
        score -= 10

    return max(0, min(100, round(score)))


# ==========================================================
# BEST & WORST CAMPAIGNS
# ==========================================================

def campaign_rankings(campaigns):

    if not campaigns:
        return None, None

    best = sorted(
        campaigns,
        key=lambda x: (
            x["conversions"],
            -x["cost_per_conversion"]
        ),
        reverse=True
    )[0]

    worst = sorted(
        campaigns,
        key=lambda x: (
            x["cost_per_conversion"],
            -x["conversions"]
        ),
        reverse=True
    )[0]

    return best, worst


# ==========================================================
# RECOMMENDATIONS
# ==========================================================

def build_recommendations(summary, campaigns):

    recommendations = []

    score = performance_score(summary)

    if score >= 85:

        recommendations.append(
            "Overall account performance is strong. Focus on scaling the highest-performing campaigns while maintaining cost efficiency."
        )

    elif score >= 70:

        recommendations.append(
            "Performance is healthy, although further creative testing and audience optimisation could improve results."
        )

    else:

        recommendations.append(
            "Overall account performance requires optimisation. Review audience targeting, creatives and campaign structure."
        )

    best, worst = campaign_rankings(campaigns)

    if best:

        recommendations.append(
            f"Top campaign: <strong>{best['name']}</strong> generated {int(best['conversions'])} conversions at €{best['cost_per_conversion']:.2f} per conversion."
        )

    if worst:

        recommendations.append(
            f"Review campaign <strong>{worst['name']}</strong> as it currently has the highest cost per conversion."
        )

    if summary["ctr"] < 1.5:

        recommendations.append(
            "CTR is below the preferred benchmark. Testing new creative concepts and headlines is recommended."
        )

    if summary["cost_per_conversion"] > 30:

        recommendations.append(
            "Cost per conversion is above target. Consider reallocating budget towards stronger campaigns."
        )

    html = []

    for recommendation in recommendations:

        html.append(f"""
<div class="recommendation-card">

    <div class="recommendation-icon">

        ✓

    </div>

    <div class="recommendation-text">

        {recommendation}

    </div>

</div>
""")

    return "\n".join(html)


# ==========================================================
# ACCOUNT HEALTH
# ==========================================================

def account_health(score):

    if score >= 90:
        return "Excellent"

    if score >= 75:
        return "Good"

    if score >= 60:
        return "Average"

    return "Needs Attention"
        # ==========================================================
# PREPARE TEMPLATE DATA
# ==========================================================

def prepare_template(client):

    summary = client["summary"]

    score = performance_score(summary)

    health = account_health(score)

    chart_json = json.dumps(
        build_chart_data(client["daily"])
    )

    return {

        "CLIENT_NAME": client["name"],

        "GENERATED_DATE": datetime.now().strftime("%d %B %Y"),

        "SUMMARY_TITLE": f"{health} Performance",

        "SUMMARY_TEXT": build_summary(summary),

        "PERFORMANCE_SCORE": score,

        "PERFORMANCE_HEALTH": health,

        "CONVERSION_NAME": client["conversion_name"],

        "KPI_CARDS": build_kpis(summary),

        "CAMPAIGN_ROWS": build_campaign_table(
            client["campaigns"]
        ),

        "CREATIVE_CARDS": build_creatives(
            client["creatives"]
        ),

        "ORGANIC_CARDS": build_organic(
            client["organic"]
        ),

        "RECOMMENDATIONS": build_recommendations(
            summary,
            client["campaigns"]
        ),

        "REPORT_DATA_JSON": chart_json

    }


# ==========================================================
# RENDER HTML
# ==========================================================

def render_dashboard(client):

    context = prepare_template(client)

    html = template.render(**context)

    output = OUTPUT_DIR / f"{client['slug']}.html"

    output.write_text(
        html,
        encoding="utf-8"
    )

    print("Generated:", output)

    return output


# ==========================================================
# GENERATE REPORTS
# ==========================================================

generated = []

for client in REPORT["clients"]:

    generated.append(
        render_dashboard(client)
    )
        # ==========================================================
# COPY STATIC ASSETS
# ==========================================================

import shutil

ASSETS_SOURCE = ROOT / "assets"

ASSETS_DESTINATION = OUTPUT_DIR / "assets"

if ASSETS_DESTINATION.exists():
    shutil.rmtree(ASSETS_DESTINATION)

if ASSETS_SOURCE.exists():
    shutil.copytree(
        ASSETS_SOURCE,
        ASSETS_DESTINATION
    )

# ==========================================================
# INDEX PAGE
# ==========================================================

index = []

index.append("""
<!DOCTYPE html>

<html>

<head>

<meta charset="utf-8">

<title>Everbold Reporting</title>

<style>

body{

font-family:Arial;

padding:60px;

background:#fafafa;

}

a{

display:block;

padding:16px;

margin-bottom:12px;

border-radius:10px;

background:white;

text-decoration:none;

color:#111;

border:1px solid #ddd;

font-size:18px;

}

</style>

</head>

<body>

<h1>Everbold Reporting</h1>

<p>Select a client report.</p>

""")

for client in REPORT["clients"]:

    index.append(

        f'<a href="{client["slug"]}.html">{client["name"]}</a>'

    )

index.append("""

</body>

</html>

""")

(
    OUTPUT_DIR / "index.html"
).write_text(

    "\n".join(index),

    encoding="utf-8"

)

# ==========================================================
# REPORT METADATA
# ==========================================================

metadata = {

    "generated": datetime.now().isoformat(),

    "client_count": len(REPORT["clients"]),

    "reports": [

        client["slug"]

        for client in REPORT["clients"]

    ]

}

with open(

    OUTPUT_DIR / "metadata.json",

    "w",

    encoding="utf-8"

) as f:

    json.dump(

        metadata,

        f,

        indent=2

    )

# ==========================================================
# FINISHED
# ==========================================================

print()

print("========================================")

print("EVERBOLD REPORTING COMPLETE")

print("========================================")

print()

print("Reports generated:")

for report in generated:

    print(report)

print()

print("Assets copied")

print("Index created")

print("Metadata created")

print()

print("Done.")
