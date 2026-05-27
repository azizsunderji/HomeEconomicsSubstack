"""
Pull tract-level under-18 population for 10 target CBSAs across 6 snapshots:
  2000  -> Decennial 2000 SF1   (2000 tract boundaries)
  2005  -> ACS5 2005-2009 (endpoint 2009)  (2000 tract boundaries; ACS5 2009 reports on 2000)
  2010  -> Decennial 2010 SF1   (2010 tract boundaries)
  2015  -> ACS5 2010-2014 (endpoint 2014)  (2010 tract boundaries)
  2020  -> Decennial 2020 DHC   (2020 tract boundaries)
  2024  -> ACS5 2019-2023 (endpoint 2023)  (2020 tract boundaries)

For each snapshot we pull by (state, county) since Census API requires it.
Output: tract-level CSV with under-18 totals at each snapshot, keyed on
the *native-year* tract GEOID. A `boundary_year` column accompanies each
snapshot to make later crosswalking explicit.

Output schema:
  cbsa_code, state_fips, county_fips, tract_fips, geoid_native, boundary_year,
  snapshot_year, under18, source

We write a LONG-format CSV (~12k tracts x 6 snapshots = ~70k rows) plus a
companion WIDE CSV with the 6 snapshot columns side-by-side, using the
union of GEOIDs across snapshot years. For tracts that exist only in some
years, missing values are NaN.

Note: 2000 boundaries -> 2010 boundaries -> 2020 boundaries are different.
The user has explicitly OK'd flagging boundary_year and crosswalking later.
"""
import csv
import json
import time
import sys
from pathlib import Path
from collections import defaultdict

import requests

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

CENSUS_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"

# Target CBSAs
TARGET_CBSAS = {
    "35620": "New York-Newark-Jersey City, NY-NJ",
    "31080": "Los Angeles-Long Beach-Anaheim, CA",
    "16980": "Chicago-Naperville-Elgin, IL-IN",
    "19100": "Dallas-Fort Worth-Arlington, TX",
    "26420": "Houston-Pasadena-The Woodlands, TX",
    "12060": "Atlanta-Sandy Springs-Roswell, GA",
    "47900": "Washington-Arlington-Alexandria, DC-VA-MD-WV",
    "33100": "Miami-Fort Lauderdale-West Palm Beach, FL",
    "37980": "Philadelphia-Camden-Wilmington, PA-NJ-DE-MD",
    "38060": "Phoenix-Mesa-Chandler, AZ",
}

# Snapshot config
SNAPSHOTS = [
    # (label, dataset, year, vars-male-under18, vars-female-under18, boundary_year, source_label)
    ("2000", "dec/sf1",  "2000",
        ["P012003","P012004","P012005","P012006"],
        ["P012027","P012028","P012029","P012030"],
        2000, "Decennial 2000 SF1"),
    ("2005", "acs/acs5", "2009",
        ["B01001_003E","B01001_004E","B01001_005E","B01001_006E"],
        ["B01001_027E","B01001_028E","B01001_029E","B01001_030E"],
        2000, "ACS 5-yr 2005-2009"),
    ("2010", "dec/sf1",  "2010",
        ["P012003","P012004","P012005","P012006"],
        ["P012027","P012028","P012029","P012030"],
        2010, "Decennial 2010 SF1"),
    ("2015", "acs/acs5", "2014",
        ["B01001_003E","B01001_004E","B01001_005E","B01001_006E"],
        ["B01001_027E","B01001_028E","B01001_029E","B01001_030E"],
        2010, "ACS 5-yr 2010-2014"),
    ("2020", "dec/dhc",  "2020",
        ["P12_003N","P12_004N","P12_005N","P12_006N"],
        ["P12_027N","P12_028N","P12_029N","P12_030N"],
        2020, "Decennial 2020 DHC"),
    ("2024", "acs/acs5", "2023",
        ["B01001_003E","B01001_004E","B01001_005E","B01001_006E"],
        ["B01001_027E","B01001_028E","B01001_029E","B01001_030E"],
        2020, "ACS 5-yr 2019-2023"),
]


def load_target_counties():
    """Return list of dicts: cbsa_code, state_fips, county_fips."""
    rows = []
    with open(DATA / "modern_msa_counties.csv") as f:
        for r in csv.DictReader(f):
            if r["cbsa_code"] in TARGET_CBSAS:
                fips = r["county_fips"]
                rows.append({
                    "cbsa_code": r["cbsa_code"],
                    "state_fips": fips[:2],
                    "county_fips": fips[2:],
                    "county_name": r["county_name"],
                })
    return rows


def fetch_tract_data(dataset, year, variables, state, county, retries=4):
    """Call Census API. variables: list of var codes (we sum them)."""
    get_str = ",".join(variables)
    url = f"https://api.census.gov/data/{year}/{dataset}"
    params = {
        "get": get_str,
        "for": "tract:*",
        "in": f"state:{state}+county:{county}",
        "key": CENSUS_KEY,
    }
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=120)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 204:
                # No content; treat as empty
                return [["state","county","tract"]]
            else:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:
            last_err = str(e)
        time.sleep(2 + attempt * 2)
    raise RuntimeError(f"Failed {url} state={state} county={county}: {last_err}")


def pull_snapshot(label, dataset, year, vars_m, vars_f, boundary_year,
                  source_label, counties):
    """Pull one snapshot for all counties. Returns dict keyed by 11-char GEOID -> under18."""
    out = {}
    all_vars = vars_m + vars_f
    n = len(counties)
    for i, c in enumerate(counties, 1):
        rows = fetch_tract_data(dataset, year, all_vars, c["state_fips"],
                                c["county_fips"])
        # First row is header
        if not rows or len(rows) < 2:
            continue
        header = rows[0]
        # variable positions
        var_idx = {v: header.index(v) for v in all_vars}
        s_idx = header.index("state")
        co_idx = header.index("county")
        tr_idx = header.index("tract")
        for r in rows[1:]:
            try:
                vals = [int(r[var_idx[v]]) if r[var_idx[v]] not in (None,"",".") else 0 for v in all_vars]
                under18 = sum(vals)
            except (ValueError, TypeError):
                under18 = None
            geoid = r[s_idx] + r[co_idx] + r[tr_idx]
            # Make sure tract is 6 chars (some 2000 records have shorter)
            tract = r[tr_idx]
            if len(tract) < 6:
                # Pad with trailing zeros? Census 2000 sometimes uses 4-digit (no decimals).
                # Standard: 6-digit tract with 2 implied decimals appended as zeros.
                tract = tract.ljust(6, "0")
            geoid = r[s_idx] + r[co_idx] + tract
            out[geoid] = {
                "cbsa_code": c["cbsa_code"],
                "state_fips": r[s_idx],
                "county_fips": r[co_idx],
                "tract_fips": tract,
                "geoid": geoid,
                "under18": under18,
                "boundary_year": boundary_year,
                "source": source_label,
            }
        if i % 10 == 0 or i == n:
            print(f"   [{label}] county {i}/{n}", flush=True)
    return out


def main():
    counties = load_target_counties()
    print(f"Loaded {len(counties)} counties across {len(TARGET_CBSAS)} CBSAs")

    # Pull each snapshot
    snapshot_data = {}  # label -> dict[geoid] -> row
    for label, dataset, year, vars_m, vars_f, boundary_year, source_label in SNAPSHOTS:
        print(f"\n=== Snapshot {label}: {source_label} ({dataset}/{year}) ===", flush=True)
        snap = pull_snapshot(label, dataset, year, vars_m, vars_f,
                             boundary_year, source_label, counties)
        print(f"   -> {len(snap)} tracts", flush=True)
        snapshot_data[label] = snap

    # Write LONG-format CSV
    long_path = DATA / "tract_under18_metro10_long.csv"
    with open(long_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cbsa_code","state_fips","county_fips","tract_fips","geoid",
                    "snapshot_year","boundary_year","under18","source"])
        for label, snap in snapshot_data.items():
            for geoid, row in snap.items():
                w.writerow([row["cbsa_code"], row["state_fips"], row["county_fips"],
                            row["tract_fips"], row["geoid"], label,
                            row["boundary_year"], row["under18"], row["source"]])
    print(f"\nWrote long: {long_path}")

    # Write WIDE-format CSV (one row per geoid, columns for each snapshot)
    # We use the *union* of GEOIDs across all snapshots.
    # boundary_year_per_snapshot is fixed by snapshot label.
    geoids = set()
    for snap in snapshot_data.values():
        geoids.update(snap.keys())
    print(f"Union of GEOIDs across snapshots: {len(geoids)}")

    wide_path = DATA / "tract_under18_metro10_snapshots.csv"
    with open(wide_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "geoid","cbsa_code","state_fips","county_fips","tract_fips",
            "under18_2000","under18_2005","under18_2010","under18_2015",
            "under18_2020","under18_2024",
            "boundary_2000","boundary_2005","boundary_2010","boundary_2015",
            "boundary_2020","boundary_2024",
        ])
        for geoid in sorted(geoids):
            # Find first snapshot that has metadata
            meta = None
            for label in ("2020","2010","2000","2015","2005","2024"):
                if geoid in snapshot_data[label]:
                    meta = snapshot_data[label][geoid]
                    break
            if meta is None:
                continue
            row = [
                geoid, meta["cbsa_code"], meta["state_fips"],
                meta["county_fips"], meta["tract_fips"],
            ]
            # under18 values
            for label in ("2000","2005","2010","2015","2020","2024"):
                v = snapshot_data[label].get(geoid)
                row.append(v["under18"] if v else "")
            # boundary years (constant by snapshot)
            for label in ("2000","2005","2010","2015","2020","2024"):
                v = snapshot_data[label].get(geoid)
                row.append(v["boundary_year"] if v else "")
            w.writerow(row)
    print(f"Wrote wide: {wide_path}")

    # Per-snapshot summary
    print("\n=== Snapshot summary ===")
    for label, snap in snapshot_data.items():
        n_tracts = len(snap)
        n_with_data = sum(1 for v in snap.values() if v["under18"] is not None)
        total_u18 = sum(v["under18"] for v in snap.values() if v["under18"] is not None)
        print(f"  {label}: {n_tracts} tracts, {n_with_data} with data, sum under18 = {total_u18:,}")


if __name__ == "__main__":
    main()
