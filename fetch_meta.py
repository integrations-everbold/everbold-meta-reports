import os
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta

API_VERSION = "v25.0"
ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
CLIENTS_FILE = Path("clients.json")
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
    CLIENTS = json.load(f)

TODAY = datetime.utcnow().date()
DATE_RANGE = {
    "since": (TODAY - timedelta(days=29)).strftime("%Y-%m-%d"),
    "until": TODAY.strftime("%Y-%m-%d")
}

def fetch_all_pages(endpoint, params=None):
    if params is None:
        params = {}
    params["access_token"] = ACCESS_TOKEN
    url = f"https://graph.facebook.com/{API_VERSION}/{endpoint}"
    results = []

    while url:
        response = requests.get(url, params=params)
        if not response.ok:
            print(response.text)
            response.raise_for_status()
        data = response.json()
        results.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = None

    return results

def action_value(actions, action_type):
    if not actions:
        return 0
    for action in actions:
        if action.get("action_type") == action_type:
            try:
                return float(action.get("value", 0))
            except Exception:
                return 0
    return 0

def money(value):
    try:
        return round(float(value), 2)
    except Exception:
        return 0

def number(value):
    try:
        return int(float(value))
    except Exception:
        return 0

def fetch_campaigns(client):
    conversion_type = client["primary_conversion_action_type"]

    fields = ",".join([
        "campaign_name",
        "campaign_id",
        "spend",
        "reach",
        "impressions",
        "clicks",
        "ctr",
        "cpc",
        "cpm",
        "frequency",
        "actions"
    ])

    rows = fetch_all_pages(
        f"{client['ad_account_id']}/insights",
        {
            "level": "campaign",
            "time_range": json.dumps(DATE_RANGE),
            "fields": fields
        }
    )

    campaigns = []
    totals = {"spend": 0, "reach": 0, "impressions": 0, "clicks": 0, "conversions": 0}

    for row in rows:
        spend = money(row.get("spend"))
        conversions = action_value(row.get("actions"), conversion_type)

        campaign = {
            "id": row.get("campaign_id"),
            "campaign_id": row.get("campaign_id"),
            "name": row.get("campaign_name"),
            "status": "Active",
            "spend": spend,
            "reach": number(row.get("reach")),
            "impressions": number(row.get("impressions")),
            "clicks": number(row.get("clicks")),
            "ctr": float(row.get("ctr", 0)),
            "cpc": money(row.get("cpc")),
            "cpm": money(row.get("cpm")),
            "frequency": float(row.get("frequency", 0)),
            "conversions": conversions,
            "cost_per_conversion": round(spend / conversions, 2) if conversions else 0
        }

        campaigns.append(campaign)
        totals["spend"] += campaign["spend"]
        totals["reach"] += campaign["reach"]
        totals["impressions"] += campaign["impressions"]
        totals["clicks"] += campaign["clicks"]
        totals["conversions"] += campaign["conversions"]

    totals["spend"] = round(totals["spend"], 2)
    totals["ctr"] = round((totals["clicks"] / totals["impressions"]) * 100, 2) if totals["impressions"] else 0
    totals["cpc"] = round(totals["spend"] / totals["clicks"], 2) if totals["clicks"] else 0
    totals["cost_per_conversion"] = round(totals["spend"] / totals["conversions"], 2) if totals["conversions"] else 0

    return sorted(campaigns, key=lambda x: x["spend"], reverse=True), totals

def fetch_creatives(client):
    conversion_type = client["primary_conversion_action_type"]

    try:
        ads = fetch_all_pages(
            f"{client['ad_account_id']}/ads",
            {
                "limit": 100,
                "fields": ",".join([
                    "id",
                    "name",
                    "status",
                    "creative{id,name,thumbnail_url}",
                    "insights.time_range(" + json.dumps(DATE_RANGE) + "){spend,reach,impressions,clicks,ctr,cpc,cpm,actions}"
                ])
            }
        )
    except Exception as e:
        print("Creative fetch skipped:", e)
        return []

    creatives = []

    for ad in ads:
        insight = {}
        if ad.get("insights", {}).get("data"):
            insight = ad["insights"]["data"][0]

        creative = ad.get("creative", {}) or {}
        spend = money(insight.get("spend"))
        conversions = action_value(insight.get("actions"), conversion_type)

        item = {
            "ad_id": ad.get("id"),
            "ad_name": ad.get("name"),
            "status": ad.get("status"),
            "thumbnail": creative.get("thumbnail_url"),
            "media_type": "image",
            "spend": spend,
            "reach": number(insight.get("reach")),
            "impressions": number(insight.get("impressions")),
            "clicks": number(insight.get("clicks")),
            "ctr": float(insight.get("ctr", 0)),
            "cpc": money(insight.get("cpc")),
            "cpm": money(insight.get("cpm")),
            "conversions": conversions,
            "cost_per_conversion": round(spend / conversions, 2) if conversions else 0
        }

        if spend > 0 or item.get("thumbnail"):
            creatives.append(item)

    return sorted(creatives, key=lambda x: (x.get("conversions", 0), x.get("spend", 0)), reverse=True)[:12]

report = {
    "generated_at": datetime.utcnow().isoformat(),
    "period": "Last 30 days",
    "clients": []
}

for client in CLIENTS:
    print("Fetching", client["name"])
    campaigns, summary = fetch_campaigns(client)
    creatives = fetch_creatives(client)

    report["clients"].append({
        "slug": client["slug"],
        "name": client["name"],
        "brand_color": client.get("brand_color"),
        "conversion_name": client["primary_conversion_name"],
        "period": "Last 30 days",
        "summary": summary,
        "campaigns": campaigns,
        "creatives": creatives
    })

with open(OUTPUT_DIR / "report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("Output:", OUTPUT_DIR / "report.json")
print("Done.")
