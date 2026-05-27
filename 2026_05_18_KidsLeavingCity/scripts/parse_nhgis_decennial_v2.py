"""
Parse decennial NHGIS files and extract NYC 5-borough under-18 population
and aged 8-17 cohort, robust to varied description patterns.

Handles:
  - "Under 1 year" / "Under 5 years"        → [0, X-1]
  - "X years"                                → [X, X]
  - "X to Y years"                           → [X, Y]
  - "X and Y years"                          → [X, Y]
  - "X years and over" / "X years and older" → [X, 999]
"""
import pandas as pd
import re
from pathlib import Path

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
NHGIS = DATA / "nhgis0122/nhgis0122_csv"

NYC_FIPS = {"005": "Bronx", "047": "Brooklyn", "061": "Manhattan", "081": "Queens", "085": "Staten Island"}

FILES = [
    (1940, "nhgis0122_ds77_1940_county.csv",  "nhgis0122_ds77_1940_county_codebook.txt"),
    (1950, "nhgis0122_ds83_1950_county.csv",  "nhgis0122_ds83_1950_county_codebook.txt"),
    (1960, "nhgis0122_ds90_1960_county.csv",  "nhgis0122_ds90_1960_county_codebook.txt"),
    (1970, "nhgis0122_ds94_1970_county.csv",  "nhgis0122_ds94_1970_county_codebook.txt"),
    (1980, "nhgis0122_ds104_1980_county.csv", "nhgis0122_ds104_1980_county_codebook.txt"),
    (1990, "nhgis0122_ds120_1990_county.csv", "nhgis0122_ds120_1990_county_codebook.txt"),
    (2000, "nhgis0122_ds146_2000_county.csv", "nhgis0122_ds146_2000_county_codebook.txt"),
    (2010, "nhgis0122_ds172_2010_county.csv", "nhgis0122_ds172_2010_county_codebook.txt"),
    (2020, "nhgis0122_ds258_2020_county.csv", "nhgis0122_ds258_2020_county_codebook.txt"),
]

VAR_RE = re.compile(r"^\s+([A-Z][A-Z0-9]+):\s+(.+)$")


def read_codebook(path):
    out = []
    for line in path.read_text(errors="ignore").splitlines():
        m = VAR_RE.match(line)
        if m:
            out.append((m.group(1), m.group(2).strip()))
    return out


def parse_age_range(desc):
    """Return (lo, hi) age range. Returns None if no age detected."""
    d = desc.lower()
    # "Under X years" / "Under X year"
    m = re.search(r"under\s+(\d+)\s+years?", d)
    if m:
        x = int(m.group(1))
        return (0, max(0, x - 1))
    # "X to Y years"
    m = re.search(r"(\d+)\s+to\s+(\d+)\s+years?", d)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    # "X and Y years" / "X and Y year"
    m = re.search(r"(\d+)\s+and\s+(\d+)\s+years?", d)
    if m:
        return (int(m.group(1)), int(m.group(2)))
    # "X years and over/older/older and over"
    m = re.search(r"(\d+)\s+years?\s+(?:and\s+)?(?:over|older)", d)
    if m:
        return (int(m.group(1)), 999)
    # "X years" (standalone single year)
    m = re.search(r"\b(\d+)\s+years?(?:\s+of\s+age)?\s*$", d)
    if m:
        return (int(m.group(1)), int(m.group(1)))
    # "X year" without "s" suffix, e.g. "1 year"
    m = re.search(r"\b(\d+)\s+year\s+of\s+age\s*$", d)
    if m:
        return (int(m.group(1)), int(m.group(1)))
    return None


def weight_under_18(lo, hi):
    if hi < 0 or lo > 17:
        return 0
    width = max(1, hi - lo + 1)
    return (min(hi, 17) - max(lo, 0) + 1) / width


def weight_8_17(lo, hi):
    if hi < 8 or lo > 17:
        return 0
    width = max(1, hi - lo + 1)
    return (min(hi, 17) - max(lo, 8) + 1) / width


results = []
for year, csv_name, cb_name in FILES:
    print(f"\n=== {year} ===")
    df = pd.read_csv(NHGIS / csv_name, encoding="latin-1")
    cb = read_codebook(NHGIS / cb_name)
    if not cb:
        print(f"  WARN: no variables found in codebook!")
        continue
    print(f"  codebook variables: {len(cb)}")

    u18_w = []
    a8_17_w = []
    debug_lines = []
    for var, desc in cb:
        rng = parse_age_range(desc)
        if rng is None:
            continue
        lo, hi = rng
        wU = weight_under_18(lo, hi)
        wA = weight_8_17(lo, hi)
        debug_lines.append(f"    {var}  {lo}-{hi}  wU={wU:.2f} wA={wA:.2f}  | {desc[:60]}")
        if wU > 0:
            u18_w.append((var, wU))
        if wA > 0:
            a8_17_w.append((var, wA))

    print(f"  u18_w: {len(u18_w)},  a8_17_w: {len(a8_17_w)}")
    if year in (1970, 1990):
        # debug
        for line in debug_lines[:25]:
            print(line)

    # Filter to NYC counties
    df["STATEA"] = df["STATEA"].astype(str).str.zfill(2)
    df["COUNTYA"] = df["COUNTYA"].astype(str).str.zfill(3)
    nyc = df[(df["STATEA"] == "36") & df["COUNTYA"].isin(NYC_FIPS.keys())].copy()

    def wsum(row, varws):
        s = 0.0
        for v, w in varws:
            val = row.get(v)
            if pd.notna(val):
                s += float(val) * w
        return s

    nyc["under_18"] = nyc.apply(lambda r: wsum(r, u18_w), axis=1)
    nyc["age_8_17"] = nyc.apply(lambda r: wsum(r, a8_17_w), axis=1)
    agg = nyc.groupby("COUNTYA")[["under_18", "age_8_17"]].sum()

    print(agg.astype(int).to_string())
    for fips, name in NYC_FIPS.items():
        if fips in agg.index:
            r = agg.loc[fips]
            results.append({
                "year": year, "borough": name, "fips": "36"+fips,
                "under_18": int(r["under_18"]),
                "age_8_17": int(r["age_8_17"]),
            })

out = pd.DataFrame(results).sort_values(["year", "borough"]).reset_index(drop=True)
out.to_csv(DATA / "nyc_decennial_pop_1940_2020.csv", index=False)

print("\n=== Final NYC 5-borough totals (under-18 and age 8-17 cohort) ===")
nyc_tot = out.groupby("year")[["under_18", "age_8_17"]].sum().astype(int)
print(nyc_tot.to_string())
