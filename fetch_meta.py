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

def best_creative_media(creative):
    image_url = creative.get("image_url")
    thumbnail_url = creative.get("thumbnail_url")
    story = creative.get("object_story_spec", {}) or {}
    video_data = story.get("video_data", {}) or {}
    link_data = story.get("link_data", {}) or {}
    photo_data = story.get("photo_data", {}) or {}
    video_id = video_data.get("video_id")
    media_url = None
    media_type = "image"

    if video_id:
        media_type = "video"
        try:
            thumbs = fetch_all_pages(f"{video_id}/thumbnails", {"fields": "uri,is_preferred"})
            preferred = [v for v in thumbs if v.get("is_preferred")]
            chosen = preferred[0] if preferred else (thumbs[0] if thumbs else None)
            if chosen:
                media_url = chosen.get("uri")
        except Exception as e:
            print("Video thumbnail fetch failed:", e)

    if not media_url:
        media_url = video_data.get("image_url") or link_data.get("picture") or link_data.get("image_url") or photo_data.get("url") or image_url or thumbnail_url

    return {"media_url": media_url, "media_type": media_type, "thumbnail_url": thumbnail_url, "image_url": image_url}

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
        a["spend"] += r["spend"]; a["reach"] += r["reach"]; a["impressions"] += r["impressions"]; a["clicks"] += r["clicks"]; a["conversions"] += r["conversions"]
    for a in acc.values():
        a["spend"] = round(a["spend"], 2)
        a["ctr"] = round((a["clicks"]/a["impressions"])*100, 2) if a["impressions"] else 0
        a["cpc"] = round(a["spend"]/a["clicks"], 2) if a["clicks"] else 0
        a["cpm"] = round((a["spend"]/a["impressions"])*1000, 2) if a["impressions"] else 0
        a["cost_per_conversion"] = round(a["spend"]/a["conversions"], 2) if a["conversions"] else 0
    return sorted(acc.values(), key=lambda x: x["spend"], reverse=True)

def fetch_creatives(client):
    conversion_type = client["primary_conversion_action_type"]
    ads = fetch_all_pages(f"{client['ad_account_id']}/ads", {
        "limit": 100,
        "fields": ",".join([
            "id","name","status",
            "creative{id,name,thumbnail_url,image_url,object_story_spec,effective_object_story_id}",
            "insights.time_range(" + json.dumps(LAST_365_RANGE) + ").time_increment(1){date_start,spend,reach,impressions,clicks,ctr,cpc,cpm,actions}"
        ])
    })
    creatives = []
    creative_daily = []
    for ad in ads:
        creative = ad.get("creative", {}) or {}
        media = best_creative_media(creative)
        rows = ad.get("insights", {}).get("data", []) or []
        totals = {"spend":0,"reach":0,"impressions":0,"clicks":0,"conversions":0}
        for row in rows:
            spend = money(row.get("spend"))
            conversions = action_value(row.get("actions"), conversion_type)
            item = {
                "date": row.get("date_start"),
                "ad_id": ad.get("id"),
                "ad_name": ad.get("name"),
                "status": ad.get("status"),
                "thumbnail": media.get("media_url"),
                "media_type": media.get("media_type"),
                "spend": spend,
                "reach": number(row.get("reach")),
                "impressions": number(row.get("impressions")),
                "clicks": number(row.get("clicks")),
                "ctr": float(row.get("ctr", 0)),
                "cpc": money(row.get("cpc")),
                "cpm": money(row.get("cpm")),
                "conversions": conversions,
                "cost_per_conversion": round(spend/conversions,2) if conversions else 0
            }
            creative_daily.append(item)
            totals["spend"] += item["spend"]; totals["reach"] += item["reach"]; totals["impressions"] += item["impressions"]; totals["clicks"] += item["clicks"]; totals["conversions"] += item["conversions"]
        spend = round(totals["spend"], 2)
        creatives.append({
            "ad_id": ad.get("id"), "ad_name": ad.get("name"), "status": ad.get("status"),
            "thumbnail": media.get("media_url"), "media_type": media.get("media_type"),
            "spend": spend, "reach": totals["reach"], "impressions": totals["impressions"], "clicks": totals["clicks"],
            "ctr": round((totals["clicks"]/totals["impressions"])*100,2) if totals["impressions"] else 0,
            "cpc": round(spend/totals["clicks"],2) if totals["clicks"] else 0,
            "cpm": round((spend/totals["impressions"])*1000,2) if totals["impressions"] else 0,
            "conversions": totals["conversions"],
            "cost_per_conversion": round(spend/totals["conversions"],2) if totals["conversions"] else 0
        })
    creatives = sorted([c for c in creatives if c["spend"] > 0], key=lambda x: (x["conversions"], x["spend"]), reverse=True)
    return creatives, creative_daily

def fetch_organic(client):
    return {"facebook": [], "instagram": []}

def summarise_daily(daily):
    spend = sum(d["spend"] for d in daily)
    conversions = sum(d["conversions"] for d in daily)
    clicks = sum(d["clicks"] for d in daily)
    impressions = sum(d["impressions"] for d in daily)
    reach = sum(d["reach"] for d in daily)
    return {
        "spend": round(spend,2), "conversions": conversions, "clicks": clicks, "impressions": impressions, "reach": reach,
        "ctr": round((clicks/impressions)*100,2) if impressions else 0,
        "cpc": round(spend/clicks,2) if clicks else 0,
        "cost_per_conversion": round(spend/conversions,2) if conversions else 0
    }

def last_30(daily):
    if not daily: return []
    latest = max(d["date"] for d in daily)
    end = datetime.strptime(latest, "%Y-%m-%d").date()
    start = end - timedelta(days=29)
    return [d for d in daily if start <= datetime.strptime(d["date"], "%Y-%m-%d").date() <= end]

report = {"generated_at": datetime.utcnow().isoformat(), "available_range_days": 365, "clients": []}

for client in CLIENTS:
    print("Fetching", client["name"])
    daily = fetch_account_daily(client)
    campaign_daily = fetch_campaign_daily(client)
    campaigns = aggregate_campaigns([r for r in campaign_daily if r["date"] in {d["date"] for d in last_30(daily)}])
    creatives, creative_daily = fetch_creatives(client)
    report["clients"].append({
        "slug": client["slug"], "name": client["name"], "brand_color": client.get("brand_color"),
        "conversion_name": client["primary_conversion_name"],
        "summary": summarise_daily(last_30(daily)),
        "daily": daily,
        "campaign_daily": campaign_daily,
        "campaigns": campaigns,
        "creative_daily": creative_daily,
        "creatives": creatives,
        "organic": fetch_organic(client)
    })

with open(OUTPUT_DIR / "report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)

print("Output:", OUTPUT_DIR / "report.json")
