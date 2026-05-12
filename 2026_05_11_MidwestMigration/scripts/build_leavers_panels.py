"""
4-panel bar charts of absolute Midwest interregional out-migrants by year.
Chart 1: income tiers (4 panels). Chart 2: education tiers (4 panels — <HS+HS combined).
"""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import pandas as pd
import numpy as np

OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

BLUE   = "#0BB4FF"
YELLOW = "#FEC439"
GREEN  = "#67A275"
RED    = "#F4743B"
CREAM  = "#DADFCE"
BG     = "#F6F7F3"
BLACK  = "#3D3733"

inc = pd.read_csv(f"{OUT}/midwest_leavers_absolute_income.csv", index_col=0)
ed  = pd.read_csv(f"{OUT}/midwest_leavers_absolute_education.csv", index_col=0)

# Drop year 2020 (zeros / not surveyed)
inc = inc.replace(0, np.nan)
ed  = ed.replace(0, np.nan)

# Combine <HS + HS/GED in education
ed["HS or less"] = ed["<HS"].fillna(0) + ed["HS/GED"].fillna(0)
ed.loc[ed[["<HS","HS/GED"]].isna().all(axis=1), "HS or less"] = np.nan

INC_PANELS = [("<$50K", GREEN), ("$50–100K", BLUE), ("$100–200K", YELLOW), ("$200K+", RED)]
ED_PANELS  = [("HS or less", RED), ("Some college", YELLOW), ("Bachelor's", BLUE), ("Master's+", GREEN)]

def plot4(data, panels, title, subtitle, fname, footer):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharey=True)
    fig.patch.set_facecolor(BG)
    years = data.index.values

    for ax, (lab, col) in zip(axes.flat, panels):
        vals = data[lab].values
        ax.bar(years, vals, color=col, width=0.82, edgecolor=BG, linewidth=0.4)
        ax.set_facecolor(BG)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.tick_params(colors=BLACK, length=0, labelsize=9)
        ax.set_xticks([2005, 2010, 2015, 2020, 2024])
        ax.set_xlim(2004.4, 2024.6)
        ax.grid(axis="y", color="white", linewidth=0.9, alpha=0.8)
        ax.set_axisbelow(True)
        ax.set_title(lab, loc="left", fontsize=12, color=BLACK, pad=8, weight="bold")
        ax.set_ylabel("Thousands", fontsize=9, color=BLACK)

    fig.text(0.04, 0.965, title, fontsize=15.5, color=BLACK, ha="left", weight="bold")
    fig.text(0.04, 0.935, subtitle, fontsize=10, color=BLACK, ha="left", style="italic")
    fig.text(0.04, 0.02, footer, fontsize=8, color=BLACK, ha="left")

    plt.tight_layout(rect=[0.04, 0.05, 0.98, 0.91])
    plt.subplots_adjust(hspace=0.32, wspace=0.18)
    fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
    fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {fname}.png/.svg")

print("Income panels…")
plot4(inc, INC_PANELS,
      "People leaving the Midwest, by household income tier",
      "Annual interregional out-migrants, real 2024 $ household income brackets, thousands. 2020 not surveyed.",
      f"{OUT}/midwest_leavers_panels_income",
      "Source: IPUMS ACS 1-Year microdata, 2005–2024. Midwest interregional out-migrants (lived in a Midwest state 1 yr ago, now outside the region). Income deflated to 2024 $ via CPI-U.")

print("Education panels…")
plot4(ed, ED_PANELS,
      "Adults leaving the Midwest, by educational attainment",
      "Annual interregional out-migrants, age 25+, thousands. 2020 not surveyed.",
      f"{OUT}/midwest_leavers_panels_education",
      "Source: IPUMS ACS 1-Year microdata, 2005–2024. Midwest interregional out-migrants, adults 25+. 'HS or less' combines no diploma and HS/GED.")

print("Done.")
