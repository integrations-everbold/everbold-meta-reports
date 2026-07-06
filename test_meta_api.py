import os
import requests

TOKEN = os.environ["META_ACCESS_TOKEN"]
AD_ACCOUNT_ID = os.environ["THR_AD_ACCOUNT_ID"]

url = f"https://graph.facebook.com/v25.0/{AD_ACCOUNT_ID}/insights"

params = {
    "access_token": TOKEN,
    "date_preset": "last_30d",
    "level": "campaign",
    "fields": "campaign_name,spend,impressions,reach,clicks,ctr,cpc,cpm,actions,cost_per_action_type"
}

response = requests.get(url, params=params)

print("Status Code:", response.status_code)
print(response.text[:5000])
