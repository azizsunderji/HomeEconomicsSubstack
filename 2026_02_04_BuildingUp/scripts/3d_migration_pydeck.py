"""
3D Spike Map: Domestic Migration by US County (2024)

Using PyDeck for high-quality WebGL rendering.
Outputs an HTML file that can be opened and screenshotted.
"""

import numpy as np
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import duckdb
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

BLUE = [11, 180, 255]      # #0BB4FF - positive migration
RED = [244, 116, 59]       # #F4743B - negative migration
BG_CREAM = [246, 247, 243] # #F6F7F3

DATA_LAKE = "/Users/azizsunderji/Dropbox/Home Economics/Data"
REFERENCE = "/Users/azizsunderji/Dropbox/Home Economics/Reference"
OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_21_Citadel/outputs"

EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']

# ============================================================================
# LOAD DATA
# ============================================================================

print("Loading data...")
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

# Load county shapefile and get centroids
gdf = gpd.read_file(f"{REFERENCE}/Shapefiles/cb_2023_county/cb_2023_us_county_5m.shp")
gdf = gdf[~gdf['STATEFP'].isin(EXCLUDE_STATES)]

# Merge data
gdf = gdf.merge(pop_df, on=['STATEFP', 'COUNTYFP'], how='left')
gdf = gdf[gdf['domestic_migration'].notna()].copy()

# Get centroids in lat/lon (WGS84)
gdf['centroid'] = gdf.geometry.centroid
gdf['lon'] = gdf['centroid'].x
gdf['lat'] = gdf['centroid'].y

print(f"Counties with data: {len(gdf)}")

# ============================================================================
# PREPARE DATA FOR PYDECK
# ============================================================================

# Scale elevation - use sqrt to compress extremes
max_migration = gdf['domestic_migration'].abs().quantile(0.98)

# Create separate dataframes for positive and negative
df = gdf[['CTYNAME', 'STNAME', 'lon', 'lat', 'population', 'domestic_migration']].copy()
df = df[df['domestic_migration'].abs() > 50]  # Filter tiny values

# Elevation scaling (meters for deck.gl)
elevation_scale = 5000 / np.sqrt(max_migration)

df['elevation'] = np.sqrt(df['domestic_migration'].abs()) * elevation_scale
df['elevation'] = df['elevation'].clip(lower=500)  # Minimum visible height

# Color based on direction
df['color'] = df['domestic_migration'].apply(
    lambda x: BLUE + [200] if x > 0 else RED + [200]
)

# Radius based on population
pop_median = df['population'].median()
max_pop = df['population'].quantile(0.95)
df['radius'] = 1000 + 4000 * (df['population'].fillna(pop_median) / max_pop).clip(upper=1) ** 0.35

print(f"Preparing {len(df)} columns for visualization")
print(f"  Positive (blue): {(df['domestic_migration'] > 0).sum()}")
print(f"  Negative (red): {(df['domestic_migration'] < 0).sum()}")

# ============================================================================
# CREATE PYDECK VISUALIZATION
# ============================================================================

# Convert to records for pydeck
data = df.to_dict('records')

# Column layer
column_layer = pdk.Layer(
    "ColumnLayer",
    data=data,
    get_position=["lon", "lat"],
    get_elevation="elevation",
    elevation_scale=1,
    radius="radius",
    get_fill_color="color",
    pickable=True,
    auto_highlight=True,
    coverage=0.8,
)

# View state - centered on continental US with tilt
view_state = pdk.ViewState(
    latitude=39.0,
    longitude=-98.0,
    zoom=3.8,
    pitch=45,
    bearing=-10,
)

# Create deck
deck = pdk.Deck(
    layers=[column_layer],
    initial_view_state=view_state,
    tooltip={
        "html": "<b>{CTYNAME}, {STNAME}</b><br/>Domestic Migration: {domestic_migration:,.0f}",
        "style": {"backgroundColor": "#3D3733", "color": "white"}
    },
    map_style="mapbox://styles/mapbox/light-v10",
)

# Save to HTML
output_path = f"{OUTPUT_DIR}/domestic_migration_3d_interactive.html"
deck.to_html(output_path)
print(f"\nSaved interactive map: {output_path}")
print("\nOpen this file in a browser, adjust the view as needed, and screenshot for your final image.")
print("You can rotate (click+drag), zoom (scroll), and tilt (right-click+drag) the map.")
