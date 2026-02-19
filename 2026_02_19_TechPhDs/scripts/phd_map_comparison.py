#!/usr/bin/env python3
"""
PhD Map Comparison: 4 Approaches
=================================
1. Hex map with population threshold (25km, only color cells with 25k+ adults)
2. Kernel density estimation (smooth continuous surface)
3. Raw PUMA choropleth (color PUMAs directly)
4. 40km hex map (larger hexes)

All use PhDs per 10,000 adults 25+ (per-capita metric).
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
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from pyproj import Transformer
from scipy.ndimage import gaussian_filter

# SVG settings
matplotlib.use('svg')
plt.rcParams['svg.fonttype'] = 'none'

# =============================================================================
# CONFIGURATION
# =============================================================================

SOURCE = "Source: ACS 5-Year (2019-2023) via IPUMS. Employed, not in school, doctoral degree holders."
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'

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

OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs"

# Colormap
cmap = LinearSegmentedColormap.from_list('phd_hex', [
    '#CEEAFF', '#5CC8FF', '#0BB4FF', '#0077CC', '#3D3733'
], N=256)

# =============================================================================
# LOAD DATA (shared across all 4 maps)
# =============================================================================

print("=" * 60)
print("Loading data...")
conn = duckdb.connect()

puma_phds = conn.execute("""
    SELECT
        STATEFIP,
        PUMA,
        SUM(PERWT) as total_phds,
        COUNT(*) as raw_n
    FROM read_csv_auto('{path}')
    WHERE EDUCD = 116
      AND EMPSTAT = 1
      AND SCHOOL = 1
      AND (DEGFIELD IN (21, 37) OR DEGFIELDD IN (2407, 2408, 5007))
    GROUP BY STATEFIP, PUMA
""".format(path=IPUMS_5YR)).df()

puma_pop = conn.execute("""
    SELECT
        STATEFIP,
        PUMA,
        SUM(CASE WHEN AGE >= 25 THEN PERWT ELSE 0 END) as pop_25plus
    FROM read_csv_auto('{path}')
    GROUP BY STATEFIP, PUMA
""".format(path=IPUMS_5YR)).df()

# Merge
puma_pop['puma_key'] = puma_pop['STATEFIP'].astype(str).str.zfill(2) + puma_pop['PUMA'].astype(str).str.zfill(5)
puma_phds['puma_key'] = puma_phds['STATEFIP'].astype(str).str.zfill(2) + puma_phds['PUMA'].astype(str).str.zfill(5)
puma_data = puma_pop.merge(puma_phds[['puma_key', 'total_phds', 'raw_n']], on='puma_key', how='left')
puma_data['total_phds'] = puma_data['total_phds'].fillna(0)
puma_data['raw_n'] = puma_data['raw_n'].fillna(0)
puma_data['phds_per_10k'] = np.where(
    puma_data['pop_25plus'] > 0,
    puma_data['total_phds'] / puma_data['pop_25plus'] * 10000,
    0
)

print(f"Total PUMAs: {len(puma_data)} ({(puma_data['total_phds'] > 0).sum()} with PhDs)")
print(f"Total PhDs: {puma_data['total_phds'].sum():,.0f}")

# Load PUMA shapefile
print("Loading PUMA shapefile...")
pumas = gpd.read_file(PUMA_SHAPEFILE)
pumas['puma_key'] = pumas['STATEFP20'] + pumas['PUMACE20']
pumas = pumas.to_crs(ALBERS)
pumas['centroid'] = pumas.geometry.centroid

# Merge PhD data with PUMA geometries (for PUMA choropleth)
puma_geo = pumas.merge(puma_data, on='puma_key', how='inner')

# Merge PhD data with centroids (for hex maps)
puma_centroids = pumas[['puma_key', 'centroid']].copy()
puma_merged = puma_data.merge(puma_centroids, on='puma_key', how='inner')
print(f"Matched PUMAs: {len(puma_merged)} of {len(puma_data)}")

# Load states
print("Loading state boundaries...")
states = gpd.read_file(STATE_SHAPEFILE)
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)
us_boundary = unary_union(states.geometry)

# Lat/lon to Albers transformer
transformer = Transformer.from_crs('EPSG:4326', ALBERS, always_xy=True)

# Shared label cities
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

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_hex(cx, cy, size):
    """Pointy-top hexagon."""
    angles = np.linspace(0, 2 * np.pi, 7)[:-1] + np.pi / 6
    points = [(cx + size * np.cos(a), cy + size * np.sin(a)) for a in angles]
    return Polygon(points)

def make_hex_grid(hex_size):
    """Generate hex grid covering US, assign PUMA data, return GeoDataFrame."""
    bounds = states.total_bounds
    pad = hex_size * 2
    minx, miny, maxx, maxy = bounds[0] - pad, bounds[1] - pad, bounds[2] + pad, bounds[3] + pad

    dx = hex_size * np.sqrt(3)
    dy = hex_size * 1.5

    hexagons = []
    hex_centers = []
    row = 0
    y = miny
    while y <= maxy:
        x_offset = (dx / 2) if (row % 2) else 0
        x = minx + x_offset
        while x <= maxx:
            hex_poly = create_hex(x, y, hex_size)
            if hex_poly.intersects(us_boundary):
                hexagons.append(hex_poly)
                hex_centers.append((x, y))
            x += dx
        y += dy
        row += 1

    hex_gdf = gpd.GeoDataFrame(
        {'hex_id': range(len(hexagons))},
        geometry=hexagons, crs=states.crs
    )

    # Assign PUMA data
    puma_points = gpd.GeoDataFrame(
        puma_merged[['puma_key', 'total_phds', 'pop_25plus', 'raw_n']],
        geometry=[Point(row['centroid'].x, row['centroid'].y) for _, row in puma_merged.iterrows()],
        crs=states.crs
    )
    joined = gpd.sjoin(puma_points, hex_gdf, how='left', predicate='within')
    hex_data_agg = joined.groupby('hex_id').agg(
        total_phds=('total_phds', 'sum'),
        pop_25plus=('pop_25plus', 'sum'),
        raw_n=('raw_n', 'sum'),
        n_pumas=('puma_key', 'count')
    ).reset_index()

    hex_gdf = hex_gdf.merge(hex_data_agg, on='hex_id', how='left')
    hex_gdf['total_phds'] = hex_gdf['total_phds'].fillna(0)
    hex_gdf['pop_25plus'] = hex_gdf['pop_25plus'].fillna(0)
    hex_gdf['phds_per_10k'] = np.where(
        hex_gdf['pop_25plus'] > 0,
        hex_gdf['total_phds'] / hex_gdf['pop_25plus'] * 10000,
        0
    )

    hex_area_sq_mi = (hex_size ** 2 * np.sqrt(3) * 3 / 2) / 2589988
    print(f"  Hex size: {hex_size/1000:.0f}km, area: {hex_area_sq_mi:.0f} sq mi, count: {len(hex_gdf)}")
    return hex_gdf

def add_labels(ax, fontprops, fontsize=6.5, scale=1.0):
    """Add city labels with leader lines."""
    for name, lon, lat, ox, oy in label_cities:
        px, py = transformer.transform(lon, lat)
        ox_s, oy_s = ox * scale, oy * scale
        ax.plot([px, px + ox_s], [py, py + oy_s],
                color=BLACK, linewidth=0.5, alpha=0.5, zorder=6)
        ax.plot(px, py, 'o', color=BLACK, markersize=2, zorder=7)
        ha = 'left' if ox_s > 0 else 'right'
        ax.text(px + ox_s, py + oy_s, name,
                fontproperties=fontprops, fontsize=fontsize,
                color=BLACK, ha=ha, va='center', zorder=7)

def add_colorbar(fig, ax, vmin, vmax, fontprops_light, fontprops_medium, label='PhDs per 10,000 adults (log scale)'):
    """Add a standard colorbar."""
    cbar_ax = inset_axes(ax, width="25%", height="2.5%", loc='lower left',
                         bbox_to_anchor=(0.05, 0.04, 1, 1),
                         bbox_transform=ax.transAxes)
    norm = Normalize(vmin=vmin, vmax=vmax)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax, orientation='horizontal')
    tick_vals = [0.1, 1, 10, 100]
    tick_vals = [v for v in tick_vals if np.log10(v) <= vmax]
    cbar.set_ticks([np.log10(v) for v in tick_vals])
    cbar.set_ticklabels([str(int(v)) if v >= 1 else str(v) for v in tick_vals])
    cbar.ax.tick_params(labelsize=6.5, length=2, pad=2)
    for label_tick in cbar.ax.get_xticklabels():
        label_tick.set_fontproperties(fontprops_light)
    cbar.outline.set_linewidth(0.5)
    cbar.outline.set_edgecolor('#ccc')
    ax.text(0.05, 0.10, label,
            transform=ax.transAxes, fontproperties=fontprops_medium,
            fontsize=7.5, color=BLACK)

def add_title_source(ax, title, subtitle, source, fontprops_bold, fontprops_light):
    """Add title, subtitle, source."""
    ax.text(0.5, 0.97, title,
            transform=ax.transAxes, ha='center', va='top',
            fontproperties=fontprops_bold, fontsize=14, color=BLACK)
    ax.text(0.5, 0.935, subtitle,
            transform=ax.transAxes, ha='center', va='top',
            fontproperties=fontprops_light, fontsize=9, color='#888')
    ax.text(0.98, 0.02, source,
            transform=ax.transAxes, ha='right', va='bottom',
            fontproperties=fontprops_light, fontsize=6, fontstyle='italic', color='#aaa')

def set_bounds(ax):
    """Set standard US bounds."""
    sb = states.total_bounds
    ax.set_xlim(sb[0] - 100000, sb[2] + 100000)
    ax.set_ylim(sb[1] - 100000, sb[3] + 100000)
    ax.set_aspect('equal')
    ax.axis('off')

# Load fonts
oracle_regular = FontProperties(fname=FONT_REGULAR)
oracle_bold = FontProperties(fname=FONT_BOLD)
oracle_light = FontProperties(fname=FONT_LIGHT)
oracle_medium = FontProperties(fname=FONT_MEDIUM)


# =============================================================================
# MAP 1: HEX WITH POPULATION THRESHOLD (25km, min 25k adults)
# =============================================================================

print("\n" + "=" * 60)
print("MAP 1: Hex with population threshold (25km, 25k+ adults)")
print("=" * 60)

hex_25k = make_hex_grid(25000)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Population threshold: only color hexes with 25k+ adults
POP_THRESHOLD = 25000
hex_colored = hex_25k[(hex_25k['total_phds'] > 0) & (hex_25k['pop_25plus'] >= POP_THRESHOLD)].copy()
hex_light = hex_25k[~hex_25k.index.isin(hex_colored.index)]  # everything else

hex_colored['log_c'] = np.log10(hex_colored['phds_per_10k'].clip(lower=0.1))
vmin = np.log10(0.1)
vmax = np.log10(hex_colored['phds_per_10k'].max())

hex_light.plot(ax=ax, facecolor='#CEEAFF', edgecolor='white', linewidth=0.3, zorder=1)
hex_colored.plot(ax=ax, column='log_c', cmap=cmap, vmin=vmin, vmax=vmax,
                 edgecolor='white', linewidth=0.3, zorder=2)

set_bounds(ax)
add_labels(ax, oracle_regular)
add_colorbar(fig, ax, vmin, vmax, oracle_light, oracle_medium)
add_title_source(ax, "Option 1: Population Threshold",
                 f"25km hexes, colored only where 25k+ adults. {len(hex_colored)} of {len(hex_25k)} hexes colored.",
                 SOURCE, oracle_bold, oracle_light)

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
out1_png = f"{OUTPUT_DIR}/phd_map_opt1_popthreshold.png"
fig.savefig(out1_png, format='png', dpi=200, facecolor=BG_CREAM, bbox_inches='tight')
print(f"Saved: {out1_png}")
plt.close()


# =============================================================================
# MAP 2: KERNEL DENSITY ESTIMATION
# =============================================================================

print("\n" + "=" * 60)
print("MAP 2: Kernel Density Estimation")
print("=" * 60)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Draw state borders as land
states.plot(ax=ax, facecolor='#EDEFE7', edgecolor='white', linewidth=0.75, zorder=1)

# Create density surface from PUMA centroids weighted by PhDs per 10k
sb = states.total_bounds
resolution = 500  # grid cells across
x_range = np.linspace(sb[0] - 50000, sb[2] + 50000, resolution)
y_range = np.linspace(sb[1] - 50000, sb[3] + 50000, resolution)

# Create empty grid
grid = np.zeros((len(y_range), len(x_range)))
weight_grid = np.zeros((len(y_range), len(x_range)))

# Place PUMA data on grid
for _, row in puma_merged.iterrows():
    cx, cy = row['centroid'].x, row['centroid'].y
    xi = np.searchsorted(x_range, cx)
    yi = np.searchsorted(y_range, cy)
    if 0 <= xi < len(x_range) and 0 <= yi < len(y_range):
        # Weight by PhD count, normalize by population
        grid[yi, xi] += row['total_phds']
        weight_grid[yi, xi] += row['pop_25plus']

# Apply Gaussian smoothing
# Sigma in grid cells — 40km / (grid cell size)
cell_size = (sb[2] - sb[0]) / resolution
sigma = 40000 / cell_size  # 40km smoothing radius

smoothed_phds = gaussian_filter(grid, sigma=sigma)
smoothed_pop = gaussian_filter(weight_grid, sigma=sigma)

# Per 10k ratio (avoiding divide by zero)
density = np.where(smoothed_pop > 100, smoothed_phds / smoothed_pop * 10000, np.nan)

# Mask outside US boundary
from shapely.vectorized import contains
xx, yy = np.meshgrid(x_range, y_range)
# We need to test which grid points are inside US
# For performance, test a subsample and interpolate
mask = np.zeros_like(density, dtype=bool)
for i in range(0, len(y_range), 5):
    for j in range(0, len(x_range), 5):
        pt = Point(x_range[j], y_range[i])
        if us_boundary.contains(pt):
            # Fill a 5x5 block
            mask[max(0,i-2):min(len(y_range),i+3), max(0,j-2):min(len(x_range),j+3)] = True

density_masked = np.where(mask, density, np.nan)

# Plot as image
vmin_kde = 0
vmax_kde = np.nanpercentile(density_masked[density_masked > 0], 99)
im = ax.imshow(density_masked, origin='lower',
               extent=[x_range[0], x_range[-1], y_range[0], y_range[-1]],
               cmap=cmap, vmin=vmin_kde, vmax=vmax_kde,
               aspect='auto', zorder=2, alpha=0.85)

# State borders on top
states.boundary.plot(ax=ax, edgecolor='white', linewidth=0.5, zorder=3)

set_bounds(ax)
add_labels(ax, oracle_regular)

# Linear colorbar for KDE
cbar_ax = inset_axes(ax, width="25%", height="2.5%", loc='lower left',
                     bbox_to_anchor=(0.05, 0.04, 1, 1),
                     bbox_transform=ax.transAxes)
cbar = fig.colorbar(im, cax=cbar_ax, orientation='horizontal')
cbar.ax.tick_params(labelsize=6.5, length=2, pad=2)
for label in cbar.ax.get_xticklabels():
    label.set_fontproperties(oracle_light)
cbar.outline.set_linewidth(0.5)
cbar.outline.set_edgecolor('#ccc')
ax.text(0.05, 0.10, 'PhDs per 10,000 adults (smoothed)',
        transform=ax.transAxes, fontproperties=oracle_medium,
        fontsize=7.5, color=BLACK)

add_title_source(ax, "Option 2: Kernel Density",
                 f"Gaussian smoothing (40km radius) of PUMA-level PhD rates",
                 SOURCE, oracle_bold, oracle_light)

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
out2_png = f"{OUTPUT_DIR}/phd_map_opt2_kde.png"
fig.savefig(out2_png, format='png', dpi=200, facecolor=BG_CREAM, bbox_inches='tight')
print(f"Saved: {out2_png}")
plt.close()


# =============================================================================
# MAP 3: RAW PUMA CHOROPLETH
# =============================================================================

print("\n" + "=" * 60)
print("MAP 3: Raw PUMA Choropleth")
print("=" * 60)

# Filter to continental US
puma_plot = puma_geo[~puma_geo['STATEFP20'].isin(EXCLUDE_STATES)].copy()
puma_plot['log_c'] = np.where(
    puma_plot['phds_per_10k'] > 0,
    np.log10(puma_plot['phds_per_10k'].clip(lower=0.1)),
    np.nan
)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

vmin = np.log10(0.1)
vmax = np.log10(puma_plot['phds_per_10k'].max())

# PUMAs with no PhDs
puma_empty = puma_plot[puma_plot['total_phds'] == 0]
puma_with = puma_plot[puma_plot['total_phds'] > 0].copy()

puma_empty.plot(ax=ax, facecolor='#CEEAFF', edgecolor='white', linewidth=0.15, zorder=1)
puma_with.plot(ax=ax, column='log_c', cmap=cmap, vmin=vmin, vmax=vmax,
               edgecolor='white', linewidth=0.15, zorder=2)

# State borders for reference
states.boundary.plot(ax=ax, edgecolor='white', linewidth=0.5, zorder=3)

set_bounds(ax)
add_labels(ax, oracle_regular)
add_colorbar(fig, ax, vmin, vmax, oracle_light, oracle_medium)
add_title_source(ax, "Option 3: Raw PUMAs",
                 f"{len(puma_with)} PUMAs with PhDs, {len(puma_empty)} without. Irregular shapes/sizes.",
                 SOURCE, oracle_bold, oracle_light)

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
out3_png = f"{OUTPUT_DIR}/phd_map_opt3_puma.png"
fig.savefig(out3_png, format='png', dpi=200, facecolor=BG_CREAM, bbox_inches='tight')
print(f"Saved: {out3_png}")
plt.close()


# =============================================================================
# MAP 4: 40km HEX MAP
# =============================================================================

print("\n" + "=" * 60)
print("MAP 4: 40km Hex Map")
print("=" * 60)

hex_40k = make_hex_grid(40000)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

hex_plot = hex_40k[hex_40k['total_phds'] > 0].copy()
hex_empty = hex_40k[hex_40k['total_phds'] == 0]

hex_plot['log_c'] = np.log10(hex_plot['phds_per_10k'].clip(lower=0.1))
vmin = np.log10(0.1)
vmax = np.log10(hex_plot['phds_per_10k'].max())

hex_empty.plot(ax=ax, facecolor='#CEEAFF', edgecolor='white', linewidth=0.3, zorder=1)
hex_plot.plot(ax=ax, column='log_c', cmap=cmap, vmin=vmin, vmax=vmax,
              edgecolor='white', linewidth=0.3, zorder=2)

set_bounds(ax)
add_labels(ax, oracle_regular)
add_colorbar(fig, ax, vmin, vmax, oracle_light, oracle_medium)

hex_area_sq_mi = (40000 ** 2 * np.sqrt(3) * 3 / 2) / 2589988
add_title_source(ax, "Option 4: 40km Hexes",
                 f"~{hex_area_sq_mi:.0f} sq mi per hex. {len(hex_plot)} with PhDs, {len(hex_empty)} empty.",
                 SOURCE, oracle_bold, oracle_light)

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
out4_png = f"{OUTPUT_DIR}/phd_map_opt4_hex40km.png"
fig.savefig(out4_png, format='png', dpi=200, facecolor=BG_CREAM, bbox_inches='tight')
print(f"Saved: {out4_png}")
plt.close()

print("\n" + "=" * 60)
print("ALL DONE. Compare:")
print(f"  1. {out1_png}")
print(f"  2. {out2_png}")
print(f"  3. {out3_png}")
print(f"  4. {out4_png}")
print("=" * 60)
