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
    print(f"Fetching {client['name']}")

    conversion_action_type = client.get("primary_conversion_action_type", "lead")

    fields = ",".join([
        "campaign_name",
        "spend",
        "impressions",
        "reach",
        "clicks",
        "ctr",
        "cpc",
        "cpm",
        "frequency",
        "actions",
        "cost_per_action_type"
    ])

    url = f"https://graph.facebook.com/{API_VERSION}/{client['ad_account_id']}/insights"

    params = {
        "access_token": TOKEN,
        "level": "campaign",
        "date_preset": "last_30d",
        "fields": fields
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    raw = response.json()

    campaigns = []

    for row in raw.get("data", []):
        spend = float(row.get("spend", 0))

        conversions = get_action_value(
            row.get("actions"),
            conversion_action_type
        )

        campaigns.append({
            "campaign_name": row.get("campaign_name"),
            "spend": spend,
            "impressions": int(row.get("impressions", 0)),
            "reach": int(row.get("reach", 0)),
            "clicks": int(row.get("clicks", 0)),
            "ctr": float(row.get("ctr", 0)),
            "cpc": float(row.get("cpc", 0)),
            "cpm": float(row.get("cpm", 0)),
            "frequency": float(row.get("frequency", 0)),
            "conversion_name": client.get("primary_conversion_name", "Leads"),
            "conversions": conversions,
            "cost_per_conversion": round(spend / conversions, 2) if conversions else 0
        })

    out = OUTPUT_DIR / client["slug"]
    out.mkdir(exist_ok=True)

    with open(out / "campaigns.json", "w") as f:
        json.dump(campaigns, f, indent=2)

print("Finished")
