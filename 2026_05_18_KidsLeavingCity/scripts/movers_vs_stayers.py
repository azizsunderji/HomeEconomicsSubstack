"""Income and post-move housing characteristics of NYC inner→outer movers with kids.

Closes gaps 1 and 2 from BRIEF.md:

  (1) Income of movers vs stayers — CPS / Brookings data is bimodal.
      Pull a clean HHINCOME by year for moving HHs (inner→outer NY MSA) vs.
      staying HHs (inner NYC, MIGRATE1=1).

  (2) Post-move housing characteristics — BEDROOMS, ROOMS, VALUEH, OWNERSHP
      of the inner→outer moving HHs. Joined to MIGCOUNTY1.

Outputs:
  data/movers_vs_stayers_income.csv      # year × group × income percentile
  data/movers_post_move_housing.csv      # year × characteristic distribution
  outputs/movers_vs_stayers_income.png   # 2-panel chart
  outputs/movers_post_move_housing.png   # 4-panel chart

Notes on filtering:
  - Inner counties (origin for movers, location for stayers):
    NY 36005 Bronx, 36047 Brooklyn, 36061 Manhattan, 36081 Queens, 36085 SI,
    NJ 34017 Hudson.
  - Suburb counties (destination for movers): NY Westchester/Nassau/Suffolk/
    Rockland/Putnam/Orange; NJ Bergen/Essex/Middlesex/Monmouth/Morris/Passaic/
    Somerset/Sussex/Union; CT Fairfield; PA Pike.
  - Households-with-kids: at least one child < 18 in the HH. We restrict to
    head-of-household rows (RELATE=1) and use the HH-level NCHILD counter.
  - Movers: head's MIGRATE1 ∈ {3,4} and MIGCOUNTY1 in inner set, destination
    in suburb set. This captures different-county moves within or across
    states. Same-county moves (MIGRATE1=2) are NOT inner→outer by construction.
  - Stayers: head MIGRATE1=1 (same house) AND currently in inner counties.
"""
import sys
import duckdb
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARQUET = "/Users/azizsunderji/Dropbox/Home Economics/Data/Reference/Microdata/ACS/acs_5year_all_windows.parquet"

# County definitions (state FIPS, county FIPS-3-digit)
INNER = [
    (36, 5), (36, 47), (36, 61), (36, 81), (36, 85),  # NYC 5 boroughs
    (34, 17),  # Hudson (Jersey City)
]
SUBURB = [
    # NY MSA suburbs
    (36, 59),   # Nassau
    (36, 87),   # Rockland
    (36, 103),  # Suffolk
    (36, 119),  # Westchester
    (36, 79),   # Putnam
    (36, 71),   # Orange
    # NJ commute-belt
    (34, 3),    # Bergen
    (34, 13),   # Essex
    (34, 23),   # Middlesex
    (34, 25),   # Monmouth
    (34, 27),   # Morris
    (34, 31),   # Passaic
    (34, 35),   # Somerset
    (34, 37),   # Sussex
    (34, 39),   # Union
    # CT
    (9, 1),     # Fairfield (note CT was state 9 pre-2022; sometimes 09)
    # PA
    (42, 103),  # Pike
]

def _county_tuple_sql(county_list, state_col, county_col):
    """Build a SQL IN-list of (state, county) tuples."""
    pairs = " OR ".join(
        f"({state_col}={s} AND {county_col}={c})" for s, c in county_list
    )
    return f"({pairs})"

def main():
    con = duckdb.connect()
    parquet = PARQUET

    inner_current = _county_tuple_sql(INNER, "STATEFIP", "COUNTYFIP")
    suburb_current = _county_tuple_sql(SUBURB, "STATEFIP", "COUNTYFIP")
    inner_origin = _county_tuple_sql(INNER, "MIGPLAC1", "MIGCOUNTY1")

    # ── MOVERS: inner → suburb in past year, HH has kids ──
    # We restrict to heads of household (RELATE=1) so each HH counted once,
    # and HHINCOME / BEDROOMS / ROOMS / VALUEH / OWNERSHP represent the HH.
    # IPUMS HHINCOME has top-codes; 9999999 = N/A. Filter those out.
    movers_q = f"""
    SELECT
      YEAR, HHWT, HHINCOME, BEDROOMS, ROOMS, VALUEH, OWNERSHP, NCHILD,
      AGE AS head_age, STATEFIP, COUNTYFIP, MIGPLAC1, MIGCOUNTY1
    FROM '{parquet}'
    WHERE RELATE = 1
      AND NCHILD >= 1
      AND MIGRATE1 IN (3, 4)
      AND {inner_origin}
      AND {suburb_current}
      AND HHINCOME != 9999999
    """
    movers = con.execute(movers_q).df()
    print(f"Movers (inner→suburb, with kids, head): {len(movers):,} rows across {movers['YEAR'].nunique()} years")

    # ── STAYERS: in inner NYC, didn't move, HH has kids ──
    stayers_q = f"""
    SELECT YEAR, HHWT, HHINCOME, BEDROOMS, ROOMS, VALUEH, OWNERSHP, NCHILD,
      AGE AS head_age, STATEFIP, COUNTYFIP
    FROM '{parquet}'
    WHERE RELATE = 1
      AND NCHILD >= 1
      AND MIGRATE1 = 1
      AND {inner_current}
      AND HHINCOME != 9999999
    """
    stayers = con.execute(stayers_q).df()
    print(f"Stayers (inner, same-house, with kids, head): {len(stayers):,} rows")

    # Adjust HHINCOME for inflation to 2023 dollars using CPI-U
    # (rough — for headline chart, real income is what matters)
    # CPI-U annual averages, 1982-84 base = 100
    cpi = {
        2009: 214.537, 2010: 218.056, 2011: 224.939, 2012: 229.594,
        2013: 232.957, 2014: 236.736, 2015: 237.017, 2016: 240.007,
        2017: 245.120, 2018: 251.107, 2019: 255.657, 2020: 258.811,
        2021: 270.970, 2022: 292.655, 2023: 304.702,
    }
    BASE_CPI = cpi[2023]
    def deflate(df):
        df = df.copy()
        df["CPI"] = df["YEAR"].map(cpi)
        df["HHINCOME_2023"] = df["HHINCOME"] * BASE_CPI / df["CPI"]
        return df
    movers = deflate(movers)
    stayers = deflate(stayers)

    # ── Weighted median + 25th/75th by year, both groups ──
    from numpy import percentile
    def weighted_quantiles(values, weights, qs=(25, 50, 75)):
        idx = np.argsort(values)
        v = np.asarray(values)[idx]
        w = np.asarray(weights)[idx]
        cum = np.cumsum(w)
        total = cum[-1]
        out = []
        for q in qs:
            target = total * q / 100
            i = np.searchsorted(cum, target)
            out.append(float(v[min(i, len(v) - 1)]))
        return out

    # 3-year rolling pool for movers: 1-year ACS has ~30-60 movers per year
    # in this specific filter, so noisy. Rolling-3 makes the trend readable.
    rows = []
    all_years = sorted(set(movers["YEAR"]) | set(stayers["YEAR"]))
    for year in all_years:
        # rolling 3-year window centered on this year (for endpoints, shifted)
        if year == min(all_years):
            window = [year, year + 1, year + 2]
        elif year == max(all_years):
            window = [year - 2, year - 1, year]
        else:
            window = [year - 1, year, year + 1]
        for label, df in [("movers", movers), ("stayers", stayers)]:
            sub = df[df["YEAR"].isin(window)]
            if len(sub) < 30:
                continue
            p25, p50, p75 = weighted_quantiles(sub["HHINCOME_2023"].values, sub["HHWT"].values)
            n_weighted = float(sub["HHWT"].sum())
            rows.append({
                "year": int(year), "group": label,
                "p25": p25, "median": p50, "p75": p75,
                "n_unweighted": len(sub),
                "n_weighted": n_weighted,
                "window": f"{window[0]}-{window[-1]}",
            })
    income_df = pd.DataFrame(rows)
    income_csv = ROOT / "data" / "movers_vs_stayers_income.csv"
    income_csv.parent.mkdir(parents=True, exist_ok=True)
    income_df.to_csv(income_csv, index=False)
    print(f"\nWrote {income_csv}")
    print(income_df.pivot_table(index="year", columns="group", values="median").round(0))

    # ── Post-move housing characteristics for movers ──
    # Pooled across years 2019-2023 (most recent 5-year window) so distributions
    # are stable. Weighted by HHWT.
    recent = movers[movers["YEAR"] >= 2019].copy()
    # IPUMS code interpretation:
    #   OWNERSHP: 1=Owned, 2=Rented. 0=N/A (not in housing unit).
    #   BEDROOMS: 0=N/A, 1=No bedroom (studio), 2=1, 3=2, 4=3, 5=4, 6=5, 7=6, ...
    #     IPUMS docs: code 0=NA, 1=No bedroom, then +1 each. So actual bedrooms = code - 1, except 0/1 = "studio/none".
    #     We'll interpret as: actual bedrooms = max(BEDROOMS - 1, 0). 0 = studio.
    #   ROOMS: total rooms in the unit (1-9+).
    #   VALUEH: 9999999 = NA (renter); top-coded otherwise.
    recent["actual_bedrooms"] = (recent["BEDROOMS"] - 1).clip(lower=0)
    recent["is_owner"] = (recent["OWNERSHP"] == 1).astype(int)
    recent_owners = recent[recent["OWNERSHP"] == 1].copy()
    recent_owners = recent_owners[recent_owners["VALUEH"] != 9999999]
    recent_owners = recent_owners[recent_owners["VALUEH"] > 0]
    recent_owners["VALUEH_2023"] = recent_owners["VALUEH"] * BASE_CPI / recent_owners["CPI"]

    # ── Same characteristics for stayers — for comparison panel ──
    recent_st = stayers[stayers["YEAR"] >= 2019].copy()
    recent_st["actual_bedrooms"] = (recent_st["BEDROOMS"] - 1).clip(lower=0)
    recent_st["is_owner"] = (recent_st["OWNERSHP"] == 1).astype(int)

    def weighted_mean(s, w):
        return float(np.average(s, weights=w)) if len(s) else float("nan")

    def weighted_median(s, w):
        return weighted_quantiles(s.values, w.values, (50,))[0]

    def dist(series, weights, bins):
        out = {}
        total_w = weights.sum()
        for b in bins:
            mask = series == b
            out[b] = float(weights[mask].sum() / total_w * 100) if total_w > 0 else 0
        return out

    # Tables
    print("\n=== POST-MOVE HOUSING (movers, 2019-2023 pooled) ===")
    print(f"  Ownership rate: {weighted_mean(recent['is_owner'], recent['HHWT'])*100:.1f}%")
    print(f"  Bedrooms — weighted median: {weighted_median(recent['actual_bedrooms'], recent['HHWT']):.1f}")
    print(f"  Rooms    — weighted median: {weighted_median(recent['ROOMS'], recent['HHWT']):.1f}")
    if len(recent_owners):
        print(f"  House value (owners only, 2023 dollars) — weighted median: ${weighted_median(recent_owners['VALUEH_2023'], recent_owners['HHWT'])/1000:.0f}K")
    print(f"\n=== POST-MOVE HOUSING (stayers, 2019-2023 pooled) ===")
    print(f"  Ownership rate: {weighted_mean(recent_st['is_owner'], recent_st['HHWT'])*100:.1f}%")
    print(f"  Bedrooms — weighted median: {weighted_median(recent_st['actual_bedrooms'], recent_st['HHWT']):.1f}")
    print(f"  Rooms    — weighted median: {weighted_median(recent_st['ROOMS'], recent_st['HHWT']):.1f}")

    # Bedroom distribution comparison
    bed_bins = list(range(0, 6))
    movers_bed = dist(recent["actual_bedrooms"].clip(upper=5), recent["HHWT"], bed_bins)
    stayers_bed = dist(recent_st["actual_bedrooms"].clip(upper=5), recent_st["HHWT"], bed_bins)
    print("\nBedroom distribution (%, post-move for movers / current for stayers, 5+ topcoded):")
    print(f"  Bedrooms  Movers  Stayers")
    for b in bed_bins:
        print(f"  {b}         {movers_bed[b]:5.1f}   {stayers_bed[b]:5.1f}")

    # Save housing characteristics
    housing_rows = []
    housing_rows.append({"group": "movers", "metric": "ownership_rate_pct", "value": weighted_mean(recent["is_owner"], recent["HHWT"])*100})
    housing_rows.append({"group": "movers", "metric": "bedrooms_median", "value": weighted_median(recent["actual_bedrooms"], recent["HHWT"])})
    housing_rows.append({"group": "movers", "metric": "rooms_median", "value": weighted_median(recent["ROOMS"], recent["HHWT"])})
    if len(recent_owners):
        housing_rows.append({"group": "movers", "metric": "house_value_median_2023", "value": weighted_median(recent_owners["VALUEH_2023"], recent_owners["HHWT"])})
    housing_rows.append({"group": "stayers", "metric": "ownership_rate_pct", "value": weighted_mean(recent_st["is_owner"], recent_st["HHWT"])*100})
    housing_rows.append({"group": "stayers", "metric": "bedrooms_median", "value": weighted_median(recent_st["actual_bedrooms"], recent_st["HHWT"])})
    housing_rows.append({"group": "stayers", "metric": "rooms_median", "value": weighted_median(recent_st["ROOMS"], recent_st["HHWT"])})
    for b in bed_bins:
        housing_rows.append({"group": "movers", "metric": f"bedrooms_share_{b}", "value": movers_bed[b]})
        housing_rows.append({"group": "stayers", "metric": f"bedrooms_share_{b}", "value": stayers_bed[b]})
    housing_df = pd.DataFrame(housing_rows)
    housing_csv = ROOT / "data" / "movers_post_move_housing.csv"
    housing_df.to_csv(housing_csv, index=False)
    print(f"\nWrote {housing_csv}")

    # ── CHARTS ──
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    BLUE = "#0BB4FF"
    YELLOW = "#FEC439"
    RED = "#F4743B"
    GREEN = "#67A275"
    BLACK = "#3D3733"
    BG = "#F6F7F3"

    plt.rcParams["svg.fonttype"] = "none"

    # CHART 1: Income comparison over time (2 panels)
    pivot_med = income_df.pivot_table(index="year", columns="group", values="median")
    pivot_p25 = income_df.pivot_table(index="year", columns="group", values="p25")
    pivot_p75 = income_df.pivot_table(index="year", columns="group", values="p75")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor=BG)
    ax = axes[0]
    ax.set_facecolor(BG)
    if "movers" in pivot_med.columns:
        ax.fill_between(pivot_med.index, pivot_p25["movers"], pivot_p75["movers"], color=BLUE, alpha=0.18, label="_nolegend_")
        ax.plot(pivot_med.index, pivot_med["movers"], color=BLUE, lw=2.5, label="Movers (inner→suburb)")
    if "stayers" in pivot_med.columns:
        ax.fill_between(pivot_med.index, pivot_p25["stayers"], pivot_p75["stayers"], color=YELLOW, alpha=0.18)
        ax.plot(pivot_med.index, pivot_med["stayers"], color=YELLOW, lw=2.5, label="Stayers (inner, same house)")
    ax.set_title("Median household income (2023 dollars, 3-year rolling)\nNYC inner-vs-outer movers with kids vs. inner-NYC stayers with kids",
                 fontsize=11, color=BLACK, loc="left")
    ax.set_xlabel("Survey year", color=BLACK)
    ax.set_ylabel("Household income, USD (2023$)", color=BLACK)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}K"))
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=BLACK)
    # Difference panel
    ax = axes[1]
    ax.set_facecolor(BG)
    if "movers" in pivot_med.columns and "stayers" in pivot_med.columns:
        diff = pivot_med["movers"] - pivot_med["stayers"]
        colors = [GREEN if d >= 0 else RED for d in diff]
        ax.bar(diff.index, diff, color=colors, alpha=0.85)
        ax.axhline(0, color=BLACK, lw=0.5)
        ax.set_title("Movers' median income — minus — stayers' median income\n(positive = movers earn MORE than stayers)",
                     fontsize=11, color=BLACK, loc="left")
        ax.set_xlabel("Survey year", color=BLACK)
        ax.set_ylabel("Difference, USD (2023$)", color=BLACK)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:+.0f}K"))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(colors=BLACK)

    fig.suptitle("Income of movers vs stayers — NYC MSA, families with kids",
                 fontsize=14, fontweight="bold", color=BLACK, x=0.05, y=0.99, ha="left")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig_path = ROOT / "outputs" / "movers_vs_stayers_income.png"
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(fig_path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.savefig(fig_path.with_suffix(".svg"), bbox_inches="tight", facecolor=BG)
    print(f"\nWrote {fig_path}")

    # CHART 2: Post-move housing characteristics (4 panels)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), facecolor=BG)

    # Panel A: Bedroom distribution
    ax = axes[0, 0]
    ax.set_facecolor(BG)
    x = np.arange(len(bed_bins))
    width = 0.4
    m_vals = [movers_bed[b] for b in bed_bins]
    s_vals = [stayers_bed[b] for b in bed_bins]
    ax.bar(x - width/2, s_vals, width, color=YELLOW, label="Stayers (inner NYC)", alpha=0.9)
    ax.bar(x + width/2, m_vals, width, color=BLUE, label="Movers (post-move)", alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{b}" if b < 5 else "5+" for b in bed_bins], color=BLACK)
    ax.set_xlabel("Bedrooms in housing unit", color=BLACK)
    ax.set_ylabel("Share of households (%)", color=BLACK)
    ax.set_title("A. Bedroom distribution — movers vs stayers", fontsize=11, color=BLACK, loc="left")
    ax.legend(fontsize=9, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=BLACK)

    # Panel B: Ownership rate
    ax = axes[0, 1]
    ax.set_facecolor(BG)
    own_movers = weighted_mean(recent["is_owner"], recent["HHWT"]) * 100
    own_stayers = weighted_mean(recent_st["is_owner"], recent_st["HHWT"]) * 100
    bars = ax.bar(["Stayers\n(inner NYC)", "Movers\n(post-move)"], [own_stayers, own_movers],
                  color=[YELLOW, BLUE], alpha=0.9, width=0.5)
    for bar, v in zip(bars, [own_stayers, own_movers]):
        ax.annotate(f"{v:.0f}%", xy=(bar.get_x() + bar.get_width()/2, v),
                    xytext=(0, 4), textcoords="offset points",
                    ha="center", color=BLACK, fontsize=12, fontweight="bold")
    ax.set_ylabel("Share of households owning (%)", color=BLACK)
    ax.set_ylim(0, 100)
    ax.set_title("B. Homeownership rate", fontsize=11, color=BLACK, loc="left")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=BLACK)

    # Panel C: Total rooms distribution
    ax = axes[1, 0]
    ax.set_facecolor(BG)
    room_bins = list(range(1, 10))  # 1-9+ topcoded
    movers_rooms = dist(recent["ROOMS"].clip(upper=9), recent["HHWT"], room_bins)
    stayers_rooms = dist(recent_st["ROOMS"].clip(upper=9), recent_st["HHWT"], room_bins)
    x = np.arange(len(room_bins))
    width = 0.4
    ax.bar(x - width/2, [stayers_rooms[b] for b in room_bins], width, color=YELLOW, label="Stayers", alpha=0.9)
    ax.bar(x + width/2, [movers_rooms[b] for b in room_bins], width, color=BLUE, label="Movers", alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{b}" if b < 9 else "9+" for b in room_bins], color=BLACK)
    ax.set_xlabel("Total rooms in unit", color=BLACK)
    ax.set_ylabel("Share of households (%)", color=BLACK)
    ax.set_title("C. Total rooms — movers vs stayers", fontsize=11, color=BLACK, loc="left")
    ax.legend(fontsize=9, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=BLACK)

    # Panel D: House value distribution for owner-movers
    ax = axes[1, 1]
    ax.set_facecolor(BG)
    if len(recent_owners):
        median_value = weighted_median(recent_owners["VALUEH_2023"], recent_owners["HHWT"])
        p25 = weighted_quantiles(recent_owners["VALUEH_2023"].values, recent_owners["HHWT"].values, (25,))[0]
        p75 = weighted_quantiles(recent_owners["VALUEH_2023"].values, recent_owners["HHWT"].values, (75,))[0]
        # Histogram
        ax.hist(recent_owners["VALUEH_2023"].values, weights=recent_owners["HHWT"].values,
                bins=40, color=BLUE, alpha=0.7, edgecolor="white")
        ax.axvline(median_value, color=BLACK, lw=2, ls="--", label=f"Median ${median_value/1000:.0f}K")
        ax.axvline(p25, color=BLACK, lw=1, ls=":", label=f"P25 ${p25/1000:.0f}K")
        ax.axvline(p75, color=BLACK, lw=1, ls=":", label=f"P75 ${p75/1000:.0f}K")
        ax.set_xlabel("House value (2023 dollars)", color=BLACK)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}K" if x < 1e6 else f"${x/1e6:.1f}M"))
        ax.set_ylabel("Weighted count", color=BLACK)
        ax.set_title("D. House value — owner-movers post-move", fontsize=11, color=BLACK, loc="left")
        ax.legend(fontsize=9, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors=BLACK)

    fig.suptitle("Post-move housing characteristics — NYC inner→suburb movers with kids (2019–2023 ACS PUMS)",
                 fontsize=13, fontweight="bold", color=BLACK, x=0.05, y=0.99, ha="left")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig_path = ROOT / "outputs" / "movers_post_move_housing.png"
    plt.savefig(fig_path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.savefig(fig_path.with_suffix(".svg"), bbox_inches="tight", facecolor=BG)
    print(f"Wrote {fig_path}")

    print("\n=== Done ===")

if __name__ == "__main__":
    main()
