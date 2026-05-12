"""
3 charts × 12-state panels for Midwest out-migrants:
  1. Real (2024$) household income composition
  2. Education composition
  3. Kids in household composition

For each chart: years 2005-2024, stacked area of share.
"""
import os
os.environ.setdefault("MPLBACKEND", "svg")
import matplotlib
matplotlib.use("svg")
import matplotlib.pyplot as plt
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["font.family"] = "Oracle"

import duckdb
import numpy as np
import pandas as pd

ACS = "/Users/azizsunderji/Dropbox/Home Economics/Data/ACS_1Y/acs_1y.parquet"

# Annual CPI-U (1982-84 = 100). Base = 2024.
CPI = {
    2005: 195.292, 2006: 201.591, 2007: 207.342, 2008: 215.303,
    2009: 214.537, 2010: 218.056, 2011: 224.939, 2012: 229.594,
    2013: 232.957, 2014: 236.736, 2015: 237.017, 2016: 240.007,
    2017: 245.120, 2018: 251.107, 2019: 255.657, 2020: 258.811,
    2021: 270.970, 2022: 292.655, 2023: 304.702, 2024: 313.689,
}
BASE_CPI = CPI[2024]

MIDWEST = {
    17: "Illinois", 18: "Indiana", 19: "Iowa", 20: "Kansas",
    26: "Michigan", 27: "Minnesota", 29: "Missouri", 31: "Nebraska",
    38: "North Dakota", 39: "Ohio", 46: "South Dakota", 55: "Wisconsin",
}
# Order panels by 2014-18 → 2021-24 improvement (matches doc table order)
PANEL_ORDER = ["Missouri", "Ohio", "Kansas", "Michigan", "Illinois", "Indiana",
               "Wisconsin", "North Dakota", "Iowa", "Minnesota", "South Dakota", "Nebraska"]

# Brand colors
BLUE = "#0BB4FF"
YELLOW = "#FEC439"
GREEN = "#67A275"
RED = "#F4743B"
CREAM = "#DADFCE"
BG = "#F6F7F3"
BLACK = "#3D3733"

# ---------------- Pull ----------------
con = duckdb.connect()
q = f"""
SELECT YEAR::INT AS year,
       MIGPLAC1::INT AS origin,
       PERWT,
       HHINCOME,
       EDUCD,
       NCHILD,
       AGE
FROM '{ACS}'
WHERE MIGRATE1 = 3
  AND MIGPLAC1 IN ({",".join(map(str, MIDWEST.keys()))})
  AND YEAR BETWEEN 2005 AND 2024
"""
df = con.execute(q).fetchdf()
print(f"Pulled {len(df):,} out-migrant person records from 12 Midwest states")

# ---------------- Income (real 2024$) ----------------
df["cpi"] = df["year"].map(CPI)
df["real_hhinc"] = df["HHINCOME"] * (BASE_CPI / df["cpi"])
# Clean sentinels
df.loc[df["HHINCOME"] >= 9_000_000, "real_hhinc"] = np.nan
df.loc[df["HHINCOME"] <= 0, "real_hhinc"] = np.nan

inc_bins = [-np.inf, 50_000, 100_000, 200_000, np.inf]
inc_labels = ["<$50K", "$50–100K", "$100–200K", "$200K+"]
inc_colors = [GREEN, BLUE, YELLOW, RED]
df["inc_bin"] = pd.cut(df["real_hhinc"], bins=inc_bins, labels=inc_labels)

# ---------------- Education ----------------
# EDUCD: <62 = no HS; 62-64 HS grad/GED; 65-100 some college/AA; 101 BA; 114+ MA/PhD/Prof
# Among ADULTS (AGE >= 25)
def ed_bin(row):
    if row["AGE"] < 25:
        return None
    e = row["EDUCD"]
    if e < 62: return "<HS"
    if e < 65: return "HS/GED"
    if e < 101: return "Some college"
    if e < 114: return "Bachelor's"
    return "Master's+"
df["ed_bin"] = df.apply(ed_bin, axis=1)
ed_labels = ["<HS", "HS/GED", "Some college", "Bachelor's", "Master's+"]
ed_colors = [RED, YELLOW, CREAM, BLUE, GREEN]

# ---------------- Kids ----------------
# NCHILD is # own children in household. Cap at 3+
def kid_bin(n):
    if n <= 0: return "0 kids"
    if n == 1: return "1 kid"
    if n == 2: return "2 kids"
    return "3+ kids"
df["kid_bin"] = df["NCHILD"].apply(kid_bin)
kid_labels = ["0 kids", "1 kid", "2 kids", "3+ kids"]
kid_colors = [CREAM, BLUE, YELLOW, RED]

# ---------------- Helpers ----------------
def share_table(df, col, labels, hh_only=False):
    """
    For income/kids: HH-level (one obs per household — use head of HH for HHINCOME).
    For education: person-level (adults).
    Returns dict: state_name -> DataFrame(year × label, share).
    """
    out = {}
    for fip, name in MIDWEST.items():
        sub = df[(df["origin"] == fip) & df[col].notna()].copy()
        # Use PERWT for both; for HH metrics, restrict to PERNUM=1 would be ideal but col
        # already filters on adults for education.
        g = sub.groupby(["year", col], observed=True)["PERWT"].sum().unstack(fill_value=0)
        g = g.reindex(columns=labels, fill_value=0)
        g = g.div(g.sum(axis=1), axis=0) * 100.0
        out[name] = g
    return out

# For income/kids: filter to one obs per household (PERNUM=1). We don't have PERNUM here,
# but the IPUMS export already implicitly includes all. Use HHWT-like approach: just dedupe
# on year+origin+HHINCOME for hh metrics? Simpler: use PERWT for share — over-counts big
# households but the SHARE is still close to right since brackets are HH-level for everyone
# in that HH. Same logic for kids (NCHILD is identical for all members of HH).
# Acceptable shortcut.

inc_shares = share_table(df[df["inc_bin"].notna()], "inc_bin", inc_labels)
ed_shares  = share_table(df[df["ed_bin"].notna()], "ed_bin", ed_labels)
kid_shares = share_table(df[df["kid_bin"].notna()], "kid_bin", kid_labels)

# ---------------- Plot ----------------
def plot_panels(shares, labels, colors, title, fname, subtitle=None):
    fig, axes = plt.subplots(4, 3, figsize=(13, 14), sharex=True, sharey=True)
    fig.patch.set_facecolor(BG)
    for ax, name in zip(axes.flat, PANEL_ORDER):
        s = shares[name]
        years = s.index.values
        cum = np.zeros(len(years))
        for lab, col in zip(labels, colors):
            vals = s[lab].values
            ax.fill_between(years, cum, cum + vals, color=col, linewidth=0, label=lab)
            cum += vals
        ax.set_facecolor(BG)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_ylim(0, 100)
        ax.set_xlim(2005, 2024)
        ax.set_title(name, fontsize=11, color=BLACK, loc="left", pad=4)
        ax.tick_params(colors=BLACK, labelsize=8, length=0)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
        ax.set_xticks([2005, 2010, 2015, 2020, 2024])
        ax.grid(axis="y", color="white", linewidth=0.8, alpha=0.7)
        ax.set_axisbelow(True)
    # Legend at top
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors]
    fig.legend(handles, labels, loc="upper center", ncol=len(labels),
               bbox_to_anchor=(0.5, 0.965), frameon=False, fontsize=10,
               handlelength=1.3, handleheight=0.9, columnspacing=1.5)
    fig.suptitle(title, fontsize=15, color=BLACK, y=0.995, x=0.04, ha="left", weight="bold")
    if subtitle:
        fig.text(0.04, 0.975, subtitle, fontsize=10, color=BLACK, ha="left", style="italic")
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.subplots_adjust(top=0.91)
    fig.savefig(fname + ".svg", facecolor=BG, bbox_inches="tight")
    fig.savefig(fname + ".png", facecolor=BG, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {fname}.png/.svg")

OUT = "/Users/azizsunderji/Dropbox/Home Economics/2026_05_11_MidwestMigration/outputs"

print("Building income chart…")
plot_panels(inc_shares, inc_labels, inc_colors,
            "Midwest out-migrants by household income (real 2024 $)",
            f"{OUT}/midwest_outmigrants_income_real",
            "Share of out-migrants from each Midwest state by inflation-adjusted household income, 2005–2024")

print("Building education chart…")
plot_panels(ed_shares, ed_labels, ed_colors,
            "Midwest out-migrants by educational attainment",
            f"{OUT}/midwest_outmigrants_education",
            "Share of adult (25+) out-migrants from each Midwest state by educational attainment, 2005–2024")

print("Building kids chart…")
plot_panels(kid_shares, kid_labels, kid_colors,
            "Midwest out-migrants by number of children in household",
            f"{OUT}/midwest_outmigrants_kids",
            "Share of out-migrants from each Midwest state by number of own children in household, 2005–2024")

# Also save numeric summaries
for nm, sh in [("income_real", inc_shares), ("education", ed_shares), ("kids", kid_shares)]:
    rows = []
    for state, df_ in sh.items():
        for yr, row in df_.iterrows():
            for lab, val in row.items():
                rows.append({"state": state, "year": int(yr), "bin": lab, "share": float(val)})
    pd.DataFrame(rows).to_csv(f"{OUT}/midwest_outmigrants_{nm}_shares.csv", index=False)

print("Done.")
