"""
Stacked-bar charts: absolute counts of Midwest inter-regional out-migrants by year,
broken down by (1) real-2024-dollar HH income tier, (2) education tier.
"""
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import duckdb
import numpy as np
import pandas as pd

ACS = "/Users/azizsunderji/Dropbox/Home Economics/Data/ACS_1Y/acs_1y.parquet"
OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

CPI = {
    2005: 195.292, 2006: 201.591, 2007: 207.342, 2008: 215.303, 2009: 214.537,
    2010: 218.056, 2011: 224.939, 2012: 229.594, 2013: 232.957, 2014: 236.736,
    2015: 237.017, 2016: 240.007, 2017: 245.120, 2018: 251.107, 2019: 255.657,
    2020: 258.811, 2021: 270.970, 2022: 292.655, 2023: 304.702, 2024: 313.689,
}
BASE = CPI[2024]
MIDWEST = (17,18,19,20,26,27,29,31,38,39,46,55)

BLUE   = "#0BB4FF"
YELLOW = "#FEC439"
GREEN  = "#67A275"
RED    = "#F4743B"
CREAM  = "#DADFCE"
BG     = "#F6F7F3"
BLACK  = "#3D3733"

con = duckdb.connect()
mw_csv = ",".join(map(str, MIDWEST))

q = f"""
SELECT YEAR::INT AS year, PERWT, HHINCOME, EDUCD, AGE
FROM '{ACS}'
WHERE MIGRATE1 = 3
  AND MIGPLAC1 IN ({mw_csv})
  AND STATEFIP NOT IN ({mw_csv})
  AND YEAR BETWEEN 2005 AND 2024
"""
df = con.execute(q).fetchdf()
print(f"Pulled {len(df):,} Midwest inter-regional out-migrant records.")

# ----- Income: deflate -----
df["cpi"] = df["year"].map(CPI)
df["real_hhinc"] = df["HHINCOME"] * (BASE / df["cpi"])
df.loc[(df["HHINCOME"] >= 9_000_000) | (df["HHINCOME"] <= 0), "real_hhinc"] = np.nan

inc_bins = [-np.inf, 50_000, 100_000, 200_000, np.inf]
inc_labels = ["<$50K", "$50–100K", "$100–200K", "$200K+"]
inc_colors = [GREEN, BLUE, YELLOW, RED]
df["inc_bin"] = pd.cut(df["real_hhinc"], bins=inc_bins, labels=inc_labels)

# ----- Education tier (adults 25+) -----
ed_labels = ["<HS", "HS/GED", "Some college", "Bachelor's", "Master's+"]
ed_colors = [RED, YELLOW, CREAM, BLUE, GREEN]
def ed_bin(row):
    if row["AGE"] < 25: return None
    e = row["EDUCD"]
    if e < 62: return "<HS"
    if e < 65: return "HS/GED"
    if e < 101: return "Some college"
    if e < 114: return "Bachelor's"
    return "Master's+"
df["ed_bin"] = df.apply(ed_bin, axis=1)

# ----- Aggregate weighted counts by year × bin -----
def agg(col):
    sub = df[df[col].notna()].copy()
    g = sub.groupby(["year", col], observed=True)["PERWT"].sum().unstack(fill_value=0)
    return g  # rows year, cols bin

inc_df = agg("inc_bin").reindex(columns=inc_labels, fill_value=0)
ed_df  = agg("ed_bin").reindex(columns=ed_labels, fill_value=0)

# Convert to thousands
inc_df_k = inc_df / 1000.0
ed_df_k  = ed_df / 1000.0

print("\nIncome totals (thousands of people, last 6 years):")
print(inc_df_k.tail(6).round(1).to_string())
print("\nEducation totals (thousands of adults 25+, last 6 years):")
print(ed_df_k.tail(6).round(1).to_string())

# Note: 2020 is missing (no ACS 1Y). Insert NaN row so the bar gap is visible.
all_years = list(range(2005, 2025))
inc_df_k = inc_df_k.reindex(all_years, fill_value=0)
ed_df_k  = ed_df_k.reindex(all_years, fill_value=0)

# ----- Plot -----
def plot_stack(data_k, labels, colors, title, subtitle, fname):
    fig, ax = plt.subplots(figsize=(11.5, 6.5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    years = data_k.index.values
    bottom = np.zeros(len(years))
    for lab, col in zip(labels, colors):
        vals = data_k[lab].values
        # Mark 2020 missing
        mask = np.where(np.array(years) == 2020, np.nan, vals)
        ax.bar(years, mask, bottom=bottom, color=col, label=lab, width=0.85,
               edgecolor=BG, linewidth=0.5)
        bottom += np.nan_to_num(mask)
    ax.set_xlim(2004.4, 2024.6)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=BLACK, length=0)
    ax.set_xticks([2005, 2010, 2015, 2020, 2024])
    ax.grid(axis="y", color="white", linewidth=0.9, alpha=0.7)
    ax.set_axisbelow(True)
    # Y axis: thousands
    ymax = bottom.max() * 1.08
    ax.set_ylim(0, ymax)
    ax.set_ylabel("Thousands of people", color=BLACK, fontsize=10)
    # Legend
    ax.legend(loc="upper right", frameon=False, fontsize=9.5, handlelength=1.2,
              handleheight=0.9, ncol=len(labels), bbox_to_anchor=(1.0, 1.10))
    # Title block
    ax.set_title("")
    fig.text(0.04, 0.94, title, fontsize=15, color=BLACK, ha="left", weight="bold")
    fig.text(0.04, 0.905, subtitle, fontsize=10, color=BLACK, ha="left", style="italic")
    fig.text(0.04, 0.02,
             "Source: IPUMS ACS 1-Year microdata, 2005–2024. Midwest inter-regional out-migrants (lived in different Midwest state 1 yr ago, now outside the region).\n2020 absent (ACS suspended due to COVID). Income deflated to 2024 dollars using CPI-U.",
             fontsize=8, color=BLACK, ha="left")
    plt.tight_layout(rect=[0.03, 0.06, 0.97, 0.86])
    fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
    fig.savefig(fname + ".png", facecolor=BG, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {fname}.png/.svg")

print("\nBuilding income chart…")
plot_stack(inc_df_k, inc_labels, inc_colors,
           "Number of people leaving the Midwest, by household income",
           "Annual out-migration to other regions, by household income (real 2024 $), thousands",
           f"{OUT}/midwest_leavers_absolute_income")

print("Building education chart…")
plot_stack(ed_df_k, ed_labels, ed_colors,
           "Number of adults leaving the Midwest, by education",
           "Annual out-migration to other regions, adults 25+, by educational attainment, thousands",
           f"{OUT}/midwest_leavers_absolute_education")

# Save numeric outputs
inc_df_k.to_csv(f"{OUT}/midwest_leavers_absolute_income.csv")
ed_df_k.to_csv(f"{OUT}/midwest_leavers_absolute_education.csv")
print("\nDone.")
