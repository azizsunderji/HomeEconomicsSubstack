"""
Parse each decennial NHGIS file and extract NYC 5-borough under-18
population + aged 8-17 cohort.

The variable naming differs per decade — we map each one explicitly using
the codebook info.
"""
import pandas as pd
import re
from pathlib import Path

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
NHGIS = DATA / "nhgis0122/nhgis0122_csv"

NYC_FIPS = {"005": "Bronx", "047": "Brooklyn", "061": "Manhattan", "081": "Queens", "085": "Staten Island"}
results = []


def read_codebook(path):
    """Yield (var_code, description) pairs from a codebook."""
    text = path.read_text(errors="ignore")
    # Variable rows look like "        BD7AA:    Male >> Under 1 year"
    for line in text.splitlines():
        m = re.match(r"\s{4,}([A-Z][A-Z0-9]+):\s+(.+)$", line)
        if m:
            yield m.group(1), m.group(2).strip()


def get_age_vars(codebook_path, age_keywords):
    """Return list of (var, desc) where desc matches an age keyword."""
    matches = []
    for var, desc in read_codebook(codebook_path):
        for kw in age_keywords:
            if kw.lower() in desc.lower():
                matches.append((var, desc))
                break
    return matches


def borough_filter(df, state_col="STATEA", county_col="COUNTYA"):
    df = df.copy()
    df[state_col] = df[state_col].astype(str).str.zfill(2)
    df[county_col] = df[county_col].astype(str).str.zfill(3)
    return df[(df[state_col] == "36") & df[county_col].isin(NYC_FIPS.keys())]


# ── 1940 — Sex by Age, 5-year buckets ─────────────────────────────────────────
# Variables in NT2B: Male/Female × {Under 1, 1-4, 5-9, 10-14, 15-19, ..., 75+}
# Need to sum Male+Female for ages under 18. The 15-19 bucket needs 3/5 weighting.
print("\n=== 1940 ===")
df40 = pd.read_csv(NHGIS / "nhgis0122_ds77_1940_county.csv", encoding="latin-1")
print(f"  Columns: {[c for c in df40.columns if c.startswith('BD')][:8]}...")
nyc40 = borough_filter(df40)
# Inspect codebook
cb40 = read_codebook(NHGIS / "nhgis0122_ds77_1940_county_codebook.txt")
ages40 = {var: desc for var, desc in cb40}
# Map age brackets - looking for Male/Female + age range
under_18_vars = []
age_8_17_vars = []
for var, desc in ages40.items():
    if "Under 1" in desc or "1 to 4" in desc or "5 to 9" in desc or "10 to 14" in desc:
        under_18_vars.append(var)
    if "15 to 19" in desc:
        under_18_vars.append((var, 0.6))  # 3/5 of 15-19 is 15-17
    if "5 to 9" in desc:
        age_8_17_vars.append((var, 0.4))  # 2/5 of 5-9 is 8-9
    elif "10 to 14" in desc:
        age_8_17_vars.append((var, 1.0))
    elif "15 to 19" in desc:
        age_8_17_vars.append((var, 0.6))  # 15-17 portion

print(f"  under_18_vars: {len(under_18_vars)}")
print(f"  age_8_17_vars: {len(age_8_17_vars)}")

def weighted_sum(df, vars_w):
    total = 0
    for item in vars_w:
        if isinstance(item, tuple):
            v, w = item
            if v in df.columns:
                total += df[v].astype(float) * w
        else:
            v = item
            if v in df.columns:
                total += df[v].astype(float)
    return total

nyc40["under_18"] = weighted_sum(nyc40, under_18_vars)
nyc40["age_8_17"] = weighted_sum(nyc40, age_8_17_vars)
agg40 = nyc40.groupby("COUNTYA")[["under_18", "age_8_17"]].sum()
print(agg40.astype(int).to_string())
for fips, name in NYC_FIPS.items():
    if fips in agg40.index:
        r = agg40.loc[fips]
        results.append({"year": 1940, "borough": name, "fips": "36"+fips,
                        "under_18": int(r["under_18"]), "age_8_17": int(r["age_8_17"])})


# ── 1950 — single-year ages 0-17 (under-20 universe) ──────────────────────────
print("\n=== 1950 ===")
df50 = pd.read_csv(NHGIS / "nhgis0122_ds83_1950_county.csv", encoding="latin-1")
print(f"  Columns: {[c for c in df50.columns if re.match(r'B', c)][:8]}...")
cb50 = list(read_codebook(NHGIS / "nhgis0122_ds83_1950_county_codebook.txt"))
ages50 = {var: desc for var, desc in cb50}
print(f"  Vars: {list(ages50.items())[:5]}")
nyc50 = borough_filter(df50)
# 1950 NT2 has single-age (and bucketed): 0, 1-2, 3-4, 5, 6, 7-9, 10-13, 14, 15, 16-17, 18-19
# All vars for ages 0-17 = the first 10 vars (everything except 18-19)
u18_vars_50 = []
a8_17_vars_50 = []
for var, desc in ages50.items():
    if "0 years" in desc or "1 to 2" in desc or "3 to 4" in desc:
        u18_vars_50.append(var)
    elif "5 years" in desc or "6 years" in desc or "7 to 9" in desc:
        u18_vars_50.append(var)
        if "7 to 9" in desc:
            a8_17_vars_50.append((var, 2/3))  # ages 8, 9 out of 7-9
    elif "10 to 13" in desc:
        u18_vars_50.append(var)
        a8_17_vars_50.append((var, 1.0))
    elif "14 years" in desc or "15 years" in desc:
        u18_vars_50.append(var)
        a8_17_vars_50.append((var, 1.0))
    elif "16 to 17" in desc:
        u18_vars_50.append(var)
        a8_17_vars_50.append((var, 1.0))

print(f"  u18: {len(u18_vars_50)}, a8_17: {len(a8_17_vars_50)}")

nyc50["under_18"] = weighted_sum(nyc50, u18_vars_50)
nyc50["age_8_17"] = weighted_sum(nyc50, a8_17_vars_50)
agg50 = nyc50.groupby("COUNTYA")[["under_18", "age_8_17"]].sum()
print(agg50.astype(int).to_string())
for fips, name in NYC_FIPS.items():
    if fips in agg50.index:
        r = agg50.loc[fips]
        results.append({"year": 1950, "borough": name, "fips": "36"+fips,
                        "under_18": int(r["under_18"]), "age_8_17": int(r["age_8_17"])})


# ── 1960 — single-year ages 0-21 ──────────────────────────────────────────────
print("\n=== 1960 ===")
df60 = pd.read_csv(NHGIS / "nhgis0122_ds90_1960_county.csv", encoding="latin-1")
cb60 = list(read_codebook(NHGIS / "nhgis0122_ds90_1960_county_codebook.txt"))
ages60 = {var: desc for var, desc in cb60}
print(f"  Vars: {list(ages60.items())[:5]}")
nyc60 = borough_filter(df60)
# Variables: "0 years", "1 year", "2 years", ..., "17 years", "18 years", ...
u18_vars_60 = []
a8_17_vars_60 = []
for var, desc in ages60.items():
    m = re.match(r"(\d+) year", desc)
    if m:
        age = int(m.group(1))
        if age < 18:
            u18_vars_60.append(var)
        if 8 <= age < 18:
            a8_17_vars_60.append(var)
print(f"  u18: {len(u18_vars_60)} (should be 18), a8_17: {len(a8_17_vars_60)} (should be 10)")

nyc60["under_18"] = weighted_sum(nyc60, u18_vars_60)
nyc60["age_8_17"] = weighted_sum(nyc60, a8_17_vars_60)
agg60 = nyc60.groupby("COUNTYA")[["under_18", "age_8_17"]].sum()
print(agg60.astype(int).to_string())
for fips, name in NYC_FIPS.items():
    if fips in agg60.index:
        r = agg60.loc[fips]
        results.append({"year": 1960, "borough": name, "fips": "36"+fips,
                        "under_18": int(r["under_18"]), "age_8_17": int(r["age_8_17"])})


# ── 1970-2020: each decade has different age-bucket structures ────────────────
# We'll parse codebook to find Male/Female by Age, then sum.

DECADES_LATER = [
    (1970, "nhgis0122_ds94_1970_county.csv",  "nhgis0122_ds94_1970_county_codebook.txt"),
    (1980, "nhgis0122_ds104_1980_county.csv", "nhgis0122_ds104_1980_county_codebook.txt"),
    (1990, "nhgis0122_ds120_1990_county.csv", "nhgis0122_ds120_1990_county_codebook.txt"),
    (2000, "nhgis0122_ds146_2000_county.csv", "nhgis0122_ds146_2000_county_codebook.txt"),
    (2010, "nhgis0122_ds172_2010_county.csv", "nhgis0122_ds172_2010_county_codebook.txt"),
    (2020, "nhgis0122_ds258_2020_county.csv", "nhgis0122_ds258_2020_county_codebook.txt"),
]


def parse_age_from_desc(desc):
    """Try to extract age bracket from a description like 'Male >> 15 to 17 years'."""
    desc = desc.lower()
    # Match patterns
    m = re.search(r"under 1 year", desc)
    if m: return (0, 0)
    m = re.search(r"(\d+)\s*(?:to|-)\s*(\d+)\s*years?", desc)
    if m: return (int(m.group(1)), int(m.group(2)))
    m = re.search(r"(\d+)\s*and\s*(\d+)\s*years?", desc)
    if m: return (int(m.group(1)), int(m.group(2)))
    m = re.search(r"(\d+)\s*years?\s*(?:old|of age)?\b", desc)
    if m: return (int(m.group(1)), int(m.group(1)))
    return None


def weight_for_under_18(lo, hi):
    """Fraction of [lo, hi] inclusive that falls in [0, 17]."""
    if hi < 0 or lo > 17:
        return 0
    lo_c = max(lo, 0); hi_c = min(hi, 17)
    width = hi - lo + 1
    return (hi_c - lo_c + 1) / width


def weight_for_8_17(lo, hi):
    if hi < 8 or lo > 17:
        return 0
    lo_c = max(lo, 8); hi_c = min(hi, 17)
    width = hi - lo + 1
    return (hi_c - lo_c + 1) / width


for year, csv_name, cb_name in DECADES_LATER:
    print(f"\n=== {year} ===")
    df = pd.read_csv(NHGIS / csv_name, encoding="latin-1")
    cb = list(read_codebook(NHGIS / cb_name))
    nyc = borough_filter(df)

    u18_w = []
    a8_17_w = []
    for var, desc in cb:
        rng = parse_age_from_desc(desc)
        if rng is None:
            continue
        lo, hi = rng
        wU = weight_for_under_18(lo, hi)
        wA = weight_for_8_17(lo, hi)
        if wU > 0:
            u18_w.append((var, wU))
        if wA > 0:
            a8_17_w.append((var, wA))

    print(f"  u18 vars: {len(u18_w)}, a8_17 vars: {len(a8_17_w)}")
    if not u18_w:
        # try to print first 5 codebook items so we can debug
        for var, desc in cb[:20]:
            print(f"   debug | {var} = {desc}")
        continue

    nyc["under_18"] = weighted_sum(nyc, u18_w)
    nyc["age_8_17"] = weighted_sum(nyc, a8_17_w)
    agg = nyc.groupby("COUNTYA")[["under_18", "age_8_17"]].sum()
    print(agg.astype(int).to_string())
    for fips, name in NYC_FIPS.items():
        if fips in agg.index:
            r = agg.loc[fips]
            results.append({"year": year, "borough": name, "fips": "36"+fips,
                            "under_18": int(r["under_18"]), "age_8_17": int(r["age_8_17"])})


out = pd.DataFrame(results).sort_values(["year", "borough"]).reset_index(drop=True)
out.to_csv(DATA / "nyc_decennial_pop_1940_2020.csv", index=False)
print("\n=== Final summary ===")
print(out.to_string(index=False))
nyc_tot = out.groupby("year")[["under_18", "age_8_17"]].sum()
print("\nNYC 5-borough totals:")
print(nyc_tot.astype(int).to_string())
