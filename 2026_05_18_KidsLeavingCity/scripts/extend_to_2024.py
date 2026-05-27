"""
Extend the city-vs-suburb chart with a 2024 datapoint.

Inputs:
  data/pep_2024_national.csv               — under-18 by county, July 2024
  data/under18_county_classification.csv   — tier per county (from earlier work)
  data/under18_city_suburb_1970_decomp.csv — existing 1950-2020 panel
  data/under18_central_cities_2024.csv     — 60-city under-18 for 2024 (from agent)

Output:
  data/under18_city_suburb_1970_decomp_to2024.csv
"""
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

# Load PEP 2024
pep = pd.read_csv(DATA / "pep_2024_national.csv", dtype={"fips_5": str})
pep = pep.rename(columns={"fips_5": "county_fips", "pop_under18_2024": "under18"})
pep["county_fips"] = pep["county_fips"].str.zfill(5)
pep["under18"] = pd.to_numeric(pep["under18"], errors="coerce")

# Load tier classification (built earlier with same A/B/C/D scheme)
# We need: A_city_core_1950, B_original_suburb_1970, C_new_city_core_post1970, D_annexed_suburb_post1970, Z_never_msa
# Use the 4-tier classification logic from build_msa_membership_panel.py output.
mem = pd.read_csv(DATA / "msa_membership_by_decade.csv", dtype={"county_fips": str})
mem["county_fips"] = mem["county_fips"].str.zfill(5)

sma1950 = pd.read_csv(DATA / "sma_1950_counties.csv", dtype={"county_fips": str})
sma1950["county_fips"] = sma1950["county_fips"].str.zfill(5)
sma_central = sma1950.groupby("county_fips", as_index=False)["is_central_county"].max()
sma_central["was_1950_central"] = sma_central["is_central_county"] == 1
sma_central = sma_central[["county_fips", "was_1950_central"]]

modern = pd.read_csv(DATA / "modern_msa_counties.csv", dtype={"county_fips": str})
modern["county_fips"] = modern["county_fips"].str.zfill(5)
modern_central = modern.groupby("county_fips", as_index=False)["central_or_outlying"].max()
modern_central["is_modern_central"] = modern_central["central_or_outlying"] == "Central"
modern_central = modern_central[["county_fips", "is_modern_central"]]

counties = pep[["county_fips"]].drop_duplicates().copy()
counties = counties.merge(mem[["county_fips", "first_msa_decade"]], on="county_fips", how="left")
counties = counties.merge(sma_central, on="county_fips", how="left")
counties = counties.merge(modern_central, on="county_fips", how="left")
counties["first_msa_decade"] = counties["first_msa_decade"].fillna(0).astype(int)
counties["was_1950_central"] = counties["was_1950_central"].fillna(False).astype(bool)
counties["is_modern_central"] = counties["is_modern_central"].fillna(False).astype(bool)


def tier(row):
    fmd = row["first_msa_decade"]
    if fmd == 0:
        return "Z_never_msa"
    if fmd == 1950 and row["was_1950_central"]:
        return "A_city_core_1950"
    if fmd <= 1970:
        return "B_original_suburb_1970"
    if row["is_modern_central"]:
        return "C_new_city_core_post1970"
    return "D_annexed_suburb_post1970"


counties["tier"] = counties.apply(tier, axis=1)
joined = pep.merge(counties[["county_fips", "tier"]], on="county_fips", how="left")
joined["tier"] = joined["tier"].fillna("Z_never_msa")

agg2024 = joined.groupby("tier", as_index=False)["under18"].sum()
print("2024 tier totals (M):")
for _, r in agg2024.iterrows():
    print(f"  {r['tier']}: {r['under18']/1e6:.2f}")
print(f"  Total: {agg2024['under18'].sum()/1e6:.2f}")

# Append to existing panel
panel = pd.read_csv(DATA / "under18_city_suburb_1970_decomp.csv")
row2024 = {"year": 2024}
for _, r in agg2024.iterrows():
    row2024[r["tier"]] = r["under18"]
# Ensure all expected columns exist
for c in ["A_city_core_1950", "B_original_suburb_1970", "C_new_city_core_post1970", "D_annexed_suburb_post1970", "Z_never_msa"]:
    if c not in row2024:
        row2024[c] = 0
panel = pd.concat([panel, pd.DataFrame([row2024])], ignore_index=True)
panel = panel.sort_values("year").reset_index(drop=True)
panel.to_csv(DATA / "under18_city_suburb_1970_decomp_to2024.csv", index=False)
print(f"\nWrote {DATA / 'under18_city_suburb_1970_decomp_to2024.csv'}")
print(panel.to_string(index=False))
