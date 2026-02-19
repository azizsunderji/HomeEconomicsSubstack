#!/usr/bin/env python3
"""
PhD Kernel Density Map (Production Version)
============================================
Gaussian KDE of technical PhD concentration per 10,000 adults.
Smoothed PUMA-level data with feathered boundary masking, log color scale,
and weather-map aesthetic.
"""

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap, Normalize
import matplotlib.cm as cm
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy as np
import pandas as pd
from shapely.geometry import Point
from shapely.ops import unary_union
from shapely.prepared import prep
from pyproj import Transformer
from scipy.ndimage import gaussian_filter

matplotlib.use('svg')
plt.rcParams['svg.fonttype'] = 'none'

# =============================================================================
# CONFIGURATION
# =============================================================================

TITLE = "Where America's AI-Ready PhDs Live"
SUBTITLE = "CS, math, EE, and physics doctoral holders per 10,000 adults"
SOURCE = "Source: ACS 5-Year (2019-2023) via IPUMS. Employed, not in school, doctoral degree holders."

OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs"
OUTPUT_SVG = f"{OUTPUT_DIR}/phd_kde_map.svg"
OUTPUT_PNG = f"{OUTPUT_DIR}/phd_kde_map.png"

BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
LAND_CREAM = '#EDEFE7'

ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
FONT_REGULAR = f"{FONT_DIR}/ABCOracle-Regular.otf"
FONT_BOLD = f"{FONT_DIR}/ABCOracle-Bold.otf"
FONT_LIGHT = f"{FONT_DIR}/ABCOracle-Light.otf"
FONT_MEDIUM = f"{FONT_DIR}/ABCOracle-Medium.otf"

IPUMS_5YR = '/tmp/ipums_degfield_5yr.csv.gz'
PUMA_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/InsuranceCosts/cb_2020_us_puma20_500k.shp'
STATE_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp'

# Smoothing bandwidth in meters (25km — roughly a commute radius)
BANDWIDTH = 25000

# Grid resolution — higher = smoother
RESOLUTION = 1000

# Feather radius for boundary mask (in grid cells) — softens coastlines
FEATHER_SIGMA = 3.0

# =============================================================================
# LOAD DATA
# =============================================================================

print("Loading data...")
conn = duckdb.connect()

puma_phds = conn.execute("""
    SELECT STATEFIP, PUMA,
        SUM(PERWT) as total_phds, COUNT(*) as raw_n
    FROM read_csv_auto('{path}')
    WHERE EDUCD = 116 AND EMPSTAT = 1 AND SCHOOL = 1
      AND (DEGFIELD IN (21, 37) OR DEGFIELDD IN (2407, 2408, 5007))
    GROUP BY STATEFIP, PUMA
""".format(path=IPUMS_5YR)).df()

puma_pop = conn.execute("""
    SELECT STATEFIP, PUMA,
        SUM(CASE WHEN AGE >= 25 THEN PERWT ELSE 0 END) as pop_25plus
    FROM read_csv_auto('{path}')
    GROUP BY STATEFIP, PUMA
""".format(path=IPUMS_5YR)).df()

puma_pop['puma_key'] = puma_pop['STATEFIP'].astype(str).str.zfill(2) + puma_pop['PUMA'].astype(str).str.zfill(5)
puma_phds['puma_key'] = puma_phds['STATEFIP'].astype(str).str.zfill(2) + puma_phds['PUMA'].astype(str).str.zfill(5)
puma_data = puma_pop.merge(puma_phds[['puma_key', 'total_phds', 'raw_n']], on='puma_key', how='left')
puma_data['total_phds'] = puma_data['total_phds'].fillna(0)
puma_data['raw_n'] = puma_data['raw_n'].fillna(0)

print(f"PUMAs: {len(puma_data)}, with PhDs: {(puma_data['total_phds'] > 0).sum()}")
print(f"Total PhDs: {puma_data['total_phds'].sum():,.0f}")

# Load PUMA shapefile for centroids
print("Loading PUMA shapefile...")
pumas = gpd.read_file(PUMA_SHAPEFILE)
pumas['puma_key'] = pumas['STATEFP20'] + pumas['PUMACE20']
pumas = pumas.to_crs(ALBERS)
pumas['centroid'] = pumas.geometry.centroid

puma_merged = puma_data.merge(pumas[['puma_key', 'centroid']], on='puma_key', how='inner')
print(f"Matched: {len(puma_merged)} PUMAs")

# Load states
print("Loading states...")
states = gpd.read_file(STATE_SHAPEFILE)
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)
us_boundary = unary_union(states.geometry)

# =============================================================================
# BUILD KDE SURFACE
# =============================================================================

print(f"Building KDE surface ({RESOLUTION}x grid, {BANDWIDTH/1000:.0f}km bandwidth)...")

sb = states.total_bounds
pad = 50000
x_range = np.linspace(sb[0] - pad, sb[2] + pad, RESOLUTION)
y_range = np.linspace(sb[1] - pad, sb[3] + pad, RESOLUTION)
cell_size = (x_range[-1] - x_range[0]) / RESOLUTION

# Place PUMA data on grid
phd_grid = np.zeros((len(y_range), len(x_range)))
pop_grid = np.zeros((len(y_range), len(x_range)))

for _, row in puma_merged.iterrows():
    cx, cy = row['centroid'].x, row['centroid'].y
    xi = np.searchsorted(x_range, cx)
    yi = np.searchsorted(y_range, cy)
    if 0 <= xi < len(x_range) and 0 <= yi < len(y_range):
        phd_grid[yi, xi] += row['total_phds']
        pop_grid[yi, xi] += row['pop_25plus']

# Gaussian smoothing — sigma in grid cells
sigma = BANDWIDTH / cell_size
print(f"  Sigma: {sigma:.1f} grid cells")

smoothed_phds = gaussian_filter(phd_grid, sigma=sigma)
smoothed_pop = gaussian_filter(pop_grid, sigma=sigma)

# Per 10k ratio — very low threshold so entire country gets some color
# Even rural areas with tiny smoothed population will show a rate
MIN_POP = 10
density = np.where(smoothed_pop > MIN_POP, smoothed_phds / smoothed_pop * 10000, 0)

# Set a floor for inside-US areas: minimum 0.01 per 10k so they get the lightest color
# (will be handled via the mask below)

print(f"  Density range (nonzero): {density[density > 0].min():.4f} to {density.max():.0f}")
print(f"  Grid cells with data: {(density > 0).sum()} of {density.size}")

# =============================================================================
# CREATE FEATHERED US BOUNDARY MASK
# =============================================================================

print("Creating boundary mask (this takes a minute)...")

us_prep = prep(us_boundary)
xx, yy = np.meshgrid(x_range, y_range)
mask = np.zeros((len(y_range), len(x_range)), dtype=float)

# Check in chunks for speed
chunk = 40
for i in range(0, len(y_range), chunk):
    i_end = min(i + chunk, len(y_range))
    for j in range(0, len(x_range), chunk):
        j_end = min(j + chunk, len(x_range))
        corners_inside = sum([
            us_prep.contains(Point(x_range[j], y_range[i])),
            us_prep.contains(Point(x_range[min(j_end-1, len(x_range)-1)], y_range[i])),
            us_prep.contains(Point(x_range[j], y_range[min(i_end-1, len(y_range)-1)])),
            us_prep.contains(Point(x_range[min(j_end-1, len(x_range)-1)], y_range[min(i_end-1, len(y_range)-1)])),
        ])
        if corners_inside == 4:
            mask[i:i_end, j:j_end] = 1.0
        elif corners_inside == 0:
            mask[i:i_end, j:j_end] = 0.0
        else:
            for ii in range(i, i_end):
                for jj in range(j, j_end):
                    mask[ii, jj] = 1.0 if us_prep.contains(Point(x_range[jj], y_range[ii])) else 0.0

print(f"  Hard mask: {(mask > 0).sum()} of {mask.size} cells ({(mask > 0).sum()/mask.size*100:.1f}%)")

# Feather the mask edges with gaussian blur for soft coastlines
feathered_mask = gaussian_filter(mask, sigma=FEATHER_SIGMA)
# Clip so interior stays fully opaque
feathered_mask = np.clip(feathered_mask * 1.5, 0, 1)  # boost slightly so interior stays at 1.0

print(f"  Feathered mask range: {feathered_mask.min():.3f} to {feathered_mask.max():.3f}")

# =============================================================================
# BUILD RGBA IMAGE
# =============================================================================

print("Building RGBA image...")

# Use a power-law scale instead of pure log to give more visual punch to peaks
# power of 0.35 gives good separation: low values get compressed, highs spread out
# This is between linear (1.0) and log — gives the "weather map" look where
# hot spots glow intensely while the background stays soft

max_density = np.nanmax(density)
# Normalize to 0-1
norm_density = density / max_density
# Apply power law (gamma correction)
GAMMA = 0.35
gamma_density = np.power(norm_density, GAMMA)

# Map through colormap
# Colormap: pale almost-white blue → sky blue → brand blue → deep blue → deep indigo
cmap_colors = [
    (0.0,  '#E8F2FB'),   # very pale blue-white (barely there)
    (0.15, '#CEEAFF'),   # pale blue
    (0.35, '#7DD3FF'),   # sky blue
    (0.55, '#0BB4FF'),   # brand blue
    (0.75, '#0066BB'),   # deep blue
    (0.90, '#1B3A6B'),   # navy
    (1.0,  '#0F1D3D'),   # very deep indigo-black
]
cmap_obj = LinearSegmentedColormap.from_list(
    'phd_weather',
    [(pos, c) for pos, c in cmap_colors],
    N=512
)

# Apply colormap to get RGBA
rgba = cmap_obj(gamma_density)

# Apply feathered mask as alpha
# Where mask is 0 (outside US), alpha = 0 (transparent)
# Where mask is 1 (inside US), alpha = full
rgba[:, :, 3] = feathered_mask

# Where density is essentially zero inside US, show very lightest color
# (the gamma transform already handles this — near-zero values map to bottom of colormap)

print(f"  Gamma scale: power {GAMMA}, max density {max_density:.0f}")

# =============================================================================
# PLOT
# =============================================================================

print("Creating figure...")
oracle_regular = FontProperties(fname=FONT_REGULAR)
oracle_bold = FontProperties(fname=FONT_BOLD)
oracle_light = FontProperties(fname=FONT_LIGHT)
oracle_medium = FontProperties(fname=FONT_MEDIUM)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Land base — very subtle, just so coastline reads
states.plot(ax=ax, facecolor=LAND_CREAM, edgecolor='none', zorder=1)

# KDE surface as RGBA image
ax.imshow(
    rgba, origin='lower',
    extent=[x_range[0], x_range[-1], y_range[0], y_range[-1]],
    aspect='auto', zorder=2,
    interpolation='bicubic'  # smooth interpolation for weather-map look
)

# State borders — thin, subtle white
states.boundary.plot(ax=ax, edgecolor='white', linewidth=0.5, alpha=0.7, zorder=3)

# Bounds
ax.set_xlim(sb[0] - 100000, sb[2] + 100000)
ax.set_ylim(sb[1] - 100000, sb[3] + 100000)
ax.set_aspect('equal')
ax.axis('off')

# =============================================================================
# LABELS (no black dots, just leader lines)
# =============================================================================

transformer = Transformer.from_crs('EPSG:4326', ALBERS, always_xy=True)

label_cities = [
    ('Bay Area',      -122.0,  37.4,   180000,  -120000),
    ('Seattle',       -122.33, 47.61,  120000,  -60000),
    ('Los Angeles',   -118.24, 34.05, -300000,  -80000),
    ('New York',      -74.01,  40.71,  150000,   50000),
    ('Boston',        -71.06,  42.36,  130000,  -50000),
    ('Washington',    -77.04,  38.91,  180000,   70000),
    ('San Diego',     -117.16, 32.72, -250000,   50000),
    ('Ann Arbor',     -83.74,  42.28,   80000,  -70000),
    ('Princeton',     -74.66,  40.35,  180000,  -70000),
    ('Albuquerque',   -106.65, 35.08, -200000,   80000),
    ('Chicago',       -87.63,  41.88,   80000,   70000),
    ('Austin',        -97.74,  30.27,  -150000,  70000),
    ('Santa Barbara', -119.70, 34.42, -280000,   60000),
    ('Ithaca',        -76.50,  42.44,  100000,   60000),
    ('Boulder',       -105.27, 40.02, -180000,   70000),
    ('Raleigh',       -78.64,  35.77,  150000,  -50000),
]

for name, lon, lat, ox, oy in label_cities:
    px, py = transformer.transform(lon, lat)

    # Leader line only — no dot
    ax.plot([px, px + ox], [py, py + oy],
            color=BLACK, linewidth=0.4, alpha=0.4, zorder=6)

    ha = 'left' if ox > 0 else 'right'
    ax.text(px + ox, py + oy, name,
            fontproperties=oracle_regular, fontsize=6.5,
            color=BLACK, ha=ha, va='center', zorder=7)

# =============================================================================
# COLORBAR
# =============================================================================

# Build a colorbar that shows the actual per-10k values
# We need to reverse-engineer the gamma mapping for tick positions
cbar_ax = inset_axes(ax, width="25%", height="2.5%", loc='lower left',
                     bbox_to_anchor=(0.05, 0.04, 1, 1),
                     bbox_transform=ax.transAxes)

# The colorbar maps 0→1 in gamma space
# To place ticks at real values, convert: gamma_pos = (val / max_density)^GAMMA
norm = Normalize(vmin=0, vmax=1)
sm = cm.ScalarMappable(cmap=cmap_obj, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, cax=cbar_ax, orientation='horizontal')

# Place ticks at meaningful PhD per 10k values
tick_vals = [0.1, 1, 5, 20, 100]
tick_vals = [v for v in tick_vals if v <= max_density]
tick_positions = [(v / max_density) ** GAMMA for v in tick_vals]
cbar.set_ticks(tick_positions)
cbar.set_ticklabels([str(int(v)) if v >= 1 else str(v) for v in tick_vals])
cbar.ax.tick_params(labelsize=6.5, length=2, pad=2)
for label in cbar.ax.get_xticklabels():
    label.set_fontproperties(oracle_light)
cbar.outline.set_linewidth(0.5)
cbar.outline.set_edgecolor('#ccc')

ax.text(0.05, 0.10, 'PhDs per 10,000 adults',
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
print("Done.")
