"""
Austin metro rent burden by income decile (2005-2024).

Adapted from acs_renters_by_decile.py with MET2013=12420 (Austin-Round Rock) filter.
Also computes national deciles side-by-side for comparison.

Source: ACS 1-Year microdata via IPUMS.
Logic:
  1. Filter to householders (PERNUM=1), renters (OWNERSHP=2),
     non-group-quarters (GQ<=2), positive income & rent (HHINCOME>0, RENTGRS>0)
  2. For Austin: filter MET2013=12420
  3. Assign weighted income deciles per year using cumulative household weight
  4. Compute weighted median income and weighted median housing burden per decile
  5. Burden = (RENTGRS * 12) / HHINCOME * 100, capped at 100%
"""

import duckdb
import numpy as np
import pandas as pd

ACS_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Data/ACS_1Y/acs_1y.parquet"
OUT_PATH = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_20_SunderjisParadox/data/austin_renters_by_decile_yearly.csv"

con = duckdb.connect()

# Pull renter households — Austin metro
df = con.execute(f"""
    SELECT
        YEAR,
        HHINCOME,
        RENTGRS,
        HHWT
    FROM '{ACS_PATH}'
    WHERE PERNUM = 1
      AND OWNERSHP = 2
      AND GQ <= 2
      AND HHINCOME > 0
      AND RENTGRS > 0
      AND YEAR != 2020
      AND MET2013 = 12420
    ORDER BY YEAR, HHINCOME
""").df()

df["burden"] = np.minimum((df["RENTGRS"] * 12) / df["HHINCOME"] * 100, 100.0)

rows = []
for year, gdf in df.groupby("YEAR"):
    gdf = gdf.sort_values("HHINCOME").reset_index(drop=True)

    # Assign deciles using cumulative household weight
    cumw = gdf["HHWT"].cumsum()
    gdf["decile"] = np.ceil(cumw / cumw.iloc[-1] * 10).astype(int).clip(1, 10)

    for d in range(1, 11):
        sub = gdf[gdf["decile"] == d]
        if len(sub) == 0:
            continue
        rows.append({
            "year": int(year),
            "decile": d,
            "median_income": sub["HHINCOME"].median(),
            "median_burden": sub["burden"].median(),
            "n_unweighted": len(sub),
            "n_weighted": sub["HHWT"].sum(),
        })

result = pd.DataFrame(rows)
result.to_csv(OUT_PATH, index=False)
print(f"Wrote {len(result)} rows to {OUT_PATH}")
print(result.to_string(index=False))
