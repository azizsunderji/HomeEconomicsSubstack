"""International net migration by region, 2010–2025."""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import duckdb
import pandas as pd

PEP = "/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates/state_pop_estimates_long.parquet"
OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

BLUE   = "#0BB4FF"
YELLOW = "#FEC439"
GREEN  = "#67A275"
RED    = "#F4743B"
BG     = "#F6F7F3"
BLACK  = "#3D3733"

REGIONS = {
    "Northeast Region": ("Northeast", BLUE),
    "Midwest Region":   ("Midwest",   GREEN),
    "South Region":     ("South",     RED),
    "West Region":      ("West",      YELLOW),
}

con = duckdb.connect()
names = "','".join(REGIONS.keys())
q = f"""
SELECT NAME, year::INT AS year, value / 1000.0 AS intl_k
FROM '{PEP}'
WHERE NAME IN ('{names}') AND measure = 'international_migration'
  AND year >= 2010 AND year <= 2025
QUALIFY ROW_NUMBER() OVER (PARTITION BY NAME, year ORDER BY vintage DESC) = 1
ORDER BY NAME, year
"""
df = con.execute(q).fetchdf()
piv = df.pivot(index="year", columns="NAME", values="intl_k")
print(piv.round(0).to_string())

fig, ax = plt.subplots(figsize=(11.5, 6.5))
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

for name, (label, color) in REGIONS.items():
    s = piv[name].dropna()
    ax.plot(s.index, s.values, color=color, linewidth=2.6, marker="o",
            markersize=5, label=label)

ax.axhline(0, color=BLACK, linewidth=0.8, alpha=0.5)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.tick_params(colors=BLACK, length=0, labelsize=9.5)
ax.set_xticks([2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024])
ax.grid(axis="y", color="white", linewidth=0.9, alpha=0.85)
ax.set_axisbelow(True)
ax.set_ylabel("Thousands of people per year", color=BLACK, fontsize=10)
ax.legend(loc="upper left", frameon=False, fontsize=11, handlelength=1.5, ncol=4,
          bbox_to_anchor=(0.0, -0.10))

fig.text(0.05, 0.96, "International net migration by region",
         fontsize=15.5, color=BLACK, ha="left", weight="bold")
fig.text(0.05, 0.925,
         "Annual net migration from abroad, thousands of people, 2010–2025.",
         fontsize=10, color=BLACK, ha="left", style="italic")
fig.text(0.05, 0.02,
         "Source: Census Population Estimates Program, vintage 2025.",
         fontsize=8, color=BLACK, ha="left")

plt.tight_layout(rect=[0.04, 0.07, 0.97, 0.91])
fname = f"{OUT}/regional_international_migration"
fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"\nsaved {fname}.png")
