"""
3D Spike Map: Domestic Migration by US County (2024)

Using matplotlib's 3D capabilities with proper geopandas base map.
This approach overlays 3D bars on a properly rendered 2D map.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import duckdb
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# FONT SETUP
# ============================================================================

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# ============================================================================
# CONFIGURATION
# ============================================================================

BLUE = "#0BB4FF"
RED = "#F4743B"
CREAM = "#DADFCE"
BG_CREAM = "#F6F7F3"
BLACK = "#3D3733"
LIGHT_BLUE = "#B8E0F7"  # Ocean

DATA_LAKE = "/Users/azizsunderji/Dropbox/Home Economics/Data"
REFERENCE = "/Users/azizsunderji/Dropbox/Home Economics/Reference"
OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_21_Citadel/outputs"

EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# ============================================================================
# LOAD DATA
# ============================================================================

print("Loading data...")
pop_df = duckdb.execute(f"""
    SELECT
        LPAD(CAST(STATE AS VARCHAR), 2, '0') as STATEFP,
        LPAD(CAST(COUNTY AS VARCHAR), 3, '0') as COUNTYFP,
        CTYNAME,
        POPESTIMATE2024 as population,
        DOMESTICMIG2024 as domestic_migration
    FROM '{DATA_LAKE}/PopulationEstimates/county_v2024.parquet'
    WHERE SUMLEV = 50
""").df()

gdf = gpd.read_file(f"{REFERENCE}/Shapefiles/cb_2023_county/cb_2023_us_county_5m.shp")
gdf = gdf[~gdf['STATEFP'].isin(EXCLUDE_STATES)]
gdf = gdf.merge(pop_df, on=['STATEFP', 'COUNTYFP'], how='left')
gdf = gdf.to_crs(ALBERS)
gdf = gdf[gdf['domestic_migration'].notna()].copy()
gdf['cx'] = gdf.geometry.centroid.x
gdf['cy'] = gdf.geometry.centroid.y

states = gpd.read_file(f"{REFERENCE}/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp")
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)

print(f"Counties: {len(gdf)}, States: {len(states)}")

# ============================================================================
# CREATE FIGURE
# ============================================================================

print("Creating figure...")
fig = plt.figure(figsize=(14, 11), dpi=200, facecolor=BG_CREAM)
ax = fig.add_subplot(111, projection='3d', computed_zorder=False)
ax.set_facecolor(BG_CREAM)

# Improve 3D rendering
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False
ax.xaxis.pane.set_edgecolor('none')
ax.yaxis.pane.set_edgecolor('none')
ax.zaxis.pane.set_edgecolor('none')

# Get bounds
bounds = states.total_bounds
map_width = bounds[2] - bounds[0]
map_height = bounds[3] - bounds[1]
map_extent = max(map_width, map_height)

print(f"Map extent: {map_extent/1000:.0f} km")

# ============================================================================
# RENDER BASE MAP AS 3D POLYGONS AT Z=0
# ============================================================================

print("Rendering base map...")

def add_polygon_to_3d(ax, polygon, z=0, facecolor=CREAM, edgecolor='#E8E8E0', linewidth=0.4):
    """Add a shapely polygon to 3D axes at height z"""
    if polygon.is_empty:
        return

    # Get exterior coordinates
    x, y = polygon.exterior.xy
    x, y = np.array(x), np.array(y)
    z_arr = np.full_like(x, z)

    # Create vertices for Poly3DCollection
    verts = [list(zip(x, y, z_arr))]

    poly = Poly3DCollection(verts, alpha=1.0, facecolor=facecolor,
                            edgecolor=edgecolor, linewidth=linewidth, zorder=1)
    ax.add_collection3d(poly)

# Add states as flat polygons at z=0
for idx, row in states.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue

    # Simplify for performance
    geom = geom.simplify(3000)

    if geom.geom_type == 'MultiPolygon':
        for poly in geom.geoms:
            add_polygon_to_3d(ax, poly, z=0)
    else:
        add_polygon_to_3d(ax, geom, z=0)

# ============================================================================
# ADD MIGRATION SPIKES
# ============================================================================

print("Adding migration spikes...")

# Scale parameters - use log scale to compress extremes
max_migration = gdf['domestic_migration'].abs().quantile(0.98)
# Use square root to compress tall spikes
height_scale = (map_extent * 0.025) / np.sqrt(max_migration)
min_height = map_extent * 0.001

pop_median = gdf['population'].median()
max_pop = gdf['population'].quantile(0.95)
min_size = map_extent * 0.002
max_size = map_extent * 0.008

# Separate positive and negative
pos_df = gdf[gdf['domestic_migration'] > 100].copy()
neg_df = gdf[gdf['domestic_migration'] < -100].copy()

print(f"Positive: {len(pos_df)}, Negative: {len(neg_df)}")

def add_bar(ax, x, y, height, size, color, alpha=0.85):
    """Add a rectangular bar at position"""
    dx = dy = size
    z = 0

    # Corner coordinates
    x_corners = [x - dx/2, x + dx/2, x + dx/2, x - dx/2]
    y_corners = [y - dy/2, y - dy/2, y + dy/2, y + dy/2]

    # Build faces list
    vertices = [
        # Bottom face
        list(zip(x_corners, y_corners, [z]*4)),
        # Top face
        list(zip(x_corners, y_corners, [z + height]*4)),
    ]

    # Side faces
    for i in range(4):
        side = [
            (x_corners[i], y_corners[i], z),
            (x_corners[(i+1)%4], y_corners[(i+1)%4], z),
            (x_corners[(i+1)%4], y_corners[(i+1)%4], z + height),
            (x_corners[i], y_corners[i], z + height)
        ]
        vertices.append(side)

    bar = Poly3DCollection(vertices, alpha=alpha, facecolor=color,
                           edgecolor=color, linewidth=0.1, zorder=10)
    ax.add_collection3d(bar)

# Add positive bars (blue) - use sqrt for compressed scale
for idx, row in pos_df.iterrows():
    migration = row['domestic_migration']
    pop = row['population'] if pd.notna(row['population']) else pop_median

    height = max(np.sqrt(migration) * height_scale, min_height)
    pop_ratio = min(pop / max_pop, 1.0)
    size = min_size + (max_size - min_size) * (pop_ratio ** 0.35)

    add_bar(ax, row['cx'], row['cy'], height, size, BLUE)

# Add negative bars (red) - use sqrt for compressed scale
for idx, row in neg_df.iterrows():
    migration = abs(row['domestic_migration'])
    pop = row['population'] if pd.notna(row['population']) else pop_median

    height = max(np.sqrt(migration) * height_scale, min_height)
    pop_ratio = min(pop / max_pop, 1.0)
    size = min_size + (max_size - min_size) * (pop_ratio ** 0.35)

    add_bar(ax, row['cx'], row['cy'], height, size, RED)

# ============================================================================
# CAMERA AND STYLING
# ============================================================================

print("Setting view...")

# Set axis limits
padding = map_extent * 0.05
ax.set_xlim(bounds[0] - padding, bounds[2] + padding)
ax.set_ylim(bounds[1] - padding, bounds[3] + padding)
ax.set_zlim(0, map_extent * 0.08)  # Reduced z range

# View angle - more top-down for clearer map view
ax.view_init(elev=55, azim=-80)  # Higher elevation for better overview

# Remove axes
ax.set_axis_off()

# Tight layout
plt.tight_layout()

# ============================================================================
# SAVE
# ============================================================================

output_path = f"{OUTPUT_DIR}/domestic_migration_3d_mpl.png"
plt.savefig(output_path, dpi=150, facecolor=BG_CREAM, bbox_inches='tight', pad_inches=0.1)
print(f"\nSaved: {output_path}")

plt.close()
print("Done!")
