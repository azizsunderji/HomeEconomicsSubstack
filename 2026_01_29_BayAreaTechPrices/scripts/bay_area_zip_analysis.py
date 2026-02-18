"""
Zip code level analysis: Information sector employment vs SFR home prices
Bay Area granular analysis (Aug–Dec 2025)
"""

import pandas as pd
import numpy as np
import duckdb
import requests
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D
import time

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# Colors
BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
RED = '#F4743B'
GREEN = '#67A275'
YELLOW = '#FEC439'

API_KEY = '06048dc3bd32068702b5ef9b49875ec0c5ca56ce'

print("=" * 70)
print("STEP 1: Loading Zillow zip code price data")
print("=" * 70)

# Get Zillow ZHVI data (Aug–Dec 2025, all home types, all 94/95 CA zips)
query = '''
SELECT
    CAST(RegionName AS VARCHAR) as zip,
    City,
    Metro,
    "2025-08-31" as price_aug,
    "2025-12-31" as price_dec,
    ("2025-12-31" - "2025-08-31") / "2025-08-31" * 100 as change_aug_dec
FROM read_csv_auto('/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/data/Zip_zhvi_all_types_sm_sa_month.csv')
WHERE StateName = 'CA'
  AND (CAST(RegionName AS VARCHAR) LIKE '94%' OR CAST(RegionName AS VARCHAR) LIKE '95%')
  AND "2025-12-31" IS NOT NULL
  AND "2025-08-31" IS NOT NULL
'''
zillow_df = duckdb.query(query).df()
print(f"Loaded {len(zillow_df)} zip codes from Zillow ZHVI")

print("\n" + "=" * 70)
print("STEP 2: Fetching ACS industry data for zip codes")
print("=" * 70)

# Get ACS data in batches
all_zips = zillow_df['zip'].tolist()
batch_size = 50
acs_results = []

for i in range(0, len(all_zips), batch_size):
    batch = all_zips[i:i+batch_size]
    zip_str = ','.join(batch)
    url = f"https://api.census.gov/data/2023/acs/acs5/subject?get=NAME,S2403_C01_001E,S2403_C01_012E&for=zip%20code%20tabulation%20area:{zip_str}&key={API_KEY}"

    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            for row in data[1:]:  # Skip header
                acs_results.append({
                    'zip': row[3],
                    'total_emp': int(row[1]) if row[1] else 0,
                    'info_emp': int(row[2]) if row[2] else 0
                })
        print(f"  Batch {i//batch_size + 1}: fetched {len(data)-1} zips")
    except Exception as e:
        print(f"  Batch {i//batch_size + 1}: error - {e}")
    time.sleep(0.2)  # Rate limiting

acs_df = pd.DataFrame(acs_results)
print(f"\nTotal ACS records: {len(acs_df)}")

# Calculate info sector percentage
acs_df['info_pct'] = np.where(acs_df['total_emp'] > 0,
                               acs_df['info_emp'] / acs_df['total_emp'] * 100,
                               np.nan)

print("\n" + "=" * 70)
print("STEP 3: Merging datasets")
print("=" * 70)

# Merge
df = zillow_df.merge(acs_df, on='zip', how='inner')
df = df.dropna(subset=['info_pct', 'change_aug_dec'])
df = df[df['total_emp'] >= 500]  # Filter for statistical reliability

print(f"Merged dataset: {len(df)} zip codes with valid data")

# Correlation
corr = df['info_pct'].corr(df['change_aug_dec'])
print(f"\nCorrelation (Info sector % vs 6-mo price change): r = {corr:.3f}")

print("\n" + "=" * 70)
print("TOP 20 ZIPS BY INFO SECTOR CONCENTRATION")
print("=" * 70)
top_info = df.nlargest(20, 'info_pct')
print(f"{'Zip':>6} {'City':20} {'Info%':>8} {'Aug-Dec':>10} {'Price':>12}")
print("-" * 60)
for _, row in top_info.iterrows():
    city = str(row['City'])[:18] if row['City'] else 'Unknown'
    print(f"{row['zip']:>6} {city:20} {row['info_pct']:7.1f}% {row['change_aug_dec']:+9.1f}% ${row['price_dec']/1e6:>9.2f}M")

print("\n" + "=" * 70)
print("TOP 20 ZIPS BY PRICE APPRECIATION")
print("=" * 70)
top_price = df.nlargest(20, 'change_aug_dec')
print(f"{'Zip':>6} {'City':20} {'Info%':>8} {'Aug-Dec':>10} {'Price':>12}")
print("-" * 60)
for _, row in top_price.iterrows():
    city = str(row['City'])[:18] if row['City'] else 'Unknown'
    print(f"{row['zip']:>6} {city:20} {row['info_pct']:7.1f}% {row['change_aug_dec']:+9.1f}% ${row['price_dec']/1e6:>9.2f}M")

# Create scatter plot
print("\n" + "=" * 70)
print("STEP 4: Creating visualization")
print("=" * 70)

fig, ax = plt.subplots(figsize=(9, 7.5))
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Color by metro area
colors = np.where(df['Metro'].str.contains('San Jose'), GREEN, BLUE)

# Size by current price (normalized)
min_price, max_price = df['price_dec'].min(), df['price_dec'].max()
sizes = 50 + (df['price_dec'] - min_price) / (max_price - min_price) * 300

scatter = ax.scatter(
    df['info_pct'],
    df['change_aug_dec'],
    s=sizes,
    c=colors,
    alpha=0.7,
    edgecolors=BLACK,
    linewidth=0.5,
    zorder=5
)

# Label notable zips
notable_zips = {
    '94027': 'Atherton',
    '94022': 'Los Altos',
    '94041': 'Mountain View',
    '94301': 'Palo Alto',
    '94114': 'SF Castro',
    '95014': 'Cupertino',
    '94040': 'Mountain View',
    '94028': 'Portola Valley',
    '94025': 'Menlo Park',
    '94024': 'Los Altos Hills',
}

for _, row in df.iterrows():
    if row['zip'] in notable_zips:
        ax.annotate(
            notable_zips[row['zip']],
            xy=(row['info_pct'], row['change_aug_dec']),
            xytext=(row['info_pct'] + 0.5, row['change_aug_dec'] + 0.3),
            fontsize=8,
            color=BLACK,
            zorder=10
        )

# Trend line
z = np.polyfit(df['info_pct'], df['change_aug_dec'], 1)
p = np.poly1d(z)
x_line = np.linspace(0, df['info_pct'].max() + 1, 100)
ax.plot(x_line, p(x_line), '--', color=RED, alpha=0.7, linewidth=2, label=f'Trend (r={corr:.2f})')

ax.axhline(y=0, color=BLACK, linewidth=0.8, alpha=0.4)

# Styling
ax.set_xlabel('Information Sector Employment (%)', fontsize=11, color=BLACK)
ax.set_ylabel('Price Change, Aug–Dec 2025 (%)', fontsize=11, color=BLACK)
ax.set_title('Bay Area Zip Codes: Tech Industry vs Home Prices', fontsize=14, fontweight='bold', color=BLACK, pad=15)

ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(colors=BLACK)

# Legend
legend_handles = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor=BLUE, markersize=10, alpha=0.7, markeredgecolor=BLACK, label='SF-Oakland Metro'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor=GREEN, markersize=10, alpha=0.7, markeredgecolor=BLACK, label='San Jose Metro'),
]
ax.legend(handles=legend_handles, loc='lower right', frameon=False, fontsize=9)

# Source
ax.text(0.01, -0.10, 'Source: Zillow ZHVI (Dec 2025), ACS 2023 5-Year Estimates',
        transform=ax.transAxes, fontsize=8, color='#888888', style='italic')

plt.tight_layout()
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/outputs/bay_area_zip_info_vs_prices.png',
            dpi=100, bbox_inches='tight', facecolor=BG_CREAM)
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/outputs/bay_area_zip_info_vs_prices.svg',
            bbox_inches='tight', facecolor=BG_CREAM)
print("\nChart saved to outputs/bay_area_zip_info_vs_prices.png")

# Save data
df.to_csv('/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/data/bay_area_zip_analysis.csv', index=False)
print("Data saved to data/bay_area_zip_analysis.csv")
