import duckdb
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.dates as mdates
from datetime import datetime, timedelta

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# Colors
COLORS = {
    'Childcare': '#67A275',
    'Housework': '#DADFCE',
    'TV & Leisure': '#FEC439',
    'Work': '#0BB4FF',
    'Socializing': '#FBCAB5',
    'Travel': '#999999',
    'Eating & Drinking': '#E8A87C',
    'Sleep & Grooming': '#D4D4D4',
    'Education': '#B8A9C9',
    'Shopping': '#F4743B',
    'Sports & Exercise': '#C6DCCB',
    'Religious': '#FFE0B2',
    'Volunteering': '#A8D8EA',
    'Phone Calls': '#D5C4A1',
    'Prof. Services': '#BCAAA4',
    'Other': '#EDEFE7',
}
BG = '#F6F7F3'
BLACK = '#3D3733'

con = duckdb.connect()

# Activity mapping — all major categories
activity_map = """
    CASE
        WHEN ACTIVITY // 10000 = 1 THEN 'Sleep & Grooming'
        WHEN ACTIVITY // 10000 IN (2, 9) THEN 'Housework'
        WHEN ACTIVITY // 10000 IN (3, 4, 10) THEN 'Childcare'
        WHEN ACTIVITY // 10000 = 5 THEN 'Work'
        WHEN ACTIVITY // 10000 = 6 THEN 'Education'
        WHEN ACTIVITY // 10000 = 7 THEN 'Shopping'
        WHEN ACTIVITY // 10000 = 8 THEN 'Prof. Services'
        WHEN ACTIVITY // 10000 = 11 THEN 'Eating & Drinking'
        WHEN ACTIVITY // 100 IN (1201, 1202) THEN 'Socializing'
        WHEN ACTIVITY // 100 IN (1203, 1204, 1205, 1299) THEN 'TV & Leisure'
        WHEN ACTIVITY // 10000 = 13 THEN 'Sports & Exercise'
        WHEN ACTIVITY // 10000 = 14 THEN 'Religious'
        WHEN ACTIVITY // 10000 = 15 THEN 'Volunteering'
        WHEN ACTIVITY // 10000 = 16 THEN 'Phone Calls'
        WHEN ACTIVITY // 10000 = 18 THEN 'Travel'
        ELSE 'Other'
    END
"""

# Compute time-of-day activity shares using DuckDB
print("Computing time-of-day shares via DuckDB...")

n_bins = 144
categories = ['Childcare', 'Housework', 'TV & Leisure', 'Work', 'Socializing',
              'Eating & Drinking', 'Travel', 'Sleep & Grooming', 'Education',
              'Shopping', 'Sports & Exercise', 'Religious', 'Volunteering',
              'Phone Calls', 'Prof. Services', 'Other']

# Explode each activity into 10-min bins in SQL, then aggregate
bin_df = con.execute(f"""
    WITH activities AS (
        SELECT
            {activity_map} as act_cat,
            (EXTRACT(HOUR FROM CAST(START AS TIME)) * 60 + EXTRACT(MINUTE FROM CAST(START AS TIME)))::INT as start_min,
            DURATION::INT as dur,
            CAST(WT06 AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD < 999 THEN 1 ELSE 0 END as is_parent
        FROM 'data/atus_ipums.parquet'
        WHERE AGE BETWEEN 25 AND 54
    ),
    exploded AS (
        SELECT
            act_cat,
            ((start_min + slot_offset) % 1440) // 10 as bin_idx,
            wt,
            is_parent
        FROM activities, UNNEST(GENERATE_SERIES(0, dur - 1, 10)) as t(slot_offset)
    )
    SELECT
        bin_idx,
        is_parent,
        act_cat,
        SUM(wt) as total_wt
    FROM exploded
    GROUP BY bin_idx, is_parent, act_cat
""").df()

# Also get total weight per bin per parent status (all activities)
total_df = con.execute(f"""
    WITH activities AS (
        SELECT
            (EXTRACT(HOUR FROM CAST(START AS TIME)) * 60 + EXTRACT(MINUTE FROM CAST(START AS TIME)))::INT as start_min,
            DURATION::INT as dur,
            CAST(WT06 AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD < 999 THEN 1 ELSE 0 END as is_parent
        FROM 'data/atus_ipums.parquet'
        WHERE AGE BETWEEN 25 AND 54
    ),
    exploded AS (
        SELECT
            ((start_min + slot_offset) % 1440) // 10 as bin_idx,
            wt,
            is_parent
        FROM activities, UNNEST(GENERATE_SERIES(0, dur - 1, 10)) as t(slot_offset)
    )
    SELECT bin_idx, is_parent, SUM(wt) as total_wt
    FROM exploded
    GROUP BY bin_idx, is_parent
""").df()

# Pivot into arrays
totals_all = {0: np.zeros(n_bins), 1: np.zeros(n_bins)}
for _, row in total_df.iterrows():
    totals_all[int(row['is_parent'])][int(row['bin_idx'])] = row['total_wt']

act_totals = {0: {c: np.zeros(n_bins) for c in categories}, 1: {c: np.zeros(n_bins) for c in categories}}
for _, row in bin_df.iterrows():
    cat = row['act_cat']
    if cat in categories:
        act_totals[int(row['is_parent'])][cat][int(row['bin_idx'])] = row['total_wt']

# Compute shares and differences
shares = {}
for cat in categories:
    parent_share = np.where(totals_all[1] > 0, act_totals[1][cat] / totals_all[1], 0)
    nonparent_share = np.where(totals_all[0] > 0, act_totals[0][cat] / totals_all[0], 0)
    shares[cat] = (parent_share - nonparent_share) * 100  # percentage points

# Reorder bins to start at 4am (bin 0 = midnight, so 4am = bin 24)
reorder = list(range(24, 144)) + list(range(0, 24))
for cat in categories:
    shares[cat] = shares[cat][reorder]

# Debug: print ranges
for cat in categories:
    print(f"  {cat:20s}  min={shares[cat].min():.1f}pp  max={shares[cat].max():.1f}pp")

# Time axis: 4am to 4am
times = [datetime(2024, 1, 1, 4, 0) + timedelta(minutes=i*10) for i in range(144)]

# Plot — matching original stacking exactly
print("Plotting...")
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

# === POSITIVE STACK (parents do more) ===
pos_bottom = np.zeros(n_bins)
labeled = set()

# Only show these 7 categories
show_cats = ['Childcare', 'Housework', 'Travel', 'Eating & Drinking',
             'Sleep & Grooming', 'TV & Leisure', 'Work']

pos_order = ['Childcare', 'Housework', 'Travel', 'Eating & Drinking', 'Sleep & Grooming']
for cat in pos_order:
    vals = np.maximum(shares[cat], 0)
    ax.fill_between(times, pos_bottom, pos_bottom + vals,
                    color=COLORS[cat], alpha=0.85, label=cat, linewidth=0.3, edgecolor='white')
    labeled.add(cat)
    pos_bottom += vals

# === NEGATIVE STACK (parents do less) ===
neg_bottom = np.zeros(n_bins)

neg_order = ['TV & Leisure', 'Work', 'Travel', 'Eating & Drinking', 'Sleep & Grooming']
for cat in neg_order:
    vals = np.minimum(shares[cat], 0)
    lbl = cat if cat not in labeled else None
    ax.fill_between(times, neg_bottom + vals, neg_bottom,
                    color=COLORS[cat], alpha=0.85, label=lbl, linewidth=0.3, edgecolor='white')
    neg_bottom += vals

# Zero line
ax.axhline(y=0, color=BLACK, linewidth=0.8, alpha=0.5)

# Set explicit axis limits
ax.set_ylim(-13, 17)
ax.set_xlim(times[0], times[-1])

# Format x-axis
ax.xaxis.set_major_formatter(mdates.DateFormatter('%-I%p'))
ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
plt.xticks(fontsize=9, color=BLACK)

# Y-axis formatting
ax.set_ylabel('')
yticks_vals = [-10, -5, 0, 5, 10, 15]
ax.set_yticks(yticks_vals)
ax.set_yticklabels([f'{int(y):+d}pp' if y != 0 else '0' for y in yticks_vals], fontsize=9, color=BLACK)
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=3, color='#999999')

# Grid
ax.yaxis.grid(True, alpha=0.2, color='#999999', linewidth=0.5)
ax.xaxis.grid(False)
ax.set_axisbelow(True)

# Spines
for spine in ax.spines.values():
    spine.set_visible(False)

# Title
ax.set_title('The parent time swap: childcare in, TV out', fontsize=16, fontweight='bold',
             color=BLACK, loc='left', pad=30, fontfamily='ABC Oracle Edu')
ax.text(0, 1.02, 'Difference in activity share: parents minus non-parents, by time of day',
        transform=ax.transAxes, fontsize=10, color='#888888', fontfamily='ABC Oracle Edu')

# Annotations
# Find childcare peak (including housework stacked on top)
cc_pos = np.maximum(shares['Childcare'], 0)
hw_pos = np.maximum(shares['Housework'], 0)
peak_idx = np.argmax(cc_pos + hw_pos)
peak_time = times[peak_idx]
peak_val = (cc_pos + hw_pos)[peak_idx]

ax.annotate(f'Childcare peak\n+{peak_val:.0f}pp',
            xy=(peak_time, peak_val), xytext=(peak_time + timedelta(hours=0.5), peak_val + 1),
            fontsize=8, color='#67A275', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#67A275', lw=1))

# Find TV trough
tv_neg = np.minimum(shares['TV & Leisure'], 0)
work_neg = np.minimum(shares['Work'], 0)
trough_idx = np.argmin(tv_neg + work_neg)
trough_time = times[trough_idx]
trough_val = (tv_neg + work_neg)[trough_idx]

ax.annotate(f'TV deficit\n{trough_val:.0f}pp',
            xy=(trough_time, tv_neg[trough_idx]),
            xytext=(trough_time - timedelta(hours=0.5), trough_val + 1),
            fontsize=8, color='#C5A200', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#C5A200', lw=1))

# Legend — only show the 5 main categories (Travel/Eating blend visually)
legend = ax.legend(loc='upper right', frameon=False, fontsize=9,
                   labelcolor=BLACK, handlelength=1.5, handleheight=1)

# Source
fig.text(0.05, 0.02, 'Source: American Time Use Survey (2003-2023), respondents aged 25-54',
         fontsize=7, color='#999999', fontstyle='italic', fontfamily='ABC Oracle Edu')

plt.subplots_adjust(left=0.08, right=0.95, top=0.88, bottom=0.10)

# Save SVG
outpath = '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_RepublicanHappiness/outputs/schedule_difference.svg'
fig.savefig(outpath, format='svg', facecolor=BG)
print(f"Saved to {outpath}")

# Also save PNG for preview
fig.savefig(outpath.replace('.svg', '_preview.png'), dpi=200, facecolor=BG)
print("Done!")
