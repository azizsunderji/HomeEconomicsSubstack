#!/usr/bin/env python3
"""
PhD Hexagonal Cartogram
========================
Each hexagon = one PUMA (~100k people), colored by technical PhD share.
Top 10 metros by PhD per capita get outlined borders.
"""

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.font_manager import FontProperties
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.patches import RegularPolygon
import matplotlib.cm as cm
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import numpy as np
import pandas as pd
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from pyproj import Transformer
from collections import deque

matplotlib.use('svg')
plt.rcParams['svg.fonttype'] = 'none'

# =============================================================================
# CONFIGURATION
# =============================================================================

TITLE = "Where America's AI-Ready PhDs Live"
SUBTITLE = "CS, math, EE, and physics doctoral holders per 10,000 adults. Each hexagon is one PUMA (~100k people)."
SOURCE = "Source: ACS 5-Year (2019-2023) via IPUMS. Employed, not in school, doctoral degree holders."

OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs"
OUTPUT_SVG = f"{OUTPUT_DIR}/phd_hex_cartogram.svg"
OUTPUT_PNG = f"{OUTPUT_DIR}/phd_hex_cartogram.png"

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
CBSA_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_cbsa/cb_2023_us_cbsa_5m.shp'

HEX_RADIUS = 20000

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
puma_data['phds_per_10k'] = np.where(
    puma_data['pop_25plus'] > 0,
    puma_data['total_phds'] / puma_data['pop_25plus'] * 10000,
    0
)

print(f"PUMAs: {len(puma_data)}, with PhDs: {(puma_data['total_phds'] > 0).sum()}")
print(f"Total PhDs: {puma_data['total_phds'].sum():,.0f}")

# Load PUMA shapefile
print("Loading PUMA shapefile...")
pumas = gpd.read_file(PUMA_SHAPEFILE)
pumas['puma_key'] = pumas['STATEFP20'] + pumas['PUMACE20']
pumas = pumas[~pumas['STATEFP20'].isin(EXCLUDE_STATES)]
pumas = pumas.to_crs(ALBERS)
pumas['cx'] = pumas.geometry.centroid.x
pumas['cy'] = pumas.geometry.centroid.y

# Load CBSA shapefile and spatial join PUMAs to metros
print("Loading CBSA shapefile...")
cbsas = gpd.read_file(CBSA_SHAPEFILE)
cbsas = cbsas.to_crs(ALBERS)

puma_centroids_gdf = gpd.GeoDataFrame(
    pumas[['puma_key']],
    geometry=[Point(r.cx, r.cy) for _, r in pumas.iterrows()],
    crs=ALBERS
)
puma_cbsa = gpd.sjoin(puma_centroids_gdf, cbsas[['NAME', 'GEOID', 'geometry']], how='left', predicate='within')
puma_cbsa = puma_cbsa.rename(columns={'NAME': 'cbsa_name', 'GEOID': 'cbsa_id'})
puma_cbsa = puma_cbsa[['puma_key', 'cbsa_name', 'cbsa_id']].drop_duplicates(subset='puma_key', keep='first')

# Merge everything
puma_merged = puma_data.merge(pumas[['puma_key', 'cx', 'cy']], on='puma_key', how='inner')
puma_merged = puma_merged.merge(puma_cbsa, on='puma_key', how='left')
print(f"Matched: {len(puma_merged)} PUMAs")

# =============================================================================
# CUSTOM METRO DEFINITIONS
# =============================================================================

# Bay Area = San Jose CBSA + San Francisco CBSA
# NYC Five Boroughs = state 36 PUMAs within ~25km of Times Square (not the full CBSA)

transformer = Transformer.from_crs('EPSG:4326', ALBERS, always_xy=True)
times_sq_x, times_sq_y = transformer.transform(-73.986, 40.758)

def assign_custom_metro(row):
    """Override CBSA names with custom metro definitions."""
    cbsa = row['cbsa_name'] if pd.notna(row['cbsa_name']) else ''

    # Bay Area: combine San Jose + San Francisco CBSAs
    if 'San Jose' in cbsa or 'San Francisco' in cbsa:
        return 'Bay Area'

    # NYC Five Boroughs: state 36, within 25km of Times Square
    if row['puma_key'].startswith('36') and 'New York' in cbsa:
        dist = np.sqrt((row['cx'] - times_sq_x)**2 + (row['cy'] - times_sq_y)**2)
        if dist < 25000:
            return 'New York City'
        else:
            return cbsa  # suburban NY — keep original CBSA

    return cbsa

puma_merged['metro'] = puma_merged.apply(assign_custom_metro, axis=1)

# =============================================================================
# COMPUTE METRO-LEVEL PhD RATES AND FIND TOP 10
# =============================================================================

print("\nComputing metro-level PhD rates...")

metro_stats = puma_merged.groupby('metro').agg(
    total_phds=('total_phds', 'sum'),
    pop_25plus=('pop_25plus', 'sum'),
    n_pumas=('puma_key', 'count'),
).reset_index()

metro_stats['phds_per_10k'] = np.where(
    metro_stats['pop_25plus'] > 0,
    metro_stats['total_phds'] / metro_stats['pop_25plus'] * 10000,
    0
)

# Filter to real metros (at least 2 PUMAs to exclude one-off rural areas)
metro_stats_real = metro_stats[
    (metro_stats['n_pumas'] >= 2) &
    (metro_stats['metro'] != '') &
    (metro_stats['metro'].notna())
].copy()

metro_stats_real = metro_stats_real.sort_values('phds_per_10k', ascending=False)

print("\nTop 20 metros by PhD per 10k adults:")
for _, r in metro_stats_real.head(20).iterrows():
    print(f"  {r['phds_per_10k']:6.1f}/10k  {r['total_phds']:8,.0f} PhDs  {r['n_pumas']:4d} PUMAs  {r['metro']}")

# Take top 10
top10 = metro_stats_real.head(10)['metro'].tolist()
print(f"\nTop 10 to highlight: {top10}")

# =============================================================================
# LOAD STATES AND BUILD CARTOGRAM
# =============================================================================

print("\nLoading states...")
states = gpd.read_file(STATE_SHAPEFILE)
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)

print("Building hexagonal cartogram...")

dx = HEX_RADIUS * np.sqrt(3)
dy = HEX_RADIUS * 1.5

def xy_to_hex(x, y):
    row = round(y / dy)
    if row % 2:
        col = round((x - dx / 2) / dx)
    else:
        col = round(x / dx)
    return (col, row)

def hex_to_xy(col, row):
    if row % 2:
        x = col * dx + dx / 2
    else:
        x = col * dx
    y = row * dy
    return (x, y)

def hex_neighbors(col, row):
    if row % 2:
        return [
            (col, row + 1), (col + 1, row + 1),
            (col - 1, row), (col + 1, row),
            (col, row - 1), (col + 1, row - 1),
        ]
    else:
        return [
            (col - 1, row + 1), (col, row + 1),
            (col - 1, row), (col + 1, row),
            (col - 1, row - 1), (col, row - 1),
        ]

def create_hex_polygon(cx, cy, radius):
    angles = np.linspace(0, 2 * np.pi, 7)[:-1] + np.pi / 6
    points = [(cx + radius * np.cos(a), cy + radius * np.sin(a)) for a in angles]
    return Polygon(points)

# Sort PUMAs by distance to ideal hex
puma_merged['target_col_row'] = puma_merged.apply(
    lambda r: xy_to_hex(r['cx'], r['cy']), axis=1
)
puma_merged['target_col'] = puma_merged['target_col_row'].apply(lambda x: x[0])
puma_merged['target_row'] = puma_merged['target_col_row'].apply(lambda x: x[1])

def dist_to_target(row):
    tx, ty = hex_to_xy(row['target_col'], row['target_row'])
    return np.sqrt((row['cx'] - tx)**2 + (row['cy'] - ty)**2)

puma_merged['dist_to_target'] = puma_merged.apply(dist_to_target, axis=1)
puma_merged = puma_merged.sort_values('dist_to_target')

# Greedy assignment
occupied = {}
assignments = {}
n_direct = 0
n_displaced = 0

for _, puma in puma_merged.iterrows():
    target = (puma['target_col'], puma['target_row'])
    if target not in occupied:
        occupied[target] = puma['puma_key']
        assignments[puma['puma_key']] = target
        n_direct += 1
    else:
        queue = deque([target])
        visited = {target}
        found = False
        while queue and not found:
            current = queue.popleft()
            for nb in hex_neighbors(*current):
                if nb not in visited:
                    visited.add(nb)
                    if nb not in occupied:
                        occupied[nb] = puma['puma_key']
                        assignments[puma['puma_key']] = nb
                        n_displaced += 1
                        found = True
                        break
                    queue.append(nb)

print(f"  Direct: {n_direct}, Displaced: {n_displaced}")

# Build hex dataframe
hex_data = []
for _, puma in puma_merged.iterrows():
    if puma['puma_key'] in assignments:
        col, row = assignments[puma['puma_key']]
        hx, hy = hex_to_xy(col, row)
        hex_data.append({
            'puma_key': puma['puma_key'],
            'phds_per_10k': puma['phds_per_10k'],
            'total_phds': puma['total_phds'],
            'pop_25plus': puma['pop_25plus'],
            'metro': puma['metro'],
            'hx': hx, 'hy': hy,
            'col': col, 'row': row,
        })

hex_df = pd.DataFrame(hex_data)

# =============================================================================
# BUILD BORDERS FOR TOP 10 METROS
# =============================================================================

print("\nBuilding borders for top 10 metros...")

metro_borders = {}
for metro_name in top10:
    hex_subset = hex_df[hex_df['metro'] == metro_name]
    if len(hex_subset) == 0:
        print(f"  WARNING: No hexes for '{metro_name}'")
        continue

    # Union hex polygons (slightly oversized so adjacent hexes merge)
    hex_polys = [create_hex_polygon(h['hx'], h['hy'], HEX_RADIUS * 1.005)
                 for _, h in hex_subset.iterrows()]
    metro_union = unary_union(hex_polys)

    metro_borders[metro_name] = {
        'geometry': metro_union,
        'center_x': hex_subset['hx'].mean(),
        'center_y': hex_subset['hy'].mean(),
        'n_hexes': len(hex_subset),
    }

    rate = metro_stats_real[metro_stats_real['metro'] == metro_name]['phds_per_10k'].values[0]
    print(f"  {metro_name}: {len(hex_subset)} hexes, {rate:.1f}/10k")

# =============================================================================
# COMPUTE LABEL OFFSETS (avoid overlap)
# =============================================================================

# Auto-assign label offsets based on position relative to map center
map_cx = hex_df['hx'].mean()
map_cy = hex_df['hy'].mean()

label_offsets = {}
for name, info in metro_borders.items():
    cx, cy = info['center_x'], info['center_y']
    # Place label on the side away from map center
    dx_off = 130000 if cx > map_cx else -130000
    dy_off = 60000 if cy > map_cy else -60000

    # Manual tweaks for known problem spots
    label_offsets[name] = (dx_off, dy_off)

# =============================================================================
# PLOT
# =============================================================================

print("\nCreating figure...")
oracle_regular = FontProperties(fname=FONT_REGULAR)
oracle_bold = FontProperties(fname=FONT_BOLD)
oracle_light = FontProperties(fname=FONT_LIGHT)
oracle_medium = FontProperties(fname=FONT_MEDIUM)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

cmap = LinearSegmentedColormap.from_list('phd_cartogram', [
    '#E8F2FB',
    '#CEEAFF',
    '#7DD3FF',
    '#0BB4FF',
    '#0066BB',
    '#1B3A6B',
    '#0F1D3D',
], N=512)

max_val = hex_df['phds_per_10k'].max()
GAMMA = 0.4

# Draw hexes (interlocking, no gaps)
for _, row in hex_df.iterrows():
    val = row['phds_per_10k']
    norm_val = (val / max_val) ** GAMMA if max_val > 0 else 0
    color = cmap(norm_val)

    hex_patch = RegularPolygon(
        (row['hx'], row['hy']),
        numVertices=6,
        radius=HEX_RADIUS,
        orientation=np.radians(30),
        facecolor=color,
        edgecolor='white',
        linewidth=0.15,
        zorder=2,
    )
    ax.add_patch(hex_patch)

# Draw top 10 metro borders (tracing hex edges)
for name, info in metro_borders.items():
    geom = info['geometry']
    if geom.geom_type == 'Polygon':
        xs, ys = geom.exterior.xy
        ax.plot(xs, ys, color=BLACK, linewidth=1.2, alpha=0.75, zorder=4)
    elif geom.geom_type == 'MultiPolygon':
        for poly in geom.geoms:
            xs, ys = poly.exterior.xy
            ax.plot(xs, ys, color=BLACK, linewidth=1.2, alpha=0.75, zorder=4)

# Labels for top 10 only
for name, info in metro_borders.items():
    ox, oy = label_offsets[name]
    cx, cy = info['center_x'], info['center_y']

    ax.plot([cx, cx + ox], [cy, cy + oy],
            color=BLACK, linewidth=0.4, alpha=0.4, zorder=6)

    ha = 'left' if ox > 0 else 'right'
    ax.text(cx + ox, cy + oy, name,
            fontproperties=oracle_regular, fontsize=6.5,
            color=BLACK, ha=ha, va='center', zorder=7)

# Bounds
all_x = hex_df['hx'].values
all_y = hex_df['hy'].values
pad = HEX_RADIUS * 5
ax.set_xlim(all_x.min() - pad, all_x.max() + pad)
ax.set_ylim(all_y.min() - pad, all_y.max() + pad)
ax.set_aspect('equal')
ax.axis('off')

# =============================================================================
# COLORBAR
# =============================================================================

cbar_ax = inset_axes(ax, width="25%", height="2.5%", loc='lower left',
                     bbox_to_anchor=(0.05, 0.04, 1, 1),
                     bbox_transform=ax.transAxes)

norm = Normalize(vmin=0, vmax=1)
sm = cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, cax=cbar_ax, orientation='horizontal')

tick_vals = [0, 1, 5, 20, 100]
tick_vals = [v for v in tick_vals if v <= max_val]
tick_positions = [(v / max_val) ** GAMMA for v in tick_vals]
cbar.set_ticks(tick_positions)
cbar.set_ticklabels([str(int(v)) for v in tick_vals])
cbar.ax.tick_params(labelsize=6.5, length=2, pad=2)
for lbl in cbar.ax.get_xticklabels():
    lbl.set_fontproperties(oracle_light)
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
        fontproperties=oracle_light, fontsize=8, color='#888')

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
print("Done.")
