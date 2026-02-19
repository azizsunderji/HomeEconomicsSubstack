#!/usr/bin/env python3
"""
PhD Hex Grid Map
================
Hexagonal grid map showing density of working PhDs (CS, Math, EE, Physics).
PUMA-level data aggregated into equal-area hex cells.
"""

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap, LogNorm
import numpy as np
import pandas as pd
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

# SVG settings for editable text
matplotlib.use('svg')
plt.rcParams['svg.fonttype'] = 'none'

# =============================================================================
# CONFIGURATION
# =============================================================================

TITLE = "Where America's AI-Ready PhDs Live"
SUBTITLE = "CS, math, EE, and physics doctoral holders per 10,000 adults"
SOURCE = "Source: ACS 5-Year (2019–2023) via IPUMS. Employed, not in school, doctoral degree holders."

OUTPUT_SVG = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/phd_hex_map.svg"
OUTPUT_PNG = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/phd_hex_map.png"

# Brand colors
BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
LAND_CREAM = '#EDEFE7'

ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']

# Hex size: distance from center to vertex in meters
# ~25 km ≈ 15 miles — gives good urban resolution
HEX_SIZE = 25000

# Font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
FONT_REGULAR = f"{FONT_DIR}/ABCOracle-Regular.otf"
FONT_BOLD = f"{FONT_DIR}/ABCOracle-Bold.otf"
FONT_LIGHT = f"{FONT_DIR}/ABCOracle-Light.otf"
FONT_MEDIUM = f"{FONT_DIR}/ABCOracle-Medium.otf"

# Data paths
IPUMS_5YR = '/tmp/ipums_degfield_5yr.csv.gz'
PUMA_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/InsuranceCosts/cb_2020_us_puma20_500k.shp'
STATE_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp'

# =============================================================================
# LOAD DATA
# =============================================================================

print("Loading PhD data at PUMA level...")
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

# Also get total population per PUMA for per-capita
puma_pop = conn.execute("""
    SELECT
        STATEFIP,
        PUMA,
        SUM(CASE WHEN AGE >= 25 THEN PERWT ELSE 0 END) as pop_25plus
    FROM read_csv_auto('{path}')
    GROUP BY STATEFIP, PUMA
""".format(path=IPUMS_5YR)).df()

# Start from ALL PUMAs (population), then left-join PhD counts
# This ensures hex cells get proper population denominators even where PhDs = 0
puma_pop['puma_key'] = puma_pop['STATEFIP'].astype(str).str.zfill(2) + puma_pop['PUMA'].astype(str).str.zfill(5)
puma_phds['puma_key'] = puma_phds['STATEFIP'].astype(str).str.zfill(2) + puma_phds['PUMA'].astype(str).str.zfill(5)
puma_data = puma_pop.merge(puma_phds[['puma_key', 'total_phds', 'raw_n']], on='puma_key', how='left')
puma_data['total_phds'] = puma_data['total_phds'].fillna(0)
puma_data['raw_n'] = puma_data['raw_n'].fillna(0)

print(f"Total PUMAs: {len(puma_data)} ({(puma_data['total_phds'] > 0).sum()} with PhDs)")
print(f"Total PhDs: {puma_data['total_phds'].sum():,.0f}")

# Load PUMA shapefile
print("Loading PUMA shapefile...")
pumas = gpd.read_file(PUMA_SHAPEFILE)
print(f"PUMA shapefile columns: {pumas.columns.tolist()}")

# Build matching key: STATEFP20 + PUMACE20
pumas['puma_key'] = pumas['STATEFP20'] + pumas['PUMACE20']
pumas = pumas.to_crs(ALBERS)

# Compute PUMA centroids
pumas['centroid'] = pumas.geometry.centroid
puma_centroids = pumas[['puma_key', 'centroid']].copy()

# Merge PhD data with centroids
puma_merged = puma_data.merge(puma_centroids, on='puma_key', how='inner')
print(f"Matched PUMAs: {len(puma_merged)} of {len(puma_data)}")
print(f"PhDs in matched PUMAs: {puma_merged['total_phds'].sum():,.0f}")

# Load states
print("Loading state boundaries...")
states = gpd.read_file(STATE_SHAPEFILE)
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)
us_boundary = unary_union(states.geometry)

# =============================================================================
# GENERATE HEX GRID
# =============================================================================

print("Generating hex grid...")

def create_hex(cx, cy, size):
    """Create a pointy-top hexagon centered at (cx, cy)."""
    angles = np.linspace(0, 2 * np.pi, 7)[:-1] + np.pi / 6
    points = [(cx + size * np.cos(a), cy + size * np.sin(a)) for a in angles]
    return Polygon(points)

# Grid bounds from states
bounds = states.total_bounds  # minx, miny, maxx, maxy
pad = HEX_SIZE * 2
minx, miny, maxx, maxy = bounds[0] - pad, bounds[1] - pad, bounds[2] + pad, bounds[3] + pad

# Hex grid spacing (pointy-top hexagons)
dx = HEX_SIZE * np.sqrt(3)       # horizontal distance between centers
dy = HEX_SIZE * 1.5              # vertical distance between rows

hexagons = []
hex_centers = []
row = 0
y = miny
while y <= maxy:
    x_offset = (dx / 2) if (row % 2) else 0
    x = minx + x_offset
    while x <= maxx:
        center = Point(x, y)
        # Only keep hexes that intersect US land
        hex_poly = create_hex(x, y, HEX_SIZE)
        if hex_poly.intersects(us_boundary):
            hexagons.append(hex_poly)
            hex_centers.append((x, y))
        x += dx
    y += dy
    row += 1

print(f"Hexes covering US: {len(hexagons)}")

hex_gdf = gpd.GeoDataFrame(
    {'hex_id': range(len(hexagons))},
    geometry=hexagons,
    crs=states.crs
)

# Hex area in square miles
hex_area_sq_mi = (HEX_SIZE ** 2 * np.sqrt(3) * 3 / 2) / 2589988
print(f"Hex area: {hex_area_sq_mi:.0f} sq miles each")

# =============================================================================
# ASSIGN PUMA DATA TO HEXES
# =============================================================================

print("Assigning PUMA data to hex cells...")

# Create GeoDataFrame of PUMA centroids with PhD data
puma_points = gpd.GeoDataFrame(
    puma_merged[['puma_key', 'total_phds', 'pop_25plus', 'raw_n']],
    geometry=[Point(row['centroid'].x, row['centroid'].y) for _, row in puma_merged.iterrows()],
    crs=states.crs
)

# Spatial join: which hex does each PUMA centroid fall in?
joined = gpd.sjoin(puma_points, hex_gdf, how='left', predicate='within')

# Aggregate by hex
hex_data = joined.groupby('hex_id').agg(
    total_phds=('total_phds', 'sum'),
    pop_25plus=('pop_25plus', 'sum'),
    raw_n=('raw_n', 'sum'),
    n_pumas=('puma_key', 'count')
).reset_index()

# Merge back to hex geometries
hex_gdf = hex_gdf.merge(hex_data, on='hex_id', how='left')
hex_gdf['total_phds'] = hex_gdf['total_phds'].fillna(0)
hex_gdf['pop_25plus'] = hex_gdf['pop_25plus'].fillna(0)
hex_gdf['phds_per_10k'] = np.where(
    hex_gdf['pop_25plus'] > 0,
    hex_gdf['total_phds'] / hex_gdf['pop_25plus'] * 10000,
    0
)

# Stats
has_phds = hex_gdf[hex_gdf['total_phds'] > 0]
print(f"Hexes with PhDs: {len(has_phds)} of {len(hex_gdf)}")
print(f"PhDs per 10k range (nonzero): {has_phds['phds_per_10k'].min():.1f} to {has_phds['phds_per_10k'].max():.0f}")
print(f"Top 5 hexes:")
for _, r in has_phds.nlargest(5, 'phds_per_10k').iterrows():
    print(f"  {r['phds_per_10k']:.0f}/10k, {r['total_phds']:,.0f} PhDs, {r['pop_25plus']:,.0f} pop, {int(r['n_pumas'])} PUMAs")

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

# No background map — let the hexes define the shape of the US

# Custom colormap
cmap = LinearSegmentedColormap.from_list('phd_hex', [
    '#CEEAFF',    # lighter blue (lowest)
    '#5CC8FF',    # medium-light blue
    '#0BB4FF',    # brand blue
    '#0077CC',    # darker blue
    '#3D3733',    # brand black
], N=256)

# Split into hexes with and without PhDs
hex_plot = hex_gdf[hex_gdf['total_phds'] > 0].copy()
hex_empty = hex_gdf[hex_gdf['total_phds'] == 0]

# Log scale for color — per 10k adults
hex_plot['log_concentration'] = np.log10(hex_plot['phds_per_10k'].clip(lower=0.1))

vmin = np.log10(0.1)
vmax = np.log10(hex_plot['phds_per_10k'].max())

# Draw empty hexes in lightest blue so whole map looks filled
hex_empty.plot(ax=ax, facecolor='#CEEAFF', edgecolor='white', linewidth=0.3, zorder=1)

# Draw PhD hexes on top
hex_plot.plot(
    ax=ax,
    column='log_concentration',
    cmap=cmap,
    vmin=vmin,
    vmax=vmax,
    edgecolor='white',
    linewidth=0.3,
    zorder=2
)

# Bounds
sb = states.total_bounds
ax.set_xlim(sb[0] - 100000, sb[2] + 100000)
ax.set_ylim(sb[1] - 100000, sb[3] + 100000)
ax.set_aspect('equal')
ax.axis('off')

# =============================================================================
# LABELS
# =============================================================================

from pyproj import Transformer

# Transform lat/lon to Albers
transformer = Transformer.from_crs('EPSG:4326', ALBERS, always_xy=True)

# Key cities: (name, lon, lat, x_offset, y_offset)
label_cities = [
    # Major tech hubs
    ('Bay Area',      -122.0,  37.4,   180000,  -120000),
    ('Seattle',       -122.33, 47.61,  120000,  -60000),
    ('Los Angeles',   -118.24, 34.05, -300000,  -80000),
    ('New York',      -74.01,  40.71,  150000,   50000),
    ('Boston',        -71.06,  42.36,  130000,  -50000),
    ('Washington',    -77.04,  38.91,  180000,   70000),
    ('San Diego',     -117.16, 32.72, -250000,   50000),
    # Less obvious / research towns
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

    # Leader line
    ax.plot([px, px + ox], [py, py + oy],
            color=BLACK, linewidth=0.5, alpha=0.5, zorder=6)

    # Dot at city location
    ax.plot(px, py, 'o', color=BLACK, markersize=2, zorder=7)

    # Label
    ha = 'left' if ox > 0 else 'right'
    ax.text(px + ox, py + oy, name,
            fontproperties=oracle_regular, fontsize=6.5,
            color=BLACK, ha=ha, va='center', zorder=7)

# =============================================================================
# COLOR BAR
# =============================================================================

from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import matplotlib.cm as cm

cbar_ax = inset_axes(ax, width="25%", height="2.5%", loc='lower left',
                     bbox_to_anchor=(0.05, 0.04, 1, 1),
                     bbox_transform=ax.transAxes)

norm = matplotlib.colors.Normalize(vmin=vmin, vmax=vmax)
sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])

cbar = fig.colorbar(sm, cax=cbar_ax, orientation='horizontal')
tick_vals = [0.1, 1, 10, 100]
tick_vals = [v for v in tick_vals if np.log10(v) <= vmax]
cbar.set_ticks([np.log10(v) for v in tick_vals])
cbar.set_ticklabels([str(int(v)) if v >= 1 else str(v) for v in tick_vals])
cbar.ax.tick_params(labelsize=6.5, length=2, pad=2)
for label in cbar.ax.get_xticklabels():
    label.set_fontproperties(oracle_light)
cbar.outline.set_linewidth(0.5)
cbar.outline.set_edgecolor('#ccc')

ax.text(0.05, 0.10, 'PhDs per 10,000 adults (log scale)',
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
