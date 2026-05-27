"""Age-matched income comparison: movers vs stayers within head-of-HH age buckets.

Sanity check on `movers_vs_stayers.py`. If movers skew older or younger than
stayers, the headline income difference could be partly a life-cycle effect
rather than a true affluence gap. We control for head's AGE bucket and
re-compute the income difference WITHIN each bucket.
"""
import duckdb
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARQUET = "/Users/azizsunderji/Dropbox/Home Economics/Data/Reference/Microdata/ACS/acs_5year_all_windows.parquet"

INNER = [(36, 5), (36, 47), (36, 61), (36, 81), (36, 85), (34, 17)]
SUBURB = [
    (36, 59), (36, 87), (36, 103), (36, 119), (36, 79), (36, 71),
    (34, 3), (34, 13), (34, 23), (34, 25), (34, 27), (34, 31), (34, 35), (34, 37), (34, 39),
    (9, 1), (42, 103),
]

def _county_tuple_sql(county_list, state_col, county_col):
    pairs = " OR ".join(f"({state_col}={s} AND {county_col}={c})" for s, c in county_list)
    return f"({pairs})"

con = duckdb.connect()
inner_current = _county_tuple_sql(INNER, "STATEFIP", "COUNTYFIP")
suburb_current = _county_tuple_sql(SUBURB, "STATEFIP", "COUNTYFIP")
inner_origin = _county_tuple_sql(INNER, "MIGPLAC1", "MIGCOUNTY1")

movers = con.execute(f"""
SELECT YEAR, HHWT, HHINCOME, AGE AS head_age
FROM '{PARQUET}'
WHERE RELATE = 1 AND NCHILD >= 1 AND MIGRATE1 IN (3, 4)
  AND {inner_origin} AND {suburb_current}
  AND HHINCOME != 9999999
""").df()
stayers = con.execute(f"""
SELECT YEAR, HHWT, HHINCOME, AGE AS head_age
FROM '{PARQUET}'
WHERE RELATE = 1 AND NCHILD >= 1 AND MIGRATE1 = 1
  AND {inner_current}
  AND HHINCOME != 9999999
""").df()
print(f"Movers: {len(movers):,} · Stayers: {len(stayers):,}")

# CPI deflation
cpi = {
    2009: 214.537, 2010: 218.056, 2011: 224.939, 2012: 229.594, 2013: 232.957,
    2014: 236.736, 2015: 237.017, 2016: 240.007, 2017: 245.120, 2018: 251.107,
    2019: 255.657, 2020: 258.811, 2021: 270.970, 2022: 292.655, 2023: 304.702,
}
BASE_CPI = cpi[2023]
for df in (movers, stayers):
    df["HHINCOME_2023"] = df["HHINCOME"] * BASE_CPI / df["YEAR"].map(cpi)

def weighted_median(values, weights):
    if len(values) == 0:
        return float("nan")
    idx = np.argsort(values)
    v = np.asarray(values)[idx]
    w = np.asarray(weights)[idx]
    cum = np.cumsum(w)
    return float(v[np.searchsorted(cum, cum[-1] / 2)])

def weighted_share(mask, weights):
    total = weights.sum()
    return float(weights[mask].sum() / total * 100) if total > 0 else 0

# Pool ALL years (2009-2023) for stable comparison since per-year sample is thin
mov = movers.copy()
sta = stayers.copy()

# Age buckets — head of household ages
buckets = [(20, 30, "20–29"), (30, 35, "30–34"), (35, 40, "35–39"),
           (40, 45, "40–44"), (45, 50, "45–49"), (50, 70, "50–69")]

print("\n=== Head-of-HH age distribution (% of HHs in each bucket) ===")
print(f"{'Bucket':<12} {'Movers':>8} {'Stayers':>8}")
for lo, hi, name in buckets:
    m_share = weighted_share((mov["head_age"] >= lo) & (mov["head_age"] < hi), mov["HHWT"])
    s_share = weighted_share((sta["head_age"] >= lo) & (sta["head_age"] < hi), sta["HHWT"])
    print(f"{name:<12} {m_share:7.1f}% {s_share:7.1f}%")

print(f"\nWeighted-mean head age — movers: {np.average(mov['head_age'], weights=mov['HHWT']):.1f}")
print(f"Weighted-mean head age — stayers: {np.average(sta['head_age'], weights=sta['HHWT']):.1f}")

# Income within age buckets
print("\n=== Median HHINCOME (2023$) within head-age buckets, pooled 2009-2023 ===")
print(f"{'Bucket':<12} {'Mover med':>10} {'Stayer med':>10} {'Diff':>10} {'M-n':>6} {'S-n':>8}")
rows = []
for lo, hi, name in buckets:
    m_sub = mov[(mov["head_age"] >= lo) & (mov["head_age"] < hi)]
    s_sub = sta[(sta["head_age"] >= lo) & (sta["head_age"] < hi)]
    if len(m_sub) < 30 or len(s_sub) < 100:
        continue
    m_med = weighted_median(m_sub["HHINCOME_2023"].values, m_sub["HHWT"].values)
    s_med = weighted_median(s_sub["HHINCOME_2023"].values, s_sub["HHWT"].values)
    print(f"{name:<12} ${m_med/1000:>7.0f}K ${s_med/1000:>7.0f}K  +${(m_med-s_med)/1000:>5.0f}K  {len(m_sub):>5} {len(s_sub):>7}")
    rows.append({"bucket": name, "movers_median": m_med, "stayers_median": s_med,
                 "diff": m_med - s_med, "movers_n": len(m_sub), "stayers_n": len(s_sub)})

df_age = pd.DataFrame(rows)
out_csv = ROOT / "data" / "movers_vs_stayers_income_age_matched.csv"
df_age.to_csv(out_csv, index=False)
print(f"\nWrote {out_csv}")

# Direct-standardized: re-weight stayers to match movers' age distribution,
# then re-compute the overall stayer median. If the gap still holds, it's not age.
print("\n=== Direct standardization: stayers re-weighted to match movers' age distribution ===")
# Define age weights = movers' share in each bucket / stayers' share in each bucket
adj_weights = sta["HHWT"].copy()
for lo, hi, _ in buckets:
    m_mask = (mov["head_age"] >= lo) & (mov["head_age"] < hi)
    s_mask = (sta["head_age"] >= lo) & (sta["head_age"] < hi)
    m_share = mov.loc[m_mask, "HHWT"].sum() / mov["HHWT"].sum()
    s_share = sta.loc[s_mask, "HHWT"].sum() / sta["HHWT"].sum()
    if s_share > 0:
        adj_weights.loc[s_mask] = sta.loc[s_mask, "HHWT"] * (m_share / s_share)
mov_med = weighted_median(mov["HHINCOME_2023"].values, mov["HHWT"].values)
sta_med = weighted_median(sta["HHINCOME_2023"].values, sta["HHWT"].values)
sta_med_adj = weighted_median(sta["HHINCOME_2023"].values, adj_weights.values)
print(f"Movers median (pooled): ${mov_med/1000:.0f}K")
print(f"Stayers median (pooled, unadjusted): ${sta_med/1000:.0f}K")
print(f"Stayers median (re-weighted to movers' age mix): ${sta_med_adj/1000:.0f}K")
print(f"Gap (movers − stayers, unadjusted): +${(mov_med-sta_med)/1000:.0f}K")
print(f"Gap (movers − stayers, age-matched): +${(mov_med-sta_med_adj)/1000:.0f}K")

# Chart: age-matched bucket comparison
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
BLUE = "#0BB4FF"; YELLOW = "#FEC439"; GREEN = "#67A275"; RED = "#F4743B"
BLACK = "#3D3733"; BG = "#F6F7F3"
plt.rcParams["svg.fonttype"] = "none"

fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor=BG)

ax = axes[0]
ax.set_facecolor(BG)
x = np.arange(len(rows))
width = 0.4
movers_meds = [r["movers_median"] / 1000 for r in rows]
stayers_meds = [r["stayers_median"] / 1000 for r in rows]
ax.bar(x - width/2, stayers_meds, width, color=YELLOW, label="Stayers", alpha=0.9)
ax.bar(x + width/2, movers_meds, width, color=BLUE, label="Movers", alpha=0.9)
ax.set_xticks(x)
ax.set_xticklabels([r["bucket"] for r in rows], color=BLACK)
ax.set_xlabel("Head-of-household age bucket", color=BLACK)
ax.set_ylabel("Median HHINCOME (2023$, thousands)", color=BLACK)
ax.set_title("A. Median income WITHIN each age bucket\nNYC inner→suburb movers with kids vs. inner-NYC stayers with kids",
             fontsize=11, color=BLACK, loc="left")
ax.legend(fontsize=10, frameon=False)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.0f}K"))
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.tick_params(colors=BLACK)

ax = axes[1]
ax.set_facecolor(BG)
diffs = [r["diff"] / 1000 for r in rows]
ax.bar(x, diffs, width=0.6, color=GREEN, alpha=0.85)
ax.set_xticks(x)
ax.set_xticklabels([r["bucket"] for r in rows], color=BLACK)
ax.set_xlabel("Head-of-household age bucket", color=BLACK)
ax.set_ylabel("Difference (movers − stayers), 2023$ thousands", color=BLACK)
ax.set_title("B. Income gap WITHIN each age bucket\n(positive = movers earn MORE than stayers of the same age)",
             fontsize=11, color=BLACK, loc="left")
ax.axhline(0, color=BLACK, lw=0.5)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:+.0f}K"))
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.tick_params(colors=BLACK)

# Footer with standardization stats
foot = (
    f"Direct standardization: stayers re-weighted to movers' age mix → "
    f"unadjusted gap = +${(mov_med-sta_med)/1000:.0f}K; age-matched gap = +${(mov_med-sta_med_adj)/1000:.0f}K. "
    f"Weighted-mean head age — movers {np.average(mov['head_age'], weights=mov['HHWT']):.1f}, stayers {np.average(sta['head_age'], weights=sta['HHWT']):.1f}."
)
fig.text(0.05, 0.01, foot, fontsize=8, color=BLACK, ha="left", style="italic")

fig.suptitle("Movers earn more than stayers — gap survives age matching",
             fontsize=14, fontweight="bold", color=BLACK, x=0.05, y=0.99, ha="left")
plt.tight_layout(rect=[0, 0.04, 1, 0.95])
fig_path = ROOT / "outputs" / "movers_vs_stayers_age_matched.png"
plt.savefig(fig_path, dpi=150, bbox_inches="tight", facecolor=BG)
plt.savefig(fig_path.with_suffix(".svg"), bbox_inches="tight", facecolor=BG)
print(f"\nWrote {fig_path}")
