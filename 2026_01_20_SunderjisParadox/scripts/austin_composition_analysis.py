"""
Austin renter composition & mobility analysis (2005-2024).

Tracks how the Austin renter population changed over the supply boom period:
  1. Income distribution (25th, 50th, 75th percentiles)
  2. Total renter population (weighted)
  3. Mobility rates (MIGRATE1): non-movers vs within-county vs within-state vs interstate
  4. Unit size distribution (BEDROOMS)
  5. Income of movers vs non-movers

Source: ACS 1-Year microdata via IPUMS, MET2013=12420 (Austin-Round Rock).
"""

import duckdb
import numpy as np
import pandas as pd

ACS_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Data/ACS_1Y/acs_1y.parquet"
BASE_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_20_SunderjisParadox/data"

con = duckdb.connect()

# Pull all Austin renter householders
df = con.execute(f"""
    SELECT
        YEAR,
        HHINCOME,
        RENTGRS,
        HHWT,
        MIGRATE1,
        BEDROOMS,
        AGE
    FROM '{ACS_PATH}'
    WHERE PERNUM = 1
      AND OWNERSHP = 2
      AND GQ <= 2
      AND HHINCOME > 0
      AND RENTGRS > 0
      AND YEAR != 2020
      AND MET2013 = 12420
    ORDER BY YEAR
""").df()

df["burden"] = np.minimum((df["RENTGRS"] * 12) / df["HHINCOME"] * 100, 100.0)
df["annual_rent"] = df["RENTGRS"] * 12

# ======= 1. Income distribution by year =======
print("=" * 60)
print("1. INCOME DISTRIBUTION OF AUSTIN RENTERS BY YEAR")
print("=" * 60)
income_rows = []
for year, gdf in df.groupby("YEAR"):
    inc = gdf["HHINCOME"]
    wt = gdf["HHWT"]
    # Weighted percentiles
    sorted_idx = inc.argsort()
    sorted_inc = inc.iloc[sorted_idx].values
    sorted_wt = wt.iloc[sorted_idx].values
    cumwt = np.cumsum(sorted_wt)
    total_wt = cumwt[-1]

    p25 = sorted_inc[np.searchsorted(cumwt, total_wt * 0.25)]
    p50 = sorted_inc[np.searchsorted(cumwt, total_wt * 0.50)]
    p75 = sorted_inc[np.searchsorted(cumwt, total_wt * 0.75)]

    income_rows.append({
        "year": int(year),
        "total_renters_weighted": int(wt.sum()),
        "n_unweighted": len(gdf),
        "income_p25": int(p25),
        "income_p50": int(p50),
        "income_p75": int(p75),
        "median_rent_monthly": int(gdf["RENTGRS"].median()),
        "median_burden": round(gdf["burden"].median(), 1),
    })

income_df = pd.DataFrame(income_rows)
income_df.to_csv(f"{BASE_DIR}/austin_income_distribution.csv", index=False)
print(income_df.to_string(index=False))

# ======= 2. Mobility rates by year =======
print("\n" + "=" * 60)
print("2. MOBILITY RATES (MIGRATE1) BY YEAR")
print("=" * 60)
print("MIGRATE1: 1=same house, 2=moved within county, 3=diff county same state, 4=diff state")
mobility_rows = []
for year, gdf in df.groupby("YEAR"):
    total_wt = gdf["HHWT"].sum()
    for mig_code in [1, 2, 3, 4]:
        sub = gdf[gdf["MIGRATE1"] == mig_code]
        pct = sub["HHWT"].sum() / total_wt * 100 if total_wt > 0 else 0
        mobility_rows.append({
            "year": int(year),
            "migrate1": mig_code,
            "n_weighted": int(sub["HHWT"].sum()),
            "pct_of_total": round(pct, 1),
        })

mobility_df = pd.DataFrame(mobility_rows)
mobility_df.to_csv(f"{BASE_DIR}/austin_mobility_rates.csv", index=False)

# Pivot for readability
mob_pivot = mobility_df.pivot(index="year", columns="migrate1", values="pct_of_total")
mob_pivot.columns = ["same_house_%", "within_county_%", "diff_county_%", "diff_state_%"]
mob_pivot["total_movers_%"] = mob_pivot["within_county_%"] + mob_pivot["diff_county_%"] + mob_pivot["diff_state_%"]
print(mob_pivot.to_string())

# ======= 3. Unit size distribution by year =======
print("\n" + "=" * 60)
print("3. UNIT SIZE (BEDROOMS) DISTRIBUTION BY YEAR")
print("=" * 60)
br_rows = []
for year, gdf in df.groupby("YEAR"):
    total_wt = gdf["HHWT"].sum()
    for br in sorted(gdf["BEDROOMS"].unique()):
        sub = gdf[gdf["BEDROOMS"] == br]
        pct = sub["HHWT"].sum() / total_wt * 100
        br_rows.append({
            "year": int(year),
            "bedrooms": int(br),
            "pct_of_total": round(pct, 1),
        })

br_df = pd.DataFrame(br_rows)
br_df.to_csv(f"{BASE_DIR}/austin_bedroom_distribution.csv", index=False)

# Pivot for readability
br_pivot = br_df.pivot(index="year", columns="bedrooms", values="pct_of_total").fillna(0)
br_pivot.columns = [f"{int(c)}BR_%" for c in br_pivot.columns]
print(br_pivot.to_string())

# ======= 4. Income of movers vs non-movers =======
print("\n" + "=" * 60)
print("4. MEDIAN INCOME & BURDEN: MOVERS vs NON-MOVERS BY YEAR")
print("=" * 60)
mover_rows = []
for year, gdf in df.groupby("YEAR"):
    non_movers = gdf[gdf["MIGRATE1"] == 1]
    movers = gdf[gdf["MIGRATE1"] > 1]
    interstate = gdf[gdf["MIGRATE1"] == 4]

    mover_rows.append({
        "year": int(year),
        "non_mover_median_income": int(non_movers["HHINCOME"].median()),
        "non_mover_median_burden": round(non_movers["burden"].median(), 1),
        "mover_median_income": int(movers["HHINCOME"].median()) if len(movers) > 0 else None,
        "mover_median_burden": round(movers["burden"].median(), 1) if len(movers) > 0 else None,
        "interstate_median_income": int(interstate["HHINCOME"].median()) if len(interstate) > 10 else None,
        "interstate_n": len(interstate),
    })

mover_df = pd.DataFrame(mover_rows)
mover_df.to_csv(f"{BASE_DIR}/austin_movers_vs_nonmovers.csv", index=False)
print(mover_df.to_string(index=False))

# ======= 5. Median rent (monthly) by year =======
print("\n" + "=" * 60)
print("5. MEDIAN MONTHLY RENT BY YEAR (Austin renters)")
print("=" * 60)
for year, gdf in df.groupby("YEAR"):
    med_rent = gdf["RENTGRS"].median()
    mean_rent = (gdf["RENTGRS"] * gdf["HHWT"]).sum() / gdf["HHWT"].sum()
    print(f"  {int(year)}: median=${int(med_rent)}, weighted_mean=${int(mean_rent)}")

# ======= 6. Age distribution of renters =======
print("\n" + "=" * 60)
print("6. MEDIAN AGE OF RENTER HOUSEHOLDERS BY YEAR")
print("=" * 60)
for year, gdf in df.groupby("YEAR"):
    med_age = gdf["AGE"].median()
    print(f"  {int(year)}: median_age={med_age:.0f}")

print("\nDone! All CSVs saved to data/")
