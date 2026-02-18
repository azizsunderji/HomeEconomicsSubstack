#!/usr/bin/env python3
"""
Create chart showing median annual home price appreciation by MSA with ±1 std dev band
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

# Load master file and filter to MSA data
print("Loading FHFA master data...")
master = pd.read_parquet("/Users/azizsunderji/Dropbox/Home Economics/Data/Price/FHFA/hpi_master.parquet")
msa = master[(master['level'] == 'MSA') & (master['hpi_flavor'] == 'all-transactions')]
print(f"MSA records: {len(msa):,}")

# For each MSA and year, compute YoY annual change using Q3 index values (Q3 2025 is most recent)
msa_q3 = msa[msa['period'] == 3].copy()
msa_q3 = msa_q3.sort_values(['place_id', 'yr'])
msa_q3['yoy_change'] = msa_q3.groupby('place_id')['index_nsa'].pct_change() * 100

# Calculate median and std by year
annual_stats = msa_q3.groupby('yr')['yoy_change'].agg(['median', 'std']).dropna()
print(f"Years with data: {annual_stats.index.min()} - {annual_stats.index.max()}")

# Create chart
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

years = annual_stats.index
median = annual_stats['median']
std = annual_stats['std']

# Shaded band (±1 std)
ax.fill_between(years, median - std, median + std, color='#0BB4FF', alpha=0.2, label='±1 Std Dev')

# Median line
ax.plot(years, median, color='#0BB4FF', linewidth=2.5, label='Median')

# Zero reference line
ax.axhline(y=0, color='#3D3733', linewidth=0.8, linestyle='--', alpha=0.5)

# Styling
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_title('Annual Home Price Appreciation by Metro Area', fontsize=16, fontweight='bold', color='#3D3733', pad=20)

# Remove y-axis tick marks, keep x-axis
ax.tick_params(axis='y', length=0, colors='#3D3733')
ax.tick_params(axis='x', colors='#3D3733')

# Y-axis formatting - % only on top label
def format_yticks(ax):
    yticks = ax.get_yticks()
    yticklabels = [f'{int(y)}' if i < len(yticks)-1 else f'{int(y)}%' for i, y in enumerate(yticks)]
    ax.set_yticklabels(yticklabels)

ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, pos: f'{int(y)}%' if pos == len(ax.get_yticks())-1 else f'{int(y)}'))

# Grid - extend to left edge
ax.yaxis.grid(True, linestyle='-', alpha=0.3, color='#3D3733')
ax.set_axisbelow(True)

# Spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)

# Source
fig.text(0.99, 0.01, 'Source: FHFA House Price Index', ha='right', va='bottom', fontsize=9, color='#666666', style='italic')

# Legend
ax.legend(loc='upper right', frameon=False)

plt.tight_layout()

output_path = "/Users/azizsunderji/Dropbox/Home Economics/01_07_2026_PriceDeviation/msa_price_appreciation_median_std.png"
plt.savefig(output_path, facecolor='#F6F7F3', edgecolor='none', bbox_inches='tight')
print(f"Chart saved to: {output_path}")
