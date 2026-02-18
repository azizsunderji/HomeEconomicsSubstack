"""
High-Rise Housing Growth: All US Metros 2010-2024
Constant-width bars: Blue = 2010 stock, Yellow = growth on top.
NYC capped. Low camera angle. Translucent.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# FONT SETUP
# ============================================================================

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf']:
    try:
        fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
    except:
        pass
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# ============================================================================
# CONFIGURATION
# ============================================================================

BLUE = "#0BB4FF"
YELLOW = "#FEC439"
CREAM = "#E8EAE0"
BG_CREAM = "#F6F7F3"
BLACK = "#3D3733"

DATA_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_04_BuildingUp/data"
REFERENCE = "/Users/azizsunderji/Dropbox/Home Economics/Reference"
OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_04_BuildingUp/outputs"

EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

NYC_CAP = 950_000
MIN_GROWTH = 5_000  # Filter on growth, not total

# ============================================================================
# LOAD DATA
# ============================================================================

print("Loading data...")

hr_data = pd.read_csv(f"{DATA_DIR}/highrise_units_all_metros.csv")

# Filter to continental US
hr_data = hr_data[(hr_data['lat'] > 24) & (hr_data['lat'] < 50) &
                   (hr_data['lon'] > -125) & (hr_data['lon'] < -66)]

# Filter on growth
hr_data = hr_data[hr_data['highrise_growth'] >= MIN_GROWTH]
print(f"Metros with growth >= {MIN_GROWTH:,}: {len(hr_data)}")

# Convert to geopandas and project
gdf = gpd.GeoDataFrame(
    hr_data,
    geometry=gpd.points_from_xy(hr_data['lon'], hr_data['lat']),
    crs="EPSG:4326"
)
gdf = gdf.to_crs(ALBERS)
gdf['x'] = gdf.geometry.x
gdf['y'] = gdf.geometry.y

# Load state boundaries
states = gpd.read_file(f"{REFERENCE}/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp")
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)

# ============================================================================
# CAP NYC
# ============================================================================

gdf['display_base'] = gdf['highrise_units_2010'].copy()
gdf['display_total'] = gdf['highrise_units_2024'].copy()

over_cap = gdf['display_total'] > NYC_CAP
if over_cap.any():
    for idx in gdf[over_cap].index:
        ratio = NYC_CAP / gdf.loc[idx, 'highrise_units_2024']
        gdf.loc[idx, 'display_base'] = gdf.loc[idx, 'highrise_units_2010'] * ratio
        gdf.loc[idx, 'display_total'] = NYC_CAP
    print(f"Capped {over_cap.sum()} metro(s) at {NYC_CAP:,}")

gdf['display_growth'] = (gdf['display_total'] - gdf['display_base']).clip(lower=0)

# ============================================================================
# CREATE FIGURE
# ============================================================================

print("Creating figure...")
fig = plt.figure(figsize=(16, 10), dpi=200, facecolor=BG_CREAM)
ax = fig.add_subplot(111, projection='3d', computed_zorder=False)
ax.set_facecolor(BG_CREAM)

ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False
ax.xaxis.pane.set_edgecolor('none')
ax.yaxis.pane.set_edgecolor('none')
ax.zaxis.pane.set_edgecolor('none')
ax.grid(False)

bounds = states.total_bounds
map_extent = max(bounds[2] - bounds[0], bounds[3] - bounds[1])

# ============================================================================
# RENDER BASE MAP
# ============================================================================

print("Rendering base map...")

def add_polygon_to_3d(ax, polygon, z=0, facecolor=CREAM, edgecolor='white', linewidth=0.4):
    if polygon.is_empty:
        return
    x, y = polygon.exterior.xy
    x, y = np.array(x), np.array(y)
    z_arr = np.full_like(x, z)
    verts = [list(zip(x, y, z_arr))]
    poly = Poly3DCollection(verts, alpha=1.0, facecolor=facecolor,
                            edgecolor=edgecolor, linewidth=linewidth, zorder=1)
    ax.add_collection3d(poly)

for idx, row in states.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue
    geom = geom.simplify(5000)
    if geom.geom_type == 'MultiPolygon':
        for poly in geom.geoms:
            add_polygon_to_3d(ax, poly, z=0)
    else:
        add_polygon_to_3d(ax, geom, z=0)

# ============================================================================
# ADD SPIKES: TAPERED BLUE BASE + CONSTANT-WIDTH YELLOW TOP
# ============================================================================

print("Adding spikes...")

height_scale = (map_extent * 0.12) / NYC_CAP  # Taller overall

# Constant width throughout
bar_width = map_extent * 0.016  # Thicker bars


def add_bar(ax, cx, cy, z_bot, z_top, w_bot, w_top, color, edge_color, alpha=1.0):
    """Add a single frustum/bar segment with given bottom and top widths."""
    if z_top <= z_bot:
        return

    hb, ht = w_bot / 2, w_top / 2

    bx = [cx - hb, cx + hb, cx + hb, cx - hb]
    by = [cy - hb, cy - hb, cy + hb, cy + hb]
    tx = [cx - ht, cx + ht, cx + ht, cx - ht]
    ty = [cy - ht, cy - ht, cy + ht, cy + ht]

    front = [(bx[0], by[0], z_bot), (bx[1], by[1], z_bot),
             (tx[1], ty[1], z_top), (tx[0], ty[0], z_top)]
    back = [(bx[3], by[3], z_bot), (bx[2], by[2], z_bot),
            (tx[2], ty[2], z_top), (tx[3], ty[3], z_top)]
    right = [(bx[1], by[1], z_bot), (bx[2], by[2], z_bot),
             (tx[2], ty[2], z_top), (tx[1], ty[1], z_top)]
    left = [(bx[0], by[0], z_bot), (bx[3], by[3], z_bot),
            (tx[3], ty[3], z_top), (tx[0], ty[0], z_top)]
    top = [(tx[0], ty[0], z_top), (tx[1], ty[1], z_top),
           (tx[2], ty[2], z_top), (tx[3], ty[3], z_top)]

    faces = Poly3DCollection([front, back, right, left, top],
                              alpha=alpha, facecolor=color,
                              edgecolor=edge_color, linewidth=0.3, zorder=10)
    ax.add_collection3d(faces)


# Identify top 10 by growth for emphasis
top10_indices = set(gdf.sort_values('highrise_growth', ascending=False).head(10).index)

# Sort back-to-front for painter's algorithm
gdf = gdf.sort_values('y', ascending=False)

for idx, row in gdf.iterrows():
    x, y = row['x'], row['y']

    base_h = row['display_base'] * height_scale
    growth_h = row['display_growth'] * height_scale

    min_h = map_extent * 0.001
    base_h = max(base_h, min_h)

    is_top10 = idx in top10_indices

    if is_top10:
        blue_fill, blue_edge = BLUE, '#0090CC'
        yellow_fill, yellow_edge = YELLOW, '#D4A520'
    else:
        # Neutral gray for non-top-10
        blue_fill, blue_edge = '#C0C0C0', '#A8A8A8'
        yellow_fill, yellow_edge = '#D0D0D0', '#B8B8B8'

    # Blue portion: constant width
    add_bar(ax, x, y, 0, base_h, bar_width, bar_width, blue_fill, blue_edge)

    # Yellow portion: same constant width, stacked on top
    if growth_h > 0:
        add_bar(ax, x, y, base_h, base_h + growth_h,
                bar_width, bar_width, yellow_fill, yellow_edge)

print(f"Added {len(gdf)} spikes")

# ============================================================================
# LABEL TOP 10 BY GROWTH
# ============================================================================

print("Adding labels...")

# Rank by actual growth (not capped display values)
top10 = gdf.sort_values('highrise_growth', ascending=False).head(10)

# Short city names from the metro_name field
def short_name(metro_name):
    """Extract first city name: 'Dallas-Fort Worth-Arlington, TX...' -> 'Dallas'"""
    return metro_name.split('-')[0].split(',')[0].strip()

for rank, (idx, row) in enumerate(top10.iterrows(), 1):
    x, y = row['x'], row['y']
    # Total display height of the spike
    base_h = max(row['display_base'] * height_scale, map_extent * 0.001)
    growth_h = max(row['display_growth'] * height_scale, 0)
    top_z = base_h + growth_h

    label = f"#{rank} {short_name(row['metro_name'])}"

    ax.text(x, y, top_z + map_extent * 0.002, label,
            fontsize=5, fontweight='bold', color=BLACK,
            ha='center', va='bottom', zorder=100)

# ============================================================================
# CAMERA AND STYLING
# ============================================================================

print("Setting view...")

padding = map_extent * 0.02
ax.set_xlim(bounds[0] - padding, bounds[2] + padding)
ax.set_ylim(bounds[1] - padding, bounds[3] + padding)
ax.set_zlim(0, map_extent * 0.14)

# Rotated slightly counterclockwise to separate Texas spikes
ax.view_init(elev=28, azim=-85)
ax.set_axis_off()

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

# Source line
fig.text(0.5, 0.02, 'Source: Census Bureau ACS, Table B25024',
         ha='center', fontsize=7, color=BLACK, alpha=0.4, style='italic')

# ============================================================================
# SAVE
# ============================================================================

# PNG
output_path = f"{OUTPUT_DIR}/highrise_growth_3d.png"
plt.savefig(output_path, dpi=200, facecolor=BG_CREAM, bbox_inches='tight', pad_inches=0.05)
print(f"Saved: {output_path}")

# SVG with editable text
import matplotlib
plt.rcParams['svg.fonttype'] = 'none'
svg_path = f"{OUTPUT_DIR}/highrise_growth_3d.svg"
plt.savefig(svg_path, format='svg', facecolor=BG_CREAM, bbox_inches='tight', pad_inches=0.05)
print(f"Saved: {svg_path}")

plt.close()
print("Done!")
