#!/usr/bin/env python3
"""
PhD Bivariate Hex Grid Map
===========================
Two-axis hex map:
  - Density axis (PhDs per sq mi): cream -> blue
  - Growth axis (% change 2010->2024): cream -> yellow
  - Both high: green

Legend is a 3x3 color grid.
"""

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle
from matplotlib.colors import to_hex
import numpy as np
import pandas as pd
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

matplotlib.use('svg')
plt.rcParams['svg.fonttype'] = 'none'

# =============================================================================
# CONFIGURATION
# =============================================================================

TITLE = "Where America's AI-Ready PhDs Live — and Where They're Moving"
SUBTITLE = "Blue = concentrated. Yellow = fast-growing since 2019. Green = both."
SOURCE = "Source: ACS 5-Year (2019–2023) and 1-Year (2018–2024) via IPUMS."

OUTPUT_SVG = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/phd_bivariate_hex_map.svg"
OUTPUT_PNG = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/phd_bivariate_hex_map.png"

BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'

ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']

HEX_SIZE = 25000

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
FONT_REGULAR = f"{FONT_DIR}/ABCOracle-Regular.otf"
FONT_BOLD = f"{FONT_DIR}/ABCOracle-Bold.otf"
FONT_LIGHT = f"{FONT_DIR}/ABCOracle-Light.otf"
FONT_MEDIUM = f"{FONT_DIR}/ABCOracle-Medium.otf"

IPUMS_5YR = '/tmp/ipums_degfield_5yr.csv.gz'
MULTIYEAR_PARQUET = '/Users/azizsunderji/Dropbox/Home Economics/Data/IPUMS/acs_1y_degfield_multiyear.parquet'
PUMA_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/InsuranceCosts/cb_2020_us_puma20_500k.shp'
STATE_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp'

# =============================================================================
# BIVARIATE COLOR SCHEME
# =============================================================================

# Four corners (RGB 0-1)
# density increases bottom->top, growth increases left->right
C_LL = np.array([237, 239, 231]) / 255  # cream (low density, low growth)
C_HL = np.array([11, 180, 255]) / 255   # blue (high density, low growth)
C_LH = np.array([254, 196, 57]) / 255   # yellow (low density, high growth)
C_HH = np.array([103, 162, 117]) / 255  # green (both high)

EMPTY_HEX_COLOR = '#E0E2DA'


def bivariate_color(s, g):
    """Bilinear interpolation. s=density [0,1], g=growth [0,1]."""
    c = (1-s)*(1-g)*C_LL + s*(1-g)*C_HL + (1-s)*g*C_LH + s*g*C_HH
    return np.clip(c, 0, 1)


# Pre-compute 3x3 grid
BV_GRID = {}
for si in range(3):
    for gi in range(3):
        c = bivariate_color(si / 2, gi / 2)
        BV_GRID[(si, gi)] = to_hex(c)

print("Bivariate color grid:")
for si in [2, 1, 0]:
    row = [BV_GRID[(si, gi)] for gi in range(3)]
    labels = ['Low', 'Med', 'High']
    print(f"  Density {labels[si]:>4s}: {row}")

# =============================================================================
# LOAD DATA
# =============================================================================

print("\nLoading PhD data at PUMA level...")
conn = duckdb.connect()

puma_phds = conn.execute("""
    SELECT
        STATEFIP, PUMA,
        SUM(PERWT) as total_phds,
        COUNT(*) as raw_n,
        MODE(MET2013) as met2013
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

puma_data = puma_phds.merge(puma_pop, on=['STATEFIP', 'PUMA'], how='left')
puma_data['puma_key'] = (puma_data['STATEFIP'].astype(str).str.zfill(2)
                         + puma_data['PUMA'].astype(str).str.zfill(5))

print(f"PUMAs with PhDs: {len(puma_data)}")
print(f"Total PhDs: {puma_data['total_phds'].sum():,.0f}")

# =============================================================================
# COMPUTE GROWTH RATES (metro-level, state-level fallback)
# =============================================================================

print("\nComputing metro-level growth rates (2018-19 vs 2023-24)...")

# Metro-level growth (lower threshold to 50 for broader coverage)
metro_growth = conn.execute("""
    WITH early AS (
        SELECT MET2013 as msa_code,
               SUM(PERWT) / 2.0 as phds_early_avg
        FROM read_parquet('{path}')
        WHERE EDUCD = 116 AND EMPSTAT = 1 AND SCHOOL = 1 AND MET2013 > 0
          AND (DEGFIELD IN (21, 37) OR DEGFIELDD IN (2407, 2408, 5007))
          AND YEAR IN (2018, 2019)
        GROUP BY MET2013
    ),
    late AS (
        SELECT MET2013 as msa_code,
               SUM(PERWT) / 2.0 as phds_late_avg
        FROM read_parquet('{path}')
        WHERE EDUCD = 116 AND EMPSTAT = 1 AND SCHOOL = 1 AND MET2013 > 0
          AND (DEGFIELD IN (21, 37) OR DEGFIELDD IN (2407, 2408, 5007))
          AND YEAR IN (2023, 2024)
        GROUP BY MET2013
    )
    SELECT
        e.msa_code,
        e.phds_early_avg as phds_early,
        COALESCE(l.phds_late_avg, 0) as phds_late,
        (COALESCE(l.phds_late_avg, 0) / e.phds_early_avg - 1) * 100 as pct_growth
    FROM early e
    LEFT JOIN late l ON e.msa_code = l.msa_code
    WHERE e.phds_early_avg >= 50
""".format(path=MULTIYEAR_PARQUET)).df()

print(f"Metros with growth data: {len(metro_growth)}")

# State-level growth as fallback for non-metro PUMAs
state_growth = conn.execute("""
    WITH early AS (
        SELECT STATEFIP,
               SUM(PERWT) / 2.0 as phds_early_avg
        FROM read_parquet('{path}')
        WHERE EDUCD = 116 AND EMPSTAT = 1 AND SCHOOL = 1
          AND (DEGFIELD IN (21, 37) OR DEGFIELDD IN (2407, 2408, 5007))
          AND YEAR IN (2018, 2019)
        GROUP BY STATEFIP
        HAVING SUM(PERWT) / 2.0 >= 20
    ),
    late AS (
        SELECT STATEFIP,
               SUM(PERWT) / 2.0 as phds_late_avg
        FROM read_parquet('{path}')
        WHERE EDUCD = 116 AND EMPSTAT = 1 AND SCHOOL = 1
          AND (DEGFIELD IN (21, 37) OR DEGFIELDD IN (2407, 2408, 5007))
          AND YEAR IN (2023, 2024)
        GROUP BY STATEFIP
    )
    SELECT
        e.STATEFIP,
        (COALESCE(l.phds_late_avg, 0) / e.phds_early_avg - 1) * 100 as state_pct_growth
    FROM early e
    LEFT JOIN late l ON e.STATEFIP = l.STATEFIP
""".format(path=MULTIYEAR_PARQUET)).df()

print(f"States with growth data: {len(state_growth)}")

# National average growth as final fallback
national_early = metro_growth['phds_early'].sum()
national_late = metro_growth['phds_late'].sum()
national_growth = (national_late / national_early - 1) * 100
print(f"National PhD growth: {national_growth:.0f}%")

# Merge metro growth onto PUMA data
puma_data = puma_data.merge(
    metro_growth[['msa_code', 'pct_growth']],
    left_on='met2013', right_on='msa_code', how='left'
)

# State-level fallback for unmatched PUMAs
puma_data = puma_data.merge(
    state_growth, on='STATEFIP', how='left'
)
puma_data['pct_growth'] = puma_data['pct_growth'].fillna(puma_data['state_pct_growth'])
puma_data['pct_growth'] = puma_data['pct_growth'].fillna(national_growth)

n_metro = puma_data['msa_code'].notna().sum()
n_state = (puma_data['msa_code'].isna() & puma_data['state_pct_growth'].notna()).sum()
n_national = (puma_data['msa_code'].isna() & puma_data['state_pct_growth'].isna()).sum()
print(f"Growth source: {n_metro} metro, {n_state} state fallback, {n_national} national fallback")

# =============================================================================
# LOAD SHAPEFILES
# =============================================================================

print("\nLoading PUMA shapefile...")
pumas = gpd.read_file(PUMA_SHAPEFILE)
pumas['puma_key'] = pumas['STATEFP20'] + pumas['PUMACE20']
pumas = pumas.to_crs(ALBERS)
pumas['centroid'] = pumas.geometry.centroid
puma_centroids = pumas[['puma_key', 'centroid']].copy()

puma_merged = puma_data.merge(puma_centroids, on='puma_key', how='inner')
print(f"Matched PUMAs: {len(puma_merged)} of {len(puma_data)}")
print(f"PhDs in matched PUMAs: {puma_merged['total_phds'].sum():,.0f}")

print("Loading state boundaries...")
states = gpd.read_file(STATE_SHAPEFILE)
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)
us_boundary = unary_union(states.geometry)

# =============================================================================
# GENERATE HEX GRID
# =============================================================================

print("\nGenerating hex grid...")


def create_hex(cx, cy, size):
    """Create a pointy-top hexagon centered at (cx, cy)."""
    angles = np.linspace(0, 2 * np.pi, 7)[:-1] + np.pi / 6
    points = [(cx + size * np.cos(a), cy + size * np.sin(a)) for a in angles]
    return Polygon(points)


bounds = states.total_bounds
pad = HEX_SIZE * 2
minx, miny, maxx, maxy = bounds[0]-pad, bounds[1]-pad, bounds[2]+pad, bounds[3]+pad

dx = HEX_SIZE * np.sqrt(3)
dy = HEX_SIZE * 1.5

hexagons = []
hex_centers = []
row = 0
y = miny
while y <= maxy:
    x_offset = (dx / 2) if (row % 2) else 0
    x = minx + x_offset
    while x <= maxx:
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

hex_area_sq_mi = (HEX_SIZE ** 2 * np.sqrt(3) * 3 / 2) / 2589988
print(f"Hex area: {hex_area_sq_mi:.0f} sq miles each")

# =============================================================================
# ASSIGN PUMA DATA TO HEXES
# =============================================================================

print("\nAssigning PUMA data to hex cells...")

puma_points = gpd.GeoDataFrame(
    puma_merged[['puma_key', 'total_phds', 'pop_25plus', 'raw_n', 'pct_growth']],
    geometry=[Point(row['centroid'].x, row['centroid'].y) for _, row in puma_merged.iterrows()],
    crs=states.crs
)

joined = gpd.sjoin(puma_points, hex_gdf, how='left', predicate='within')

# Aggregate by hex
# For growth: PhD-weighted average
def weighted_growth(group):
    weights = group['total_phds']
    if weights.sum() == 0:
        return national_growth
    return np.average(group['pct_growth'], weights=weights)


hex_data = joined.groupby('hex_id').agg(
    total_phds=('total_phds', 'sum'),
    pop_25plus=('pop_25plus', 'sum'),
    raw_n=('raw_n', 'sum'),
    n_pumas=('puma_key', 'count'),
).reset_index()

# Compute weighted growth separately
hex_growth = joined.groupby('hex_id').apply(weighted_growth).reset_index()
hex_growth.columns = ['hex_id', 'growth_rate']

hex_data = hex_data.merge(hex_growth, on='hex_id', how='left')

# Merge back to hex geometries
hex_gdf = hex_gdf.merge(hex_data, on='hex_id', how='left')
hex_gdf['total_phds'] = hex_gdf['total_phds'].fillna(0)
hex_gdf['phds_per_sq_mi'] = hex_gdf['total_phds'] / hex_area_sq_mi
hex_gdf['growth_rate'] = hex_gdf['growth_rate'].fillna(0)

# Stats
has_phds = hex_gdf[hex_gdf['total_phds'] > 0].copy()
print(f"\nHexes with PhDs: {len(has_phds)} of {len(hex_gdf)}")
print(f"Density range: {has_phds['phds_per_sq_mi'].min():.2f} to {has_phds['phds_per_sq_mi'].max():.1f} PhDs/mi²")
print(f"Growth range: {has_phds['growth_rate'].min():.0f}% to {has_phds['growth_rate'].max():.0f}%")

# =============================================================================
# CLASSIFY INTO 3x3 BINS
# =============================================================================

print("\nClassifying hexes into bivariate bins...")

# Density: quantile terciles (well-distributed)
density_vals = has_phds['phds_per_sq_mi']
d_breaks = [density_vals.quantile(1/3), density_vals.quantile(2/3)]

# Growth: fixed meaningful breaks for 5-year window (2018-19 vs 2023-24)
# < 0% = shrinking, 0-50% = modest growth, > 50% = strong growth
g_breaks = [0, 50]

print(f"Density breaks: {d_breaks[0]:.2f}, {d_breaks[1]:.2f} PhDs/mi²")
print(f"Growth breaks: {g_breaks[0]}%, {g_breaks[1]}% (fixed: shrinking | modest | strong)")

# Show growth distribution
for label, lo, hi in [('< 0% (shrinking)', -999, 0), ('0-50% (modest)', 0, 50), ('> 50% (strong)', 50, 999)]:
    n = len(has_phds[(has_phds['growth_rate'] > lo) & (has_phds['growth_rate'] <= hi)])
    print(f"  Growth {label}: {n} hexes")


def classify(val, breaks):
    if val <= breaks[0]:
        return 0
    if val <= breaks[1]:
        return 1
    return 2


has_phds = has_phds.copy()
has_phds['d_bin'] = has_phds['phds_per_sq_mi'].apply(lambda v: classify(v, d_breaks))
has_phds['g_bin'] = has_phds['growth_rate'].apply(lambda v: classify(v, g_breaks))
has_phds['bv_color'] = has_phds.apply(lambda r: BV_GRID[(r['d_bin'], r['g_bin'])], axis=1)

# Distribution
print("\nBivariate distribution:")
labels = ['Low', 'Med', 'High']
for si in [2, 1, 0]:
    counts = []
    for gi in range(3):
        n = len(has_phds[(has_phds['d_bin'] == si) & (has_phds['g_bin'] == gi)])
        counts.append(f"{n:>4d}")
    print(f"  Density {labels[si]:>4s}: {' | '.join(counts)}  (Growth: Low | Med | High)")

# Merge colors back to full hex gdf
hex_gdf = hex_gdf.merge(
    has_phds[['hex_id', 'd_bin', 'g_bin', 'bv_color']],
    on='hex_id', how='left'
)

# =============================================================================
# CREATE FIGURE
# =============================================================================

print("\nCreating figure...")
oracle_regular = FontProperties(fname=FONT_REGULAR)
oracle_bold = FontProperties(fname=FONT_BOLD)
oracle_light = FontProperties(fname=FONT_LIGHT)
oracle_medium = FontProperties(fname=FONT_MEDIUM)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Draw empty hexes
hex_empty = hex_gdf[hex_gdf['total_phds'] == 0]
hex_empty.plot(ax=ax, facecolor=EMPTY_HEX_COLOR, edgecolor='white', linewidth=0.3, zorder=1)

# Draw PhD hexes colored by bivariate class
hex_with = hex_gdf[hex_gdf['total_phds'] > 0].copy()

# Plot each bivariate class separately for correct coloring
for (d_bin, g_bin), color in BV_GRID.items():
    subset = hex_with[(hex_with['d_bin'] == d_bin) & (hex_with['g_bin'] == g_bin)]
    if len(subset) > 0:
        subset.plot(ax=ax, facecolor=color, edgecolor='white', linewidth=0.3, zorder=2)

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
    ax.plot([px, px + ox], [py, py + oy],
            color=BLACK, linewidth=0.5, alpha=0.5, zorder=6)
    ax.plot(px, py, 'o', color=BLACK, markersize=2, zorder=7)
    ha = 'left' if ox > 0 else 'right'
    ax.text(px + ox, py + oy, name,
            fontproperties=oracle_regular, fontsize=6.5,
            color=BLACK, ha=ha, va='center', zorder=7)

# =============================================================================
# BIVARIATE LEGEND (3x3 square grid)
# =============================================================================

# Position legend in bottom-left
leg_x = 0.04   # left edge in axes coords
leg_y = 0.04   # bottom edge
cell_w = 0.028  # width of each cell
cell_h = 0.028  # height of each cell
gap = 0.002     # gap between cells

for si in range(3):
    for gi in range(3):
        rx = leg_x + gi * (cell_w + gap)
        ry = leg_y + si * (cell_h + gap)
        rect = Rectangle(
            (rx, ry), cell_w, cell_h,
            transform=ax.transAxes,
            facecolor=BV_GRID[(si, gi)],
            edgecolor='white',
            linewidth=0.5,
            zorder=10
        )
        ax.add_patch(rect)

# Axis labels for legend
legend_right = leg_x + 3 * (cell_w + gap)
legend_top = leg_y + 3 * (cell_h + gap)

# Growth arrow (horizontal)
ax.annotate('',
    xy=(legend_right, leg_y - 0.008),
    xytext=(leg_x, leg_y - 0.008),
    xycoords='axes fraction',
    arrowprops=dict(arrowstyle='->', color=BLACK, lw=0.8),
    zorder=10)
ax.text(leg_x + (legend_right - leg_x) / 2, leg_y - 0.022,
        'Growth',
        transform=ax.transAxes, ha='center', va='top',
        fontproperties=oracle_medium, fontsize=6.5, color=BLACK)

# Density arrow (vertical)
ax.annotate('',
    xy=(leg_x - 0.008, legend_top),
    xytext=(leg_x - 0.008, leg_y),
    xycoords='axes fraction',
    arrowprops=dict(arrowstyle='->', color=BLACK, lw=0.8),
    zorder=10)
ax.text(leg_x - 0.018, leg_y + (legend_top - leg_y) / 2,
        'Density',
        transform=ax.transAxes, ha='center', va='center',
        fontproperties=oracle_medium, fontsize=6.5, color=BLACK,
        rotation=90)

# =============================================================================
# TITLE AND SOURCE
# =============================================================================

ax.text(0.5, 0.97, TITLE,
        transform=ax.transAxes, ha='center', va='top',
        fontproperties=oracle_bold, fontsize=13, color=BLACK)

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
print(f"\nSaved SVG: {OUTPUT_SVG}")

fig.savefig(OUTPUT_PNG, format='png', dpi=200, facecolor=BG_CREAM, bbox_inches='tight')
print(f"Saved PNG: {OUTPUT_PNG}")

plt.close()
