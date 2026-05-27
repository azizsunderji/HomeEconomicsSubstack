"""
Submit NHGIS extract for decennial age data at county level, 1940-2020.

Single extract spanning all decades using NHGIS individual-decennial datasets
plus the 1970-2020 time-series table B57.

Output: NYC 5-borough under-18 population + aged 8-17 cohort at each decennial census.
"""
import json
import time
import requests
from pathlib import Path

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

API_KEY = "59cba10d8a5da536fc06b59d2762e4c5859b48dbb5215e13b449ba09"
BASE = "https://api.ipums.org"
HDRS = {"Authorization": API_KEY, "Content-Type": "application/json"}

extract_def = {
    "description": "NYC 5-borough age data, decennial 1940-2020 (KidsLeavingCity)",
    "dataFormat": "csv_no_header",
    "datasets": {
        "1940_cAge":   {"dataTables": ["NT2B"],  "geogLevels": ["county"]},  # Sex by Age (5-yr buckets)
        "1950_cAge":   {"dataTables": ["NT2"],   "geogLevels": ["county"]},  # Age 0-17 (under-20 universe)
        "1960_cAge2":  {"dataTables": ["NT2"],   "geogLevels": ["county"]},  # Age 0-21 single-year
        "1970_Cnt1":   {"dataTables": ["NT18"],  "geogLevels": ["county"]},  # Sex by Age
        "1980_STF1":   {"dataTables": ["NT10B"], "geogLevels": ["county"]},  # Sex by Age
        "1990_STF1":   {"dataTables": ["NP13"],  "geogLevels": ["county"]},  # Sex by Age (avoid NP12 race-specific)
        "2000_SF1a":   {"dataTables": ["NP012B"],"geogLevels": ["county"]},  # Population by Sex by Age
        "2010_SF1a":   {"dataTables": ["P12"],   "geogLevels": ["county"]},  # Sex by Age (single yr 0-21+)
        "2020_DHCa":   {"dataTables": ["P12"],   "geogLevels": ["county"]},  # Sex by Age (5-yr buckets in 2020)
    },
}

print("Submitting NHGIS extract for 1940-2020 age data...")
resp = requests.post(f"{BASE}/extracts?collection=nhgis&version=2",
                     headers=HDRS, data=json.dumps(extract_def), timeout=60)
print(f"HTTP {resp.status_code}")
print(resp.text[:3000])
