#!/usr/bin/env python3
"""
Stacked area chart: % falling (bottom) vs % rising (top)
With step/bar-like appearance
"""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/01_07_2026_PriceDeviation"

# Load and process ZIP data
print("Loading ZIP data...")
df = pd.read_parquet("/Users/azizsunderji/Dropbox/Home Economics/Data/Price/Zillow/zillow_zhvi_zip.parquet")

# Get date columns
date_cols = [c for c in df.columns if c.startswith('20') or c.startswith('19')]
date_cols = sorted(date_cols)

# Melt to long format
id_cols = [c for c in df.columns if c not in date_cols]
df_long = df.melt(id_vars=id_cols, value_vars=date_cols, var_name='date', value_name='zhvi')
df_long['date'] = pd.to_datetime(df_long['date'])
df_long = df_long.dropna(subset=['zhvi'])

# Compute YoY change for each region
df_long = df_long.sort_values(['RegionID', 'date'])
df_long['yoy_change'] = df_long.groupby('RegionID')['zhvi'].pct_change(periods=12) * 100
df_long = df_long.dropna(subset=['yoy_change'])

# Convert to quarterly for stepped look
df_long['quarter'] = df_long['date'].dt.to_period('Q')

quarterly_stats = df_long.groupby('quarter').agg(
    count=('yoy_change', 'count'),
    pct_positive=('yoy_change', lambda x: (x > 0).mean() * 100),
    pct_negative=('yoy_change', lambda x: (x < 0).mean() * 100),
).reset_index()

quarterly_stats = quarterly_stats[quarterly_stats['count'] >= 1000]
quarterly_stats['date'] = quarterly_stats['quarter'].dt.to_timestamp()

print(f"Date range: {quarterly_stats['date'].min().strftime('%Y-Q%q')} to {quarterly_stats['date'].max().strftime('%Y-%m')}")

# Create chart with stacked bars
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

dates = quarterly_stats['date']
pct_down = quarterly_stats['pct_negative']
pct_up = quarterly_stats['pct_positive']

# Calculate bar width (roughly 92 days for quarterly, no gaps)
bar_width = 92

# Stacked bars: falling on bottom (black), rising on top (blue)
ax.bar(dates, pct_down, width=bar_width, color='#3D3733', label='Price Decreasing', linewidth=0)
ax.bar(dates, pct_up, width=bar_width, bottom=pct_down, color='#0BB4FF', label='Price Increasing', linewidth=0)

ax.axhline(y=50, color='#3D3733', linewidth=1, linestyle='--', alpha=0.3)

ax.set_ylim(0, 100)
ax.set_title('Share of ZIP Codes with Rising vs Falling Prices\n(Year-over-Year)', fontsize=16, fontweight='bold', color='#3D3733', pad=20)
ax.tick_params(axis='y', length=0, colors='#3D3733')
ax.tick_params(axis='x', colors='#3D3733')
ax.yaxis.grid(True, linestyle='-', alpha=0.3, color='#3D3733')
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.legend(loc='lower left', frameon=False)
fig.text(0.99, 0.01, 'Source: Zillow Home Value Index', ha='right', va='bottom', fontsize=9, color='#666666', style='italic')

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/pct_up_down_stacked_v2.png", facecolor='#F6F7F3', edgecolor='none', bbox_inches='tight')
print("Saved: pct_up_down_stacked_v2.png")
plt.close()

# Print latest stats
latest = quarterly_stats.iloc[-1]
print(f"\nLatest ({latest['quarter']}): {latest['pct_positive']:.1f}% rising, {latest['pct_negative']:.1f}% falling")
