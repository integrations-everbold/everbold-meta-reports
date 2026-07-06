import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
OUTPUT_DIR = Path("docs/reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open("clients.json", "r") as f:
    clients = json.load(f)


def money(value):
    return f"€{value:,.2f}"


def number(value):
    return f"{value:,.0f}"


for client in clients:
    slug = client["slug"]
    name = client["name"]
    conversion_name = client.get("primary_conversion_name", "Conversions")

    campaign_file = DATA_DIR / slug / "campaigns.json"

    if not campaign_file.exists():
        print(f"No data found for {name}")
        continue

    with open(campaign_file, "r") as f:
        campaigns = json.load(f)

    total_spend = sum(c["spend"] for c in campaigns)
    total_conversions = sum(c["conversions"] for c in campaigns)
    total_clicks = sum(c["clicks"] for c in campaigns)
    total_impressions = sum(c["impressions"] for c in campaigns)
    total_reach = sum(c["reach"] for c in campaigns)

    avg_cost_per_conversion = total_spend / total_conversions if total_conversions else 0
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions else 0
    avg_cpc = total_spend / total_clicks if total_clicks else 0

    campaigns_sorted = sorted(campaigns, key=lambda x: x["spend"], reverse=True)

    rows = ""
    for c in campaigns_sorted:
        rows += f"""
        <tr>
            <td>{c["campaign_name"]}</td>
            <td>{money(c["spend"])}</td>
            <td>{number(c["conversions"])}</td>
            <td>{money(c["cost_per_conversion"])}</td>
            <td>{c["ctr"]:.2f}%</td>
            <td>{money(c["cpc"])}</td>
            <td>{number(c["reach"])}</td>
            <td>{number(c["impressions"])}</td>
        </tr>
        """

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{name} Meta Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
:root {{
    --orange: #ff530d;
    --black: #0f0f0f;
    --white: #fcfcfc;
    --muted: #666;
    --border: #ececec;
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    font-family: Inter, Arial, sans-serif;
    background: var(--white);
    color: var(--black);
}}

.layout {{
    display: grid;
    grid-template-columns: 260px 1fr;
    min-height: 100vh;
}}

.sidebar {{
    background: #0f0f0f;
    color: white;
    padding: 32px 24px;
}}

.brand {{
    color: var(--orange);
    font-size: 28px;
    font-weight: 900;
    letter-spacing: -1px;
    margin-bottom: 48px;
}}

.nav-item {{
    padding: 14px 16px;
    border-radius: 12px;
    margin-bottom: 8px;
    color: #d7d7d7;
}}

.nav-item.active {{
    background: var(--orange);
    color: white;
}}

.main {{
    padding: 40px;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 36px;
}}

.eyebrow {{
    color: var(--orange);
    font-weight: 700;
    margin-bottom: 8px;
}}

h1 {{
    font-size: 48px;
    line-height: 1.05;
    margin: 0;
    letter-spacing: -2px;
}}

.subtext {{
    color: var(--muted);
    margin-top: 12px;
}}

.summary-box {{
    background: linear-gradient(135deg, #fff4ef, #ffffff);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 28px;
    max-width: 420px;
}}

.summary-box h3 {{
    margin-top: 0;
}}

.kpis {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 18px;
    margin-bottom: 32px;
}}

.card {{
    background: white;
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 24px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.04);
}}

.card-label {{
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 14px;
}}

.card-value {{
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -1px;
}}

.section {{
    background: white;
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 28px;
    box-shadow: 0 12px 30px rgba(0,0,0,0.04);
    margin-bottom: 28px;
}}

.section h2 {{
    margin-top: 0;
    font-size: 24px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}}

th {{
    text-align: left;
    color: var(--muted);
    font-weight: 600;
    padding: 14px;
    border-bottom: 1px solid var(--border);
}}

td {{
    padding: 16px 14px;
    border-bottom: 1px solid var(--border);
}}

tr:hover {{
    background: #fff7f3;
}}

.footer {{
    color: var(--muted);
    font-size: 13px;
    margin-top: 24px;
}}

@media (max-width: 1000px) {{
    .layout {{
        grid-template-columns: 1fr;
    }}

    .sidebar {{
        display: none;
    }}

    .kpis {{
        grid-template-columns: repeat(2, 1fr);
    }}

    .header {{
        display: block;
    }}

    h1 {{
        font-size: 38px;
    }}
}}
</style>
</head>

<body>
<div class="layout">
    <aside class="sidebar">
        <div class="brand">EVERBOLD</div>
        <div class="nav-item active">Executive Summary</div>
        <div class="nav-item">Campaign Performance</div>
        <div class="nav-item">Creative Performance</div>
        <div class="nav-item">Organic Performance</div>
        <div class="nav-item">Recommendations</div>
    </aside>

    <main class="main">
        <div class="header">
            <div>
                <div class="eyebrow">Meta Advertising Report</div>
                <h1>{name}<br>Performance Report</h1>
                <div class="subtext">Last 30 days · Generated {datetime.now().strftime("%d %B %Y")}</div>
            </div>

            <div class="summary-box">
                <h3>Executive Summary</h3>
                <p>
                    {name} generated <strong>{number(total_conversions)} {conversion_name}</strong> from
                    <strong>{money(total_spend)}</strong> in Meta ad spend, with an average
                    cost per {conversion_name.lower()} of <strong>{money(avg_cost_per_conversion)}</strong>.
                </p>
            </div>
        </div>

        <div class="kpis">
            <div class="card">
                <div class="card-label">Spend</div>
                <div class="card-value">{money(total_spend)}</div>
            </div>
            <div class="card">
                <div class="card-label">{conversion_name}</div>
                <div class="card-value">{number(total_conversions)}</div>
            </div>
            <div class="card">
                <div class="card-label">Cost per {conversion_name}</div>
                <div class="card-value">{money(avg_cost_per_conversion)}</div>
            </div>
            <div class="card">
                <div class="card-label">CTR</div>
                <div class="card-value">{avg_ctr:.2f}%</div>
            </div>
            <div class="card">
                <div class="card-label">Reach</div>
                <div class="card-value">{number(total_reach)}</div>
            </div>
        </div>

        <div class="section">
            <h2>Campaign Performance</h2>
            <table>
                <thead>
                    <tr>
                        <th>Campaign</th>
                        <th>Spend</th>
                        <th>{conversion_name}</th>
                        <th>Cost per {conversion_name}</th>
                        <th>CTR</th>
                        <th>CPC</th>
                        <th>Reach</th>
                        <th>Impressions</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>

        <div class="footer">
            Prepared by Everbold Reporting.
        </div>
    </main>
</div>
</body>
</html>
"""

    client_output = OUTPUT_DIR / slug
    client_output.mkdir(parents=True, exist_ok=True)

    with open(client_output / "index.html", "w") as f:
        f.write(html)

    print(f"Generated report for {name}: {client_output / 'index.html'}")
