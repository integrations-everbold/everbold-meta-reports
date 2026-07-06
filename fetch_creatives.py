import json
import os
import requests
from pathlib import Path

TOKEN = os.environ["META_ACCESS_TOKEN"]
API_VERSION = "v25.0"

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

with open("clients.json", "r") as f:
    clients = json.load(f)


def get_action_value(actions, target_action_type):
    if not actions:
        return 0

    for action in actions:
        if action.get("action_type") == target_action_type:
            try:
                return float(action["value"])
            except:
                return 0

    return 0


for client in clients:
    print(f"Fetching creative data for {client['name']}")

    conversion_action_type = client.get("primary_conversion_action_type", "lead")

    url = f"https://graph.facebook.com/{API_VERSION}/{client['ad_account_id']}/ads"

    params = {
        "access_token": TOKEN,
        "limit": 100,
        "fields": ",".join([
            "id",
            "name",
            "status",
            "creative{id,name,thumbnail_url}",
            "insights.date_preset(last_30d){spend,impressions,reach,clicks,ctr,cpc,cpm,actions}"
        ])
    }

    all_ads = []

    while url:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        for ad in data.get("data", []):
            insights = {}
            insight_rows = ad.get("insights", {}).get("data", [])

            if insight_rows:
                insights = insight_rows[0]

            spend = float(insights.get("spend", 0))
            conversions = get_action_value(insights.get("actions"), conversion_action_type)

            creative = ad.get("creative", {})

            all_ads.append({
                "ad_id": ad.get("id"),
                "ad_name": ad.get("name"),
                "status": ad.get("status"),
                "creative_id": creative.get("id"),
                "creative_name": creative.get("name"),
                "thumbnail_url": creative.get("thumbnail_url"),
                "spend": spend,
                "impressions": int(float(insights.get("impressions", 0))),
                "reach": int(float(insights.get("reach", 0))),
                "clicks": int(float(insights.get("clicks", 0))),
                "ctr": float(insights.get("ctr", 0)),
                "cpc": float(insights.get("cpc", 0)),
                "cpm": float(insights.get("cpm", 0)),
                "conversions": conversions,
                "cost_per_conversion": round(spend / conversions, 2) if conversions else 0
            })

        url = data.get("paging", {}).get("next")
        params = None

    out = OUTPUT_DIR / client["slug"]
    out.mkdir(exist_ok=True)

    with open(out / "creatives.json", "w") as f:
        json.dump(all_ads, f, indent=2)

print("Finished creative fetch")
