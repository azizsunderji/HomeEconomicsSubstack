"""
Pull county-level under-18 population for the 22 New York-Newark-Jersey City
MSA counties from every ACS 5-year endpoint we can get (2009 through 2023).

Output: data/nyc_county_under18_acs5_ts.csv
  county_fips,county_name,state_fips,year,under18,acs5_window

Endpoint year N = ACS 5-year (N-4)–N. So endpoint 2009 = 2005-2009, 2023 = 2019-2023.
"""
import csv
import time
from pathlib import Path

import requests

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

CENSUS_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"

# 22 NYC MSA counties grouped by state
NYC_COUNTIES = {
    "34": {  # NJ
        "003": "Bergen", "013": "Essex", "017": "Hudson",
        "019": "Hunterdon", "023": "Middlesex", "025": "Monmouth",
        "027": "Morris", "029": "Ocean", "031": "Passaic",
        "035": "Somerset", "037": "Sussex", "039": "Union",
    },
    "36": {  # NY
        "005": "Bronx", "047": "Kings (Brooklyn)", "059": "Nassau",
        "061": "New York (Manhattan)", "079": "Putnam", "081": "Queens",
        "085": "Richmond (Staten Island)", "087": "Rockland",
        "103": "Suffolk", "119": "Westchester",
    },
}

# B01001 cells = sex by age. Under-18 = male 003-006 + female 027-030
UNDER18_VARS = [
    "B01001_003E", "B01001_004E", "B01001_005E", "B01001_006E",
    "B01001_027E", "B01001_028E", "B01001_029E", "B01001_030E",
]

ENDPOINTS = list(range(2009, 2024))  # 2009..2023 inclusive


def pull_one(year: int, state_fips: str):
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {
        "get": ",".join(UNDER18_VARS + ["NAME"]),
        "for": "county:*",
        "in": f"state:{state_fips}",
        "key": CENSUS_KEY,
    }
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    header = data[0]
    rows = data[1:]
    idx = {h: header.index(h) for h in header}
    out = []
    for row in rows:
        county_fips = row[idx["county"]]
        if county_fips not in NYC_COUNTIES[state_fips]:
            continue
        under18 = sum(int(row[idx[v]]) for v in UNDER18_VARS)
        out.append({
            "county_fips": state_fips + county_fips,
            "county_name": NYC_COUNTIES[state_fips][county_fips],
            "state_fips": state_fips,
            "year": year,
            "under18": under18,
            "acs5_window": f"{year-4}-{year}",
        })
    return out


def main():
    all_rows = []
    for year in ENDPOINTS:
        for state in NYC_COUNTIES:
            try:
                rows = pull_one(year, state)
                all_rows.extend(rows)
                print(f"  {year} state {state}: {len(rows)} counties")
            except Exception as e:
                print(f"  {year} state {state}: ERROR {e}")
            time.sleep(0.15)
    out_path = DATA / "nyc_county_under18_acs5_ts.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "county_fips", "county_name", "state_fips", "year", "under18", "acs5_window",
        ])
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nWrote {len(all_rows)} rows → {out_path}")
    # Coverage summary
    counties = sorted({r["county_fips"] for r in all_rows})
    years = sorted({r["year"] for r in all_rows})
    print(f"Counties: {len(counties)}; Years: {min(years)}-{max(years)} ({len(years)} endpoints)")


if __name__ == "__main__":
    main()
