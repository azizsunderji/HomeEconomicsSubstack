"""
Scatter: Population growth vs High-rise unit growth (2010-2024)
Shows whether metros are densifying faster than they're growing.
Points above the 1:1 line = building up faster than population demands.
"""

import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import time

# ============================================================================
# FONT SETUP
# ============================================================================

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    try:
        fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
    except:
        pass
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# ============================================================================
# COLORS
# ============================================================================

BLUE = "#0BB4FF"
YELLOW = "#FEC439"
RED = "#F4743B"
GREEN = "#67A275"
BLACK = "#3D3733"
BG_CREAM = "#F6F7F3"
CREAM = "#DADFCE"
LIGHT_GREEN = "#C6DCCB"

DATA_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_04_BuildingUp/data"
OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_04_BuildingUp/outputs"
API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"

# ============================================================================
# PULL POPULATION DATA
# ============================================================================

def pull_pop(year):
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {
        "get": "NAME,B01003_001E",
        "for": "metropolitan statistical area/micropolitan statistical area:*",
        "key": API_KEY
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    geo_col = [c for c in df.columns if 'metropolitan' in c.lower()]
    df = df.rename(columns={geo_col[0]: 'CBSA'})
    df['B01003_001E'] = pd.to_numeric(df['B01003_001E'], errors='coerce')
    df = df.rename(columns={'B01003_001E': f'pop_{year}'})
    df['CBSA'] = df['CBSA'].astype(str)
    return df[['CBSA', f'pop_{year}']]

print("Pulling population data...")
pop_2010 = pull_pop(2010)
time.sleep(1)
pop_2024 = pull_pop(2024)

# ============================================================================
# MERGE WITH HIGHRISE DATA
# ============================================================================

hr = pd.read_csv(f"{DATA_DIR}/highrise_units_all_metros.csv")
hr['CBSA'] = hr['CBSA'].astype(str)

hr = hr.merge(pop_2024, on='CBSA', how='left')
hr = hr.merge(pop_2010, on='CBSA', how='left')
hr = hr.dropna(subset=['pop_2024', 'pop_2010'])
hr = hr[hr['highrise_units_2010'] > 0]

hr['pop_growth_pct'] = (hr['pop_2024'] - hr['pop_2010']) / hr['pop_2010'] * 100
hr['hr_growth_pct'] = hr['highrise_growth'] / hr['highrise_units_2010'] * 100

# Focus on metros with pop > 500K in 2024 and reasonable growth ranges
df = hr[hr['pop_2024'] >= 500_000].copy()
df = df[(df['pop_growth_pct'] > -10) & (df['pop_growth_pct'] < 80)]
df = df[df['hr_growth_pct'] < 200]

print(f"Metros in chart: {len(df)}")

# ============================================================================
# CATEGORIZE
# ============================================================================

sunbelt_cities = ['Dallas', 'Houston', 'Phoenix', 'Atlanta', 'Austin', 'San Antonio',
                  'Nashville', 'Charlotte', 'Orlando', 'Tampa', 'Jacksonville', 'Raleigh',
                  'Las Vegas', 'San Antonio']
coastal_cities = ['New York', 'Los Angeles', 'Chicago', 'San Francisco', 'Boston',
                  'Philadelphia', 'Seattle', 'Washington', 'Minneapolis', 'Miami',
                  'Denver', 'Portland']

def categorize(name):
    for city in sunbelt_cities:
        if city in name:
            return 'Sun Belt'
    for city in coastal_cities:
        if city in name:
            return 'Coastal/Legacy'
    return 'Other'

def short_name(name):
    return name.split('-')[0].split(',')[0].strip()

df['category'] = df['metro_name'].apply(categorize)
df['city'] = df['metro_name'].apply(short_name)

# ============================================================================
# PLOT
# ============================================================================

print("Creating chart...")

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100, facecolor=BG_CREAM)
ax.set_facecolor(BG_CREAM)

# 1:1 reference line
max_val = max(df['pop_growth_pct'].max(), df['hr_growth_pct'].max()) * 1.1
ax.plot([-10, max_val], [-10, max_val], color=BLACK, linewidth=0.8, alpha=0.3,
        linestyle='--', zorder=1)

# Label the 1:1 line
ax.text(52, 48, '1:1 line', fontsize=7, color=BLACK, alpha=0.4, rotation=28,
        style='italic')

# Plot each category
for cat, color, marker, size in [
    ('Other', CREAM, 'o', 30),
    ('Coastal/Legacy', BLUE, 's', 50),
    ('Sun Belt', YELLOW, 'D', 55),
]:
    subset = df[df['category'] == cat]
    ax.scatter(subset['pop_growth_pct'], subset['hr_growth_pct'],
               c=color, edgecolors=BLACK, linewidth=0.6, s=size,
               marker=marker, zorder=3 if cat != 'Other' else 2,
               label=cat, alpha=0.95)

# Label Sun Belt and Coastal cities
label_cities = df[df['category'].isin(['Sun Belt', 'Coastal/Legacy'])].copy()

# Manual nudges for overlapping labels
nudges = {
    'New York': (1, -6),
    'Los Angeles': (1, -6),
    'Chicago': (1.5, 2),
    'Dallas': (-1, 3),
    'Houston': (1.5, 2),
    'Washington': (1, -6),
    'Philadelphia': (1.5, 2),
    'Atlanta': (1.5, 2),
    'Miami': (1, -6),
    'Phoenix': (-1, 3),
    'Boston': (1.5, 2),
    'San Francisco': (-1, -6),
    'Seattle': (1.5, 2),
    'Minneapolis': (1.5, 2),
    'Tampa': (1.5, 2),
    'Austin': (1.5, 2),
    'San Antonio': (1.5, 2),
    'Nashville': (1.5, 2),
    'Charlotte': (1.5, 2),
    'Orlando': (1.5, 2),
    'Las Vegas': (1.5, 2),
    'Denver': (1.5, 2),
    'Portland': (1.5, 2),
    'Raleigh': (1.5, 2),
}

for _, row in label_cities.iterrows():
    dx, dy = nudges.get(row['city'], (1.5, 2))
    ax.annotate(row['city'], (row['pop_growth_pct'], row['hr_growth_pct']),
                xytext=(dx, dy), textcoords='offset points',
                fontsize=6.5, color=BLACK, fontweight='medium',
                zorder=5)

# Axes
ax.set_xlabel('Population growth, 2010–2024 (%)', fontsize=10, color=BLACK, labelpad=8)
ax.set_ylabel('High-rise unit growth, 2010–2024 (%)', fontsize=10, color=BLACK, labelpad=8)

# Title
ax.text(0, 1.08, 'Building up faster than growing out', transform=ax.transAxes,
        fontsize=16, fontweight='bold', color=BLACK, va='bottom')
ax.text(0, 1.03, 'High-rise unit growth vs. population growth in major U.S. metros, 2010–2024',
        transform=ax.transAxes, fontsize=9, color=BLACK, alpha=0.7, va='bottom')

# Gridlines
ax.grid(axis='y', color='white', linewidth=0.8, zorder=0)
ax.grid(axis='x', color='white', linewidth=0.8, zorder=0)
ax.set_axisbelow(True)

# Spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color(BLACK)
ax.spines['bottom'].set_linewidth(0.5)

# Ticks
ax.tick_params(axis='both', colors=BLACK, labelsize=8)
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=3)

# Y-axis: only top label gets %
yticks = ax.get_yticks()
ylabels = [f'{int(t)}' for t in yticks]
if len(ylabels) > 0:
    ylabels[-1] = f'{int(yticks[-1])}%'
ax.set_yticklabels(ylabels)

# X-axis labels with %
xticks = ax.get_xticks()
ax.set_xticklabels([f'{int(t)}%' for t in xticks])

# Legend
legend = ax.legend(loc='upper left', frameon=False, fontsize=8, labelspacing=0.8)
for text in legend.get_texts():
    text.set_color(BLACK)

# Annotation: above the line
ax.text(5, 115, 'Above line = densifying\nfaster than growing',
        fontsize=7, color=BLACK, alpha=0.5, style='italic',
        ha='left', va='top')

# Source
ax.text(0, -0.08, 'Source: Census Bureau ACS 5-Year Estimates, Table B25024 (Units in Structure)',
        transform=ax.transAxes, fontsize=6.5, color=BLACK, alpha=0.4, style='italic')

plt.tight_layout()

output_path = f"{OUTPUT_DIR}/densification_scatter.png"
plt.savefig(output_path, dpi=200, facecolor=BG_CREAM, bbox_inches='tight', pad_inches=0.3)
print(f"Saved: {output_path}")

plt.close()
print("Done!")
