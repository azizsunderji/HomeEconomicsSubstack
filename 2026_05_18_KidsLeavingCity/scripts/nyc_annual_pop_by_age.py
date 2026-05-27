"""
Pull annual PEP single-age estimates for NYC 5 boroughs, 2010-2024.

V2019 (DATE_CODE 3=2010, 4=2011, ..., 12=2019) covers 2010-2019
V2024 (DATE_CODE 1=2020, ..., 5=2024)               covers 2020-2024
"""
import requests
import pandas as pd
from pathlib import Path
import time

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"

NYC_COUNTIES = ["005", "047", "061", "081", "085"]  # Bronx, Kings (Brooklyn), New York (Manhattan), Queens, Richmond (Staten Island)

# PEP V2019 single-age estimates: 2010-2019
# Endpoint: https://api.census.gov/data/2019/pep/charage
# For single age, use 'AGE' variable. Use DATE_CODE per https://api.census.gov/data/2019/pep/charage/variables.html

def pull_v2019():
    """V2019 has DATE_CODE 3=Apr 2010 base, 4=July 2010, 5=July 2011, ..., 12=July 2018, 13=July 2019."""
    url = "https://api.census.gov/data/2019/pep/charage"
    rows_all = []
    for date_code in range(4, 14):  # July 2010 through July 2019
        params = {
            "get": "POP,AGE,DATE_CODE,DATE_DESC",
            "for": f"county:{','.join(NYC_COUNTIES)}",
            "in": "state:36",
            "DATE_CODE": str(date_code),
            "key": API_KEY,
        }
        for attempt in range(4):
            r = requests.get(url, params=params, timeout=45)
            if r.status_code == 200:
                data = r.json()
                hdr, rows = data[0], data[1:]
                df = pd.DataFrame(rows, columns=hdr)
                rows_all.append(df)
                print(f"  V2019 DATE_CODE={date_code}: {len(df)} rows")
                break
            print(f"  V2019 DATE_CODE={date_code} attempt {attempt}: HTTP {r.status_code}")
            time.sleep(3)
    out = pd.concat(rows_all, ignore_index=True)
    return out


def pull_v2024():
    """V2024: DATE_CODE 1=Apr 2020 base, 2=July 2020, 3=July 2021, 4=July 2022, 5=July 2023, 6=July 2024."""
    url = "https://api.census.gov/data/2024/pep/charage"
    rows_all = []
    for date_code in range(2, 7):  # July 2020 through July 2024
        params = {
            "get": "POP,AGE,DATE_CODE,DATE_DESC",
            "for": f"county:{','.join(NYC_COUNTIES)}",
            "in": "state:36",
            "DATE_CODE": str(date_code),
            "key": API_KEY,
        }
        for attempt in range(4):
            r = requests.get(url, params=params, timeout=45)
            if r.status_code == 200:
                data = r.json()
                hdr, rows = data[0], data[1:]
                df = pd.DataFrame(rows, columns=hdr)
                rows_all.append(df)
                print(f"  V2024 DATE_CODE={date_code}: {len(df)} rows")
                break
            print(f"  V2024 DATE_CODE={date_code} attempt {attempt}: HTTP {r.status_code}")
            time.sleep(3)
    out = pd.concat(rows_all, ignore_index=True)
    return out


print("Pulling V2019 single-age county data...")
v19 = pull_v2019()
print("\nPulling V2024 single-age county data...")
v24 = pull_v2024()

both = pd.concat([v19, v24], ignore_index=True)
both["POP"] = pd.to_numeric(both["POP"], errors="coerce")
both["AGE"] = pd.to_numeric(both["AGE"], errors="coerce")

# Drop AGE=999 (totals)
both = both[both["AGE"] != 999].copy()

# Extract year from DATE_DESC like "7/1/2015 population estimate" → 2015
both["year"] = both["DATE_DESC"].str.extract(r"(\d{4})").astype(int)
both["fips5"] = "36" + both["county"]

# Keep just kid-relevant ages 0-18 (need 17 to know how many will age out)
kids = both[both["AGE"] <= 18].copy()

# Pivot by year × age (summed across 5 boroughs)
nyc_agg = kids.groupby(["year", "AGE"], as_index=False)["POP"].sum()
piv = nyc_agg.pivot(index="year", columns="AGE", values="POP").fillna(0).astype(int)
piv.columns = [f"age_{c}" for c in piv.columns]
piv = piv.reset_index().sort_values("year")
piv["under_18"] = piv[[f"age_{i}" for i in range(18)]].sum(axis=1)

piv.to_csv(DATA / "nyc_5boro_singleage_2010_2024.csv", index=False)
print(f"\nWrote nyc_5boro_singleage_2010_2024.csv — {len(piv)} years")
print("\nUnder-18 totals and age-17 (for aging-out) by year:")
print(piv[["year", "under_18", "age_17"]].to_string(index=False))
