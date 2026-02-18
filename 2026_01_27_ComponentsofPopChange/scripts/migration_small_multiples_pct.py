"""
Small Multiples: Components of Population Change (2024-2025)
Four maps with consistent color scale:
- Natural change
- Domestic migration
- International migration
- Total population change

Color scheme: Black (shrinking) -> White (neutral) -> Blue (growing)
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
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
# COLOR SCHEME: 5 discrete buckets
# Intense red -> Light red -> Cream -> Light blue -> Intense blue
# =============================================================================
INTENSE_RED = '#F4743B'
LIGHT_RED = '#FBCAB5'
CREAM = '#DADFCE'
LIGHT_BLUE = '#A8DEFF'  # Lighter version of blue
INTENSE_BLUE = '#0BB4FF'

# Create discrete colormap with 5 colors
discrete_colors = [INTENSE_RED, LIGHT_RED, CREAM, LIGHT_BLUE, INTENSE_BLUE]
diverging_cmap = mcolors.ListedColormap(discrete_colors)

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

# Get 2025 components (percentage of population)
states['natural'] = states['NATURALCHG2025']
states['domestic'] = states['DOMESTICMIG2025']
states['international'] = states['INTERNATIONALMIG2025']
states['total'] = states['NPOPCHG_2025']
states['pop'] = states['POPESTIMATE2024']

# Use percentage rates
states['natural_pct'] = states['natural'] / states['pop'] * 100
states['domestic_pct'] = states['domestic'] / states['pop'] * 100
states['international_pct'] = states['international'] / states['pop'] * 100
states['total_pct'] = states['total'] / states['pop'] * 100

# Set bucket boundaries for percentage rates (same scale for all 4 maps)
# Boundaries in percentage points
pct_boundaries = [-np.inf, -0.5, -0.1, 0.1, 0.5, np.inf]
print(f"Percentage boundaries: <-0.5%, -0.5 to -0.1%, -0.1 to +0.1%, +0.1 to +0.5%, >+0.5%")
shared_norm = mcolors.BoundaryNorm(pct_boundaries, diverging_cmap.N)

# =============================================================================
# LOAD SHAPEFILE
# =============================================================================

shp_path = DATA_DIR / "Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp"
gdf = gpd.read_file(shp_path)

# Albers projection
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
gdf = gdf.to_crs(ALBERS)

# Exclude non-continental
exclude_fips = ['02', '15', '60', '66', '69', '72', '78']
gdf = gdf[~gdf['STATEFP'].isin(exclude_fips)]

# Merge
states['STATEFP'] = states['STATE'].astype(str).str.zfill(2)
gdf = gdf.merge(states[['STATEFP', 'natural_pct', 'domestic_pct',
                         'international_pct', 'total_pct', 'NAME']],
                on='STATEFP', how='left')

# =============================================================================
# CREATE SMALL MULTIPLES
# =============================================================================

fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=100)
fig.patch.set_facecolor('#F6F7F3')

# Map configurations: (column, title, axes, norm)
maps = [
    ('natural_pct', 'Natural Change\n(births minus deaths)', axes[0, 0], shared_norm),
    ('domestic_pct', 'Domestic Migration', axes[0, 1], shared_norm),
    ('international_pct', 'International Migration', axes[1, 0], shared_norm),
    ('total_pct', 'Total Population Change', axes[1, 1], shared_norm),
]

for col, title, ax, norm in maps:
    ax.set_facecolor('#F6F7F3')

    col_min = gdf[col].min()
    col_max = gdf[col].max()
    print(f"{title.replace(chr(10), ' ')}: {col_min:.1f} to {col_max:.1f}")

    # Plot using appropriate normalization
    gdf.plot(column=col, ax=ax, cmap=diverging_cmap, norm=norm,
             edgecolor='white', linewidth=0.3)

    # Styling
    ax.set_xlim(gdf.total_bounds[0] - 100000, gdf.total_bounds[2] + 100000)
    ax.set_ylim(gdf.total_bounds[1] - 50000, gdf.total_bounds[3] + 50000)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=14, fontweight='bold', color='#3D3733', pad=10)

# Main title
fig.suptitle('Components of U.S. Population Change\nJuly 2024 – July 2025 (as % of population)',
             fontsize=18, fontweight='bold', color='#3D3733', y=0.98)

# Add single shared legend (same scale for all 4 maps)
cbar_ax = fig.add_axes([0.25, 0.04, 0.5, 0.02])
cbar_ax.set_facecolor('#F6F7F3')
for i, color in enumerate(discrete_colors):
    cbar_ax.add_patch(plt.Rectangle((i/5, 0), 1/5, 1, facecolor=color, edgecolor='white', linewidth=0.5))
cbar_ax.set_xlim(0, 1)
cbar_ax.set_ylim(0, 1)
cbar_ax.axis('off')
cbar_ax.text(0.5, 1.5, 'Percent of population', ha='center', va='bottom', fontsize=9, fontweight='bold', color='#3D3733')
for pos, label in zip([0.1, 0.3, 0.5, 0.7, 0.9], ['< -0.5%', '-0.5%\nto -0.1%', '-0.1%\nto +0.1%', '+0.1%\nto +0.5%', '> +0.5%']):
    cbar_ax.text(pos, -0.4, label, ha='center', va='top', fontsize=7, color='#3D3733')

# Source
fig.text(0.02, 0.01, 'Source: Census Bureau Population Estimates, Vintage 2025 (released Jan 27, 2026)',
         fontsize=8, color='#888888', style='italic')

plt.subplots_adjust(top=0.88, bottom=0.12, hspace=0.15, wspace=0.05)

# Save
OUTPUT_DIR.mkdir(exist_ok=True)
plt.savefig(OUTPUT_DIR / "migration_components_small_multiples_pct.png",
            facecolor='#F6F7F3', bbox_inches='tight', dpi=150)
plt.savefig(OUTPUT_DIR / "migration_components_small_multiples_pct.svg",
            facecolor='#F6F7F3', bbox_inches='tight')

print(f"\nSaved to {OUTPUT_DIR / 'migration_components_small_multiples_pct.png'}")

# Print summary stats for context
print("\n" + "="*60)
print("SUMMARY STATISTICS (rate per 1,000)")
print("="*60)
for col, title, _, _ in maps:
    min_idx = gdf[col].idxmin()
    max_idx = gdf[col].idxmax()
    min_name = gdf.loc[min_idx, 'NAME_y'] if 'NAME_y' in gdf.columns else gdf.loc[min_idx, 'NAME']
    max_name = gdf.loc[max_idx, 'NAME_y'] if 'NAME_y' in gdf.columns else gdf.loc[max_idx, 'NAME']
    print(f"\n{title.replace(chr(10), ' ')}:")
    print(f"  Min: {gdf[col].min():.1f} ({min_name})")
    print(f"  Max: {gdf[col].max():.1f} ({max_name})")
