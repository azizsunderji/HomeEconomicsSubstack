#!/usr/bin/env python3
"""
Pull under-18 population for 60 named central cities of top 50 1950 SMAs.

Source: Census Bureau ACS API, table B01001 (Sex by Age).
Under-18 = sum of variables (003,004,005,006) male + (027,028,029,030) female.

Tries ACS 1-year 2024 first (most recent), falls back to ACS 5-year 2023 for
places <65k or any place not in the 1-year dataset.

Output: data/under18_central_cities_2024.csv
"""

import csv
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
import json

# --- Config ---
PROJECT_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
INPUT_CSV = PROJECT_DIR / "data" / "central_city_place_fips_all172.csv"
OUTPUT_CSV = PROJECT_DIR / "data" / "under18_central_cities_2024_all172.csv"

API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"

# Under-18 variables in B01001 (Sex by Age)
# Male: 003 (<5), 004 (5-9), 005 (10-14), 006 (15-17)
# Female: 027 (<5), 028 (5-9), 029 (10-14), 030 (15-17)
UNDER18_VARS = [
    "B01001_003E", "B01001_004E", "B01001_005E", "B01001_006E",
    "B01001_027E", "B01001_028E", "B01001_029E", "B01001_030E",
]

# Manually corrected place FIPS where the input CSV has stale codes.
# Verified against ACS 2019-2023 5-yr `place:*&in=state:XX` queries
# (run 2026-05-24). Many CT cities shifted codes after the 2022
# planning-region redesignation; Indianapolis/Louisville have
# "(balance)" entities with different FIPS than the historical city;
# several OH and MA codes also differ from the input.
# Map: (state_fips_2digit, original_place_fips_7digit) -> corrected_place_fips_7digit
PLACE_FIPS_CORRECTIONS = {
    # Connecticut
    ("09", "0907000"): "0908420",  # Bristol
    ("09", "0935000"): "0937000",  # Hartford
    ("09", "0950000"): "0950370",  # New Britain
    ("09", "0953000"): "0952000",  # New Haven
    ("09", "0954000"): "0955990",  # Norwalk
    ("09", "0972000"): "0980000",  # Waterbury
    # Massachusetts
    ("25", "2522000"): "2523000",  # Fall River
    ("25", "2530000"): "2530840",  # Holyoke
    ("25", "2534000"): "2534550",  # Lawrence
    ("25", "2581000"): "2582000",  # Worcester
    # New York
    ("36", "3667000"): "3665508",  # Schenectady
    ("36", "3675000"): "3675484",  # Troy
    # Ohio
    ("39", "3900100"): "3901000",  # Akron
    ("39", "3920000"): "3921000",  # Dayton
    ("39", "3989000"): "3988000",  # Youngstown
    # Indiana
    ("18", "1836000"): "1836003",  # Indianapolis (balance)
    # Kentucky
    ("21", "2148000"): "2148006",  # Louisville/Jefferson Cty metro govt (balance)
}


def fetch_place(year: int, dataset: str, state_fips: str, place_fips_full: str):
    """Fetch under-18 population for a single place from the ACS API.

    place_fips_full is the 7-char combined state(2)+place(5) FIPS, e.g. '3651000'.
    The API expects the 5-digit place code (last 5 chars) with state passed via 'in='.
    Returns int total under-18, or None if not found / not available.
    """
    place_code = place_fips_full[-5:]  # last 5 = place code
    state_code = state_fips.zfill(2)

    base = f"https://api.census.gov/data/{year}/acs/{dataset}"
    params = {
        "get": ",".join(UNDER18_VARS),
        "for": f"place:{place_code}",
        "in": f"state:{state_code}",
        "key": API_KEY,
    }
    url = f"{base}?{urlencode(params)}"

    try:
        with urlopen(url, timeout=30) as resp:
            body = resp.read().decode("utf-8").strip()
        if not body:
            # Empty response — typically means place isn't in this dataset
            # (e.g. ACS 1-year only covers places >=65k)
            return None
        data = json.loads(body)
    except HTTPError as e:
        if e.code in (204, 404):
            return None
        print(f"  HTTP {e.code} for {state_code}/{place_code} year={year} {dataset}", file=sys.stderr)
        return None
    except URLError as e:
        print(f"  URL error for {state_code}/{place_code}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        # Non-JSON body usually means the place isn't covered
        return None

    if not data or len(data) < 2:
        return None

    header = data[0]
    row = data[1]

    total = 0
    for v in UNDER18_VARS:
        idx = header.index(v)
        val = row[idx]
        if val is None:
            return None
        # Census API returns negative annotation codes for unavailable data
        ival = int(val)
        if ival < 0:
            return None
        total += ival
    return total


def main():
    # Read input
    rows = []
    with open(INPUT_CSV, "r", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    print(f"Loaded {len(rows)} cities from {INPUT_CSV.name}")

    results = []
    grand_total = 0
    failed = []

    for r in rows:
        city = r["central_city"]
        state_fips = r["state_fips"].zfill(2)
        place_fips_orig = r["place_fips"].zfill(7)

        # Apply correction if input FIPS is known-stale
        place_fips = PLACE_FIPS_CORRECTIONS.get((state_fips, place_fips_orig), place_fips_orig)
        if place_fips != place_fips_orig:
            print(f"  [correction] {city}: {place_fips_orig} -> {place_fips}")

        # 1) Try ACS 1-year 2024
        val = fetch_place(2024, "acs1", state_fips, place_fips)
        source = None
        if val is not None and val > 0:
            source = "ACS 2024 1-yr"
        else:
            # 2) Fall back to ACS 5-year 2019-2023 (released Dec 2024)
            val = fetch_place(2023, "acs5", state_fips, place_fips)
            if val is not None and val > 0:
                source = "ACS 2019-2023 5-yr"

        if val is None or val == 0 or source is None:
            failed.append((city, state_fips, place_fips))
            print(f"  FAILED: {city} ({state_fips}/{place_fips})")
            results.append({
                "place_fips": place_fips_orig,
                "state_fips": state_fips,
                "central_city": city,
                "under18_2024": "",
                "year_source": "",
            })
        else:
            grand_total += val
            print(f"  {city:25s} ({state_fips}/{place_fips}) = {val:>9,}  [{source}]")
            results.append({
                "place_fips": place_fips_orig,
                "state_fips": state_fips,
                "central_city": city,
                "under18_2024": val,
                "year_source": source,
            })

        # Be polite to the API
        time.sleep(0.05)

    # Write output
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["place_fips", "state_fips", "central_city", "under18_2024", "year_source"],
        )
        writer.writeheader()
        writer.writerows(results)

    print(f"\nWrote {OUTPUT_CSV}")
    print(f"\nTotal under-18 across {len(rows)} cities: {grand_total:,}")
    print(f"Failed cities: {len(failed)}")
    for city, sf, pf in failed:
        print(f"  - {city} ({sf}/{pf})")


if __name__ == "__main__":
    main()
