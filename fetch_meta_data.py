import os
import json
import requests
from pathlib import Path

TOKEN = os.environ["META_ACCESS_TOKEN"]
AD_ACCOUNT_ID = os.environ["THR_AD_ACCOUNT_ID"]
API_VERSION = "v25.0"

OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

FIELDS = ",".join([
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

url = f"https://graph.facebook.com/{API_VERSION}/{AD_ACCOUNT_ID}/insights"

params = {
    "access_token": TOKEN,
    "date_preset": "last_30d",
    "level": "campaign",
    "fields": FIELDS
}

response = requests.get(url, params=params)
response.raise_for_status()

raw_data = response.json()

def get_action_value(actions, possible_names):
    if not actions:
        return 0

    for action in actions:
        if action.get("action_type") in possible_names:
            try:
                return float(action.get("value", 0))
            except ValueError:
                return 0

    return 0

campaigns = []

for row in raw_data.get("data", []):
    spend = float(row.get("spend", 0))
    leads = get_action_value(row.get("actions", []), [
        "lead",
        "onsite_conversion.lead_grouped",
        "offsite_conversion.fb_pixel_lead",
        "onsite_conversion.messaging_conversation_started_7d"
    ])

    cpl = spend / leads if leads > 0 else 0

    campaigns.append({
        "campaign_name": row.get("campaign_name", ""),
        "spend": spend,
        "impressions": int(float(row.get("impressions", 0))),
        "reach": int(float(row.get("reach", 0))),
        "clicks": int(float(row.get("clicks", 0))),
        "ctr": float(row.get("ctr", 0)),
        "cpc": float(row.get("cpc", 0)),
        "cpm": float(row.get("cpm", 0)),
        "frequency": float(row.get("frequency", 0)),
        "leads": leads,
        "cpl": cpl
    })

summary = {
    "total_spend": sum(c["spend"] for c in campaigns),
    "total_impressions": sum(c["impressions"] for c in campaigns),
    "total_reach": sum(c["reach"] for c in campaigns),
    "total_clicks": sum(c["clicks"] for c in campaigns),
    "total_leads": sum(c["leads"] for c in campaigns),
}

summary["average_cpl"] = (
    summary["total_spend"] / summary["total_leads"]
    if summary["total_leads"] > 0
    else 0
)

with open(OUTPUT_DIR / "campaigns.json", "w") as f:
    json.dump(campaigns, f, indent=2)

with open(OUTPUT_DIR / "summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("Meta data fetched successfully.")
print(json.dumps(summary, indent=2))
