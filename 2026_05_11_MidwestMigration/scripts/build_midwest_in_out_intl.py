"""
Midwest (region-wide): domestic in / domestic out / international net migration.
Three series on one chart, harmonized time axis.
"""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import duckdb
import numpy as np
import pandas as pd

MIG = "/Users/azizsunderji/Dropbox/Home Economics/Data/State_Migration/state_to_state_migration_2005_2024.parquet"
PEP = "/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates/state_pop_estimates_long.parquet"
OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

GREEN = "#67A275"
BLUE  = "#0BB4FF"
RED   = "#F4743B"
BG    = "#F6F7F3"
BLACK = "#3D3733"

MIDWEST = ["Illinois","Indiana","Iowa","Kansas","Michigan","Minnesota",
           "Missouri","Nebraska","North Dakota","Ohio","South Dakota","Wisconsin"]

con = duckdb.connect()
mw_csv = "'" + "','".join(MIDWEST) + "'"

# Domestic in/out from ACS state-to-state matrix (interregional only)
q_acs = f"""
WITH flows AS (
  SELECT year::INT AS year, origin, destination, flow
  FROM '{MIG}'
  WHERE year >= 2010
    AND (origin IN ({mw_csv}) OR destination IN ({mw_csv}))
    AND NOT (origin IN ({mw_csv}) AND destination IN ({mw_csv}))
)
SELECT year,
       SUM(CASE WHEN destination IN ({mw_csv}) THEN flow ELSE 0 END) / 1000.0 AS in_k,
       SUM(CASE WHEN origin IN ({mw_csv}) THEN flow ELSE 0 END) / 1000.0 AS out_k
FROM flows GROUP BY year ORDER BY year
"""
acs = con.execute(q_acs).fetchdf()
print("ACS in/out:")
print(acs.to_string(index=False))

# International net from PEP (use latest vintage)
q_pep = f"""
SELECT year::INT AS year, value / 1000.0 AS intl_net_k
FROM '{PEP}'
WHERE NAME = 'Midwest Region' AND measure = 'international_migration'
  AND year >= 2010 AND year <= 2025
QUALIFY ROW_NUMBER() OVER (PARTITION BY year ORDER BY vintage DESC) = 1
ORDER BY year
"""
pep = con.execute(q_pep).fetchdf()
print("\nPEP international net:")
print(pep.to_string(index=False))

# Merge — both should cover 2010-2024/25
df = pd.merge(acs, pep, on="year", how="outer").sort_values("year")
# Drop 2020 (ACS suspended)
df.loc[df["year"] == 2020, ["in_k","out_k"]] = np.nan

print("\nMerged:")
print(df.to_string(index=False))

# ── Plot ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11.5, 6.5))
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

yrs = df["year"].values
ax.plot(yrs, df["out_k"].values, color=RED, linewidth=2.4, marker="o", markersize=5, label="Domestic outflow")
ax.plot(yrs, df["in_k"].values,  color=BLUE, linewidth=2.4, marker="o", markersize=5, label="Domestic inflow")
ax.plot(yrs, df["intl_net_k"].values, color=GREEN, linewidth=2.4, marker="o", markersize=5, label="International net")

ax.axhline(0, color=BLACK, linewidth=0.8, alpha=0.5)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.tick_params(colors=BLACK, length=0, labelsize=9.5)
ax.set_xticks([2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024])
ax.grid(axis="y", color="white", linewidth=0.9, alpha=0.85)
ax.set_axisbelow(True)
ax.set_ylabel("Thousands of people per year", color=BLACK, fontsize=10)

ax.legend(loc="lower left", frameon=False, fontsize=10.5, handlelength=1.5,
          ncol=3, bbox_to_anchor=(0.0, -0.18))

fig.text(0.05, 0.96, "Midwest migration components",
         fontsize=15.5, color=BLACK, ha="left", weight="bold")
fig.text(0.05, 0.925,
         "Annual flows in thousands, 2010–2025. Domestic flows are interregional (intra-Midwest excluded). International is net.",
         fontsize=10, color=BLACK, ha="left", style="italic")
fig.text(0.05, 0.02,
         "Sources: Census Bureau ACS state-to-state migration matrix (domestic in/out); Census PEP vintage 2025 (international net). 2020 ACS suspended.",
         fontsize=8, color=BLACK, ha="left")

plt.tight_layout(rect=[0.04, 0.07, 0.97, 0.91])
fname = f"{OUT}/midwest_in_out_international"
fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"\nsaved {fname}.png/.svg")
