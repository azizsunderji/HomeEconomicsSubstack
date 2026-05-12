"""Total population by region, 2010–2025."""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import duckdb

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
SELECT NAME, year::INT AS year, value / 1e6 AS pop_m
FROM '{PEP}'
WHERE NAME IN ('{names}') AND measure = 'population'
  AND year >= 2010 AND year <= 2025
QUALIFY ROW_NUMBER() OVER (PARTITION BY NAME, year ORDER BY vintage DESC) = 1
ORDER BY NAME, year
"""
df = con.execute(q).fetchdf()
piv = df.pivot(index="year", columns="NAME", values="pop_m")
print(piv.round(1).to_string())

fig, ax = plt.subplots(figsize=(11.5, 6.5))
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

for name, (label, color) in REGIONS.items():
    s = piv[name].dropna()
    ax.plot(s.index, s.values, color=color, linewidth=2.6, marker="o",
            markersize=5, label=label)
    # Right-edge label
    y_last = s.iloc[-1]
    x_last = s.index[-1]
    ax.text(x_last + 0.2, y_last, f"{label} {y_last:.1f}M",
            color=color, fontsize=10, va="center", weight="bold")

for sp in ax.spines.values():
    sp.set_visible(False)
ax.tick_params(colors=BLACK, length=0, labelsize=9.5)
ax.set_xticks([2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024])
ax.set_xlim(2009.7, 2027.5)
ax.grid(axis="y", color="white", linewidth=0.9, alpha=0.85)
ax.set_axisbelow(True)
ax.set_ylabel("Population, millions", color=BLACK, fontsize=10)

fig.text(0.05, 0.96, "Total population by region",
         fontsize=15.5, color=BLACK, ha="left", weight="bold")
fig.text(0.05, 0.925,
         "Region population, millions, 2010–2025.",
         fontsize=10, color=BLACK, ha="left", style="italic")
fig.text(0.05, 0.02,
         "Source: Census Population Estimates Program, vintage 2025.",
         fontsize=8, color=BLACK, ha="left")

plt.tight_layout(rect=[0.04, 0.05, 0.94, 0.91])
fname = f"{OUT}/regional_population"
fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
plt.close(fig)
print(f"\nsaved {fname}.png")
