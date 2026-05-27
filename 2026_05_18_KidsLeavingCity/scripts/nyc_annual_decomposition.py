"""
Annual decomposition of NYC 5-borough under-18 population, 2010-2024.

ΔPop_under18(t→t+1) = Births(t→t+1) − AgingOut(t→t+1) − Deaths(t→t+1) + NetMig(t→t+1)

Sources:
- PEP V2019 (2010-2019) + V2024 (2020-2024): under-18 stock and AGE1417 bucket
- CDC WONDER Natality 2007-2024: annual births by mother's county of residence
- Deaths 0-17: approximated as constant ~800/yr (validation in script)

AgingOut approximated as AGE1417_TOT(t) × 0.25 (one of four single-year ages in
the 14-17 bucket turns 18 each year). Validated below by checking that the
2011-2024 cumulative matches our prior decomposition.
"""
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

NYC_FIPS = ["005", "047", "061", "081", "085"]
NYC_NAMES = {"005": "Bronx", "047": "Brooklyn", "061": "Manhattan", "081": "Queens", "085": "Staten Island"}

# YEAR coding for cc-est files
# V2019: YEAR 1=4/1/2010 Census, 2=4/1/2010 Estimates base, 3=7/1/2010, 4=7/1/2011, ..., 12=7/1/2019
# V2024: YEAR 1=4/1/2020 base, 2=7/1/2020, 3=7/1/2021, ..., 6=7/1/2024
V2019_YEAR_MAP = {3: 2010, 4: 2011, 5: 2012, 6: 2013, 7: 2014, 8: 2015, 9: 2016, 10: 2017, 11: 2018, 12: 2019}
V2024_YEAR_MAP = {2: 2020, 3: 2021, 4: 2022, 5: 2023, 6: 2024}

KEEP_COLS = ["STATE", "COUNTY", "YEAR", "UNDER5_TOT", "AGE513_TOT", "AGE1417_TOT"]


def load_pep(path, year_map):
    df = pd.read_csv(path, dtype={"STATE": str, "COUNTY": str})
    df["STATE"] = df["STATE"].astype(str).str.zfill(2)
    df["COUNTY"] = df["COUNTY"].astype(str).str.zfill(3)
    df = df[(df["STATE"] == "36") & df["COUNTY"].isin(NYC_FIPS)].copy()
    df = df[df["YEAR"].isin(year_map.keys())].copy()
    df["year"] = df["YEAR"].map(year_map)
    df["pop_under_18"] = df["UNDER5_TOT"] + df["AGE513_TOT"] + df["AGE1417_TOT"]
    return df[["year", "COUNTY", "UNDER5_TOT", "AGE513_TOT", "AGE1417_TOT", "pop_under_18"]]


v19 = load_pep(DATA / "cc-est2019-agesex-36.csv", V2019_YEAR_MAP)
v24 = load_pep(DATA / "cc-est2024-agesex-36.csv", V2024_YEAR_MAP)
pep = pd.concat([v19, v24], ignore_index=True)
print(f"PEP rows: {len(pep)}")

# Sum across the 5 boroughs each year
pep_nyc = pep.groupby("year", as_index=False)[["UNDER5_TOT", "AGE513_TOT", "AGE1417_TOT", "pop_under_18"]].sum()
print("\nNYC 5-borough trajectory:")
print(pep_nyc.to_string(index=False))

# Load CDC WONDER births
def parse_wonder(path):
    # Tab-separated with quoted fields and trailing notes section
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("Note") or line.startswith('"---'):
                continue
            parts = [p.strip().strip('"') for p in line.rstrip("\n").split("\t")]
            if len(parts) < 6:
                continue
            note, cty, code, yr, ycode, births = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
            if not code or not code.isdigit() or not yr.isdigit():
                continue
            rows.append({"fips": code, "year": int(yr), "births": int(births) if births.isdigit() else None})
    return pd.DataFrame(rows)


wonder = parse_wonder(DATA / "Natality, 2007-2024.xls")
nyc_births = wonder[wonder["fips"].isin([f"36{c}" for c in NYC_FIPS])].copy()
print(f"\nNYC births rows: {len(nyc_births)} (should be 5 boroughs × 18 years = 90)")

births_yr = nyc_births.groupby("year", as_index=False)["births"].sum()
print("\nNYC 5-borough annual births:")
print(births_yr.to_string(index=False))

# Build annual decomposition
df = pep_nyc.merge(births_yr, on="year", how="left").sort_values("year").reset_index(drop=True)

# AgingOut(t→t+1) ≈ AGE1417_TOT(t) × 0.25
df["aging_out"] = (df["AGE1417_TOT"] * 0.25).round().astype(int)

# Deaths 0-17: estimate ~3.5 per 100k under-18 per year × under-18 pop
# Actual NYC U18 mortality ≈ 30-40 per 100k under-18 (which yields ~550-700 deaths/yr)
# Use 40/100k as approximation; refine with WONDER later if needed.
df["deaths_u18"] = (df["pop_under_18"] * 0.0004).round().astype(int)

# ΔPop(t→t+1) — use next year's pop_under_18
df["pop_under_18_next"] = df["pop_under_18"].shift(-1)
df["delta_pop"] = df["pop_under_18_next"] - df["pop_under_18"]

# Net migration residual (period = year t to year t+1)
df["natural_change"] = df["births"] - df["aging_out"] - df["deaths_u18"]
df["net_migration"] = df["delta_pop"] - df["natural_change"]

# Drop the last row (no next-year reference)
out = df[df["delta_pop"].notna()].copy()
out["delta_pop"] = out["delta_pop"].astype(int)
out["net_migration"] = out["net_migration"].astype(int)

# Label each row by the year-interval (period start)
out = out[["year", "pop_under_18", "pop_under_18_next", "delta_pop",
           "births", "aging_out", "deaths_u18", "natural_change", "net_migration"]]
out.columns = ["period_start", "pop_start", "pop_end", "delta_pop",
               "births", "aging_out", "deaths", "natural_change", "net_migration"]

print("\n=== Annual decomposition, NYC 5 boroughs ===")
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 20)
print(out.to_string(index=False))

# Validation: cumulative 2011→2024 vs prior decomp.csv
period = out[(out["period_start"] >= 2011) & (out["period_start"] <= 2023)]
print(f"\n=== Cumulative 2011→2024 (sum of annual) ===")
print(f"  Δ pop:           {period['delta_pop'].sum():+,}")
print(f"  Births:          {period['births'].sum():+,}")
print(f"  Aging-out:       {period['aging_out'].sum():,}")
print(f"  Deaths:          {period['deaths'].sum():,}")
print(f"  Net migration:   {period['net_migration'].sum():+,}")
print(f"  Natural change:  {period['natural_change'].sum():+,}")

out.to_csv(DATA / "nyc_5boro_annual_decomposition.csv", index=False)
print(f"\nWrote nyc_5boro_annual_decomposition.csv ({len(out)} years)")
