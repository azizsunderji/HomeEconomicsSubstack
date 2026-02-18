"""
3D Spike Map: Domestic Migration by US County (2024)

Uses PyVista to create a 3D visualization where counties are extruded
based on net domestic migration - positive values rise up, negative sink down.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import pyvista as pv
from shapely.geometry import Polygon, MultiPolygon
import duckdb

# ============================================================================
# CONFIGURATION
# ============================================================================

# Color palette from brand guidelines
BLUE = "#0BB4FF"      # Positive migration (gaining people)
RED = "#F4743B"       # Negative migration (losing people)
CREAM = "#DADFCE"     # Land base
BG_CREAM = "#F6F7F3"  # Background
BLACK = "#3D3733"     # Borders/text

# Paths
DATA_LAKE = "/Users/azizsunderji/Dropbox/Home Economics/Data"
REFERENCE = "/Users/azizsunderji/Dropbox/Home Economics/Reference"
OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_21_Citadel/outputs"

# Exclude non-continental states
EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']  # AK, HI, territories

# Albers Equal Area projection for proper US proportions
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# ============================================================================
# LOAD AND PREPARE DATA
# ============================================================================

print("Loading county population data...")
pop_df = duckdb.execute(f"""
    SELECT
        LPAD(CAST(STATE AS VARCHAR), 2, '0') as STATEFP,
        LPAD(CAST(COUNTY AS VARCHAR), 3, '0') as COUNTYFP,
        STNAME,
        CTYNAME,
        POPESTIMATE2024 as population,
        DOMESTICMIG2024 as domestic_migration,
        RDOMESTICMIG2024 as domestic_migration_rate
    FROM '{DATA_LAKE}/PopulationEstimates/county_v2024.parquet'
    WHERE SUMLEV = 50  -- County level only
""").df()

print(f"Loaded {len(pop_df)} counties")

print("Loading county shapefile...")
gdf = gpd.read_file(f"{REFERENCE}/Shapefiles/cb_2023_county/cb_2023_us_county_5m.shp")

# Filter to continental US
gdf = gdf[~gdf['STATEFP'].isin(EXCLUDE_STATES)]
print(f"Continental US counties: {len(gdf)}")

# Merge population data with geometry
gdf = gdf.merge(pop_df, on=['STATEFP', 'COUNTYFP'], how='left')
print(f"After merge: {len(gdf)} counties, {gdf['domestic_migration'].notna().sum()} with migration data")

# Reproject to Albers Equal Area
gdf = gdf.to_crs(ALBERS)

# Drop rows without migration data
gdf = gdf[gdf['domestic_migration'].notna()].copy()

# ============================================================================
# CONVERT GEOMETRIES TO 3D MESHES
# ============================================================================

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple (0-255)"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def polygon_to_mesh(polygon, base_z=0, height=0):
    """Convert a shapely polygon to a PyVista mesh (extruded prism)"""
    if polygon.is_empty:
        return None

    # Get exterior coordinates
    coords = np.array(polygon.exterior.coords)

    if len(coords) < 4:
        return None

    # Create 2D polygon mesh
    points_2d = coords[:-1]  # Remove duplicate closing point
    n_points = len(points_2d)

    # Create bottom and top faces
    bottom_points = np.column_stack([points_2d, np.full(n_points, base_z)])
    top_points = np.column_stack([points_2d, np.full(n_points, base_z + height)])

    all_points = np.vstack([bottom_points, top_points])

    # Create faces
    faces = []

    # Bottom face (reversed for correct normal)
    bottom_face = [n_points] + list(range(n_points-1, -1, -1))
    faces.extend(bottom_face)

    # Top face
    top_face = [n_points] + list(range(n_points, 2*n_points))
    faces.extend(top_face)

    # Side faces
    for i in range(n_points):
        next_i = (i + 1) % n_points
        # Each side is a quad
        side_face = [4, i, next_i, next_i + n_points, i + n_points]
        faces.extend(side_face)

    faces = np.array(faces)

    return pv.PolyData(all_points, faces=faces)

def geometry_to_meshes(geom, base_z, height):
    """Convert any shapely geometry to list of meshes"""
    meshes = []

    if isinstance(geom, Polygon):
        mesh = polygon_to_mesh(geom, base_z, height)
        if mesh is not None:
            meshes.append(mesh)
    elif isinstance(geom, MultiPolygon):
        for poly in geom.geoms:
            mesh = polygon_to_mesh(poly, base_z, height)
            if mesh is not None:
                meshes.append(mesh)

    return meshes

print("\nConverting geometries to 3D meshes...")

# Scale factor for extrusion height
# Using absolute migration numbers, scaled to reasonable visual height
# Typical range: -50,000 to +100,000
max_abs_migration = gdf['domestic_migration'].abs().quantile(0.99)
height_scale = 200000 / max_abs_migration  # Max height ~200km in map units

print(f"Max absolute migration (99th pctl): {max_abs_migration:,.0f}")
print(f"Height scale: {height_scale:.2f}")

# Create meshes for each county
positive_meshes = []
negative_meshes = []
base_meshes = []

blue_rgb = hex_to_rgb(BLUE)
red_rgb = hex_to_rgb(RED)
cream_rgb = hex_to_rgb(CREAM)

for idx, row in gdf.iterrows():
    geom = row.geometry
    migration = row['domestic_migration']

    if pd.isna(migration) or geom is None or geom.is_empty:
        continue

    # Base layer (thin)
    base_height = 1000  # 1km base
    base_meshes.extend(geometry_to_meshes(geom, 0, base_height))

    # Extrusion based on migration
    if abs(migration) > 100:  # Threshold to avoid tiny spikes
        extrusion_height = abs(migration) * height_scale

        if migration > 0:
            # Positive: extrude upward from base
            meshes = geometry_to_meshes(geom, base_height, extrusion_height)
            positive_meshes.extend(meshes)
        else:
            # Negative: we'll color the base differently and add a subtle downward indication
            # For visual clarity, we extrude upward but color red
            meshes = geometry_to_meshes(geom, base_height, extrusion_height * 0.7)  # Slightly shorter
            negative_meshes.extend(meshes)

print(f"Created {len(positive_meshes)} positive meshes, {len(negative_meshes)} negative meshes")

# ============================================================================
# RENDER THE SCENE
# ============================================================================

print("\nSetting up PyVista scene...")

# Use off-screen rendering for high-quality output
plotter = pv.Plotter(off_screen=True, window_size=[2700, 2250])  # 3x resolution for 900x750 output
plotter.set_background(BG_CREAM)

# Combine meshes for efficiency
if base_meshes:
    base_combined = base_meshes[0]
    for m in base_meshes[1:]:
        base_combined = base_combined.merge(m)
    plotter.add_mesh(base_combined, color=cream_rgb, opacity=1.0,
                     smooth_shading=True, show_edges=False)

if positive_meshes:
    pos_combined = positive_meshes[0]
    for m in positive_meshes[1:]:
        pos_combined = pos_combined.merge(m)
    plotter.add_mesh(pos_combined, color=blue_rgb, opacity=0.85,
                     smooth_shading=True, show_edges=False)

if negative_meshes:
    neg_combined = negative_meshes[0]
    for m in negative_meshes[1:]:
        neg_combined = neg_combined.merge(m)
    plotter.add_mesh(neg_combined, color=red_rgb, opacity=0.85,
                     smooth_shading=True, show_edges=False)

# Set up camera for isometric-ish view
bounds = base_combined.bounds if base_meshes else [0, 1, 0, 1, 0, 1]
center_x = (bounds[0] + bounds[1]) / 2
center_y = (bounds[2] + bounds[3]) / 2
center_z = 0

# Camera position: elevated, slightly to the southeast for good 3D effect
camera_distance = (bounds[1] - bounds[0]) * 1.2
plotter.camera_position = [
    (center_x + camera_distance * 0.3, center_y - camera_distance * 0.5, camera_distance * 0.6),  # Camera position
    (center_x, center_y, center_z),  # Focal point
    (0, 0, 1)  # Up vector
]

# Add lighting
plotter.enable_shadows()
plotter.add_light(pv.Light(position=(center_x, center_y + camera_distance, camera_distance * 2),
                           focal_point=(center_x, center_y, 0),
                           intensity=0.8))

# Save
output_path = f"{OUTPUT_DIR}/domestic_migration_3d_map.png"
plotter.screenshot(output_path)
print(f"\nSaved to: {output_path}")

plotter.close()
print("Done!")
