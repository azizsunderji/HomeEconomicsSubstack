"""Midwest net domestic vs net international migration, 2010-2025."""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import duckdb
import pandas as pd

PEP = "/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates/state_pop_estimates_long.parquet"
OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

GREEN = "#67A275"
RED   = "#F4743B"
BG    = "#F6F7F3"
BLACK = "#3D3733"

con = duckdb.connect()
q = f"""
SELECT measure, year::INT AS year, value / 1000.0 AS val_k
FROM '{PEP}'
WHERE NAME = 'Midwest Region'
  AND measure IN ('domestic_migration', 'international_migration')
  AND year >= 2010 AND year <= 2025
QUALIFY ROW_NUMBER() OVER (PARTITION BY measure, year ORDER BY vintage DESC) = 1
ORDER BY year, measure
"""
df = con.execute(q).fetchdf()
piv = df.pivot(index="year", columns="measure", values="val_k")
print(piv.round(0).to_string())

fig, ax = plt.subplots(figsize=(11.5, 6.5))
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

yrs = piv.index.values
ax.plot(yrs, piv["domestic_migration"].values, color=RED,   linewidth=2.6, marker="o", markersize=5, label="Net domestic")
ax.plot(yrs, piv["international_migration"].values, color=GREEN, linewidth=2.6, marker="o", markersize=5, label="Net international")

ax.axhline(0, color=BLACK, linewidth=0.8, alpha=0.5)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.tick_params(colors=BLACK, length=0, labelsize=9.5)
ax.set_xticks([2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024])
ax.grid(axis="y", color="white", linewidth=0.9, alpha=0.85)
ax.set_axisbelow(True)
ax.set_ylabel("Thousands of people per year", color=BLACK, fontsize=10)
ax.legend(loc="upper left", frameon=False, fontsize=11, handlelength=1.5,
          ncol=2, bbox_to_anchor=(0.0, -0.10))

fig.text(0.05, 0.96, "Midwest: net domestic vs net international migration",
         fontsize=15.5, color=BLACK, ha="left", weight="bold")
fig.text(0.05, 0.925,
         "Annual net flows, thousands of people, 2010–2025.",
         fontsize=10, color=BLACK, ha="left", style="italic")
fig.text(0.05, 0.02,
         "Source: Census Population Estimates Program, vintage 2025. Midwest = 12 states (IL, IN, IA, KS, MI, MN, MO, NE, ND, OH, SD, WI).",
         fontsize=8, color=BLACK, ha="left")

plt.tight_layout(rect=[0.04, 0.07, 0.97, 0.91])
fname = f"{OUT}/midwest_domestic_vs_international_net"
fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"\nsaved {fname}.png")
