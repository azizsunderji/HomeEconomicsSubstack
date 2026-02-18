"""
Vertical Small Multiples: Components of Population Change (2024-2025)
Four maps stacked vertically with state labels
"""

import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path

# Ensure text is editable in SVG
plt.rcParams['svg.fonttype'] = 'none'

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
# =============================================================================
INTENSE_RED = '#F4743B'
LIGHT_RED = '#FBCAB5'
CREAM = '#DADFCE'
LIGHT_BLUE = '#A8DEFF'
INTENSE_BLUE = '#0BB4FF'

discrete_colors = [INTENSE_RED, LIGHT_RED, CREAM, LIGHT_BLUE, INTENSE_BLUE]
diverging_cmap = mcolors.ListedColormap(discrete_colors)

# Percentage boundaries
pct_boundaries = [-np.inf, -0.5, -0.1, 0.1, 0.5, np.inf]
shared_norm = mcolors.BoundaryNorm(pct_boundaries, diverging_cmap.N)

# =============================================================================
# LOAD DATA
# =============================================================================
pop = pd.read_parquet(DATA_DIR / "PopulationEstimates/state_v2025.parquet")

regions = ['United States', 'Northeast Region', 'Midwest Region', 'South Region',
           'West Region', 'Puerto Rico', 'Middle Atlantic', 'New England',
           'East North Central', 'West North Central', 'South Atlantic',
           'East South Central', 'West South Central', 'Mountain', 'Pacific']
states = pop[~pop['NAME'].isin(regions)].copy()

states['pop'] = states['POPESTIMATE2024']
states['natural_pct'] = states['NATURALCHG2025'] / states['pop'] * 100
states['domestic_pct'] = states['DOMESTICMIG2025'] / states['pop'] * 100
states['international_pct'] = states['INTERNATIONALMIG2025'] / states['pop'] * 100
states['total_pct'] = states['NPOPCHG_2025'] / states['pop'] * 100

# Classify into buckets
def get_bucket(val):
    if val < -0.5: return 0  # intense red
    elif val < -0.1: return 1  # light red
    elif val < 0.1: return 2  # cream
    elif val < 0.5: return 3  # light blue
    else: return 4  # intense blue

states['natural_bucket'] = states['natural_pct'].apply(get_bucket)
states['domestic_bucket'] = states['domestic_pct'].apply(get_bucket)
states['international_bucket'] = states['international_pct'].apply(get_bucket)
states['total_bucket'] = states['total_pct'].apply(get_bucket)

# =============================================================================
# LOAD SHAPEFILE
# =============================================================================
shp_path = DATA_DIR / "Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp"
gdf = gpd.read_file(shp_path)

ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
gdf = gdf.to_crs(ALBERS)

exclude_fips = ['02', '15', '60', '66', '69', '72', '78']
gdf = gdf[~gdf['STATEFP'].isin(exclude_fips)]

states['STATEFP'] = states['STATE'].astype(str).str.zfill(2)
gdf = gdf.merge(states[['STATEFP', 'NAME', 'natural_pct', 'domestic_pct',
                         'international_pct', 'total_pct',
                         'natural_bucket', 'domestic_bucket',
                         'international_bucket', 'total_bucket']],
                on='STATEFP', how='left', suffixes=('_geo', ''))

# Use merged NAME column
if 'NAME' not in gdf.columns and 'NAME_geo' in gdf.columns:
    gdf['NAME'] = gdf['NAME_geo']

# Calculate centroids for labeling
gdf['centroid'] = gdf.geometry.centroid
gdf['centroid_x'] = gdf['centroid'].x
gdf['centroid_y'] = gdf['centroid'].y

# =============================================================================
# STATE ABBREVIATIONS
# =============================================================================
state_abbrev = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
    'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
    'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
    'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
    'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
    'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
    'District of Columbia': 'DC'
}

# =============================================================================
# CREATE FIGURE - 4 rows, 1 column
# =============================================================================
fig, axes = plt.subplots(4, 1, figsize=(14, 24), dpi=100)
fig.patch.set_facecolor('#F6F7F3')

# Manual label offsets for small/overlapping states (x_offset, y_offset)
label_offsets = {
    'Vermont': (500000, 300000),
    'New Hampshire': (550000, 150000),
    'Massachusetts': (600000, 0),
    'Rhode Island': (550000, -150000),
    'Connecticut': (500000, -300000),
    'New Jersey': (450000, -100000),
    'Delaware': (400000, -200000),
    'Maryland': (450000, -350000),
    'District of Columbia': (500000, -500000),
    'West Virginia': (0, -200000),
    'Maine': (350000, 200000),
    'Illinois': (0, 150000),
    'Colorado': (0, -150000),
    'New Mexico': (0, -200000),
    'Louisiana': (150000, -200000),
    'Washington': (0, 150000),
}

def add_labels(ax, gdf, states_to_label, color='#3D3733'):
    """Add state labels with leader lines where needed"""
    for _, row in gdf.iterrows():
        if row['NAME'] in states_to_label:
            abbrev = state_abbrev.get(row['NAME'], row['NAME'][:2])
            cx, cy = row['centroid_x'], row['centroid_y']

            if row['NAME'] in label_offsets:
                ox, oy = label_offsets[row['NAME']]
                # Draw leader line
                ax.annotate(abbrev, xy=(cx, cy), xytext=(cx + ox, cy + oy),
                           fontsize=8, fontweight='bold', color=color,
                           ha='center', va='center',
                           arrowprops=dict(arrowstyle='-', color='#888888', lw=0.5))
            else:
                ax.text(cx, cy, abbrev, fontsize=8, fontweight='bold', color=color,
                       ha='center', va='center')

# Map configurations
maps_config = [
    {
        'col': 'natural_pct',
        'title': 'Natural Change (births minus deaths)',
        'ax': axes[0],
        'labels': ['Utah', 'Texas'] + list(gdf[gdf['natural_bucket'] <= 1]['NAME'].values)  # Utah, Texas, and red states
    },
    {
        'col': 'domestic_pct',
        'title': 'Domestic Migration',
        'ax': axes[1],
        'labels': list(gdf[gdf['domestic_bucket'] == 1]['NAME'].values)  # Light red only (not intense red)
    },
    {
        'col': 'international_pct',
        'title': 'International Migration',
        'ax': axes[2],
        'labels': [n for n in gdf[gdf['international_bucket'] == 4]['NAME'].values
                   if n not in ['Texas', 'Florida']]  # Intense blue except TX and FL
    },
    {
        'col': 'total_pct',
        'title': 'Total Population Change',
        'ax': axes[3],
        'labels': ['Vermont']
    },
]

for config in maps_config:
    ax = config['ax']
    col = config['col']
    title = config['title']
    labels_to_show = config['labels']

    ax.set_facecolor('#F6F7F3')

    # Plot
    gdf.plot(column=col, ax=ax, cmap=diverging_cmap, norm=shared_norm,
             edgecolor='white', linewidth=0.3)

    # Styling - extend right side for labels
    ax.set_xlim(gdf.total_bounds[0] - 100000, gdf.total_bounds[2] + 800000)
    ax.set_ylim(gdf.total_bounds[1] - 100000, gdf.total_bounds[3] + 100000)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(title, fontsize=14, fontweight='bold', color='#3D3733', pad=10, loc='left')

    # Add labels
    add_labels(ax, gdf, labels_to_show)

# Main title
fig.suptitle('Components of U.S. Population Change\nJuly 2024 – July 2025 (as % of population)',
             fontsize=18, fontweight='bold', color='#3D3733', y=0.98)

# Add shared legend at bottom
legend_ax = fig.add_axes([0.25, 0.02, 0.5, 0.015])
legend_ax.set_facecolor('#F6F7F3')
for i, color in enumerate(discrete_colors):
    legend_ax.add_patch(plt.Rectangle((i/5, 0), 1/5, 1, facecolor=color, edgecolor='white', linewidth=0.5))
legend_ax.set_xlim(0, 1)
legend_ax.set_ylim(0, 1)
legend_ax.axis('off')
for pos, label in zip([0.1, 0.3, 0.5, 0.7, 0.9], ['< -0.5%', '-0.5% to\n-0.1%', '-0.1% to\n+0.1%', '+0.1% to\n+0.5%', '> +0.5%']):
    legend_ax.text(pos, -0.5, label, ha='center', va='top', fontsize=8, color='#3D3733')

# Source
fig.text(0.02, 0.01, 'Source: Census Bureau Population Estimates, Vintage 2025 (released Jan 27, 2026)',
         fontsize=9, color='#888888', style='italic')

plt.subplots_adjust(top=0.94, bottom=0.05, hspace=0.1)

# Save
plt.savefig(OUTPUT_DIR / "migration_components_vertical.png", facecolor='#F6F7F3',
            bbox_inches='tight', dpi=150)
plt.savefig(OUTPUT_DIR / "migration_components_vertical.svg", facecolor='#F6F7F3',
            bbox_inches='tight')

print(f"Saved to {OUTPUT_DIR / 'migration_components_vertical.png'}")

# Print which states are being labeled
print("\n=== States being labeled ===")
for config in maps_config:
    print(f"\n{config['title']}:")
    print(f"  {config['labels']}")
