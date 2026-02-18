"""
3D Spike Map: Domestic Migration by US County (2024)

Clean column/spike visualization with columns at county centroids.
Height represents net domestic migration (people moving in/out).
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import pyvista as pv
import duckdb

# ============================================================================
# CONFIGURATION
# ============================================================================

# Color palette from brand guidelines
BLUE = "#0BB4FF"      # Positive migration (gaining people)
RED = "#F4743B"       # Negative migration (losing people)
CREAM = "#DADFCE"     # Land base
BG_CREAM = "#F6F7F3"  # Background
BLACK = "#3D3733"     # Borders

# Paths
DATA_LAKE = "/Users/azizsunderji/Dropbox/Home Economics/Data"
REFERENCE = "/Users/azizsunderji/Dropbox/Home Economics/Reference"
OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_21_Citadel/outputs"

# Exclude non-continental states
EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']

# Albers Equal Area projection
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# ============================================================================
# LOAD DATA
# ============================================================================

print("Loading county population data...")
pop_df = duckdb.execute(f"""
    SELECT
        LPAD(CAST(STATE AS VARCHAR), 2, '0') as STATEFP,
        LPAD(CAST(COUNTY AS VARCHAR), 3, '0') as COUNTYFP,
        STNAME,
        CTYNAME,
        POPESTIMATE2024 as population,
        DOMESTICMIG2024 as domestic_migration
    FROM '{DATA_LAKE}/PopulationEstimates/county_v2024.parquet'
    WHERE SUMLEV = 50
""").df()

print(f"Loaded {len(pop_df)} counties")

print("Loading county shapefile...")
gdf = gpd.read_file(f"{REFERENCE}/Shapefiles/cb_2023_county/cb_2023_us_county_5m.shp")
gdf = gdf[~gdf['STATEFP'].isin(EXCLUDE_STATES)]

# Merge and reproject
gdf = gdf.merge(pop_df, on=['STATEFP', 'COUNTYFP'], how='left')
gdf = gdf.to_crs(ALBERS)
gdf = gdf[gdf['domestic_migration'].notna()].copy()

# Get centroids
gdf['centroid'] = gdf.geometry.centroid
gdf['cx'] = gdf['centroid'].x
gdf['cy'] = gdf['centroid'].y

print(f"Counties with data: {len(gdf)}")

# Also load state boundaries for a cleaner base
print("Loading state boundaries...")
states = gpd.read_file(f"{REFERENCE}/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp")
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)

# ============================================================================
# CREATE VISUALIZATION
# ============================================================================

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

print("\nBuilding 3D scene...")

plotter = pv.Plotter(off_screen=True, window_size=[2700, 2250])
plotter.set_background(hex_to_rgb(BG_CREAM))

# Create base map from state boundaries (flat polygon)
print("Creating base map...")
base_points = []
base_faces = []
point_offset = 0

# Use dissolved US boundary for clean base
us_boundary = states.dissolve()

for idx, row in us_boundary.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue

    # Handle MultiPolygon
    if geom.geom_type == 'MultiPolygon':
        polys = list(geom.geoms)
    else:
        polys = [geom]

    for poly in polys:
        if poly.is_empty:
            continue
        # Simplify to reduce vertex count
        poly = poly.simplify(5000)  # 5km tolerance
        coords = np.array(poly.exterior.coords)[:-1]
        n = len(coords)
        if n < 3:
            continue

        # Add points with z=-1000 (slightly below spikes)
        pts = np.column_stack([coords, np.full(n, -1000)])
        base_points.append(pts)

        face = [n] + list(range(point_offset, point_offset + n))
        base_faces.extend(face)
        point_offset += n

if base_points:
    all_base_points = np.vstack(base_points)
    base_mesh = pv.PolyData(all_base_points, faces=np.array(base_faces))
    # Compute normals to ensure proper rendering
    base_mesh.compute_normals(inplace=True, flip_normals=True)
    plotter.add_mesh(base_mesh, color=hex_to_rgb(CREAM), opacity=1.0,
                     show_edges=False, lighting=True, smooth_shading=False)

# Create spikes/columns at county centroids
print("Creating migration spikes...")

# Scale: max spike height relative to map extent
bounds = base_mesh.bounds
map_extent = max(bounds[1] - bounds[0], bounds[3] - bounds[2])

# Height scaling - make spikes proportional to map
max_migration = gdf['domestic_migration'].abs().quantile(0.98)
height_scale = (map_extent * 0.04) / max_migration  # Max spike is 4% of map width (reduced)
min_height = map_extent * 0.001  # Minimum visible spike

print(f"Map extent: {map_extent/1000:.0f} km")
print(f"Max migration (98th pctl): {max_migration:,.0f}")

# Column radius based on population (larger counties get wider columns)
pop_for_radius = gdf['population'].fillna(gdf['population'].median())
max_pop = pop_for_radius.quantile(0.95)
min_radius = map_extent * 0.001  # Smaller min radius
max_radius = map_extent * 0.006  # Smaller max radius

positive_columns = []
negative_columns = []

for idx, row in gdf.iterrows():
    migration = row['domestic_migration']
    if pd.isna(migration) or abs(migration) < 50:  # Skip tiny values
        continue

    cx, cy = row['cx'], row['cy']
    pop = row['population'] if pd.notna(row['population']) else pop_for_radius.median()

    # Column radius based on population
    pop_ratio = min(pop / max_pop, 1.0)
    radius = min_radius + (max_radius - min_radius) * (pop_ratio ** 0.4)

    # Height based on migration
    height = max(abs(migration) * height_scale, min_height)

    # Create cylinder - start at base level (-1000), rise up
    base_z = -1000
    cylinder = pv.Cylinder(
        center=(cx, cy, base_z + height/2),
        direction=(0, 0, 1),
        radius=radius,
        height=height,
        resolution=16
    )

    if migration > 0:
        positive_columns.append(cylinder)
    else:
        negative_columns.append(cylinder)

print(f"Created {len(positive_columns)} positive, {len(negative_columns)} negative columns")

# Combine and add to plotter
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

# ============================================================================
# CAMERA AND LIGHTING
# ============================================================================

print("Setting up camera...")

center_x = (bounds[0] + bounds[1]) / 2
center_y = (bounds[2] + bounds[3]) / 2

# Elevated view from the south-southeast, looking down at map
camera_dist = map_extent * 0.7
plotter.camera_position = [
    (center_x + camera_dist * 0.15, center_y - camera_dist * 0.45, camera_dist * 0.55),
    (center_x, center_y + camera_dist * 0.05, -1000),  # Look at base level
    (0, 0.3, 1)  # Tilted up vector for better perspective
]

# Add lighting for depth
plotter.add_light(pv.Light(
    position=(center_x - camera_dist, center_y + camera_dist, camera_dist * 1.5),
    focal_point=(center_x, center_y, 0),
    intensity=0.7
))

# ============================================================================
# SAVE OUTPUT
# ============================================================================

output_path = f"{OUTPUT_DIR}/domestic_migration_spikes.png"
plotter.screenshot(output_path)
print(f"\nSaved: {output_path}")

plotter.close()
print("Done!")
