"""
Austin vs National rent trajectory (Zillow ZORI).
Year-over-year % change in rents, highlighting the Austin supply boom divergence.
"""

import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# Color palette
BLACK = '#3D3733'
BLUE = '#0BB4FF'
RED = '#F4743B'
BACKGROUND = '#F6F7F3'
CREAM = '#DADFCE'

# Load ZORI data
DATA_PATH = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_20_SunderjisParadox/data/zillow_zori_metro.csv"
OUT_SVG = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_20_SunderjisParadox/outputs/austin_vs_national_rent_yoy.svg"
OUT_PNG = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_20_SunderjisParadox/outputs/austin_vs_national_rent_yoy.png"

df = pd.read_csv(DATA_PATH)

# Extract Austin and National rows
date_cols = [c for c in df.columns if '-' in c and c[:4].isdigit()]
national = df[df['RegionName'] == 'United States'][date_cols].iloc[0]
austin = df[df['RegionName'] == 'Austin, TX'][date_cols].iloc[0]

# Convert to time series
dates = pd.to_datetime(date_cols)
nat_series = pd.Series(national.values.astype(float), index=dates)
aus_series = pd.Series(austin.values.astype(float), index=dates)

# Compute YoY % change (need 12 months of data)
nat_yoy = nat_series.pct_change(periods=12) * 100
aus_yoy = aus_series.pct_change(periods=12) * 100

# Drop first 12 months (NaN)
nat_yoy = nat_yoy.dropna()
aus_yoy = aus_yoy.dropna()

# Create figure
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BACKGROUND)
ax.set_facecolor(BACKGROUND)

# Zero line
ax.axhline(y=0, color=BLACK, linewidth=0.5, alpha=0.3)

# Plot lines
ax.plot(nat_yoy.index, nat_yoy.values, color=BLACK, linewidth=2, label='National', zorder=3)
ax.plot(aus_yoy.index, aus_yoy.values, color=BLUE, linewidth=2.5, label='Austin, TX', zorder=4)

# Shade the supply boom period (2022-2024) where Austin rents fell
boom_start = pd.Timestamp('2022-08-01')
boom_end = aus_yoy.index[-1]
ax.axvspan(boom_start, boom_end, alpha=0.08, color=BLUE, zorder=1)
ax.text(pd.Timestamp('2023-06-01'), ax.get_ylim()[1] * 0.85, 'Supply boom\nperiod',
        fontsize=9, color=BLUE, ha='center', va='top', alpha=0.8)

# Labels at end of lines
last_nat = nat_yoy.iloc[-1]
last_aus = aus_yoy.iloc[-1]
ax.text(nat_yoy.index[-1] + pd.Timedelta(days=15), last_nat, f'National\n{last_nat:+.1f}%',
        fontsize=9, color=BLACK, va='center')
ax.text(aus_yoy.index[-1] + pd.Timedelta(days=15), last_aus, f'Austin\n{last_aus:+.1f}%',
        fontsize=9, color=BLUE, va='center')

# Y-axis formatting
yticks = range(-10, 25, 5)
ax.set_yticks(yticks)
ax.set_yticklabels([f'{y}%' if y == max(yticks) else str(y) for y in yticks])
ax.set_ylim(-12, 22)

# Grid and spines
ax.yaxis.grid(True, color='white', linewidth=1.2)
ax.xaxis.grid(False)
ax.set_axisbelow(True)

for spine in ['top', 'right', 'left']:
    ax.spines[spine].set_visible(False)
ax.spines['bottom'].set_color(BLACK)
ax.spines['bottom'].set_linewidth(0.5)

ax.tick_params(axis='y', length=0, labelcolor=BLACK)
ax.tick_params(axis='x', colors=BLACK)

# Title and subtitle
ax.set_title("Austin rents boomed, then crashed. National rents kept climbing.",
             fontsize=13, fontweight='bold', color=BLACK, pad=25)
fig.text(0.5, 0.915, "Year-over-year change in Zillow Observed Rent Index (ZORI), 2016-2026",
         ha='center', fontsize=10, color='#888888')

# Source
fig.text(0.5, 0.02,
         'Source: Zillow Research, ZORI (smoothed, all homes, metro level). Jan 2016 - Jan 2026.',
         ha='center', fontsize=8, color='#888888', style='italic')

plt.tight_layout()
plt.subplots_adjust(bottom=0.08, top=0.88)

plt.savefig(OUT_SVG, format='svg', facecolor=BACKGROUND, edgecolor='none', bbox_inches='tight')
plt.savefig(OUT_PNG, format='png', facecolor=BACKGROUND, edgecolor='none', bbox_inches='tight', dpi=150)
print(f"Saved to {OUT_SVG}")

# Print key data points
print(f"\nAustin peak YoY: {aus_yoy.max():.1f}% ({aus_yoy.idxmax().strftime('%Y-%m')})")
print(f"Austin trough YoY: {aus_yoy.min():.1f}% ({aus_yoy.idxmin().strftime('%Y-%m')})")
print(f"Austin latest: {last_aus:.1f}%")
print(f"National latest: {last_nat:.1f}%")
