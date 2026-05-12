"""
State-by-state decomposition of Midwest net migration change, 2021 → 2024.
Green = fewer leaving (Δ_outflow < 0)
Blue  = more arriving (Δ_inflow > 0)
Black tick = net change.
"""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import duckdb
import pandas as pd

MIG = "/Users/azizsunderji/Dropbox/Home Economics/Data/State_Migration/state_to_state_migration_2005_2024.parquet"
OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

GREEN = "#67A275"
BLUE  = "#0BB4FF"
BG    = "#F6F7F3"
BLACK = "#3D3733"

MIDWEST = ["Illinois","Indiana","Iowa","Kansas","Michigan","Minnesota",
           "Missouri","Nebraska","North Dakota","Ohio","South Dakota","Wisconsin"]

con = duckdb.connect()

# Inflow / outflow per state per year — interregional only (other side outside Midwest)
mw_csv = "'" + "','".join(MIDWEST) + "'"
q = f"""
WITH flows AS (
  SELECT year::INT AS year, origin, destination, flow
  FROM '{MIG}'
  WHERE year IN (2021, 2024)
    AND (origin IN ({mw_csv}) OR destination IN ({mw_csv}))
    AND NOT (origin IN ({mw_csv}) AND destination IN ({mw_csv}))
),
outflow AS (
  SELECT year, origin AS state, SUM(flow) AS out_flow
  FROM flows
  WHERE origin IN ({mw_csv})
  GROUP BY year, origin
),
inflow AS (
  SELECT year, destination AS state, SUM(flow) AS in_flow
  FROM flows
  WHERE destination IN ({mw_csv})
  GROUP BY year, destination
)
SELECT COALESCE(o.state, i.state) AS state, o.year AS year,
       o.out_flow, i.in_flow
FROM outflow o
FULL OUTER JOIN inflow i ON o.state = i.state AND o.year = i.year
"""
df = con.execute(q).fetchdf()
print("Raw flows:")
print(df.sort_values(["state","year"]).to_string(index=False))

# Pivot to wide format
piv = df.pivot_table(index="state", columns="year", values=["out_flow","in_flow"])
piv.columns = [f"{m}_{y}" for m, y in piv.columns]

# Convert to thousands, compute deltas
piv = piv / 1000.0
piv["d_inflow"]  = piv["in_flow_2024"]  - piv["in_flow_2021"]
piv["d_outflow"] = piv["out_flow_2024"] - piv["out_flow_2021"]
# Net improvement = (decline in outflow) + (increase in inflow)
# = -d_outflow + d_inflow
piv["green"] = -piv["d_outflow"]  # fewer leaving (positive if outflow shrank)
piv["blue"]  = piv["d_inflow"]    # more arriving (positive if inflow grew)
piv["net"]   = piv["green"] + piv["blue"]

piv = piv.sort_values("net", ascending=False)
print("\nDecomposition (thousands per year, 2021 → 2024):")
print(piv[["green","blue","net"]].round(2).to_string())

# ── PLOT ──────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 7.5))
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

states = piv.index.tolist()
y = list(range(len(states)))[::-1]  # top state at top

for i, st in zip(y, states):
    g = piv.loc[st, "green"]
    b = piv.loc[st, "blue"]
    n = piv.loc[st, "net"]
    # When both same sign: stack from 0 so they don't overlap.
    # When opposite signs: each from 0 on its respective side of zero.
    if (g >= 0 and b >= 0) or (g <= 0 and b <= 0):
        ax.barh(i, g, color=GREEN, height=0.72, edgecolor=BG, linewidth=0.5)
        ax.barh(i, b, left=g, color=BLUE,  height=0.72, edgecolor=BG, linewidth=0.5)
    else:
        ax.barh(i, g, color=GREEN, height=0.72, edgecolor=BG, linewidth=0.5)
        ax.barh(i, b, color=BLUE,  height=0.72, edgecolor=BG, linewidth=0.5)
    # Net tick
    ax.plot([n, n], [i - 0.36, i + 0.36], color=BLACK, linewidth=2.4, solid_capstyle="butt")
    # Net label — outside the rightmost extent
    right_extent = max(g, b, n, 0)
    left_extent  = min(g, b, n, 0)
    label = f"{'+' if n >= 0 else ''}{n:.1f}K"
    if n >= 0:
        ax.text(right_extent + 0.6, i, label, va="center", ha="left",
                fontsize=10.5, color=BLACK, weight="bold")
    else:
        ax.text(left_extent - 0.6, i, label, va="center", ha="right",
                fontsize=10.5, color=BLACK, weight="bold")

ax.set_yticks(y)
ax.set_yticklabels(states, fontsize=11, color=BLACK)
for sp in ax.spines.values():
    sp.set_visible(False)
ax.axvline(0, color=BLACK, linewidth=1.0)
ax.tick_params(colors=BLACK, length=0, labelsize=10)
ax.grid(axis="x", color="white", linewidth=0.9, alpha=0.8)
ax.set_axisbelow(True)

# X label format
def k_fmt(x, _):
    sign = "+" if x > 0 else ""
    return f"{sign}{x:.0f}K"
from matplotlib.ticker import FuncFormatter
ax.xaxis.set_major_formatter(FuncFormatter(k_fmt))

# Title + subtitle (no axes obstructing)
ax.set_title("")
fig.text(0.05, 0.96, "Where the Midwest's improvement comes from — by state",
         fontsize=15.5, color=BLACK, ha="left", weight="bold")
fig.text(0.05, 0.925,
         "Single-year change in net migration, 2021 → 2024, thousands per year.",
         fontsize=10.5, color=BLACK, ha="left", style="italic")

# Legend
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
legend = [
    Patch(facecolor=GREEN, edgecolor=BG, label="Fewer leaving"),
    Patch(facecolor=BLUE,  edgecolor=BG, label="More arriving"),
    Line2D([0],[0], color=BLACK, linewidth=2.4, label="Net change"),
]
ax.legend(handles=legend, loc="lower left", bbox_to_anchor=(-0.02, -0.18),
          ncol=3, frameon=False, fontsize=10, handlelength=1.4, columnspacing=2)

fig.text(0.05, 0.02,
         "Source: Census Bureau ACS state-to-state migration matrix; intra-Midwest moves excluded.",
         fontsize=8, color=BLACK, ha="left")

plt.tight_layout(rect=[0.05, 0.06, 0.98, 0.90])
fname = f"{OUT}/midwest_state_decomposition_2021v2024"
fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
plt.close(fig)
print(f"\nsaved {fname}.svg/.png")
