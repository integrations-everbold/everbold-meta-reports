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
LAST_30_RANGE = {
    "since": (TODAY - timedelta(days=29)).strftime("%Y-%m-%d"),
    "until": TODAY.strftime("%Y-%m-%d")
}
LAST_365_RANGE = {
    "since": (TODAY - timedelta(days=364)).strftime("%Y-%m-%d"),
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

def fetch_campaign_summary(client):
    print(f"Fetching campaign summary for {client['name']}")
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
            "time_range": json.dumps(LAST_30_RANGE),
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
        totals["spend"] += spend
        totals["reach"] += campaign["reach"]
        totals["impressions"] += campaign["impressions"]
        totals["clicks"] += campaign["clicks"]
        totals["conversions"] += conversions

    totals["ctr"] = round((totals["clicks"] / totals["impressions"]) * 100, 2) if totals["impressions"] else 0
    totals["cpc"] = round(totals["spend"] / totals["clicks"], 2) if totals["clicks"] else 0
    totals["cost_per_conversion"] = round(totals["spend"] / totals["conversions"], 2) if totals["conversions"] else 0
    return campaigns, totals

def fetch_daily(client):
    print(f"Fetching 365-day daily trends for {client['name']}")
    conversion_type = client["primary_conversion_action_type"]

    fields = ",".join([
        "date_start",
        "spend",
        "reach",
        "impressions",
        "clicks",
        "ctr",
        "cpc",
        "cpm",
        "actions"
    ])

    rows = fetch_all_pages(
        f"{client['ad_account_id']}/insights",
        {
            "level": "account",
            "time_increment": 1,
            "time_range": json.dumps(LAST_365_RANGE),
            "fields": fields
        }
    )

    daily = []
    for row in rows:
        spend = money(row.get("spend"))
        conversions = action_value(row.get("actions"), conversion_type)
        daily.append({
            "date": row["date_start"],
            "spend": spend,
            "conversions": conversions,
            "cost_per_conversion": round(spend / conversions, 2) if conversions else 0,
            "reach": number(row.get("reach")),
            "impressions": number(row.get("impressions")),
            "clicks": number(row.get("clicks")),
            "ctr": float(row.get("ctr", 0)),
            "cpc": money(row.get("cpc")),
            "cpm": money(row.get("cpm"))
        })
    return daily

def fetch_creatives(client):
    print(f"Fetching creatives for {client['name']}")
    creatives = []
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
                    "creative{id,name,thumbnail_url,image_url}",
                    "insights.time_range(" + json.dumps(LAST_30_RANGE) + "){spend,reach,impressions,clicks,ctr,cpc,cpm,actions}"
                ])
            }
        )

        for ad in ads:
            insight = {}
            if ad.get("insights", {}).get("data"):
                insight = ad["insights"]["data"][0]

            spend = money(insight.get("spend"))
            conversions = action_value(insight.get("actions"), conversion_type)
            creative = ad.get("creative", {})

            creatives.append({
                "ad_id": ad.get("id"),
                "ad_name": ad.get("name"),
                "status": ad.get("status"),
                "thumbnail": creative.get("image_url") or creative.get("thumbnail_url"),
                "creative_name": creative.get("name"),
                "spend": spend,
                "reach": number(insight.get("reach")),
                "impressions": number(insight.get("impressions")),
                "clicks": number(insight.get("clicks")),
                "ctr": float(insight.get("ctr", 0)),
                "cpc": money(insight.get("cpc")),
                "cpm": money(insight.get("cpm")),
                "conversions": conversions,
                "cost_per_conversion": round(spend / conversions, 2) if conversions else 0
            })
    except Exception as e:
        print("Creative fetch failed:", e)

    return creatives

def fetch_organic(client):
    return {"facebook": [], "instagram": []}

report = {
    "generated_at": datetime.utcnow().isoformat(),
    "default_range": "last_30",
    "available_range_days": 365,
    "clients": []
}

print("====================================")
print("EVERBOLD META REPORTING")
print("====================================")
print("Clients loaded:", len(CLIENTS))

for client in CLIENTS:
    campaigns, summary = fetch_campaign_summary(client)
    daily = fetch_daily(client)
    creatives = fetch_creatives(client)
    organic = fetch_organic(client)

    report["clients"].append({
        "slug": client["slug"],
        "name": client["name"],
        "brand_color": client.get("brand_color"),
        "conversion_name": client["primary_conversion_name"],
        "summary": summary,
        "daily": daily,
        "campaigns": campaigns,
        "creatives": creatives,
        "organic": organic
    })

with open(OUTPUT_DIR / "report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("Output:", OUTPUT_DIR / "report.json")
print("Done.")
