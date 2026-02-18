"""
05_charts.py
Publication-quality charts for Republican Happiness analysis.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Register Oracle fonts
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

DATA_DIR = '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_RepublicanHappiness/data'
OUT_DIR = '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_RepublicanHappiness/outputs'

# Colors
BLUE = '#0BB4FF'
RED = '#F4743B'
PURPLE = '#967BB6'
BLACK = '#3D3733'
BG = '#F6F7F3'
CREAM = '#DADFCE'

# =========================================================
# CHART 1: Happiness by activity x political lean (grouped bar)
# =========================================================
happy_df = pd.read_parquet(f'{DATA_DIR}/happiness_by_activity_lean.parquet')

# Pivot and sort by Red-Blue gap
pivot = happy_df.pivot(index='activity', columns='political_lean', values='mean_happiness')
pivot['gap'] = pivot['Red'] - pivot['Blue']
pivot = pivot.sort_values('gap', ascending=True)

# Shorten category names
name_map = {
    'Socializing & Leisure': 'Socializing & Leisure',
    'Caring for Household Members': 'Childcare',
    'Religious & Spiritual': 'Religious',
    'Sports & Exercise': 'Sports & Exercise',
    'Eating & Drinking': 'Eating & Drinking',
    'Telephone Calls': 'Phone Calls',
}
pivot.index = [name_map.get(x, x) for x in pivot.index]

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

y = np.arange(len(pivot))
bar_height = 0.25

ax.barh(y + bar_height, pivot['Blue'], height=bar_height, color=BLUE, label='Blue areas', zorder=3)
ax.barh(y, pivot['Purple'], height=bar_height, color=PURPLE, label='Purple areas', zorder=3)
ax.barh(y - bar_height, pivot['Red'], height=bar_height, color=RED, label='Red areas', zorder=3)

ax.set_yticks(y)
ax.set_yticklabels(pivot.index, fontsize=10, color=BLACK)
ax.set_xlabel('')
ax.set_xlim(3.0, 5.5)

# Gridlines
ax.xaxis.grid(True, color='white', linewidth=0.8, zorder=0)
ax.yaxis.grid(False)
ax.set_axisbelow(True)

# X-axis labels
xticks = ax.get_xticks()
ax.set_xticklabels([f'{x:.0f}' if i < len(xticks)-1 else f'{x:.0f} /6' for i, x in enumerate(xticks)],
                    fontsize=9, color=BLACK)

# Remove spines
for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=3, color='#999999')

# Title
ax.set_title('How happy are people during each activity?', fontsize=16, fontweight='bold',
             color=BLACK, loc='left', pad=30)
ax.text(0, 1.02, 'Average happiness score (0-6) by activity and county political lean',
        transform=ax.transAxes, fontsize=11, color='#666666')

# Legend
ax.legend(loc='lower right', frameon=False, fontsize=10)

# Source
fig.text(0.12, 0.02, 'Source: ATUS Well-Being Module (2010, 2012, 2013, 2021); 2020 presidential election results',
         fontsize=8, color='#999999', style='italic')

plt.tight_layout(rect=[0, 0.04, 1, 0.96])
plt.savefig(f'{OUT_DIR}/happiness_by_activity.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.savefig(f'{OUT_DIR}/happiness_by_activity.svg', bbox_inches='tight', facecolor=BG)
print("Saved happiness_by_activity.png/svg")
plt.close()


# =========================================================
# CHART 2: Decomposition waterfall
# =========================================================
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

# The two components
components = ['Composition\n(what people do)', 'Level\n(how happy doing it)', 'Total Gap']
values = [0.0053, 0.0611, 0.0665]
colors = [PURPLE, RED, BLACK]

# Waterfall: first two stack, third is total
bars = ax.bar([0, 1, 2.2], values, width=0.7, color=colors, zorder=3, edgecolor='white', linewidth=0.5)

# Add value labels
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.001,
            f'+{val:.3f}\n({val/0.0665*100:.0f}%)', ha='center', va='bottom',
            fontsize=11, color=BLACK, fontweight='bold')

ax.set_xticks([0, 1, 2.2])
ax.set_xticklabels(components, fontsize=11, color=BLACK)
ax.set_ylabel('')
ax.set_ylim(0, 0.095)

# Y-axis formatting
ax.set_yticks([0, 0.02, 0.04, 0.06, 0.08])
ax.set_yticklabels(['0', '0.02', '0.04', '0.06', '0.08 pts'], fontsize=9, color=BLACK)

# Gridlines
ax.yaxis.grid(True, color='white', linewidth=0.8, zorder=0)
ax.xaxis.grid(False)

for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=0)

ax.set_title('Why are red areas happier?', fontsize=16, fontweight='bold',
             color=BLACK, loc='left', pad=30)
ax.text(0, 1.02, 'Oaxaca decomposition of the Red-Blue happiness gap (0.066 points on 0-6 scale)',
        transform=ax.transAxes, fontsize=11, color='#666666')

fig.text(0.12, 0.02, 'Source: ATUS Well-Being Module; 2020 presidential election results',
         fontsize=8, color='#999999', style='italic')

plt.tight_layout(rect=[0, 0.04, 1, 0.96])
plt.savefig(f'{OUT_DIR}/decomposition_waterfall.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.savefig(f'{OUT_DIR}/decomposition_waterfall.svg', bbox_inches='tight', facecolor=BG)
print("Saved decomposition_waterfall.png/svg")
plt.close()


# =========================================================
# CHART 3: Time allocation comparison (grouped bar)
# =========================================================
time_df = pd.read_parquet(f'{DATA_DIR}/time_by_activity_lean.parquet')
pivot_time = time_df.pivot(index='activity', columns='political_lean', values='minutes_per_day')
pivot_time['diff'] = pivot_time['Red'] - pivot_time['Blue']
pivot_time = pivot_time.sort_values('diff', ascending=True)
pivot_time.index = [name_map.get(x, x) for x in pivot_time.index]

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

y = np.arange(len(pivot_time))
bar_height = 0.25

ax.barh(y + bar_height, pivot_time['Blue'], height=bar_height, color=BLUE, label='Blue areas', zorder=3)
ax.barh(y, pivot_time['Purple'], height=bar_height, color=PURPLE, label='Purple areas', zorder=3)
ax.barh(y - bar_height, pivot_time['Red'], height=bar_height, color=RED, label='Red areas', zorder=3)

ax.set_yticks(y)
ax.set_yticklabels(pivot_time.index, fontsize=10, color=BLACK)

# Gridlines
ax.xaxis.grid(True, color='white', linewidth=0.8, zorder=0)
ax.yaxis.grid(False)

for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=3, color='#999999')

# X-axis: show 'min' on top label
xticks = ax.get_xticks()
labels = [f'{int(x)}' for x in xticks]
if len(labels) > 0:
    labels[-1] = f'{int(xticks[-1])} min'
ax.set_xticklabels(labels, fontsize=9, color=BLACK)

ax.set_title('How long do people spend on each activity?', fontsize=16, fontweight='bold',
             color=BLACK, loc='left', pad=30)
ax.text(0, 1.02, 'Average minutes per day (among participants) by county political lean',
        transform=ax.transAxes, fontsize=11, color='#666666')

ax.legend(loc='lower right', frameon=False, fontsize=10)

fig.text(0.12, 0.02, 'Source: ATUS Well-Being Module (2010, 2012, 2013, 2021); 2020 presidential election results',
         fontsize=8, color='#999999', style='italic')

plt.tight_layout(rect=[0, 0.04, 1, 0.96])
plt.savefig(f'{OUT_DIR}/time_allocation.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.savefig(f'{OUT_DIR}/time_allocation.svg', bbox_inches='tight', facecolor=BG)
print("Saved time_allocation.png/svg")
plt.close()


# =========================================================
# CHART 4: Within-metro comparison (dot plot)
# =========================================================
metro_df = pd.read_parquet(f'{DATA_DIR}/within_metro_happiness.parquet')
metro_df = metro_df.sort_values('gap', ascending=True)

# Only show named metros
metro_df = metro_df[metro_df['metro_name'].apply(lambda x: not x.isdigit())]

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

y = np.arange(len(metro_df))

# Horizontal bars showing gap
colors = [RED if g > 0 else BLUE for g in metro_df['gap']]
ax.barh(y, metro_df['gap'], color=colors, height=0.6, zorder=3, alpha=0.8)

# Zero line
ax.axvline(x=0, color=BLACK, linewidth=0.8, zorder=2)

ax.set_yticks(y)
ax.set_yticklabels(metro_df['metro_name'], fontsize=10, color=BLACK)

# Gridlines
ax.xaxis.grid(True, color='white', linewidth=0.8, zorder=0)
ax.yaxis.grid(False)

for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=3, color='#999999')

# Add labels
ax.text(0.02, 0.01, '← Blue counties happier', transform=ax.transAxes,
        fontsize=9, color=BLUE, style='italic')
ax.text(0.98, 0.01, 'Red counties happier →', transform=ax.transAxes,
        fontsize=9, color=RED, style='italic', ha='right')

ax.set_title('Within-metro happiness gap: red vs. blue counties', fontsize=16, fontweight='bold',
             color=BLACK, loc='left', pad=30)
ax.text(0, 1.02, 'Difference in average happiness (red county minus blue county within same metro)',
        transform=ax.transAxes, fontsize=11, color='#666666')

fig.text(0.12, 0.02, 'Source: ATUS Well-Being Module; 2020 presidential election results',
         fontsize=8, color='#999999', style='italic')

plt.tight_layout(rect=[0, 0.05, 1, 0.96])
plt.savefig(f'{OUT_DIR}/within_metro_gap.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.savefig(f'{OUT_DIR}/within_metro_gap.svg', bbox_inches='tight', facecolor=BG)
print("Saved within_metro_gap.png/svg")
plt.close()


# =========================================================
# CHART 5: Scatter — county Trump share vs avg happiness
# =========================================================
atus = pd.read_parquet(f'{DATA_DIR}/atus_wb_politics.parquet')
county_only = atus[atus['geo_level'] == 'county']

# County-level aggregation
county_stats = county_only.groupby('county_fips').apply(
    lambda g: pd.Series({
        'trump_share': g['trump_share'].iloc[0],
        'mean_happy': np.average(g['SCHAPPY'], weights=g['AWBWT']),
        'n_people': g['CASEID'].nunique(),
    })
).reset_index()

# Only counties with enough sample
county_stats = county_stats[county_stats['n_people'] >= 10]

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

# Size by log population
sizes = np.clip(county_stats['n_people'] * 3, 10, 300)

# Color by Trump share
colors = [RED if ts > 50 else BLUE for ts in county_stats['trump_share']]
alphas = 0.5

ax.scatter(county_stats['trump_share'], county_stats['mean_happy'],
           s=sizes, c=colors, alpha=alphas, edgecolors='white', linewidth=0.3, zorder=3)

# Trend line
from numpy.polynomial import polynomial as P
mask = county_stats['trump_share'].notna() & county_stats['mean_happy'].notna()
z = np.polyfit(county_stats.loc[mask, 'trump_share'], county_stats.loc[mask, 'mean_happy'],
               1, w=np.sqrt(county_stats.loc[mask, 'n_people']))
p = np.poly1d(z)
x_line = np.linspace(10, 90, 100)
ax.plot(x_line, p(x_line), color=BLACK, linewidth=2, zorder=4, linestyle='--')

# Gridlines
ax.yaxis.grid(True, color='white', linewidth=0.8, zorder=0)
ax.xaxis.grid(True, color='white', linewidth=0.8, zorder=0)

for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=3, color='#999999')

# Axis labels
ax.set_xlabel('Trump 2020 vote share (%)', fontsize=11, color=BLACK)
xticks = ax.get_xticks()
ax.set_xticklabels([f'{int(x)}' if i < len(xticks)-1 else f'{int(x)}%' for i, x in enumerate(xticks)],
                    fontsize=9, color=BLACK)

yticks = ax.get_yticks()
ax.set_yticklabels([f'{y:.1f}' if i < len(yticks)-1 else f'{y:.1f} /6' for i, y in enumerate(yticks)],
                    fontsize=9, color=BLACK)

# Slope annotation
slope_per_10 = z[0] * 10
ax.text(0.98, 0.05, f'Slope: +{slope_per_10:.3f} per 10pp Trump share',
        transform=ax.transAxes, fontsize=9, color=BLACK, ha='right', style='italic')

ax.set_title('County Trump share vs. average happiness', fontsize=16, fontweight='bold',
             color=BLACK, loc='left', pad=30)
ax.text(0, 1.02, 'Each dot = one county, sized by ATUS sample. Dashed line = weighted linear fit.',
        transform=ax.transAxes, fontsize=11, color='#666666')

fig.text(0.12, 0.02, 'Source: ATUS Well-Being Module; 2020 presidential election results. Counties with n≥10.',
         fontsize=8, color='#999999', style='italic')

plt.tight_layout(rect=[0, 0.04, 1, 0.96])
plt.savefig(f'{OUT_DIR}/county_scatter.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.savefig(f'{OUT_DIR}/county_scatter.svg', bbox_inches='tight', facecolor=BG)
print("Saved county_scatter.png/svg")
plt.close()

print("\nAll charts saved to outputs/")
