"""
Create Since2019 Price Map
Shows home price changes from Jan 2020 to Nov 2025 by ZIP code.
Replicates methodology from yoy_price_map_final.svg
"""

import duckdb
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.colors as mcolors
from matplotlib.font_manager import FontProperties
from matplotlib.colorbar import ColorbarBase
import numpy as np
import pandas as pd

# SVG settings for editable text
matplotlib.use('svg')
plt.rcParams['svg.fonttype'] = 'none'

# =============================================================================
# CONFIGURATION (from CLAUDE.md NATIONAL MAPS specs)
# =============================================================================

# Colors
BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
LAND_CREAM = '#EDEFE7'

# Albers Equal Area projection
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# States to exclude (non-continental)
EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']

# Bubble sizing parameters (in map meters, then converted to display points)
MAX_RADIUS = 12000
SCALE = 6000
MIN_RADIUS = 800

# Display size range (scatter s parameter = area in points^2)
# Original SVG had radii 0.11-1.62 pts, so s = pi*r^2 = 0.038 to 8.25
S_MIN = 0.04
S_MAX = 8.25

# Opacity
ALPHA = 0.35

# Font - register Oracle font with matplotlib
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
FONT_PATH = f"{FONT_DIR}/ABCOracle-Regular.otf"

import matplotlib.font_manager as fm
# Add all Oracle fonts to matplotlib's font manager
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")

# Set as default font
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# Data paths
ZILLOW_PARQUET = '/Users/azizsunderji/Dropbox/Home Economics/Data/Prices/zillow_zhvi_zip.parquet'
ZCTA_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/UnzippedShapefiles/ZCTA/tl_2020_us_zcta520.shp'
STATE_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp'
POP_CSV = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Populations/PopulationByZIP.csv'

# Output
OUTPUT_PATH = '/Users/azizsunderji/Dropbox/Home Economics/2026_01_05_PriceMaps/01_05_2026_Since2019/Since2019.svg'

# =============================================================================
# LOAD DATA
# =============================================================================

print("Loading Zillow data...")
conn = duckdb.connect()
df = conn.execute("""
    SELECT
        RegionName as zip,
        "2020-01-31" as price_jan2020,
        "2025-11-30" as price_nov2025
    FROM read_parquet('{}')
    WHERE "2020-01-31" IS NOT NULL AND "2025-11-30" IS NOT NULL
""".format(ZILLOW_PARQUET)).df()

df['change'] = ((df['price_nov2025'] - df['price_jan2020']) / df['price_jan2020']) * 100
df['zip'] = df['zip'].astype(str).str.zfill(5)

print(f"Total ZIPs with data: {len(df)}")
print(f"Positive changes: {(df['change'] > 0).sum()}")
print(f"Negative changes: {(df['change'] <= 0).sum()}")
print(f"Min change: {df['change'].min():.1f}%")
print(f"Max change: {df['change'].max():.1f}%")

# Load ZCTA shapefile
print("Loading ZCTA shapefile...")
zcta = gpd.read_file(ZCTA_SHAPEFILE)
zcta['ZCTA5CE20'] = zcta['ZCTA5CE20'].astype(str).str.zfill(5)

# Project to Albers first, then compute centroids
print("Projecting to Albers and computing centroids...")
zcta = zcta.to_crs(ALBERS)
zcta['centroid'] = zcta.geometry.centroid
zip_centroids = gpd.GeoDataFrame(zcta[['ZCTA5CE20']], geometry=zcta['centroid'], crs=zcta.crs)

# Load population data
print("Loading population data...")
pop_df = pd.read_csv(POP_CSV, encoding='latin-1')
pop_df.columns = ['zcta', 'name', 'population']
pop_df['zip'] = pop_df['zcta'].astype(str).str.zfill(5)
pop_df['population'] = pd.to_numeric(pop_df['population'], errors='coerce')

# Merge all data
print("Merging data...")
merged = zip_centroids.merge(df, left_on='ZCTA5CE20', right_on='zip', how='inner')
merged = merged.merge(pop_df[['zip', 'population']], on='zip', how='left')
merged['population'] = merged['population'].fillna(1000)

print(f"Final merged records: {len(merged)}")

# Load state boundaries
print("Loading state boundaries...")
states = gpd.read_file(STATE_SHAPEFILE)
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)

# =============================================================================
# CALCULATE BUBBLE SIZES AND COLORS
# =============================================================================

# Asymptotic curve for bubble sizes (in map meters)
merged['radius'] = MAX_RADIUS * (1 - np.exp(-merged['population'] / SCALE))
merged['radius'] = merged['radius'].clip(MIN_RADIUS, MAX_RADIUS)

# Convert to display size (scatter s parameter)
# Normalize radius to 0-1, then scale to S_MIN-S_MAX
merged['s'] = S_MIN + (merged['radius'] - MIN_RADIUS) / (MAX_RADIUS - MIN_RADIUS) * (S_MAX - S_MIN)

# Binary colors: black (below median) / blue (above median)
median_change = merged['change'].median()
print(f"Median change: {median_change:.1f}%")

merged['color'] = merged['change'].apply(lambda x: BLUE if x >= median_change else BLACK)

# =============================================================================
# CREATE FIGURE
# =============================================================================

print("Creating figure...")
oracle_font = FontProperties(fname=FONT_PATH)

# Match original dimensions (648pt x 540pt = 6.48 x 5.4 inches at 100 dpi)
fig, ax = plt.subplots(figsize=(6.48, 5.4), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Plot states
states.plot(ax=ax, facecolor=LAND_CREAM, edgecolor='white', linewidth=0.75)

# Get coordinates for scatter
coords = merged.geometry.apply(lambda g: (g.x, g.y))
x = [c[0] for c in coords]
y = [c[1] for c in coords]

# Plot bubbles
ax.scatter(x, y, s=merged['s'], c=merged['color'], alpha=ALPHA, linewidths=0)

# Set bounds with padding
bounds = states.total_bounds
ax.set_xlim(bounds[0] - 100000, bounds[2] + 100000)
ax.set_ylim(bounds[1] - 100000, bounds[3] + 100000)
ax.set_aspect('equal')
ax.axis('off')

# =============================================================================
# ADD LEGEND (Binary)
# =============================================================================

legend_y = 0.12
ax.scatter([0.18], [legend_y], s=60, c=BLACK, alpha=ALPHA, transform=ax.transAxes)
ax.text(0.21, legend_y, f'Below median (+{median_change:.0f}%)', transform=ax.transAxes, va='center',
        fontproperties=oracle_font, fontsize=8, color=BLACK)
ax.scatter([0.55], [legend_y], s=60, c=BLUE, alpha=ALPHA, transform=ax.transAxes)
ax.text(0.58, legend_y, f'Above median (+{median_change:.0f}%)', transform=ax.transAxes, va='center',
        fontproperties=oracle_font, fontsize=8, color=BLACK)

# =============================================================================
# ADD CITY LABELS (Top 30 by population)
# =============================================================================

from pyproj import Transformer

top_cities = [
    ("New York", 40.7128, -74.0060),
    ("Los Angeles", 34.0522, -118.2437),
    ("Chicago", 41.8781, -87.6298),
    ("Houston", 29.7604, -95.3698),
    ("Phoenix", 33.4484, -112.0740),
    ("Philadelphia", 39.9526, -75.1652),
    ("San Antonio", 29.4241, -98.4936),
    ("San Diego", 32.7157, -117.1611),
    ("Dallas", 32.7767, -96.7970),
    ("San Jose", 37.3382, -121.8863),
    ("Austin", 30.2672, -97.7431),
    ("Jacksonville", 30.3322, -81.6557),
    ("Fort Worth", 32.7555, -97.3308),
    ("Columbus", 39.9612, -82.9988),
    ("Charlotte", 35.2271, -80.8431),
    ("San Francisco", 37.7749, -122.4194),
    ("Indianapolis", 39.7684, -86.1581),
    ("Seattle", 47.6062, -122.3321),
    ("Denver", 39.7392, -104.9903),
    ("Washington", 38.9072, -77.0369),
    ("Boston", 42.3601, -71.0589),
    ("Nashville", 36.1627, -86.7816),
    ("Detroit", 42.3314, -83.0458),
    ("Oklahoma City", 35.4676, -97.5164),
    ("Portland", 45.5152, -122.6784),
    ("Las Vegas", 36.1699, -115.1398),
    ("Memphis", 35.1495, -90.0490),
    ("Louisville", 38.2527, -85.7585),
    ("Baltimore", 39.2904, -76.6122),
    ("Milwaukee", 43.0389, -87.9065),
    ("Miami", 25.7617, -80.1918),
    # Additional major metros (large metro, smaller city proper)
    ("Atlanta", 33.7490, -84.3880),
    ("Tampa", 27.9506, -82.4572),
    ("Minneapolis", 44.9778, -93.2650),
    ("St. Louis", 38.6270, -90.1994),
    ("Pittsburgh", 40.4406, -79.9959),
    ("Cleveland", 41.4993, -81.6944),
    ("Cincinnati", 39.1031, -84.5120),
    ("Kansas City", 39.0997, -94.5786),
    ("Orlando", 28.5383, -81.3792),
    ("Raleigh", 35.7796, -78.6382),
    ("Salt Lake City", 40.7608, -111.8910),
]

# Transform lat/lon to Albers
transformer = Transformer.from_crs("EPSG:4326", ALBERS, always_xy=True)

for city, lat, lon in top_cities:
    x_city, y_city = transformer.transform(lon, lat)
    ax.annotate(city, (x_city, y_city), fontsize=5, fontproperties=oracle_font,
                color=BLACK, ha='center', va='bottom',
                xytext=(0, 3), textcoords='offset points')

# =============================================================================
# ADD TITLE
# =============================================================================

ax.text(0.5, 0.97, 'Home Price Changes: Jan 2020 to Nov 2025',
        transform=ax.transAxes, ha='center', va='top',
        fontproperties=oracle_font, fontsize=12, color=BLACK)

# =============================================================================
# SAVE
# =============================================================================

plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
plt.savefig(OUTPUT_PATH, format='svg', facecolor=BG_CREAM)
plt.close()

print(f"\nSaved to: {OUTPUT_PATH}")
