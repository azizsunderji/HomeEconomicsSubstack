#!/usr/bin/env python3
"""
Charts exploring whether current market shows unusual dispersion:
1. Standard deviation over time
2. Coefficient of variation (std / median) over time
3. Stacked area: % going up vs % going down
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

df_long['year_month'] = df_long['date'].dt.to_period('M')

print(f"Processing {df_long['RegionID'].nunique():,} ZIP codes...")

# Compute monthly stats
monthly_stats = df_long.groupby('year_month').agg(
    median=('yoy_change', 'median'),
    std=('yoy_change', 'std'),
    count=('yoy_change', 'count'),
    pct_positive=('yoy_change', lambda x: (x > 0).mean() * 100),
    pct_negative=('yoy_change', lambda x: (x < 0).mean() * 100),
    pct_flat=('yoy_change', lambda x: (x == 0).mean() * 100)
).reset_index()

monthly_stats = monthly_stats[monthly_stats['count'] >= 1000]  # Require sufficient coverage
monthly_stats['date'] = monthly_stats['year_month'].dt.to_timestamp()
monthly_stats['coef_var'] = monthly_stats['std'] / monthly_stats['median'].abs()

print(f"Date range: {monthly_stats['date'].min().strftime('%Y-%m')} to {monthly_stats['date'].max().strftime('%Y-%m')}")

# === CHART 1: Standard Deviation Over Time ===
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

ax.plot(monthly_stats['date'], monthly_stats['std'], color='#0BB4FF', linewidth=2.5)
ax.axhline(y=monthly_stats['std'].median(), color='#3D3733', linewidth=1, linestyle='--', alpha=0.5, label=f"Historical median: {monthly_stats['std'].median():.1f}")

ax.set_title('Standard Deviation of Annual Price Changes\nAcross ZIP Codes', fontsize=16, fontweight='bold', color='#3D3733', pad=20)
ax.tick_params(axis='y', length=0, colors='#3D3733')
ax.tick_params(axis='x', colors='#3D3733')
ax.yaxis.grid(True, linestyle='-', alpha=0.3, color='#3D3733')
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.legend(loc='upper right', frameon=False)
fig.text(0.99, 0.01, 'Source: Zillow Home Value Index', ha='right', va='bottom', fontsize=9, color='#666666', style='italic')

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/std_dev_over_time.png", facecolor='#F6F7F3', edgecolor='none', bbox_inches='tight')
print("Saved: std_dev_over_time.png")
plt.close()

# === CHART 2: Coefficient of Variation Over Time ===
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

ax.plot(monthly_stats['date'], monthly_stats['coef_var'], color='#0BB4FF', linewidth=2.5)

ax.set_title('Coefficient of Variation (Std Dev / |Median|)\nof Annual Price Changes', fontsize=16, fontweight='bold', color='#3D3733', pad=20)
ax.tick_params(axis='y', length=0, colors='#3D3733')
ax.tick_params(axis='x', colors='#3D3733')
ax.yaxis.grid(True, linestyle='-', alpha=0.3, color='#3D3733')
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
fig.text(0.99, 0.01, 'Source: Zillow Home Value Index', ha='right', va='bottom', fontsize=9, color='#666666', style='italic')

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/coef_var_over_time.png", facecolor='#F6F7F3', edgecolor='none', bbox_inches='tight')
print("Saved: coef_var_over_time.png")
plt.close()

# === CHART 3: Stacked Area - % Going Up vs Down ===
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

dates = monthly_stats['date']
pct_up = monthly_stats['pct_positive']
pct_down = monthly_stats['pct_negative']

ax.fill_between(dates, 0, pct_up, color='#0BB4FF', alpha=0.7, label='Price Increasing')
ax.fill_between(dates, pct_up, 100, color='#F4743B', alpha=0.7, label='Price Decreasing')

ax.axhline(y=50, color='#3D3733', linewidth=1, linestyle='--', alpha=0.5)

ax.set_ylim(0, 100)
ax.set_title('Share of ZIP Codes with Rising vs Falling Prices\n(Year-over-Year)', fontsize=16, fontweight='bold', color='#3D3733', pad=20)
ax.tick_params(axis='y', length=0, colors='#3D3733')
ax.tick_params(axis='x', colors='#3D3733')
ax.yaxis.grid(True, linestyle='-', alpha=0.3, color='#3D3733')
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.legend(loc='upper right', frameon=False)
fig.text(0.99, 0.01, 'Source: Zillow Home Value Index', ha='right', va='bottom', fontsize=9, color='#666666', style='italic')

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/pct_up_down_stacked.png", facecolor='#F6F7F3', edgecolor='none', bbox_inches='tight')
print("Saved: pct_up_down_stacked.png")
plt.close()

# Print current stats
latest = monthly_stats.iloc[-1]
print(f"\n=== Latest ({latest['date'].strftime('%Y-%m')}) ===")
print(f"  Median YoY change: {latest['median']:.1f}%")
print(f"  Std Dev: {latest['std']:.1f}")
print(f"  Coef of Var: {latest['coef_var']:.2f}")
print(f"  % Rising: {latest['pct_positive']:.1f}%")
print(f"  % Falling: {latest['pct_negative']:.1f}%")

print("\nDone!")
