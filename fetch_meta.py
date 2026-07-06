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
LAST_30_RANGE = {"since": (TODAY - timedelta(days=29)).strftime("%Y-%m-%d"), "until": TODAY.strftime("%Y-%m-%d")}
LAST_365_RANGE = {"since": (TODAY - timedelta(days=364)).strftime("%Y-%m-%d"), "until": TODAY.strftime("%Y-%m-%d")}

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

def fetch_account_daily(client):
    conversion_type = client["primary_conversion_action_type"]
    fields = ",".join(["date_start","spend","reach","impressions","clicks","ctr","cpc","cpm","actions"])
    rows = fetch_all_pages(f"{client['ad_account_id']}/insights", {
        "level": "account",
        "time_increment": 1,
        "time_range": json.dumps(LAST_365_RANGE),
        "fields": fields
    })
    daily = []
    for row in rows:
        spend = money(row.get("spend"))
        conversions = action_value(row.get("actions"), conversion_type)
        daily.append({
            "date": row.get("date_start"),
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

def fetch_campaign_daily(client):
    conversion_type = client["primary_conversion_action_type"]
    fields = ",".join(["date_start","campaign_id","campaign_name","spend","reach","impressions","clicks","ctr","cpc","cpm","actions"])
    rows = fetch_all_pages(f"{client['ad_account_id']}/insights", {
        "level": "campaign",
        "time_increment": 1,
        "time_range": json.dumps(LAST_365_RANGE),
        "fields": fields
    })
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

def aggregate_campaigns(rows):
    acc = {}
    for r in rows:
        key = r["campaign_id"] or r["name"]
        if key not in acc:
            acc[key] = {"id": r["campaign_id"], "name": r["name"], "status": "Active", "spend":0, "reach":0, "impressions":0, "clicks":0, "conversions":0}
        a = acc[key]
        a["spend"] += r["spend"]
        a["reach"] += r["reach"]
        a["impressions"] += r["impressions"]
        a["clicks"] += r["clicks"]
        a["conversions"] += r["conversions"]
    for a in acc.values():
        a["spend"] = round(a["spend"], 2)
        a["ctr"] = round((a["clicks"]/a["impressions"])*100, 2) if a["impressions"] else 0
        a["cpc"] = round(a["spend"]/a["clicks"], 2) if a["clicks"] else 0
        a["cpm"] = round((a["spend"]/a["impressions"])*1000, 2) if a["impressions"] else 0
        a["cost_per_conversion"] = round(a["spend"]/a["conversions"], 2) if a["conversions"] else 0
    return sorted(acc.values(), key=lambda x: x["spend"], reverse=True)

def last_30(daily):
    if not daily:
        return []
    latest = max(d["date"] for d in daily)
    end = datetime.strptime(latest, "%Y-%m-%d").date()
    start = end - timedelta(days=29)
    return [d for d in daily if start <= datetime.strptime(d["date"], "%Y-%m-%d").date() <= end]

def summarise_daily(daily):
    spend = sum(d["spend"] for d in daily)
    conversions = sum(d["conversions"] for d in daily)
    clicks = sum(d["clicks"] for d in daily)
    impressions = sum(d["impressions"] for d in daily)
    reach = sum(d["reach"] for d in daily)
    return {
        "spend": round(spend,2),
        "conversions": conversions,
        "clicks": clicks,
        "impressions": impressions,
        "reach": reach,
        "ctr": round((clicks/impressions)*100,2) if impressions else 0,
        "cpc": round(spend/clicks,2) if clicks else 0,
        "cost_per_conversion": round(spend/conversions,2) if conversions else 0
    }

def fetch_creatives(client):
    conversion_type = client["primary_conversion_action_type"]
    creatives = []
    try:
        ads = fetch_all_pages(f"{client['ad_account_id']}/ads", {
            "limit": 100,
            "fields": ",".join([
                "id",
                "name",
                "status",
                "creative{id,name,thumbnail_url}",
                "insights.time_range(" + json.dumps(LAST_30_RANGE) + "){spend,reach,impressions,clicks,ctr,cpc,cpm,actions}"
            ])
        })
    except Exception as e:
        print("Creative fetch skipped:", e)
        return [], []

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
            "cost_per_conversion": round(spend/conversions,2) if conversions else 0
        }
        if spend > 0:
            creatives.append(item)

    creatives = sorted(creatives, key=lambda x: (x["conversions"], x["spend"]), reverse=True)
    return creatives, []

report = {"generated_at": datetime.utcnow().isoformat(), "available_range_days": 365, "clients": []}

for client in CLIENTS:
    print("Fetching", client["name"])
    daily = fetch_account_daily(client)
    campaign_daily = fetch_campaign_daily(client)
    campaigns = aggregate_campaigns([r for r in campaign_daily if r["date"] in {d["date"] for d in last_30(daily)}])
    creatives, creative_daily = fetch_creatives(client)

    report["clients"].append({
        "slug": client["slug"],
        "name": client["name"],
        "brand_color": client.get("brand_color"),
        "conversion_name": client["primary_conversion_name"],
        "summary": summarise_daily(last_30(daily)),
        "daily": daily,
        "campaign_daily": campaign_daily,
        "campaigns": campaigns,
        "creative_daily": creative_daily,
        "creatives": creatives,
        "organic": {"facebook": [], "instagram": []}
    })

with open(OUTPUT_DIR / "report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("Output:", OUTPUT_DIR / "report.json")
