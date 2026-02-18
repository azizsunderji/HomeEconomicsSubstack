"""
Download Natural Earth 10m admin-1 shapefile, simplify, export as TopoJSON.
Output: data/admin1_simplified.topojson

Uses 10m resolution (not 50m) to get full ~4,500 sub-national regions worldwide.
"""
import os
import sys
import zipfile
import requests
import geopandas as gpd
import topojson as tp

BASE_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_10_LLMLanguages"
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

NE_URL = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
ZIP_PATH = os.path.join(DATA_DIR, "ne_10m_admin_1.zip")
EXTRACT_DIR = os.path.join(DATA_DIR, "ne_10m_admin_1")
OUTPUT_PATH = os.path.join(DATA_DIR, "admin1_simplified.topojson")

# Step 1: Download
if not os.path.exists(ZIP_PATH):
    print("Downloading Natural Earth 10m admin-1 shapefile...")
    r = requests.get(NE_URL, stream=True)
    r.raise_for_status()
    with open(ZIP_PATH, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"  Downloaded {os.path.getsize(ZIP_PATH) / 1e6:.1f} MB")
else:
    print(f"Using cached zip: {ZIP_PATH}")

# Step 2: Extract
if not os.path.exists(EXTRACT_DIR):
    print("Extracting...")
    os.makedirs(EXTRACT_DIR, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        zf.extractall(EXTRACT_DIR)
    print(f"  Extracted to {EXTRACT_DIR}")

# Step 3: Load with geopandas
shp_file = os.path.join(EXTRACT_DIR, "ne_10m_admin_1_states_provinces.shp")
print(f"Loading shapefile: {shp_file}")
gdf = gpd.read_file(shp_file)
print(f"  Loaded {len(gdf)} admin-1 regions")

# Step 4: Keep only needed columns
keep_cols = ["iso_a2", "name", "admin", "iso_3166_2", "geometry"]
available = set(gdf.columns)
if "iso_3166_2" not in available and "code_hasc" in available:
    gdf["iso_3166_2"] = gdf["code_hasc"]
    print("  Note: Using 'code_hasc' as iso_3166_2 substitute")

gdf = gdf[[c for c in keep_cols if c in gdf.columns]]

# Step 5: Simplify geometry — more aggressive since 10m is very detailed
# tolerance=0.05 degrees ≈ ~5km, good balance of size vs detail
print("Simplifying geometries (tolerance=0.05)...")
gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.05, preserve_topology=True)

# Drop any null/empty geometries
gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()]
print(f"  {len(gdf)} regions after simplification")

# Step 6: Convert to TopoJSON (shared arcs compress well)
print("Converting to TopoJSON...")
topo = tp.Topology(gdf, toposimplify=0.0001)
topo_json = topo.to_json()

with open(OUTPUT_PATH, "w") as f:
    f.write(topo_json)

file_size = os.path.getsize(OUTPUT_PATH) / 1e6
print(f"  Saved to {OUTPUT_PATH} ({file_size:.1f} MB)")

# Print distribution by country
country_counts = gdf["iso_a2"].value_counts()
print(f"\nTop 20 countries by admin-1 region count:")
for country, count in country_counts.head(20).items():
    print(f"  {country}: {count}")

# Print some key countries for verification
for cc in ["IN", "NG", "ET", "PK", "CN", "ZA", "ID", "RU", "ES", "CD"]:
    subset = gdf[gdf["iso_a2"] == cc]
    if len(subset) > 0:
        codes = subset["iso_3166_2"].tolist()
        print(f"\n{cc} ({len(subset)} regions): {codes[:10]}{'...' if len(codes) > 10 else ''}")
