"""
Submit NHGIS extract for time-series table D08 (Persons by Age [2]: Children
and Adults) at county level for decennial years 1970-2010.

We already have annual PEP under-18 for 2010-2024; this extends history to 1970.
"""
import json
import time
import requests
from pathlib import Path

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
DATA.mkdir(exist_ok=True)

API_KEY = "59cba10d8a5da536fc06b59d2762e4c5859b48dbb5215e13b449ba09"
BASE = "https://api.ipums.org"
HDRS = {"Authorization": API_KEY, "Content-Type": "application/json"}

extract_def = {
    "description": "Under-18 by county, decennial 1970-2010 (KidsLeavingCity)",
    "dataFormat": "csv_no_header",
    "timeSeriesTableLayout": "time_by_row_layout",
    "timeSeriesTables": {
        "D08": {
            "geogLevels": ["county"],
            "years": ["1970", "1980", "1990", "2000", "2010"],
        }
    },
}

print("Submitting extract...")
resp = requests.post(
    f"{BASE}/extracts?collection=nhgis&version=2",
    headers=HDRS,
    data=json.dumps(extract_def),
    timeout=60,
)
print(f"  HTTP {resp.status_code}")
print(resp.text[:1500])
resp.raise_for_status()
info = resp.json()
extract_num = info["number"]
print(f"\nExtract submitted: #{extract_num}")

# Save for downloader
(DATA / "nhgis_extract_id.txt").write_text(str(extract_num))

# Poll status
print("\nPolling status...")
status = ""
for attempt in range(60):
    time.sleep(15)
    r = requests.get(
        f"{BASE}/extracts/{extract_num}?collection=nhgis&version=2",
        headers=HDRS,
        timeout=30,
    )
    if r.status_code != 200:
        print(f"  attempt {attempt}: HTTP {r.status_code}")
        continue
    s = r.json()
    status = s.get("status", "")
    print(f"  attempt {attempt}: status = {status}")
    if status == "completed":
        print("\nReady. Download URLs:")
        for k, v in s.get("downloadLinks", {}).items():
            print(f"  {k}: {v}")
        (DATA / "nhgis_extract_status.json").write_text(json.dumps(s, indent=2))
        break
    if status in ("failed", "canceled"):
        print(f"Extract {status}: {s}")
        break
else:
    print("Timeout — check status later")
