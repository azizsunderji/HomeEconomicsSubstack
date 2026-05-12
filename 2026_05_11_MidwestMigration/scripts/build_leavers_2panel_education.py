"""2-panel education chart: no degree vs degree."""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import pandas as pd
import numpy as np

OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"
BLUE, YELLOW, GREEN, RED, BG, BLACK = "#0BB4FF", "#FEC439", "#67A275", "#F4743B", "#F6F7F3", "#3D3733"

ed = pd.read_csv(f"{OUT}/midwest_leavers_absolute_education.csv", index_col=0).replace(0, np.nan)
ed["No degree"] = ed[["<HS","HS/GED","Some college"]].sum(axis=1, min_count=1)
ed["Bachelor's or more"] = ed[["Bachelor's","Master's+"]].sum(axis=1, min_count=1)

PANELS = [("No degree", RED), ("Bachelor's or more", GREEN)]

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
fig.patch.set_facecolor(BG)
years = ed.index.values

for ax, (lab, col) in zip(axes, PANELS):
    vals = ed[lab].values
    ax.bar(years, vals, color=col, width=0.82, edgecolor=BG, linewidth=0.4)
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=BLACK, length=0, labelsize=9)
    ax.set_xticks([2005, 2010, 2015, 2020, 2024])
    ax.set_xlim(2004.4, 2024.6)
    ax.grid(axis="y", color="white", linewidth=0.9, alpha=0.8)
    ax.set_axisbelow(True)
    ax.set_title(lab, loc="left", fontsize=13, color=BLACK, pad=8, weight="bold")
    ax.set_ylabel("Thousands", fontsize=9, color=BLACK)

fig.text(0.04, 0.965, "Adults leaving the Midwest, by degree status",
         fontsize=16, color=BLACK, ha="left", weight="bold")
fig.text(0.04, 0.93, "Annual interregional out-migrants, age 25+, thousands. 2020 not surveyed.",
         fontsize=10, color=BLACK, ha="left", style="italic")
fig.text(0.04, 0.02,
         "Source: IPUMS ACS 1-Year microdata, 2005–2024. 'No degree' = <HS + HS/GED + Some college/AA. 'Bachelor's or more' = bachelor's + master's/professional/PhD.",
         fontsize=8, color=BLACK, ha="left")

plt.tight_layout(rect=[0.04, 0.05, 0.98, 0.89])
plt.subplots_adjust(wspace=0.12)
fname = f"{OUT}/midwest_leavers_2panel_education"
fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
plt.close(fig)

# Quick stats
print("No degree:    2005 {:.0f}K → 2024 {:.0f}K  Δ {:+.0f}K".format(ed.loc[2005,"No degree"], ed.loc[2024,"No degree"], ed.loc[2024,"No degree"]-ed.loc[2005,"No degree"]))
print("BA or more:   2005 {:.0f}K → 2024 {:.0f}K  Δ {:+.0f}K".format(ed.loc[2005,"Bachelor's or more"], ed.loc[2024,"Bachelor's or more"], ed.loc[2024,"Bachelor's or more"]-ed.loc[2005,"Bachelor's or more"]))
print(f"saved {fname}.png/.svg")
