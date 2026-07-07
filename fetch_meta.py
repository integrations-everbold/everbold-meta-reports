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
LAST_365_RANGE = {
    "since": (TODAY - timedelta(days=364)).strftime("%Y-%m-%d"),
    "until": TODAY.strftime("%Y-%m-%d")
}
LAST_30_RANGE = {
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

def fetch_campaign_daily(client):
    conversion_type = client["primary_conversion_action_type"]

    fields = ",".join([
        "date_start",
        "campaign_id",
        "campaign_name",
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
            "level": "campaign",
            "time_increment": 1,
            "time_range": json.dumps(LAST_365_RANGE),
            "fields": fields
        }
    )

    out = []

    for row in rows:
        spend = money(row.get("spend"))
        conversions = action_value(row.get("actions"), conversion_type)

        out.append({
            "date": row.get("date_start"),
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
            "conversions": conversions,
            "cost_per_conversion": round(spend / conversions, 2) if conversions else 0
        })

    return out

def aggregate_daily_from_campaigns(campaign_daily):
    by_date = {}

    for row in campaign_daily:
        date = row.get("date")
        if not date:
            continue

        if date not in by_date:
            by_date[date] = {
                "date": date,
                "spend": 0,
                "conversions": 0,
                "reach": 0,
                "impressions": 0,
                "clicks": 0
            }

        item = by_date[date]
        item["spend"] += row.get("spend", 0)
        item["conversions"] += row.get("conversions", 0)
        item["reach"] += row.get("reach", 0)
        item["impressions"] += row.get("impressions", 0)
        item["clicks"] += row.get("clicks", 0)

    daily = []

    for item in by_date.values():
        spend = item["spend"]
        conversions = item["conversions"]
        clicks = item["clicks"]
        impressions = item["impressions"]

        item["spend"] = round(spend, 2)
        item["ctr"] = round((clicks / impressions) * 100, 2) if impressions else 0
        item["cpc"] = round(spend / clicks, 2) if clicks else 0
        item["cpm"] = round((spend / impressions) * 1000, 2) if impressions else 0
        item["cost_per_conversion"] = round(spend / conversions, 2) if conversions else 0

        daily.append(item)

    return sorted(daily, key=lambda x: x["date"])

def aggregate_campaigns(rows):
    acc = {}

    for row in rows:
        key = row.get("campaign_id") or row.get("name")

        if key not in acc:
            acc[key] = {
                "id": row.get("campaign_id"),
                "name": row.get("name"),
                "status": "Active",
                "spend": 0,
                "reach": 0,
                "impressions": 0,
                "clicks": 0,
                "conversions": 0
            }

        item = acc[key]
        item["spend"] += row.get("spend", 0)
        item["reach"] += row.get("reach", 0)
        item["impressions"] += row.get("impressions", 0)
        item["clicks"] += row.get("clicks", 0)
        item["conversions"] += row.get("conversions", 0)

    campaigns = []

    for item in acc.values():
        spend = item["spend"]
        clicks = item["clicks"]
        impressions = item["impressions"]
        conversions = item["conversions"]

        item["spend"] = round(spend, 2)
        item["ctr"] = round((clicks / impressions) * 100, 2) if impressions else 0
        item["cpc"] = round(spend / clicks, 2) if clicks else 0
        item["cpm"] = round((spend / impressions) * 1000, 2) if impressions else 0
        item["cost_per_conversion"] = round(spend / conversions, 2) if conversions else 0

        campaigns.append(item)

    return sorted(campaigns, key=lambda x: x["spend"], reverse=True)

def last_30_dates(daily):
    if not daily:
        return set()

    latest = max(row["date"] for row in daily)
    end = datetime.strptime(latest, "%Y-%m-%d").date()
    start = end - timedelta(days=29)

    return {
        row["date"]
        for row in daily
        if start <= datetime.strptime(row["date"], "%Y-%m-%d").date() <= end
    }

def summarise_daily(daily):
    spend = sum(row.get("spend", 0) for row in daily)
    conversions = sum(row.get("conversions", 0) for row in daily)
    clicks = sum(row.get("clicks", 0) for row in daily)
    impressions = sum(row.get("impressions", 0) for row in daily)
    reach = sum(row.get("reach", 0) for row in daily)

    return {
        "spend": round(spend, 2),
        "conversions": conversions,
        "clicks": clicks,
        "impressions": impressions,
        "reach": reach,
        "ctr": round((clicks / impressions) * 100, 2) if impressions else 0,
        "cpc": round(spend / clicks, 2) if clicks else 0,
        "cost_per_conversion": round(spend / conversions, 2) if conversions else 0
    }

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
                    "insights.time_range(" + json.dumps(LAST_30_RANGE) + "){spend,reach,impressions,clicks,ctr,cpc,cpm,actions}"
                ])
            }
        )
    except Exception as e:
        print("Creative fetch skipped:", e)
        return [], []

    creatives = []

    for ad in ads:
        rows = ad.get("insights", {}).get("data", []) or []
        insight = rows[0] if rows else {}
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

    creatives = sorted(
        creatives,
        key=lambda x: (x.get("conversions", 0), x.get("spend", 0)),
        reverse=True
    )[:12]

    return creatives, []

report = {
    "generated_at": datetime.utcnow().isoformat(),
    "available_range_days": 365,
    "clients": []
}

for client in CLIENTS:
    print("Fetching", client["name"])

    campaign_daily = fetch_campaign_daily(client)
    daily = aggregate_daily_from_campaigns(campaign_daily)

    latest_30 = last_30_dates(daily)
    latest_campaign_rows = [
        row for row in campaign_daily
        if row.get("date") in latest_30
    ]

    campaigns = aggregate_campaigns(latest_campaign_rows)
    creatives, creative_daily = fetch_creatives(client)
    summary = summarise_daily([
        row for row in daily
        if row.get("date") in latest_30
    ])

    report["clients"].append({
        "slug": client["slug"],
        "name": client["name"],
        "brand_color": client.get("brand_color"),
        "conversion_name": client["primary_conversion_name"],
        "summary": summary,
        "daily": daily,
        "campaign_daily": campaign_daily,
        "campaigns": campaigns,
        "creative_daily": creative_daily,
        "creatives": creatives,
        "organic": {
            "facebook": [],
            "instagram": []
        }
    })

with open(OUTPUT_DIR / "report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("Output:", OUTPUT_DIR / "report.json")
print("Done.")
