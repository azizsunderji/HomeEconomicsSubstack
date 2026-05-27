"""
Extend the NY area under-18 time series back to 1970 using NHGIS D08.

Reads:
- data/nhgis0121/nhgis0121_csv/nhgis0121_ts_nominal_county.csv  (1970-2010 decennial)
- data/ny_under18_timeseries.csv                                 (2010-2024 annual PEP)

Writes:
- data/ny_under18_extended.csv  (1970, 1980, 1990, 2000, 2010, then annual 2011-2024)

Strategy: For 2010, use the NHGIS Census 2010 figure (April 1) which should align
closely with the PEP April 2010 baseline. Then PEP for 2011-2024.
The two Connecticut planning regions (09120, 09190) start in 2022 only — pre-2010
data is blank for them, and they get NaN for the entire pre-PEP period.
"""
import pandas as pd
from pathlib import Path

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

# Existing 2010-2024 series
pep = pd.read_csv(DATA / "ny_under18_timeseries.csv")
target_counties = [c for c in pep.columns if c != "year"]
print(f"Target counties: {len(target_counties)}")

# NHGIS historical
nh = pd.read_csv(DATA / "nhgis0121/nhgis0121_csv/nhgis0121_ts_nominal_county.csv",
                 dtype={"STATEFP": str, "COUNTYFP": str})
nh["fips5"] = nh["STATEFP"].str.zfill(2) + nh["COUNTYFP"].str.zfill(3)
nh = nh[nh["fips5"].isin(target_counties)].copy()
print(f"NHGIS rows matched to NY counties: {len(nh)}  (= 5 yrs × {len(nh)//5 if len(nh)%5==0 else '?'} counties)")

# Pivot to year × county
hist = nh.pivot_table(index="YEAR", columns="fips5", values="D08AA", aggfunc="sum")
hist.index.name = "year"
hist = hist.reset_index()

# Reorder columns to match PEP
hist = hist[["year"] + [c for c in target_counties if c in hist.columns]]

# Stack: NHGIS 1970, 1980, 1990, 2000 (drop NHGIS 2010 — use PEP 2010), then PEP 2010+
hist_pre2010 = hist[hist["year"] != 2010].copy()
combined = pd.concat([hist_pre2010, pep], ignore_index=True).sort_values("year").reset_index(drop=True)

# Verify
print("\nCombined year list:", combined["year"].tolist())
print(f"\nManhattan (36061) trajectory:")
print(combined[["year", "36061"]].to_string(index=False))
print(f"\nBrooklyn (36047) trajectory:")
print(combined[["year", "36047"]].to_string(index=False))

# Sanity check: NHGIS 2010 vs PEP 2010 for a few counties
nhgis_2010 = nh[nh["YEAR"] == 2010].set_index("fips5")["D08AA"]
pep_2010 = pep[pep["year"] == 2010].iloc[0]
print("\n=== NHGIS Census 2010 vs PEP April 2010 baseline ===")
for c in ["36005", "36047", "36061", "36081", "36085", "34003", "34013"]:
    if c in nhgis_2010.index:
        n = nhgis_2010[c]
        p = pep_2010.get(c)
        diff_pct = (p - n) / n * 100 if n else 0
        print(f"  {c}: NHGIS={n:>8.0f}  PEP={p:>8.0f}  diff={diff_pct:+.2f}%")

combined.to_csv(DATA / "ny_under18_extended.csv", index=False)
print(f"\nWrote ny_under18_extended.csv — {len(combined)} rows")
