"""
Bivariate Choropleth: Domestic vs International Migration (2024-2025)
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# Paths
DATA_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Data")
OUTPUT_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Explorations/2026_01_27_ComponentsofPopChange/outputs")

# =============================================================================
# COLOR SCHEME - Option 2: Simple Two-Tone
# =============================================================================
# Corners:
#   Blue (#0BB4FF) = high domestic, low international (domestic magnet)
#   Yellow (#FEC439) = low domestic, high international (immigrant gateway)
#   Green (#67A275) = high domestic, high international (winning both)
#   Cream (#DADFCE) = low domestic, low international (neither)

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))

def blend_colors(c1, c2, t):
    """Blend two RGB colors, t=0 gives c1, t=1 gives c2"""
    return tuple(c1[i] * (1-t) + c2[i] * t for i in range(3))

# Define corner colors
BLUE = hex_to_rgb('#0BB4FF')    # High domestic, Low international
YELLOW = hex_to_rgb('#FEC439')  # Low domestic, High international
GREEN = hex_to_rgb('#67A275')   # High domestic, High international
CREAM = hex_to_rgb('#E8EBE0')   # Low domestic, Low international (slightly darker than bg)

# Build 3x3 grid by blending
# Row 0 (low domestic): Cream -> blend -> Yellow
# Row 1 (med domestic): blend -> blend -> blend
# Row 2 (high domestic): Blue -> blend -> Green

def get_bivariate_color(dom_class, intl_class):
    """
    dom_class: 0 (low), 1 (med), 2 (high) - domestic migration
    intl_class: 0 (low), 1 (med), 2 (high) - international migration
    """
    # Blend along domestic axis first
    dom_t = dom_class / 2.0  # 0, 0.5, 1
    intl_t = intl_class / 2.0  # 0, 0.5, 1

    # Bottom row (low intl): CREAM to BLUE
    bottom = blend_colors(CREAM, BLUE, dom_t)
    # Top row (high intl): YELLOW to GREEN
    top = blend_colors(YELLOW, GREEN, dom_t)
    # Blend vertically
    final = blend_colors(bottom, top, intl_t)
    return rgb_to_hex(final)

# Pre-compute the 3x3 grid
COLOR_GRID = {}
for d in range(3):
    for i in range(3):
        COLOR_GRID[(d, i)] = get_bivariate_color(d, i)

print("Color grid (domestic rows, international cols):")
for d in [2, 1, 0]:  # Print high to low
    row = [COLOR_GRID[(d, i)] for i in range(3)]
    print(f"  Dom {d}: {row}")

# =============================================================================
# LOAD DATA
# =============================================================================

# Population estimates
pop = pd.read_parquet(DATA_DIR / "PopulationEstimates/state_v2025.parquet")

# Filter to states only
regions = ['United States', 'Northeast Region', 'Midwest Region', 'South Region',
           'West Region', 'Puerto Rico', 'Middle Atlantic', 'New England',
           'East North Central', 'West North Central', 'South Atlantic',
           'East South Central', 'West South Central', 'Mountain', 'Pacific']
states = pop[~pop['NAME'].isin(regions)].copy()

# Get 2025 components
states['domestic'] = states['DOMESTICMIG2025']
states['international'] = states['INTERNATIONALMIG2025']
states['pop'] = states['POPESTIMATE2024']

# Normalize by population (per 1000 residents)
states['domestic_rate'] = states['domestic'] / states['pop'] * 1000
states['international_rate'] = states['international'] / states['pop'] * 1000

print(f"\nDomestic rate range: {states['domestic_rate'].min():.1f} to {states['domestic_rate'].max():.1f} per 1000")
print(f"International rate range: {states['international_rate'].min():.1f} to {states['international_rate'].max():.1f} per 1000")

# =============================================================================
# CLASSIFY INTO 3x3 GRID
# =============================================================================

# Use terciles for classification
def classify_tercile(series):
    """Classify into 0, 1, 2 based on terciles"""
    q1 = series.quantile(0.33)
    q2 = series.quantile(0.67)
    return pd.cut(series, bins=[-np.inf, q1, q2, np.inf], labels=[0, 1, 2]).astype(int)

states['dom_class'] = classify_tercile(states['domestic_rate'])
states['intl_class'] = classify_tercile(states['international_rate'])

# Assign colors
states['color'] = states.apply(lambda r: COLOR_GRID[(r['dom_class'], r['intl_class'])], axis=1)

# Show classification
print("\nClassification:")
for _, row in states.sort_values('domestic_rate', ascending=False).iterrows():
    print(f"  {row['NAME']:20s}: dom={row['domestic_rate']:6.1f} ({row['dom_class']}), "
          f"intl={row['international_rate']:5.1f} ({row['intl_class']}) -> {row['color']}")

# =============================================================================
# LOAD SHAPEFILE AND MERGE
# =============================================================================

# State shapefile
shp_path = DATA_DIR / "Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp"
gdf = gpd.read_file(shp_path)

# Albers projection for continental US
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
gdf = gdf.to_crs(ALBERS)

# Exclude non-continental
exclude_fips = ['02', '15', '60', '66', '69', '72', '78']
gdf = gdf[~gdf['STATEFP'].isin(exclude_fips)]

# Merge with population data
states['STATEFP'] = states['STATE'].astype(str).str.zfill(2)
gdf = gdf.merge(states[['STATEFP', 'domestic_rate', 'international_rate',
                         'dom_class', 'intl_class', 'color']],
                on='STATEFP', how='left')

# =============================================================================
# CREATE MAP
# =============================================================================

fig, ax = plt.subplots(figsize=(12, 8), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

# Plot states with bivariate colors
for idx, row in gdf.iterrows():
    if pd.notna(row['color']):
        gdf[gdf.index == idx].plot(ax=ax, color=row['color'],
                                    edgecolor='white', linewidth=0.5)

# Styling
ax.set_xlim(gdf.total_bounds[0] - 100000, gdf.total_bounds[2] + 100000)
ax.set_ylim(gdf.total_bounds[1] - 100000, gdf.total_bounds[3] + 100000)
ax.set_aspect('equal')
ax.axis('off')

# Title
ax.set_title('Where Americans Are Moving\nDomestic vs. International Migration, Jul 2024 – Jul 2025',
             fontsize=16, fontweight='bold', color='#3D3733', pad=20)

# =============================================================================
# BIVARIATE LEGEND
# =============================================================================

# Create legend in bottom right
legend_size = 0.12  # Size as fraction of figure
legend_x = 0.82
legend_y = 0.15

# Add legend axes
legend_ax = fig.add_axes([legend_x, legend_y, legend_size, legend_size])
legend_ax.set_facecolor('#F6F7F3')

# Draw 3x3 grid
cell_size = 1/3
for d in range(3):
    for i in range(3):
        color = COLOR_GRID[(d, i)]
        rect = mpatches.Rectangle((i * cell_size, d * cell_size),
                                   cell_size, cell_size,
                                   facecolor=color, edgecolor='white', linewidth=0.5)
        legend_ax.add_patch(rect)

legend_ax.set_xlim(0, 1)
legend_ax.set_ylim(0, 1)
legend_ax.set_aspect('equal')
legend_ax.axis('off')

# Legend labels
legend_ax.text(0.5, -0.12, 'International →', ha='center', va='top', fontsize=9, color='#3D3733')
legend_ax.text(-0.08, 0.5, 'Domestic →', ha='right', va='center', fontsize=9, color='#3D3733', rotation=90)

# Corner labels
legend_ax.text(0.02, 0.02, 'Neither', ha='left', va='bottom', fontsize=7, color='#3D3733', alpha=0.7)
legend_ax.text(0.98, 0.02, 'Immigrant\ngateway', ha='right', va='bottom', fontsize=7, color='#3D3733', alpha=0.7)
legend_ax.text(0.02, 0.98, 'Domestic\nmagnet', ha='left', va='top', fontsize=7, color='#3D3733', alpha=0.7)
legend_ax.text(0.98, 0.98, 'Both', ha='right', va='top', fontsize=7, color='#3D3733', alpha=0.7)

# Source
ax.text(0.02, 0.02, 'Source: Census Bureau Population Estimates, Vintage 2025 (released Jan 27, 2026)',
        transform=ax.transAxes, fontsize=8, color='#888888', style='italic', va='bottom')

plt.tight_layout()

# Save
OUTPUT_DIR.mkdir(exist_ok=True)
plt.savefig(OUTPUT_DIR / "bivariate_migration_map.png", facecolor='#F6F7F3',
            bbox_inches='tight', dpi=150)
plt.savefig(OUTPUT_DIR / "bivariate_migration_map.svg", facecolor='#F6F7F3',
            bbox_inches='tight')
print(f"\nSaved to {OUTPUT_DIR / 'bivariate_migration_map.png'}")
