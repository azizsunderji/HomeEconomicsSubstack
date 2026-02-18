"""
3D Spike Map: Domestic Migration by US County (2024)

Clean approach using proper triangulated surfaces.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import pyvista as pv
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import duckdb
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

BLUE = "#0BB4FF"
RED = "#F4743B"
CREAM = "#DADFCE"
BG_CREAM = "#F6F7F3"
BLACK = "#3D3733"

DATA_LAKE = "/Users/azizsunderji/Dropbox/Home Economics/Data"
REFERENCE = "/Users/azizsunderji/Dropbox/Home Economics/Reference"
OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_21_Citadel/outputs"

EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

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
# BUILD SCENE
# ============================================================================

print("Building scene...")
plotter = pv.Plotter(off_screen=True, window_size=[2700, 2250])
plotter.set_background(hex_to_rgb(BG_CREAM))

# Get bounds for scaling
all_bounds = states.total_bounds
map_width = all_bounds[2] - all_bounds[0]
map_height = all_bounds[3] - all_bounds[1]
map_extent = max(map_width, map_height)
center_x = (all_bounds[0] + all_bounds[2]) / 2
center_y = (all_bounds[1] + all_bounds[3]) / 2

print(f"Map extent: {map_extent/1000:.0f} km")

# Create base plane (ocean/background)
padding = map_extent * 0.1
plane = pv.Plane(
    center=(center_x, center_y, -500),
    direction=(0, 0, 1),
    i_size=map_width + padding*2,
    j_size=map_height + padding*2,
    i_resolution=1,
    j_resolution=1
)
plotter.add_mesh(plane, color=hex_to_rgb("#C5D3E8"), opacity=1.0, lighting=False)  # Light blue for ocean

# Add states as extruded polygons (thin)
print("Adding state bases...")
for idx, row in states.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue

    # Simplify geometry
    geom = geom.simplify(2000)

    if geom.geom_type == 'MultiPolygon':
        polys = list(geom.geoms)
    else:
        polys = [geom]

    for poly in polys:
        if poly.is_empty or poly.exterior is None:
            continue

        coords = np.array(poly.exterior.coords)[:-1]
        if len(coords) < 3:
            continue

        # Create a simple triangulated surface
        points = np.column_stack([coords[:, 0], coords[:, 1], np.zeros(len(coords))])

        # Use delaunay triangulation for proper surface
        try:
            cloud = pv.PolyData(points)
            surface = cloud.delaunay_2d()
            plotter.add_mesh(surface, color=hex_to_rgb(CREAM), opacity=1.0,
                           show_edges=False, lighting=True)
        except:
            pass

# Migration spike parameters
max_migration = gdf['domestic_migration'].abs().quantile(0.98)
height_scale = (map_extent * 0.035) / max_migration
min_height = map_extent * 0.001

pop_for_radius = gdf['population'].fillna(gdf['population'].median())
max_pop = pop_for_radius.quantile(0.95)
min_radius = map_extent * 0.0008
max_radius = map_extent * 0.004

# Create spikes
print("Creating spikes...")
positive_columns = []
negative_columns = []

for idx, row in gdf.iterrows():
    migration = row['domestic_migration']
    if pd.isna(migration) or abs(migration) < 100:
        continue

    cx, cy = row['cx'], row['cy']
    pop = row['population'] if pd.notna(row['population']) else pop_for_radius.median()

    pop_ratio = min(pop / max_pop, 1.0)
    radius = min_radius + (max_radius - min_radius) * (pop_ratio ** 0.35)
    height = max(abs(migration) * height_scale, min_height)

    cylinder = pv.Cylinder(
        center=(cx, cy, height/2),
        direction=(0, 0, 1),
        radius=radius,
        height=height,
        resolution=12
    )

    if migration > 0:
        positive_columns.append(cylinder)
    else:
        negative_columns.append(cylinder)

print(f"Spikes: {len(positive_columns)} positive, {len(negative_columns)} negative")

if positive_columns:
    pos_mesh = positive_columns[0]
    for c in positive_columns[1:]:
        pos_mesh = pos_mesh.merge(c)
    plotter.add_mesh(pos_mesh, color=hex_to_rgb(BLUE), opacity=0.9,
                     smooth_shading=True, lighting=True)

if negative_columns:
    neg_mesh = negative_columns[0]
    for c in negative_columns[1:]:
        neg_mesh = neg_mesh.merge(c)
    plotter.add_mesh(neg_mesh, color=hex_to_rgb(RED), opacity=0.9,
                     smooth_shading=True, lighting=True)

# Camera setup - isometric view from south-southeast
print("Setting camera...")
camera_dist = map_extent * 0.65
plotter.camera_position = [
    (center_x + camera_dist * 0.2, center_y - camera_dist * 0.4, camera_dist * 0.5),
    (center_x, center_y, 0),
    (0, 0.2, 1)
]

# Lighting
plotter.add_light(pv.Light(
    position=(center_x - camera_dist, center_y + camera_dist, camera_dist * 1.2),
    focal_point=(center_x, center_y, 0),
    intensity=0.6
))

# Save
output_path = f"{OUTPUT_DIR}/domestic_migration_3d.png"
plotter.screenshot(output_path)
print(f"\nSaved: {output_path}")

plotter.close()
print("Done!")
