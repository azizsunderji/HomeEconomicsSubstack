"""
Explore NHGIS time series tables for tract-level age data
to find ones standardized to 2020 boundaries with under-18.
"""
import json
import requests
from pathlib import Path

API_KEY = "59cba10d8a5da536fc06b59d2762e4c5859b48dbb5215e13b449ba09"
BASE = "https://api.ipums.org"
HDRS = {"Authorization": API_KEY}

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

# Get list of time series tables
r = requests.get(f"{BASE}/metadata/nhgis/time_series_tables?version=2&pageNumber=1&pageSize=400",
                 headers=HDRS, timeout=60)
ts_list = r.json()["data"]

# Filter to age-related
age_tables = []
for t in ts_list:
    desc = t.get("description", "").lower()
    if "age" in desc and "race" not in desc and "sex" not in desc and "median" not in desc and "hispanic" not in desc and "white" not in desc and "black" not in desc and "asian" not in desc and "american indian" not in desc and "household" not in desc and "group quarters" not in desc:
        age_tables.append(t["name"])

print(f"Candidate age-only tables: {age_tables}")

# Detail each
results = {}
for name in age_tables:
    rd = requests.get(f"{BASE}/metadata/nhgis/time_series_tables/{name}?version=2",
                      headers=HDRS, timeout=30)
    d = rd.json()
    geog_levels = [g["name"] for g in d.get("geogLevels", [])]
    years = [y["name"] for y in d.get("years", [])]
    stand = d.get("geographicIntegration")
    has_tract = "tract" in geog_levels
    has_2020 = "2020" in years
    has_2000 = "2000" in years
    has_under_18 = any("17" in ts.get("description","") for ts in d.get("timeSeries", []))
    print(f"\n{name}: {d.get('description')}")
    print(f"  Standardized: {stand}")
    print(f"  Years: {years}")
    print(f"  Has tract: {has_tract}, 2020: {has_2020}, 2000: {has_2000}, under_18_bucket: {has_under_18}")
    results[name] = {
        "desc": d.get("description"),
        "standardized": stand,
        "years": years,
        "has_tract": has_tract,
        "geog_levels": geog_levels,
        "time_series": [(ts["name"], ts["description"]) for ts in d.get("timeSeries",[])],
    }

with open(DATA / "nhgis_tract_age_options.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved to {DATA / 'nhgis_tract_age_options.json'}")
