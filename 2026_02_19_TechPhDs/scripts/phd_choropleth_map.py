#!/usr/bin/env python3
"""
PhD Choropleth Map
==================
Metro-level choropleth showing density of working PhDs (CS, Math, EE, Physics)
per square mile. Highlights the Northeast corridor's concentration.
"""

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

# SVG settings for editable text
matplotlib.use('svg')
plt.rcParams['svg.fonttype'] = 'none'

# =============================================================================
# CONFIGURATION
# =============================================================================

TITLE = "Where America's AI-Ready PhDs Live"
SUBTITLE = "CS, math, EE, and physics doctoral holders per square mile, by metro area"
SOURCE = "Source: ACS 5-Year (2019–2023) via IPUMS. Employed, not in school, doctoral degree holders."

OUTPUT_SVG = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/phd_choropleth_map.svg"
OUTPUT_PNG = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/phd_choropleth_map.png"

# Brand colors
BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
LAND_CREAM = '#EDEFE7'
LIGHT_BLUE = '#C6E8FF'

# Albers Equal Area projection
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']

MIN_POP = 150000

# Font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
FONT_REGULAR = f"{FONT_DIR}/ABCOracle-Regular.otf"
FONT_BOLD = f"{FONT_DIR}/ABCOracle-Bold.otf"
FONT_LIGHT = f"{FONT_DIR}/ABCOracle-Light.otf"
FONT_MEDIUM = f"{FONT_DIR}/ABCOracle-Medium.otf"

# Data paths
IPUMS_5YR = '/tmp/ipums_degfield_5yr.csv.gz'
CBSA_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_cbsa/cb_2023_us_cbsa_5m.shp'
STATE_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp'

# =============================================================================
# LOAD DATA
# =============================================================================

print("Loading PhD data from ACS 5-year...")
conn = duckdb.connect()

phd_data = conn.execute("""
    WITH cs_phds AS (
        SELECT MET2013 as msa_code, SUM(PERWT) as total_phds, COUNT(*) as raw_n
        FROM read_csv_auto('{path}')
        WHERE EDUCD = 116 AND EMPSTAT = 1 AND SCHOOL = 1 AND MET2013 > 0
          AND (DEGFIELD IN (21, 37) OR DEGFIELDD IN (2407, 2408, 5007))
        GROUP BY MET2013
    ),
    total_pop AS (
        SELECT MET2013 as msa_code, SUM(CASE WHEN AGE >= 25 THEN PERWT ELSE 0 END) as pop_25plus
        FROM read_csv_auto('{path}')
        WHERE MET2013 > 0
        GROUP BY MET2013
    )
    SELECT c.msa_code, c.total_phds, c.raw_n, t.pop_25plus
    FROM cs_phds c JOIN total_pop t ON c.msa_code = t.msa_code
    WHERE t.pop_25plus >= {min_pop}
""".format(path=IPUMS_5YR, min_pop=MIN_POP)).df()

print(f"Metros after pop filter: {len(phd_data)}")

# Load CBSA shapefile
print("Loading CBSA shapefile...")
cbsa = gpd.read_file(CBSA_SHAPEFILE)
cbsa['CBSAFP'] = cbsa['CBSAFP'].astype(int)
cbsa = cbsa.to_crs(ALBERS)

# Compute area in square miles
cbsa['area_sq_mi'] = cbsa.geometry.area / 2589988

# Merge
merged = cbsa.merge(phd_data, left_on='CBSAFP', right_on='msa_code', how='inner')
merged['phds_per_sq_mi'] = merged['total_phds'] / merged['area_sq_mi']

# Filter to continental US
states = gpd.read_file(STATE_SHAPEFILE)
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)
state_bounds = states.total_bounds

merged_centroids = merged.geometry.centroid
merged = merged[
    (merged_centroids.x >= state_bounds[0] - 200000) &
    (merged_centroids.x <= state_bounds[2] + 200000) &
    (merged_centroids.y >= state_bounds[1] - 200000) &
    (merged_centroids.y <= state_bounds[3] + 200000)
]

print(f"Final metros on map: {len(merged)}")
print(f"PhDs/mi² range: {merged['phds_per_sq_mi'].min():.2f} to {merged['phds_per_sq_mi'].max():.1f}")

# =============================================================================
# CREATE FIGURE
# =============================================================================

print("Creating figure...")
oracle_regular = FontProperties(fname=FONT_REGULAR)
oracle_bold = FontProperties(fname=FONT_BOLD)
oracle_light = FontProperties(fname=FONT_LIGHT)
oracle_medium = FontProperties(fname=FONT_MEDIUM)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Plot states first (background)
states.plot(ax=ax, facecolor=LAND_CREAM, edgecolor='white', linewidth=0.75, zorder=1)

# Custom colormap: cream → light blue → blue → dark blue
cmap = LinearSegmentedColormap.from_list('phd_density', [
    LAND_CREAM,   # 0 — blends with background
    '#B3DFFF',    # low
    '#0BB4FF',    # medium — brand blue
    '#0066AA',    # high
    '#003366',    # very high
], N=256)

# Use log-ish scale for color: clip at 0.05 and 10
vmin = 0.05
vmax = 10
merged['color_val'] = merged['phds_per_sq_mi'].clip(vmin, vmax)
merged['color_val_log'] = np.log10(merged['color_val'])

# Plot choropleth
merged.plot(
    ax=ax,
    column='color_val_log',
    cmap=cmap,
    vmin=np.log10(vmin),
    vmax=np.log10(vmax),
    edgecolor='white',
    linewidth=0.3,
    zorder=2
)

# Re-draw state borders on top
states.boundary.plot(ax=ax, edgecolor='white', linewidth=0.75, zorder=3)

# Bounds
ax.set_xlim(state_bounds[0] - 100000, state_bounds[2] + 100000)
ax.set_ylim(state_bounds[1] - 100000, state_bounds[3] + 100000)
ax.set_aspect('equal')
ax.axis('off')

# =============================================================================
# LABELS
# =============================================================================

# Label top metros by density
top = merged.nlargest(12, 'phds_per_sq_mi').copy()

def short_name(name):
    parts = name.split('-')
    city = parts[0].split(',')[0].strip()
    state = name.split(',')[-1].strip().split('-')[0].strip() if ',' in name else ''
    return f"{city}, {state}" if state else city

top['label'] = top['NAME'].apply(short_name)
top['label_text'] = top.apply(
    lambda r: f"{short_name(r['NAME'])} ({r['phds_per_sq_mi']:.1f})", axis=1
)

offsets = {
    41940: (200000, -100000),   # San Jose
    41860: (-450000, 80000),    # San Francisco
    45940: (100000, 60000),     # Trenton
    14460: (120000, -60000),    # Boston
    35620: (150000, 50000),     # New York
    28740: (80000, -40000),     # New Haven? Kingston?
    47900: (120000, 70000),     # Washington DC
    31080: (-250000, 100000),   # LA
    42100: (-400000, -40000),   # Santa Cruz
    11460: (80000, -70000),     # Ann Arbor
    42660: (120000, -60000),    # Seattle
    12580: (100000, -40000),    # Baltimore
    35300: (80000, 50000),      # New Haven
    14860: (80000, -40000),     # Bridgeport
    27060: (80000, -50000),     # Ithaca
    41740: (-200000, 80000),    # San Diego
}

for _, row in top.iterrows():
    cx, cy = row.geometry.centroid.x, row.geometry.centroid.y
    ox, oy = offsets.get(row['msa_code'], (100000, -30000))

    ax.plot([cx, cx + ox], [cy, cy + oy],
            color=BLACK, linewidth=0.5, alpha=0.5, zorder=6)
    ax.text(cx + ox, cy + oy, row['label_text'],
            fontproperties=oracle_regular, fontsize=6.5,
            color=BLACK, ha='left', va='center', zorder=7)

# =============================================================================
# COLOR BAR LEGEND
# =============================================================================

from mpl_toolkits.axes_grid1.inset_locator import inset_axes
cbar_ax = inset_axes(ax, width="25%", height="2.5%", loc='lower left',
                     bbox_to_anchor=(0.05, 0.04, 1, 1),
                     bbox_transform=ax.transAxes)

import matplotlib.cm as cm
norm = matplotlib.colors.Normalize(vmin=np.log10(vmin), vmax=np.log10(vmax))
sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])

cbar = fig.colorbar(sm, cax=cbar_ax, orientation='horizontal')
cbar.set_ticks([np.log10(v) for v in [0.1, 0.5, 1, 5, 10]])
cbar.set_ticklabels(['0.1', '0.5', '1', '5', '10'])
cbar.ax.tick_params(labelsize=6.5, length=2, pad=2)
for label in cbar.ax.get_xticklabels():
    label.set_fontproperties(oracle_light)

cbar.outline.set_linewidth(0.5)
cbar.outline.set_edgecolor('#ccc')

ax.text(0.05, 0.10, 'PhDs per square mile',
        transform=ax.transAxes, fontproperties=oracle_medium,
        fontsize=7.5, color=BLACK)

# =============================================================================
# TITLE AND SOURCE
# =============================================================================

ax.text(0.5, 0.97, TITLE,
        transform=ax.transAxes, ha='center', va='top',
        fontproperties=oracle_bold, fontsize=14, color=BLACK)

ax.text(0.5, 0.935, SUBTITLE,
        transform=ax.transAxes, ha='center', va='top',
        fontproperties=oracle_light, fontsize=9, color='#888')

ax.text(0.98, 0.02, SOURCE,
        transform=ax.transAxes, ha='right', va='bottom',
        fontproperties=oracle_light, fontsize=6, fontstyle='italic', color='#aaa')

# =============================================================================
# SAVE
# =============================================================================

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

plt.savefig(OUTPUT_SVG, format='svg', facecolor=BG_CREAM)
print(f"Saved SVG: {OUTPUT_SVG}")

fig.savefig(OUTPUT_PNG, format='png', dpi=200, facecolor=BG_CREAM, bbox_inches='tight')
print(f"Saved PNG: {OUTPUT_PNG}")

plt.close()
