"""
12-state panel time-series of Midwest interregional inflow/outflow, 2010-2024.
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
OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

GREEN = "#67A275"
BLUE  = "#0BB4FF"
RED   = "#F4743B"
BG    = "#F6F7F3"
BLACK = "#3D3733"

MIDWEST = ["Illinois","Indiana","Iowa","Kansas","Michigan","Minnesota",
           "Missouri","Nebraska","North Dakota","Ohio","South Dakota","Wisconsin"]
# Same panel order as the other charts
PANEL_ORDER = ["Missouri","Ohio","Kansas","Michigan","Illinois","Indiana",
               "Wisconsin","North Dakota","Iowa","Minnesota","South Dakota","Nebraska"]

con = duckdb.connect()
mw_csv = "'" + "','".join(MIDWEST) + "'"

q = f"""
WITH flows AS (
  SELECT year::INT AS year, origin, destination, flow
  FROM '{MIG}'
  WHERE (origin IN ({mw_csv}) OR destination IN ({mw_csv}))
    AND NOT (origin IN ({mw_csv}) AND destination IN ({mw_csv}))
),
outflow AS (
  SELECT year, origin AS state, SUM(flow) / 1000.0 AS out_k
  FROM flows WHERE origin IN ({mw_csv})
  GROUP BY year, origin
),
inflow AS (
  SELECT year, destination AS state, SUM(flow) / 1000.0 AS in_k
  FROM flows WHERE destination IN ({mw_csv})
  GROUP BY year, destination
)
SELECT COALESCE(o.state, i.state) AS state, COALESCE(o.year, i.year) AS year,
       o.out_k, i.in_k
FROM outflow o
FULL OUTER JOIN inflow i ON o.state = i.state AND o.year = i.year
ORDER BY state, year
"""
df = con.execute(q).fetchdf()
df["state"] = df["state"].fillna("").astype(str)
df["year"]  = df["year"].astype(int)
df = df[(df["year"] >= 2010) & (df["year"] <= 2024)]

# Determine common y-axis range
all_vals = pd.concat([df["in_k"], df["out_k"]]).dropna()
ymax = float(all_vals.max()) * 1.08

fig, axes = plt.subplots(4, 3, figsize=(13, 11), sharex=True, sharey=True)
fig.patch.set_facecolor(BG)

for ax, st in zip(axes.flat, PANEL_ORDER):
    sub = df[df["state"] == st].sort_values("year")
    yrs = sub["year"].values
    o   = sub["out_k"].values
    i   = sub["in_k"].values
    # Insert NaN for missing 2020 (ACS suspended)
    all_yrs = list(range(2010, 2025))
    yvals_o = []
    yvals_i = []
    for y in all_yrs:
        if y == 2020:
            yvals_o.append(np.nan); yvals_i.append(np.nan)
        else:
            mask = sub["year"] == y
            yvals_o.append(sub.loc[mask,"out_k"].values[0] if mask.any() else np.nan)
            yvals_i.append(sub.loc[mask,"in_k"].values[0]  if mask.any() else np.nan)
    yvals_o = np.array(yvals_o)
    yvals_i = np.array(yvals_i)
    yrs_arr = np.array(all_yrs)

    ax.plot(yrs_arr, yvals_o, color=RED,  linewidth=2.0, marker="o", markersize=3.6, label="Out")
    ax.plot(yrs_arr, yvals_i, color=BLUE, linewidth=2.0, marker="o", markersize=3.6, label="In")
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=BLACK, length=0, labelsize=8.5)
    ax.set_xticks([2010, 2015, 2020, 2024])
    ax.set_xlim(2009.5, 2024.5)
    ax.set_ylim(0, ymax)
    ax.grid(axis="y", color="white", linewidth=0.9, alpha=0.85)
    ax.set_axisbelow(True)
    ax.set_title(st, loc="left", fontsize=11, color=BLACK, pad=4, weight="bold")

# Legend
handles, labels = axes[0,0].get_legend_handles_labels()
fig.legend(handles, ["Outflow", "Inflow"], loc="upper right",
           bbox_to_anchor=(0.96, 0.965), frameon=False, fontsize=10,
           handlelength=1.6, ncol=2, columnspacing=2)

fig.text(0.04, 0.965, "Midwest interregional flows by state — inflow vs outflow",
         fontsize=15.5, color=BLACK, ha="left", weight="bold")
fig.text(0.04, 0.935, "Annual flows in thousands of people, 2010–2024. 2020 not surveyed.",
         fontsize=10, color=BLACK, ha="left", style="italic")
fig.text(0.04, 0.015,
         "Source: Census Bureau ACS state-to-state migration matrix; intra-Midwest moves excluded.",
         fontsize=8, color=BLACK, ha="left")

plt.tight_layout(rect=[0.04, 0.04, 0.97, 0.91])
plt.subplots_adjust(hspace=0.35, wspace=0.13)
fname = f"{OUT}/midwest_state_inflow_outflow_panels"
fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
plt.close(fig)
print(f"saved {fname}.png")
