#!/usr/bin/env python3
"""
Create charts showing median annual home price appreciation with ±1 std dev band
Using Zillow ZHVI data for Metro and ZIP levels
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

def load_and_process_zillow(filepath, geo_type):
    """Load Zillow wide-format data and compute YoY changes"""
    print(f"Loading {geo_type} data...")
    df = pd.read_parquet(filepath)

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

    # Get year-month and aggregate stats
    df_long['year_month'] = df_long['date'].dt.to_period('M')

    monthly_stats = df_long.groupby('year_month')['yoy_change'].agg(['median', 'std', 'count']).dropna()
    monthly_stats = monthly_stats[monthly_stats['count'] >= 50]  # Require at least 50 regions
    monthly_stats.index = monthly_stats.index.to_timestamp()

    print(f"  Date range: {monthly_stats.index.min().strftime('%Y-%m')} to {monthly_stats.index.max().strftime('%Y-%m')}")
    print(f"  Regions with data: {df_long['RegionID'].nunique():,}")

    return monthly_stats

def create_chart(stats, geo_type, output_path):
    """Create the median + std dev band chart"""
    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor('#F6F7F3')
    ax.set_facecolor('#F6F7F3')

    dates = stats.index
    median = stats['median']
    std = stats['std']

    # Shaded band (±1 std)
    ax.fill_between(dates, median - std, median + std, color='#0BB4FF', alpha=0.2, label='±1 Std Dev')

    # Median line
    ax.plot(dates, median, color='#0BB4FF', linewidth=2.5, label='Median')

    # Zero reference line
    ax.axhline(y=0, color='#3D3733', linewidth=0.8, linestyle='--', alpha=0.5)

    # Styling
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_title(f'Annual Home Price Appreciation by {geo_type}', fontsize=16, fontweight='bold', color='#3D3733', pad=20)

    # Remove y-axis tick marks, keep x-axis
    ax.tick_params(axis='y', length=0, colors='#3D3733')
    ax.tick_params(axis='x', colors='#3D3733')

    # Grid - extend to left edge
    ax.yaxis.grid(True, linestyle='-', alpha=0.3, color='#3D3733')
    ax.set_axisbelow(True)

    # Spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    # Source
    fig.text(0.99, 0.01, 'Source: Zillow Home Value Index', ha='right', va='bottom', fontsize=9, color='#666666', style='italic')

    # Legend
    ax.legend(loc='upper right', frameon=False)

    plt.tight_layout()
    plt.savefig(output_path, facecolor='#F6F7F3', edgecolor='none', bbox_inches='tight')
    print(f"Chart saved: {output_path}")
    plt.close()

# Process Metro data
metro_stats = load_and_process_zillow(
    "/Users/azizsunderji/Dropbox/Home Economics/Data/Price/Zillow/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.parquet",
    "Metro"
)
create_chart(metro_stats, "Metro Area",
             "/Users/azizsunderji/Dropbox/Home Economics/01_07_2026_PriceDeviation/zillow_metro_appreciation.png")

# Process ZIP data
zip_stats = load_and_process_zillow(
    "/Users/azizsunderji/Dropbox/Home Economics/Data/Price/Zillow/zillow_zhvi_zip.parquet",
    "ZIP"
)
create_chart(zip_stats, "ZIP Code",
             "/Users/azizsunderji/Dropbox/Home Economics/01_07_2026_PriceDeviation/zillow_zip_appreciation.png")

print("\nDone!")
