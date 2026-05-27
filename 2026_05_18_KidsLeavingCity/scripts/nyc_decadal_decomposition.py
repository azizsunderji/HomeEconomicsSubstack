"""
Build NYC 5-borough decadal decomposition of under-18 population 1940-2020.

For each decade T → T+10:
  ΔPop_under18 = Births(T to T+9) − [Aging-out + Deaths](T to T+10) + NetMig(T to T+10)
  Aging-out ≈ Pop_aged_8_17(T)  (cohort that turns 18 during the decade)

Data sources (single-source policy):
  - Population by age: NHGIS individual decennial census tables, all-persons universe
    1940: 1940_cAge / NT2B   (Sex by Age, 5-yr buckets — Persons)
    1950: 1950_cAge / NT2    (Age, single-yr+buckets — Persons Under 20)
    1960: 1960_cAge2 / NT2   (Age, single-yr — Persons under 21)
    1970: 1970_Cnt1 / NT18   (Sex by Age, single-yr 0-17 — Persons)
    1980: 1980_STF1 / NT10B  (Sex by Age — Persons)
    1990: 1990_STF1 / NP11   (Age — Persons) [from extract #123]
    2000: 2000_SF1a / NP012B (Sex by Age — Persons)
    2010: 2010_SF1a / P12    (Sex by Age — Persons)
    2020: 2020_DHCa / P12    (Sex by Age — Persons)
  - Births: NYC DOH Summary of Vital Statistics, sum of borough births (mom-of-residence)
"""
import re
import pandas as pd
from pathlib import Path

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
NHGIS_122 = DATA / "nhgis0122/nhgis0122_csv"
NHGIS_123 = DATA / "nhgis0123/nhgis0123_csv"

NYC_FIPS = {"005": "Bronx", "047": "Brooklyn", "061": "Manhattan", "081": "Queens", "085": "Staten Island"}
# 1940-1960 NHGIS uses COUNTYA = FIPS×10 (Bronx=050 not 005). Also "Brooklyn" was called
# "Kings", Manhattan was "New York", Staten Island was "Richmond". Filter by name for safety.
NYC_BOROUGH_NAMES = ["Bronx", "Kings", "New York", "Queens", "Richmond"]
NAME_TO_FIPS = {"Bronx": "005", "Kings": "047", "New York": "061", "Queens": "081", "Richmond": "085"}

FILES = [
    (1940, NHGIS_122 / "nhgis0122_ds77_1940_county.csv",  NHGIS_122 / "nhgis0122_ds77_1940_county_codebook.txt"),
    (1950, NHGIS_122 / "nhgis0122_ds83_1950_county.csv",  NHGIS_122 / "nhgis0122_ds83_1950_county_codebook.txt"),
    (1960, NHGIS_122 / "nhgis0122_ds90_1960_county.csv",  NHGIS_122 / "nhgis0122_ds90_1960_county_codebook.txt"),
    (1970, NHGIS_122 / "nhgis0122_ds94_1970_county.csv",  NHGIS_122 / "nhgis0122_ds94_1970_county_codebook.txt"),
    (1980, NHGIS_122 / "nhgis0122_ds104_1980_county.csv", NHGIS_122 / "nhgis0122_ds104_1980_county_codebook.txt"),
    (1990, NHGIS_123 / "nhgis0123_ds120_1990_county.csv", NHGIS_123 / "nhgis0123_ds120_1990_county_codebook.txt"),
    (2000, NHGIS_122 / "nhgis0122_ds146_2000_county.csv", NHGIS_122 / "nhgis0122_ds146_2000_county_codebook.txt"),
    (2010, NHGIS_122 / "nhgis0122_ds172_2010_county.csv", NHGIS_122 / "nhgis0122_ds172_2010_county_codebook.txt"),
    (2020, NHGIS_122 / "nhgis0122_ds258_2020_county.csv", NHGIS_122 / "nhgis0122_ds258_2020_county_codebook.txt"),
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
    """Return (lo, hi) for an age description, or None.

    Handles formats observed across NHGIS 1940-2020:
      - "Under X year(s)"           → (0, X-1)
      - "X to Y year(s) (of age)"   → (X, Y)
      - "X-Y" or "X-Y years"        → (X, Y)
      - "X and Y year(s)"           → (X, Y)
      - "X year(s) (of age) and over/older" → (X, 999)
      - "X year(s) (of age)" or "X years and over"
      - Just digits "5", "14"       → (X, X)
    """
    d = desc.lower()
    if ">>" in d:
        d = d.split(">>")[-1].strip()
    d = d.strip()

    # "Under X year(s)"  — keep open-ended (anywhere)
    m = re.search(r"under\s+(\d+)\s+years?", d)
    if m:
        x = int(m.group(1))
        return (0, max(0, x - 1))

    # "X year(s) and over/older" or "X+ years"
    m = re.search(r"(\d+)\s+years?\s+(?:and\s+)?(?:over|older)", d)
    if m:
        return (int(m.group(1)), 999)

    # "X and Y year(s)"  e.g. "10 and 11 years"
    m = re.search(r"(\d+)\s+and\s+(\d+)\s+years?", d)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # "X to Y" with optional trailing text "years (of age)"
    m = re.search(r"(\d+)\s+to\s+(\d+)(?:\s+years?(?:\s+of\s+age)?)?", d)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # "X-Y" with optional trailing "years"
    m = re.search(r"(\d+)\s*-\s*(\d+)(?:\s+years?)?", d)
    if m:
        return (int(m.group(1)), int(m.group(2)))

    # "X year(s) (of age)" standalone — must be whole string
    m = re.fullmatch(r"\s*(\d+)\s+years?(?:\s+of\s+age)?\s*", d)
    if m:
        return (int(m.group(1)), int(m.group(1)))

    # Just a digit, no "year" suffix (1970 NT18 style)
    m = re.fullmatch(r"\s*(\d+)\s*", d)
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


def parse_year(year, csv_path, cb_path):
    cb = read_codebook(cb_path)
    df = pd.read_csv(csv_path, encoding="latin-1")
    # Filter to NYC by STATE name and COUNTY name — robust across the FIPS-code
    # quirks of older NHGIS files (pre-1970 use COUNTYA = FIPS × 10).
    if "STATE" in df.columns and "COUNTY" in df.columns:
        # Strip " County" suffix and also " Borough" if present
        df["_cty"] = (df["COUNTY"].astype(str)
                                  .str.replace(r"\s+County$", "", regex=True)
                                  .str.replace(r"\s+Borough$", "", regex=True)
                                  .str.strip())
        nyc = df[(df["STATE"] == "New York") & df["_cty"].isin(NYC_BOROUGH_NAMES)].copy()
        nyc["fips_5"] = nyc["_cty"].map(NAME_TO_FIPS).map(lambda c: "36" + c)
    else:
        df["STATEA"] = df["STATEA"].astype(str).str.zfill(2)
        df["COUNTYA"] = df["COUNTYA"].astype(str).str.zfill(3)
        nyc = df[(df["STATEA"] == "36") & df["COUNTYA"].isin(NYC_FIPS.keys())].copy()
        nyc["fips_5"] = "36" + nyc["COUNTYA"]

    u18_w, a8_17_w = [], []
    for var, desc in cb:
        rng = parse_age_range(desc)
        if rng is None:
            continue
        lo, hi = rng
        wU = weight_under_18(lo, hi)
        wA = weight_8_17(lo, hi)
        if wU > 0 and var in nyc.columns:
            u18_w.append((var, wU))
        if wA > 0 and var in nyc.columns:
            a8_17_w.append((var, wA))

    def wsum(row, varws):
        s = 0.0
        for v, w in varws:
            val = row.get(v)
            if pd.notna(val):
                s += float(val) * w
        return s

    nyc["under_18"] = nyc.apply(lambda r: wsum(r, u18_w), axis=1)
    nyc["age_8_17"] = nyc.apply(lambda r: wsum(r, a8_17_w), axis=1)
    return nyc.groupby("fips_5")[["under_18", "age_8_17"]].sum()


# Parse all years
pop = {}
for year, csv_path, cb_path in FILES:
    agg = parse_year(year, csv_path, cb_path)
    nyc_total = agg.sum()
    pop[year] = {
        "under_18": int(nyc_total["under_18"]),
        "age_8_17": int(nyc_total["age_8_17"]),
    }
    print(f"{year}: under_18={pop[year]['under_18']:>9,}  age_8_17={pop[year]['age_8_17']:>9,}")

# Load births
births_df = pd.read_csv(DATA / "nyc_doh_births_historical.csv")
# Use residents_sum_of_boroughs when available, else estimate from total × 0.91
def total_births(row):
    if pd.notna(row.get("NYC_residents_sum_of_boroughs")):
        return int(row["NYC_residents_sum_of_boroughs"])
    if pd.notna(row.get("NYC_total_reported")):
        return int(row["NYC_total_reported"] * 0.91)  # ratio observed 1995-2023
    return None

births_df["resident_births"] = births_df.apply(total_births, axis=1)
births_by_yr = births_df.set_index("year")["resident_births"]
print("\nNYC births by year (resident-only, est. for pre-1995):")
print(births_by_yr.dropna().astype(int).to_string())

# Build decadal decomposition
decades = [(1940, 1950), (1950, 1960), (1960, 1970), (1970, 1980),
           (1980, 1990), (1990, 2000), (2000, 2010), (2010, 2020)]

rows = []
for t, t10 in decades:
    if t not in pop or t10 not in pop:
        continue
    pop_t = pop[t]["under_18"]
    pop_t10 = pop[t10]["under_18"]
    delta_pop = pop_t10 - pop_t
    aging_out = pop[t]["age_8_17"]  # cohort that turns 18 during decade
    # Births during decade T to T+9
    decade_births = int(births_by_yr.loc[t:t10-1].sum())
    natural_change = decade_births - aging_out
    net_mig = delta_pop - natural_change
    rows.append({
        "decade_start": t,
        "decade_end": t10,
        "label": f"{t}–{str(t10)[-2:]}",
        "pop_start": pop_t,
        "pop_end": pop_t10,
        "delta_pop": delta_pop,
        "births": decade_births,
        "aging_out": aging_out,
        "natural_change": natural_change,
        "net_migration": net_mig,
    })

out = pd.DataFrame(rows)
out.to_csv(DATA / "nyc_decadal_decomposition.csv", index=False)
print("\n=== NYC 5-borough decadal decomposition ===")
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
print(out.to_string(index=False))
print(f"\nWrote nyc_decadal_decomposition.csv ({len(out)} decades)")
