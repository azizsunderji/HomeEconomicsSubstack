"""Submit follow-up NHGIS extract: 1990 NP11 (Age, universe=Persons)."""
import json, requests
API_KEY = "59cba10d8a5da536fc06b59d2762e4c5859b48dbb5215e13b449ba09"
BASE = "https://api.ipums.org"
HDRS = {"Authorization": API_KEY, "Content-Type": "application/json"}

extract_def = {
    "description": "1990 NYC age fix (NP11 Persons by Age) (KidsLeavingCity)",
    "dataFormat": "csv_no_header",
    "datasets": {
        "1990_STF1":   {"dataTables": ["NP11"], "geogLevels": ["county"]},  # Age, universe=Persons
    },
}
resp = requests.post(f"{BASE}/extracts?collection=nhgis&version=2",
                     headers=HDRS, data=json.dumps(extract_def), timeout=60)
print(f"HTTP {resp.status_code}")
print(resp.text[:1000])
