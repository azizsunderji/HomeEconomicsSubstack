"""
Finalize the tract under-18 snapshot output.

Reads:
  data/tract_under18_metro10_snapshots.csv   (wide)
  data/tract_under18_metro10_long.csv        (long)

Produces a final cleaned version with:
  - gisjoin column (NHGIS format: G<state(2)>0<county(3)>0<tract(6)>)
  - Summary CSV per metro / per snapshot of total under-18

Also prints a coverage report (tracts per snapshot, tracts missing, etc.)
"""
import csv
from pathlib import Path
from collections import defaultdict

DATA = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity/data")

WIDE_IN  = DATA / "tract_under18_metro10_snapshots.csv"
LONG_IN  = DATA / "tract_under18_metro10_long.csv"
WIDE_OUT = DATA / "tract_under18_metro10_snapshots.csv"  # overwrite with gisjoin added
METRO_SUMMARY = DATA / "tract_under18_metro10_metro_summary.csv"


def to_gisjoin(state, county, tract):
    """NHGIS GISJOIN: G + state(2) + 0 + county(3) + 0 + tract(6)"""
    return f"G{state}0{county}0{tract}"


def main():
    # Read wide CSV
    with open(WIDE_IN) as f:
        rows = list(csv.DictReader(f))
    print(f"Read {len(rows)} rows from wide CSV")

    # Add gisjoin
    for r in rows:
        r["gisjoin"] = to_gisjoin(r["state_fips"], r["county_fips"], r["tract_fips"])

    # Snapshot summary
    snapshots = ("2000","2005","2010","2015","2020","2024")
    print("\n=== Coverage per snapshot ===")
    for sn in snapshots:
        col = f"under18_{sn}"
        n_present = sum(1 for r in rows if r[col] not in ("","None"))
        total = sum(int(r[col]) for r in rows if r[col] not in ("","None"))
        print(f"  {sn}: {n_present} tracts, total under18 = {total:,}")

    # Per CBSA & snapshot totals
    cbsa_totals = defaultdict(lambda: {sn: 0 for sn in snapshots})
    cbsa_tracts = defaultdict(lambda: {sn: 0 for sn in snapshots})
    for r in rows:
        cbsa = r["cbsa_code"]
        for sn in snapshots:
            v = r[f"under18_{sn}"]
            if v not in ("","None"):
                cbsa_totals[cbsa][sn] += int(v)
                cbsa_tracts[cbsa][sn] += 1

    print("\n=== Per-CBSA totals ===")
    cbsa_names = {
        "35620":"New York","31080":"Los Angeles","16980":"Chicago",
        "19100":"Dallas","26420":"Houston","12060":"Atlanta",
        "47900":"Washington","33100":"Miami","37980":"Philadelphia","38060":"Phoenix",
    }
    with open(METRO_SUMMARY, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["cbsa_code","cbsa_name"] + [f"under18_{sn}" for sn in snapshots]
                   + [f"tracts_{sn}" for sn in snapshots])
        for c in sorted(cbsa_totals.keys()):
            name = cbsa_names.get(c, c)
            row = [c, name] + [cbsa_totals[c][sn] for sn in snapshots] \
                  + [cbsa_tracts[c][sn] for sn in snapshots]
            w.writerow(row)
            print(f"  {c} ({name}): " + ", ".join(
                f"{sn}={cbsa_totals[c][sn]:,}" for sn in snapshots))

    # Write back wide CSV with gisjoin
    out_fields = (
        ["gisjoin","geoid","cbsa_code","state_fips","county_fips","tract_fips"]
        + [f"under18_{sn}" for sn in snapshots]
        + [f"boundary_{sn}" for sn in snapshots]
    )
    with open(WIDE_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in out_fields})
    print(f"\nUpdated wide CSV (added gisjoin): {WIDE_OUT}")
    print(f"Wrote per-metro summary: {METRO_SUMMARY}")


if __name__ == "__main__":
    main()
