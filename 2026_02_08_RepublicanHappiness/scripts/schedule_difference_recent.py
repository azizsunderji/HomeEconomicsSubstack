"""
Schedule difference chart: parents of young kids (AGEYCHILD <= 5) vs non-parents
Filters: ages 25-54, weekdays only, employed (EMPSTAT IN (1,2))
"""
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
    'Sleep': '#D4D4D4',
    'Education': '#B8A9C9',
    'Shopping': '#F4743B',
    'Sports & Exercise': '#C6DCCB',
    'Religious': '#FFE0B2',
    'Volunteering': '#A8D8EA',
    'Phone Calls': '#D5C4A1',
    'Prof. Services': '#BCAAA4',
    'Grooming': '#D4D4D4',
    'Other': '#EDEFE7',
}
BG = '#F6F7F3'
BLACK = '#3D3733'

con = duckdb.connect()

# Activity mapping — all major categories
activity_map = """
    CASE
        WHEN ACTIVITY // 100 IN (101, 102) THEN 'Sleep'
        WHEN ACTIVITY // 10000 = 1 THEN 'Grooming'
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

# Filters:
# - Ages 25-54
# - Weekdays only (DAY 2-6: Mon-Fri)
# - Employed (EMPSTAT IN (1,2))
# - Parents: AGEYCHILD <= 5 (youngest child 0-5)
# - Non-parents: AGEYCHILD >= 999 (no children)
base_filter = "AGE BETWEEN 25 AND 54 AND DAY BETWEEN 2 AND 6 AND EMPSTAT IN (1,2) AND YEAR IN (2023, 2024)"
parent_filter = f"{base_filter} AND AGEYCHILD <= 5"
nonparent_filter = f"{base_filter} AND AGEYCHILD >= 999"

print("Computing time-of-day shares via DuckDB...")
print(f"Filters: weekdays, employed, ages 25-54")
print(f"Parents: youngest child <= 5 | Non-parents: no children")

n_bins = 48  # 30-min bins for smaller sample
categories = ['Childcare', 'Housework', 'TV & Leisure', 'Work', 'Socializing',
              'Eating & Drinking', 'Travel', 'Sleep', 'Education',
              'Shopping', 'Sports & Exercise', 'Religious', 'Volunteering',
              'Phone Calls', 'Prof. Services', 'Grooming', 'Other']

# Compute for parents (young kids)
bin_df_parent = con.execute(f"""
    WITH activities AS (
        SELECT
            {activity_map} as act_cat,
            (EXTRACT(HOUR FROM CAST(START AS TIME)) * 60 + EXTRACT(MINUTE FROM CAST(START AS TIME)))::INT as start_min,
            DURATION::INT as dur,
            CAST(WT06 AS DOUBLE) as wt
        FROM 'data/atus_ipums.parquet'
        WHERE {parent_filter}
    ),
    exploded AS (
        SELECT act_cat, ((start_min + slot_offset) % 1440) // 30 as bin_idx, wt
        FROM activities, UNNEST(GENERATE_SERIES(0, dur - 1, 30)) as t(slot_offset)
    )
    SELECT bin_idx, act_cat, SUM(wt) as total_wt
    FROM exploded GROUP BY bin_idx, act_cat
""").df()

total_parent = con.execute(f"""
    WITH activities AS (
        SELECT
            (EXTRACT(HOUR FROM CAST(START AS TIME)) * 60 + EXTRACT(MINUTE FROM CAST(START AS TIME)))::INT as start_min,
            DURATION::INT as dur, CAST(WT06 AS DOUBLE) as wt
        FROM 'data/atus_ipums.parquet'
        WHERE {parent_filter}
    ),
    exploded AS (
        SELECT ((start_min + slot_offset) % 1440) // 30 as bin_idx, wt
        FROM activities, UNNEST(GENERATE_SERIES(0, dur - 1, 30)) as t(slot_offset)
    )
    SELECT bin_idx, SUM(wt) as total_wt FROM exploded GROUP BY bin_idx
""").df()

# Compute for non-parents
bin_df_nonparent = con.execute(f"""
    WITH activities AS (
        SELECT
            {activity_map} as act_cat,
            (EXTRACT(HOUR FROM CAST(START AS TIME)) * 60 + EXTRACT(MINUTE FROM CAST(START AS TIME)))::INT as start_min,
            DURATION::INT as dur,
            CAST(WT06 AS DOUBLE) as wt
        FROM 'data/atus_ipums.parquet'
        WHERE {nonparent_filter}
    ),
    exploded AS (
        SELECT act_cat, ((start_min + slot_offset) % 1440) // 30 as bin_idx, wt
        FROM activities, UNNEST(GENERATE_SERIES(0, dur - 1, 30)) as t(slot_offset)
    )
    SELECT bin_idx, act_cat, SUM(wt) as total_wt
    FROM exploded GROUP BY bin_idx, act_cat
""").df()

total_nonparent = con.execute(f"""
    WITH activities AS (
        SELECT
            (EXTRACT(HOUR FROM CAST(START AS TIME)) * 60 + EXTRACT(MINUTE FROM CAST(START AS TIME)))::INT as start_min,
            DURATION::INT as dur, CAST(WT06 AS DOUBLE) as wt
        FROM 'data/atus_ipums.parquet'
        WHERE {nonparent_filter}
    ),
    exploded AS (
        SELECT ((start_min + slot_offset) % 1440) // 30 as bin_idx, wt
        FROM activities, UNNEST(GENERATE_SERIES(0, dur - 1, 30)) as t(slot_offset)
    )
    SELECT bin_idx, SUM(wt) as total_wt FROM exploded GROUP BY bin_idx
""").df()

# Print sample sizes
n_parent = con.execute(f"SELECT COUNT(DISTINCT CASEID) FROM 'data/atus_ipums.parquet' WHERE {parent_filter}").fetchone()[0]
n_nonparent = con.execute(f"SELECT COUNT(DISTINCT CASEID) FROM 'data/atus_ipums.parquet' WHERE {nonparent_filter}").fetchone()[0]
print(f"  Parents (child<=5): {n_parent:,} people")
print(f"  Non-parents: {n_nonparent:,} people")

# Pivot into arrays
tot_p = np.zeros(n_bins)
for _, row in total_parent.iterrows():
    tot_p[int(row['bin_idx'])] = row['total_wt']

tot_np = np.zeros(n_bins)
for _, row in total_nonparent.iterrows():
    tot_np[int(row['bin_idx'])] = row['total_wt']

act_p = {c: np.zeros(n_bins) for c in categories}
for _, row in bin_df_parent.iterrows():
    cat = row['act_cat']
    if cat in categories:
        act_p[cat][int(row['bin_idx'])] = row['total_wt']

act_np = {c: np.zeros(n_bins) for c in categories}
for _, row in bin_df_nonparent.iterrows():
    cat = row['act_cat']
    if cat in categories:
        act_np[cat][int(row['bin_idx'])] = row['total_wt']

# Compute shares and differences
shares = {}
for cat in categories:
    parent_share = np.where(tot_p > 0, act_p[cat] / tot_p, 0)
    nonparent_share = np.where(tot_np > 0, act_np[cat] / tot_np, 0)
    shares[cat] = (parent_share - nonparent_share) * 100

# Reorder bins to start at 4am
reorder = list(range(8, 48)) + list(range(0, 8))  # 4am = bin 8 for 30-min bins
for cat in categories:
    shares[cat] = shares[cat][reorder]

# Debug: print ranges
for cat in categories:
    print(f"  {cat:20s}  min={shares[cat].min():.1f}pp  max={shares[cat].max():.1f}pp")

# Time axis: 4am to 4am
times = [datetime(2024, 1, 1, 4, 0) + timedelta(minutes=i*30) for i in range(48)]

# Convert shares from pp to minutes per hour: pp * 60/100 = pp * 0.6
mins = {}
for cat in categories:
    mins[cat] = shares[cat] * 0.6  # minutes per hour

# Compute cumulative sleep deficit (minutes) across the day
# Each bin = 10 min. Sleep deficit at bin i = shares['Sleep'][i] / 100 * 10 minutes
sleep_deficit_per_bin = shares['Sleep'] / 100 * 30  # minutes lost per 30-min bin
cumulative_sleep = np.cumsum(sleep_deficit_per_bin)
total_sleep_deficit = cumulative_sleep[-1]
print(f"  Total daily sleep deficit: {total_sleep_deficit:.0f} minutes")

# Plot: two panels — main area chart + cumulative sleep below
print("Plotting...")
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(9, 9), dpi=100,
                               gridspec_kw={'height_ratios': [4, 1], 'hspace': 0.08},
                               sharex=True)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
ax2.set_facecolor(BG)

# === MAIN CHART (minutes per hour) ===
pos_bottom = np.zeros(n_bins)
labeled = set()

pos_order = ['Childcare', 'Housework', 'Travel', 'Eating & Drinking', 'Sleep']
for cat in pos_order:
    vals = np.maximum(mins[cat], 0)
    ax.fill_between(times, pos_bottom, pos_bottom + vals,
                    color=COLORS[cat], alpha=0.85, label=cat, linewidth=0.3, edgecolor='white')
    labeled.add(cat)
    pos_bottom += vals

neg_bottom = np.zeros(n_bins)
neg_order = ['TV & Leisure', 'Work', 'Travel', 'Eating & Drinking', 'Sleep']
for cat in neg_order:
    vals = np.minimum(mins[cat], 0)
    lbl = cat if cat not in labeled else None
    ax.fill_between(times, neg_bottom + vals, neg_bottom,
                    color=COLORS[cat], alpha=0.85, label=lbl, linewidth=0.3, edgecolor='white')
    neg_bottom += vals

# Zero line
ax.axhline(y=0, color=BLACK, linewidth=0.8, alpha=0.5)

# Y-axis for main chart (minutes per hour)
import math
y_lo = min(neg_bottom.min(), -1) * 1.1
y_hi = max(pos_bottom.max(), 1) * 1.1
ax.set_ylim(y_lo, y_hi)
ax.set_xlim(times[0], times[-1])

step = 3  # 3 minutes per hour increments
lo = int(math.floor(y_lo / step) * step)
hi = int(math.ceil(y_hi / step) * step)
yticks_vals = list(range(lo, hi + 1, step))
ax.set_yticks(yticks_vals)
ax.set_yticklabels([f'{y:+d} min' if y != 0 else '0' for y in yticks_vals], fontsize=9, color=BLACK)
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=0)  # hide x ticks on top panel

# Grid
ax.yaxis.grid(True, alpha=0.2, color='#999999', linewidth=0.5)
ax.xaxis.grid(False)
ax.set_axisbelow(True)

# Spines
for spine in ax.spines.values():
    spine.set_visible(False)

# Title
ax.set_title('The parent time swap (2023-2024)', fontsize=16, fontweight='bold',
             color=BLACK, loc='left', pad=30, fontfamily='ABC Oracle Edu')
ax.text(0, 1.02, 'Difference in time use per hour: parents (child \u22645) minus non-parents, weekdays, employed',
        transform=ax.transAxes, fontsize=10, color='#888888', fontfamily='ABC Oracle Edu')

# Annotations — childcare peak (in minutes)
cc_pos = np.maximum(mins['Childcare'], 0)
hw_pos = np.maximum(mins['Housework'], 0)
peak_idx = np.argmax(cc_pos + hw_pos)
peak_time = times[peak_idx]
peak_val = (cc_pos + hw_pos)[peak_idx]

ax.annotate(f'Childcare peak\n+{peak_val:.0f} min/hr',
            xy=(peak_time, peak_val), xytext=(peak_time + timedelta(hours=0.5), peak_val + 0.5),
            fontsize=8, color='#67A275', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#67A275', lw=1))

# TV trough
tv_neg = np.minimum(mins['TV & Leisure'], 0)
work_neg = np.minimum(mins['Work'], 0)
trough_idx = np.argmin(tv_neg + work_neg)
trough_time = times[trough_idx]
trough_val = (tv_neg + work_neg)[trough_idx]

ax.annotate(f'TV deficit\n{trough_val:.0f} min/hr',
            xy=(trough_time, tv_neg[trough_idx]),
            xytext=(trough_time - timedelta(hours=0.5), trough_val + 0.5),
            fontsize=8, color='#C5A200', fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#C5A200', lw=1))

# Legend
legend = ax.legend(loc='upper right', frameon=False, fontsize=9,
                   labelcolor=BLACK, handlelength=1.5, handleheight=1)

# === CUMULATIVE SLEEP DEFICIT PANEL (bars) ===
bar_width = timedelta(minutes=9)  # slightly less than 10-min bin for small gaps
bar_colors = [COLORS['Sleep'] if v < 0 else '#C6DCCB' for v in cumulative_sleep]
ax2.bar(times, cumulative_sleep, width=bar_width, color=bar_colors, alpha=0.6, linewidth=0)
ax2.axhline(y=0, color=BLACK, linewidth=0.5, alpha=0.3)

# Label the final deficit
ax2.annotate(f'{total_sleep_deficit:.0f} min',
             xy=(times[-1], cumulative_sleep[-1]),
             xytext=(times[-1] - timedelta(hours=1.5), cumulative_sleep[-1] - 8),
             fontsize=9, fontweight='bold', color=BLACK,
             arrowprops=dict(arrowstyle='->', color=BLACK, lw=1))

ax2.set_ylabel('Cumulative\nsleep deficit', fontsize=8, color='#888888', rotation=0,
               labelpad=50, va='center')
ax2.set_xlim(times[0], times[-1])

# Y formatting for sleep panel
ax2.tick_params(axis='y', length=0)
yticks2 = [int(cumulative_sleep.min() // 10) * 10, 0, int(cumulative_sleep.max() // 10 + 1) * 10]
ax2.set_yticks(yticks2)
ax2.set_yticklabels([f'{y:+d} min' if y != 0 else '0' for y in yticks2], fontsize=8, color=BLACK)

# X formatting on bottom panel
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%-I%p'))
ax2.xaxis.set_major_locator(mdates.HourLocator(interval=2))
ax2.tick_params(axis='x', length=3, color='#999999', labelsize=9)

ax2.yaxis.grid(True, alpha=0.2, color='#999999', linewidth=0.5)
ax2.xaxis.grid(False)
ax2.set_axisbelow(True)
for spine in ax2.spines.values():
    spine.set_visible(False)

# Source
fig.text(0.05, 0.02, f'Source: ATUS 2023-2024, ages 25-54, weekdays, employed (n={n_parent:,} parents, {n_nonparent:,} non-parents)',
         fontsize=7, color='#999999', fontstyle='italic', fontfamily='ABC Oracle Edu')

plt.subplots_adjust(left=0.10, right=0.95, top=0.90, bottom=0.07)

# Save
outpath = '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_RepublicanHappiness/outputs/schedule_difference_recent.svg'
fig.savefig(outpath, format='svg', facecolor=BG)
print(f"Saved SVG to {outpath}")

fig.savefig(outpath.replace('.svg', '.png'), dpi=200, facecolor=BG)
print("Saved PNG preview")
print("Done!")
