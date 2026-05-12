"""
4-panel regional comparison: births vs deaths per region, 2011-2025.
Harmonized y-axis.
"""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import duckdb
import pandas as pd
import numpy as np

PEP = "/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates/state_pop_estimates_long.parquet"
OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

BLUE   = "#0BB4FF"
YELLOW = "#FEC439"
GREEN  = "#67A275"
RED    = "#F4743B"
CREAM  = "#DADFCE"
BG     = "#F6F7F3"
BLACK  = "#3D3733"

REGIONS = ["Northeast Region", "Midwest Region", "South Region", "West Region"]
REGION_TITLES = {"Northeast Region": "Northeast", "Midwest Region": "Midwest",
                 "South Region": "South", "West Region": "West"}

con = duckdb.connect()
q = f"""
SELECT NAME, year::INT AS year, measure, value, vintage
FROM '{PEP}'
WHERE NAME IN ('Northeast Region', 'Midwest Region', 'South Region', 'West Region')
  AND measure IN ('births', 'deaths', 'natural_change', 'population')
"""
df = con.execute(q).fetchdf()

# Take the LATEST vintage per (NAME, year, measure)
df = df.sort_values(["NAME", "year", "measure", "vintage"]).drop_duplicates(
    subset=["NAME", "year", "measure"], keep="last")

# Pivot
piv = df.pivot_table(index=["NAME", "year"], columns="measure", values="value").reset_index()
piv = piv[(piv["year"] >= 2011) & (piv["year"] <= 2025) & (piv["year"] != 2020)]

# Convert to thousands
for c in ["births", "deaths", "natural_change", "population"]:
    if c in piv.columns:
        piv[c] = piv[c] / 1000.0

print("Regional natural-change snapshot:")
for r in REGIONS:
    sub = piv[piv["NAME"] == r].sort_values("year")
    print(f"\n{REGION_TITLES[r]}:")
    print(sub[["year","births","deaths","natural_change"]].round(1).to_string(index=False))

# Plot
fig, axes = plt.subplots(2, 2, figsize=(13, 8.5), sharey=True, sharex=True)
fig.patch.set_facecolor(BG)

# Determine y range
all_vals = pd.concat([piv["births"], piv["deaths"]]).dropna()
ymax = all_vals.max() * 1.08
ymin = 0

for ax, r in zip(axes.flat, REGIONS):
    sub = piv[piv["NAME"] == r].sort_values("year")
    yrs = sub["year"].values
    b = sub["births"].values
    d = sub["deaths"].values

    ax.fill_between(yrs, d, b, where=b > d, color=GREEN, alpha=0.18, linewidth=0,
                    label="natural increase" if r == "Northeast Region" else None)
    ax.fill_between(yrs, b, d, where=d > b, color=RED, alpha=0.18, linewidth=0,
                    label="natural decrease" if r == "Northeast Region" else None)
    ax.plot(yrs, b, color=GREEN, linewidth=2.2, marker="o", markersize=4, label="births")
    ax.plot(yrs, d, color=RED,   linewidth=2.2, marker="o", markersize=4, label="deaths")

    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=BLACK, length=0, labelsize=9)
    ax.set_xticks([2011, 2014, 2017, 2020, 2023, 2025])
    ax.set_xlim(2010.7, 2025.3)
    ax.set_ylim(ymin, ymax)
    ax.grid(axis="y", color="white", linewidth=0.9, alpha=0.8)
    ax.set_axisbelow(True)
    ax.set_title(REGION_TITLES[r], loc="left", fontsize=13, color=BLACK, pad=8, weight="bold")
    ax.set_ylabel("Thousands per year", fontsize=9, color=BLACK)
    # Annotate last natural change
    last = sub.iloc[-1]
    nc = last["births"] - last["deaths"]
    ax.text(0.99, 0.05,
            f"{int(last['year'])} natural change: {nc:+.0f}K",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=10, color=BLACK,
            bbox=dict(facecolor=BG, edgecolor="none", pad=2))

# Legend (use first panel's handles)
handles, labels = axes[0,0].get_legend_handles_labels()
fig.legend(handles, labels, loc="upper right", frameon=False, fontsize=10,
           bbox_to_anchor=(0.97, 0.95), ncol=4, handlelength=1.5)

fig.text(0.04, 0.965, "Births vs deaths by region",
         fontsize=16, color=BLACK, ha="left", weight="bold")
fig.text(0.04, 0.93,
         "Annual births and deaths in thousands, 2011–2025. Shaded area = natural change (green = increase, red = decrease).",
         fontsize=10, color=BLACK, ha="left", style="italic")
fig.text(0.04, 0.02,
         "Source: Census Population Estimates Program, vintage 2025. Region totals (50 states + DC, by Census region).",
         fontsize=8, color=BLACK, ha="left")

plt.tight_layout(rect=[0.03, 0.05, 0.98, 0.89])
plt.subplots_adjust(hspace=0.30, wspace=0.10)

fname = f"{OUT}/regional_births_deaths"
fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
plt.close(fig)
print(f"\nsaved {fname}.png/.svg")

# Print bookend table
print("\n=== Natural change (births - deaths), thousands ===")
print(f"{'Region':12s} {'2011':>8s} {'2018':>8s} {'2021':>8s} {'2025':>8s}  {'Δ 2011→2025':>13s}")
for r in REGIONS:
    sub = piv[piv["NAME"] == r].set_index("year")
    nm = REGION_TITLES[r]
    def get_nc(y):
        if y in sub.index: return sub.loc[y, "births"] - sub.loc[y, "deaths"]
        return np.nan
    nc11, nc18, nc21, nc25 = get_nc(2011), get_nc(2018), get_nc(2021), get_nc(2025)
    print(f"{nm:12s} {nc11:>8.0f} {nc18:>8.0f} {nc21:>8.0f} {nc25:>8.0f}  {nc25-nc11:>+13.0f}")

print("\n=== Births vs deaths bookends ===")
print(f"{'Region':12s} {'B2011':>7s} {'B2025':>7s} {'ΔB':>7s} | {'D2011':>7s} {'D2025':>7s} {'ΔD':>7s}")
for r in REGIONS:
    sub = piv[piv["NAME"] == r].set_index("year")
    nm = REGION_TITLES[r]
    if 2011 in sub.index and 2025 in sub.index:
        b11, b25 = sub.loc[2011, "births"], sub.loc[2025, "births"]
        d11, d25 = sub.loc[2011, "deaths"], sub.loc[2025, "deaths"]
        print(f"{nm:12s} {b11:>7.0f} {b25:>7.0f} {b25-b11:>+7.0f} | {d11:>7.0f} {d25:>7.0f} {d25-d11:>+7.0f}")
