"""
Bay Area housing gains: anomalous or not?
Compare SF/SJ/Oakland metro to top 50 US metros using Redfin + Zillow data.
Both seasonally adjusted and non-SA, at metro level.
"""

import duckdb
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ── Paths ──
REDFIN_METRO = "/Users/azizsunderji/Dropbox/Home Economics/Data/Redfin/monthly_metro.parquet"
ZILLOW_METRO = "/Users/azizsunderji/Dropbox/Home Economics/Data/Price/Zillow/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.parquet"
OUTDIR = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs"
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"

# ── Brand ──
BLUE   = "#0BB4FF"
YELLOW = "#FEC439"
GREEN  = "#67A275"
RED    = "#F4743B"
BLACK  = "#3D3733"
BG     = "#F6F7F3"
CREAM  = "#DADFCE"
LIGHT_RED = "#FBCAB5"
LIGHT_GREEN = "#C6DCCB"

for f in ['ABCOracle-Regular.otf','ABCOracle-Bold.otf','ABCOracle-Light.otf','ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

con = duckdb.connect()

# ── Bay Area metro names in Redfin ──
BA_METROS = [
    "San Francisco, CA metro area",
    "San Jose, CA metro area",
    "Oakland, CA metro area",
]

# ── Comparison metros (largest US metros) ──
COMPARISON_METROS = [
    "New York, NY metro area",
    "Los Angeles, CA metro area",
    "Chicago, IL metro area",
    "Houston, TX metro area",
    "Dallas, TX metro area",
    "Atlanta, GA metro area",
    "Miami, FL metro area",
    "Phoenix, AZ metro area",
    "Seattle, WA metro area",
    "Boston, MA metro area",
    "Denver, CO metro area",
    "Austin, TX metro area",
    "Nashville, TN metro area",
    "Portland, OR metro area",
    "Minneapolis, MN metro area",
    "Charlotte, NC metro area",
    "San Diego, CA metro area",
    "Tampa, FL metro area",
    "Washington, DC metro area",
    "Detroit, MI metro area",
]

ALL_METROS = BA_METROS + COMPARISON_METROS

# ════════════════════════════════════════════
# PART 1: REDFIN — Median Sale Price YoY
# ════════════════════════════════════════════

def get_redfin_yoy(sa_flag):
    """Get median sale price YoY for All Residential, SA or not."""
    label = "Seasonally Adjusted" if sa_flag else "Not Seasonally Adjusted"
    df = con.execute(f"""
        SELECT PERIOD_BEGIN as date, REGION as metro,
               MEDIAN_SALE_PRICE, MEDIAN_SALE_PRICE_YOY,
               MEDIAN_PPSF, MEDIAN_PPSF_YOY
        FROM '{REDFIN_METRO}'
        WHERE PROPERTY_TYPE = 'All Residential'
          AND IS_SEASONALLY_ADJUSTED = {sa_flag}
          AND PERIOD_BEGIN >= '2019-01-01'
    """).df()
    df['date'] = pd.to_datetime(df['date'])
    return df, label


def plot_redfin_yoy_comparison(sa_flag, metric='MEDIAN_SALE_PRICE_YOY', ylabel='Median Sale Price YoY %'):
    df, sa_label = get_redfin_yoy(sa_flag)

    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Plot comparison metros in light gray
    for m in COMPARISON_METROS:
        mdf = df[df['metro'] == m].sort_values('date')
        if len(mdf) > 0:
            ax.plot(mdf['date'], mdf[metric]*100, color='#C0C0C0', alpha=0.3, linewidth=0.8)

    # Plot BA metros boldly
    ba_colors = {BA_METROS[0]: BLUE, BA_METROS[1]: GREEN, BA_METROS[2]: RED}
    ba_labels = {"San Francisco, CA metro area": "San Francisco",
                 "San Jose, CA metro area": "San Jose",
                 "Oakland, CA metro area": "Oakland"}

    for m in BA_METROS:
        mdf = df[df['metro'] == m].sort_values('date')
        if len(mdf) > 0:
            ax.plot(mdf['date'], mdf[metric]*100, color=ba_colors[m],
                    linewidth=2.5, label=ba_labels[m], zorder=5)

    ax.axhline(y=0, color=BLACK, linewidth=0.5, alpha=0.5)
    ax.legend(loc='upper right', frameon=False, fontsize=10)

    ax.set_title(f"Bay Area vs. Major US Metros: {ylabel}\n({sa_label}, Redfin)",
                 fontsize=14, fontweight='bold', color=BLACK, pad=15)

    # Gridlines
    ax.grid(axis='y', color='#E0E0E0', linewidth=0.5)
    ax.grid(axis='x', visible=False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', length=0)

    # Y-axis: format with % on top tick only
    yticks = ax.get_yticks()
    yticklabels = [f"{int(v)}" for v in yticks]
    if len(yticklabels) > 0:
        yticklabels[-1] = f"{int(yticks[-1])}%"
    ax.set_yticklabels(yticklabels)

    ax.set_xlabel('')
    ax.set_ylabel('')

    # Source
    fig.text(0.12, 0.02, "Source: Redfin monthly metro data", fontsize=8,
             fontstyle='italic', color='gray')

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    suffix = "sa" if sa_flag else "nsa"
    fig.savefig(f"{OUTDIR}/ba_vs_metros_redfin_{suffix}.png", facecolor=BG, bbox_inches='tight')
    fig.savefig(f"{OUTDIR}/ba_vs_metros_redfin_{suffix}.svg", facecolor=BG, bbox_inches='tight')
    plt.close()
    print(f"Saved ba_vs_metros_redfin_{suffix}")


# ════════════════════════════════════════════
# PART 2: REDFIN — Recent YoY ranking table
# ════════════════════════════════════════════

def redfin_recent_ranking(sa_flag):
    """Rank metros by most recent YoY median sale price change."""
    sa_label = "SA" if sa_flag else "NSA"
    df = con.execute(f"""
        SELECT REGION as metro, PERIOD_BEGIN as date,
               MEDIAN_SALE_PRICE_YOY, MEDIAN_PPSF_YOY
        FROM '{REDFIN_METRO}'
        WHERE PROPERTY_TYPE = 'All Residential'
          AND IS_SEASONALLY_ADJUSTED = {sa_flag}
          AND PERIOD_BEGIN = (
              SELECT MAX(PERIOD_BEGIN) FROM '{REDFIN_METRO}'
              WHERE PROPERTY_TYPE = 'All Residential'
                AND IS_SEASONALLY_ADJUSTED = {sa_flag}
                AND MEDIAN_SALE_PRICE_YOY IS NOT NULL
          )
        ORDER BY MEDIAN_SALE_PRICE_YOY DESC
    """).df()
    return df, sa_label


# ════════════════════════════════════════════
# PART 3: ZILLOW ZHVI — indexed growth chart
# ════════════════════════════════════════════

def plot_zillow_indexed():
    """Zillow ZHVI metro data — index to Jan 2019 = 100, plot through latest."""
    # Zillow is wide format — unpivot
    df_raw = con.execute(f"""
        SELECT * FROM '{ZILLOW_METRO}'
    """).df()

    # Get date columns
    id_cols = ['RegionID', 'SizeRank', 'RegionName', 'RegionType', 'StateName']
    date_cols = [c for c in df_raw.columns if c not in id_cols]

    df_long = df_raw.melt(id_vars=id_cols, value_vars=date_cols,
                           var_name='date', value_name='zhvi')
    df_long['date'] = pd.to_datetime(df_long['date'])
    df_long = df_long[df_long['date'] >= '2019-01-01'].copy()
    df_long['zhvi'] = pd.to_numeric(df_long['zhvi'], errors='coerce')

    # Map Zillow metro names to match
    zillow_ba = ['San Francisco, CA', 'San Jose, CA', 'Oakland, CA']
    zillow_compare = [
        'New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Houston, TX',
        'Dallas, TX', 'Atlanta, GA', 'Miami, FL', 'Phoenix, AZ',
        'Seattle, WA', 'Boston, MA', 'Denver, CO', 'Austin, TX',
        'Nashville, TN', 'Portland, OR', 'Minneapolis, MN', 'Charlotte, NC',
        'San Diego, CA', 'Tampa, FL', 'Washington, DC', 'Detroit, MI',
    ]

    # Check which names actually exist
    available = set(df_long['RegionName'].unique())

    # Try matching
    def find_metro(name, available):
        if name in available:
            return name
        # Try partial match
        base = name.split(',')[0]
        matches = [a for a in available if base in a]
        return matches[0] if matches else None

    ba_map = {}
    for m in zillow_ba:
        found = find_metro(m, available)
        if found:
            ba_map[found] = m

    comp_map = {}
    for m in zillow_compare:
        found = find_metro(m, available)
        if found:
            comp_map[found] = m

    # Index to Jan 2019
    def index_series(group):
        base_val = group.loc[group['date'].dt.to_period('M') == '2019-01', 'zhvi']
        if len(base_val) > 0 and base_val.values[0] > 0:
            group['indexed'] = group['zhvi'] / base_val.values[0] * 100
        else:
            group['indexed'] = np.nan
        return group

    all_metros_z = list(ba_map.keys()) + list(comp_map.keys())
    df_sub = df_long[df_long['RegionName'].isin(all_metros_z)].copy()
    df_sub = df_sub.groupby('RegionName', group_keys=False).apply(index_series)

    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Comparison in gray
    for m in comp_map:
        mdf = df_sub[df_sub['RegionName'] == m].sort_values('date')
        if len(mdf) > 0:
            ax.plot(mdf['date'], mdf['indexed'], color='#C0C0C0', alpha=0.3, linewidth=0.8)

    # BA metros
    ba_colors_z = {}
    ba_labels_z = {}
    color_list = [BLUE, GREEN, RED]
    for i, (k, v) in enumerate(ba_map.items()):
        ba_colors_z[k] = color_list[i]
        ba_labels_z[k] = v.split(',')[0]

    for m in ba_map:
        mdf = df_sub[df_sub['RegionName'] == m].sort_values('date')
        if len(mdf) > 0:
            ax.plot(mdf['date'], mdf['indexed'], color=ba_colors_z[m],
                    linewidth=2.5, label=ba_labels_z[m], zorder=5)

    ax.axhline(y=100, color=BLACK, linewidth=0.5, alpha=0.5, linestyle='--')
    ax.legend(loc='upper left', frameon=False, fontsize=10)

    ax.set_title("Bay Area vs. Major US Metros: Home Value Growth\n(Zillow ZHVI, Indexed Jan 2019 = 100)",
                 fontsize=14, fontweight='bold', color=BLACK, pad=15)

    ax.grid(axis='y', color='#E0E0E0', linewidth=0.5)
    ax.grid(axis='x', visible=False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.set_xlabel('')
    ax.set_ylabel('')

    fig.text(0.12, 0.02, "Source: Zillow ZHVI (middle tier, seasonally adjusted)",
             fontsize=8, fontstyle='italic', color='gray')

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(f"{OUTDIR}/ba_vs_metros_zillow_indexed.png", facecolor=BG, bbox_inches='tight')
    fig.savefig(f"{OUTDIR}/ba_vs_metros_zillow_indexed.svg", facecolor=BG, bbox_inches='tight')
    plt.close()
    print("Saved ba_vs_metros_zillow_indexed")

    return df_sub


# ════════════════════════════════════════════
# PART 4: REDFIN — Percentile rank chart
# ════════════════════════════════════════════

def plot_redfin_percentile_rank():
    """
    For each month, rank all metros by YoY price change.
    Show where BA metros fall in the distribution.
    """
    df = con.execute(f"""
        SELECT PERIOD_BEGIN as date, REGION as metro,
               MEDIAN_SALE_PRICE_YOY as yoy
        FROM '{REDFIN_METRO}'
        WHERE PROPERTY_TYPE = 'All Residential'
          AND IS_SEASONALLY_ADJUSTED = False
          AND PERIOD_BEGIN >= '2019-01-01'
          AND MEDIAN_SALE_PRICE_YOY IS NOT NULL
    """).df()
    df['date'] = pd.to_datetime(df['date'])

    # Compute percentile rank per month
    def pct_rank(group):
        group['pct_rank'] = group['yoy'].rank(pct=True) * 100
        return group

    df = df.groupby('date', group_keys=False).apply(pct_rank)

    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Shade regions
    ax.axhspan(0, 25, color=LIGHT_RED, alpha=0.3)
    ax.axhspan(75, 100, color=LIGHT_GREEN, alpha=0.3)
    ax.axhline(y=50, color=BLACK, linewidth=0.5, alpha=0.3, linestyle='--')

    ba_colors = {BA_METROS[0]: BLUE, BA_METROS[1]: GREEN, BA_METROS[2]: RED}
    ba_labels = {"San Francisco, CA metro area": "San Francisco",
                 "San Jose, CA metro area": "San Jose",
                 "Oakland, CA metro area": "Oakland"}

    for m in BA_METROS:
        mdf = df[df['metro'] == m].sort_values('date')
        if len(mdf) > 0:
            ax.plot(mdf['date'], mdf['pct_rank'], color=ba_colors[m],
                    linewidth=2.5, label=ba_labels[m], zorder=5)

    ax.set_ylim(0, 100)
    ax.legend(loc='upper right', frameon=False, fontsize=10)

    ax.set_title("Bay Area: Percentile Rank Among All US Metros\n(YoY Median Sale Price Change, Redfin NSA)",
                 fontsize=14, fontweight='bold', color=BLACK, pad=15)

    # Labels for shaded regions
    ax.text(df['date'].min(), 87, "Top quartile", fontsize=9, color=GREEN, alpha=0.7)
    ax.text(df['date'].min(), 12, "Bottom quartile", fontsize=9, color=RED, alpha=0.7)

    ax.grid(axis='y', color='#E0E0E0', linewidth=0.5)
    ax.grid(axis='x', visible=False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.set_xlabel('')
    ax.set_ylabel('')

    fig.text(0.12, 0.02, "Source: Redfin monthly metro data (not seasonally adjusted)",
             fontsize=8, fontstyle='italic', color='gray')

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(f"{OUTDIR}/ba_percentile_rank.png", facecolor=BG, bbox_inches='tight')
    fig.savefig(f"{OUTDIR}/ba_percentile_rank.svg", facecolor=BG, bbox_inches='tight')
    plt.close()
    print("Saved ba_percentile_rank")


# ════════════════════════════════════════════
# PART 5: Summary stats
# ════════════════════════════════════════════

def print_summary_stats():
    """Print key numbers for the analysis."""
    # Most recent Redfin NSA data
    df_recent = con.execute(f"""
        WITH latest AS (
            SELECT MAX(PERIOD_BEGIN) as max_date
            FROM '{REDFIN_METRO}'
            WHERE PROPERTY_TYPE = 'All Residential'
              AND IS_SEASONALLY_ADJUSTED = False
              AND MEDIAN_SALE_PRICE_YOY IS NOT NULL
        )
        SELECT r.REGION as metro, r.PERIOD_BEGIN as date,
               r.MEDIAN_SALE_PRICE, r.MEDIAN_SALE_PRICE_YOY,
               r.MEDIAN_PPSF_YOY
        FROM '{REDFIN_METRO}' r, latest l
        WHERE r.PROPERTY_TYPE = 'All Residential'
          AND r.IS_SEASONALLY_ADJUSTED = False
          AND r.PERIOD_BEGIN = l.max_date
          AND r.MEDIAN_SALE_PRICE_YOY IS NOT NULL
        ORDER BY r.MEDIAN_SALE_PRICE_YOY DESC
    """).df()

    print("\n" + "="*70)
    print(f"MOST RECENT REDFIN DATA: {df_recent['date'].iloc[0]}")
    print("="*70)

    # BA metros
    print("\nBAY AREA METROS:")
    for m in BA_METROS:
        row = df_recent[df_recent['metro'] == m]
        if len(row) > 0:
            yoy = row['MEDIAN_SALE_PRICE_YOY'].values[0]
            price = row['MEDIAN_SALE_PRICE'].values[0]
            rank = (df_recent['MEDIAN_SALE_PRICE_YOY'] >= yoy).sum()
            total = len(df_recent)
            pct = rank / total * 100
            print(f"  {m}: YoY={yoy*100:.1f}%, Price=${price:,.0f}, "
                  f"Rank {rank}/{total} (top {pct:.0f}%)")

    # Distribution stats
    med = df_recent['MEDIAN_SALE_PRICE_YOY'].median() * 100
    p25 = df_recent['MEDIAN_SALE_PRICE_YOY'].quantile(0.25) * 100
    p75 = df_recent['MEDIAN_SALE_PRICE_YOY'].quantile(0.75) * 100
    print(f"\nALL METROS DISTRIBUTION: Median={med:.1f}%, P25={p25:.1f}%, P75={p75:.1f}%")

    # Top 10
    print("\nTOP 10 METROS BY YoY PRICE CHANGE:")
    for _, row in df_recent.head(10).iterrows():
        print(f"  {row['metro']}: {row['MEDIAN_SALE_PRICE_YOY']*100:.1f}%")

    # Bottom 10
    print("\nBOTTOM 10 METROS BY YoY PRICE CHANGE:")
    for _, row in df_recent.tail(10).iterrows():
        print(f"  {row['metro']}: {row['MEDIAN_SALE_PRICE_YOY']*100:.1f}%")

    # 6-month trend for BA
    print("\n\nBA 6-MONTH TREND (Redfin NSA):")
    for m in BA_METROS:
        trend = con.execute(f"""
            SELECT PERIOD_BEGIN as date, MEDIAN_SALE_PRICE_YOY as yoy
            FROM '{REDFIN_METRO}'
            WHERE PROPERTY_TYPE = 'All Residential'
              AND IS_SEASONALLY_ADJUSTED = False
              AND REGION = '{m}'
              AND MEDIAN_SALE_PRICE_YOY IS NOT NULL
            ORDER BY PERIOD_BEGIN DESC
            LIMIT 6
        """).df()
        trend = trend.sort_values('date')
        vals = [f"{v*100:.1f}%" for v in trend['yoy']]
        dates = [d.strftime('%b') for d in pd.to_datetime(trend['date'])]
        print(f"  {m}:")
        print(f"    {' → '.join(dates)}")
        print(f"    {' → '.join(vals)}")


# ════════════════════════════════════════════
# RUN
# ════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating Redfin YoY charts (SA and NSA)...")
    plot_redfin_yoy_comparison(sa_flag=True)
    plot_redfin_yoy_comparison(sa_flag=False)

    print("\nGenerating Zillow indexed growth chart...")
    plot_zillow_indexed()

    print("\nGenerating percentile rank chart...")
    plot_redfin_percentile_rank()

    print("\nSummary statistics...")
    print_summary_stats()

    print("\nDone.")
