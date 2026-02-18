"""
Map of Bay Area zip codes:
- Color: Home price change Aug–Dec 2025 (black negative, cream zero, blue positive)
- Overlay: solid yellow for top-quartile tech worker concentration
- Circular vignette fading to background cream
- Water areas filled (using Natural Earth shapefiles)
"""

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch, Circle, Wedge
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.colors as mcolors
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point, box
from shapely.ops import unary_union
import warnings
import os

warnings.filterwarnings('ignore')

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# Colors
BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
YELLOW = '#FEC439'
DARK_CREAM = '#DADFCE'

# Map settings
MI_TO_M = 1609.34
VIEW_RADIUS_MI = 40
FADE_START_MI = 32
FADE_END_MI = 42
WATER_OPACITY = 0.2
WATER_BUFFER_M = 2000

# Albers Equal Area projection
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# Center on Bay Area (roughly between SF and SJ)
CENTER_LONLAT = (-122.15, 37.55)

# Paths
DATA_DIR = '/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/data'
OUTPUT_DIR = '/Users/azizsunderji/Dropbox/Home Economics/2026_01_29_BayAreaTechPrices/outputs'
OCEAN_PATH = '/Users/azizsunderji/Dropbox/Home Economics/2026_01_05_PriceMaps/01_05_2026_Since2019/data/ne_10m_ocean.shp'
LAKES_PATH = '/Users/azizsunderji/Dropbox/Home Economics/2026_01_05_PriceMaps/01_05_2026_Since2019/data/ne_10m_lakes.shp'

print("Loading zip code data...")
df = pd.read_csv(f'{DATA_DIR}/bay_area_zip_analysis.csv')
df['zip'] = df['zip'].astype(str).str.zfill(5)

# Load Bay Area ZCTAs and filter to those within view radius of center
print("Loading Bay Area ZCTA geometries...")
all_zcta = gpd.read_file(f'{DATA_DIR}/tl_2023_us_zcta520.shp',
                         where="ZCTA5CE20 LIKE '94%' OR ZCTA5CE20 LIKE '95%'")
all_zcta = all_zcta.to_crs(ALBERS)

# Get center in Albers early so we can filter
center_point = gpd.GeoSeries([Point(CENTER_LONLAT)], crs='EPSG:4326').to_crs(ALBERS)[0]
r_view = VIEW_RADIUS_MI * MI_TO_M

# Only keep ZCTAs whose centroid is within view radius + small buffer
all_zcta['dist_to_center'] = all_zcta.geometry.centroid.distance(center_point)
all_zcta = all_zcta[all_zcta['dist_to_center'] < r_view + 10000].copy()
all_zcta = all_zcta.drop(columns='dist_to_center')
print(f"Loaded {len(all_zcta)} ZCTAs within view area")

# Merge with our data (left join to keep all geometries)
gdf = all_zcta.merge(df, left_on='ZCTA5CE20', right_on='zip', how='left')
gdf_no_data_count = gdf['change_aug_dec'].isna().sum()
gdf['change_aug_dec'] = gdf['change_aug_dec'].fillna(1.3)  # Middle bucket midpoint
gdf_with_data = gdf.copy()
print(f"With price data: {len(gdf) - gdf_no_data_count}, filled as 0%: {gdf_no_data_count}")

# Calculate top quartile tech concentration using only SF/SJ metro zips (original area)
metro_mask = gdf_with_data['Metro'].str.contains('San Francisco|San Jose', na=False)
top_quartile_threshold = gdf_with_data.loc[metro_mask, 'info_pct'].quantile(0.75)
gdf_with_data['top_quartile_tech'] = gdf_with_data['info_pct'] >= top_quartile_threshold
print(f"\nTop quartile threshold: {top_quartile_threshold:.1f}%")
print(f"Zips in top quartile: {gdf_with_data['top_quartile_tech'].sum()}")

# Discrete 5-step colormap with quantile breaks (computed on metro zips only)
from matplotlib.colors import BoundaryNorm, ListedColormap
step_colors = [
    '#EDEFE7',   # Pale gray-cream (worst — recedes)
    '#DADFCE',   # Cream
    '#B5CFBA',   # Muted green
    '#67A275',   # Green
    '#2D5A3F',   # Dark green (best — pops)
]
cmap = ListedColormap(step_colors)

# Quantile breaks from SF/SJ metro zips for equal counts in the core area
metro_mask = gdf_with_data['Metro'].str.contains('San Francisco|San Jose', na=False)
metro_values = gdf_with_data.loc[metro_mask, 'change_aug_dec'].dropna()
quantile_breaks = np.quantile(metro_values, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
# Extend edges to capture all data (including non-metro)
bounds = quantile_breaks.copy()
bounds[0] = min(bounds[0], gdf_with_data['change_aug_dec'].min()) - 0.01
bounds[-1] = max(bounds[-1], gdf_with_data['change_aug_dec'].max()) + 0.01
norm = BoundaryNorm(bounds, cmap.N)
print(f"Quantile breaks: {[f'{b:.1f}%' for b in quantile_breaks]}")

print(f"\nPrice change range: {gdf_with_data['change_aug_dec'].min():.1f}% to {gdf_with_data['change_aug_dec'].max():.1f}%")

# Radii already calculated above
padding = 15000

# View bounds
xmin = center_point.x - r_view - padding
xmax = center_point.x + r_view + padding
ymin = center_point.y - r_view - padding
ymax = center_point.y + r_view + padding
view_bounds = box(xmin, ymin, xmax, ymax)

# Load water
print("Loading water...")
water_gdfs = []
for path in [OCEAN_PATH, LAKES_PATH]:
    if os.path.exists(path):
        try:
            view_gdf = gpd.GeoDataFrame(geometry=[view_bounds], crs=ALBERS)
            water = gpd.read_file(path).to_crs(ALBERS)
            water_clip = gpd.clip(water, view_gdf)
            if len(water_clip) > 0:
                water_clip['geometry'] = water_clip.geometry.buffer(WATER_BUFFER_M)
                water_gdfs.append(water_clip)
        except Exception as e:
            print(f"  Warning loading {path}: {e}")

# Create figure
print("Rendering map...")
fig, ax = plt.subplots(figsize=(9, 7.5), facecolor=BG_CREAM)
ax.set_facecolor(BG_CREAM)
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

# Draw water: flat light blue (gradient to be added in Illustrator via Inner Glow)
for water_gdf in water_gdfs:
    water_gdf.plot(ax=ax, facecolor=BLUE, edgecolor='none', alpha=0.10, zorder=0)

# Plot all zip codes with cream outlines
gdf_with_data.plot(ax=ax,
         column='change_aug_dec',
         cmap=cmap,
         norm=norm,
         edgecolor='none',
         linewidth=0,
         legend=False,
         zorder=2)

# Add 0.5pt zip boundaries
gdf_with_data.boundary.plot(ax=ax, color=BG_CREAM, linewidth=0.5, zorder=3)

# Tech overlay: solid yellow, dissolved so contiguous areas merge
tech_zips = gdf_with_data[gdf_with_data['top_quartile_tech']].copy()
tech_dissolved = tech_zips.dissolve()
tech_dissolved.plot(ax=ax,
                    color=YELLOW,
                    alpha=0.35,
                    edgecolor='none',
                    zorder=4)

# (Fade effect removed — will be added in Illustrator)

# City labels
# Need to project city label coords to Albers
city_labels = {
    'San Francisco': (-122.44, 37.77),
    'Oakland': (-122.22, 37.81),
    'San Jose': (-121.88, 37.32),
    'Palo Alto': (-122.16, 37.45),
    'Berkeley': (-122.27, 37.88),
    'Mountain View': (-122.07, 37.40),
    'Fremont': (-121.95, 37.52),
    'Walnut Creek': (-122.05, 37.91),
    'San Mateo': (-122.32, 37.55),
}

for city, (lon, lat) in city_labels.items():
    pt = gpd.GeoSeries([Point(lon, lat)], crs='EPSG:4326').to_crs(ALBERS)[0]
    dist = center_point.distance(pt)
    if dist < r_view * 0.85:
        ax.annotate(city, xy=(pt.x, pt.y), fontsize=9, color=BLACK,
                    ha='center', fontweight='bold', zorder=20)

ax.set_aspect('equal')
ax.axis('off')

# Title
ax.set_title('Bay Area Home Prices & Tech Worker Concentration by Zip Code',
             fontsize=14, fontweight='bold', color=BLACK, pad=15)

# Colorbar
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, shrink=0.5, aspect=20, pad=0.02)
cbar.set_label('Home Price Change, Aug–Dec 2025 (%)', fontsize=10, color=BLACK)
cbar.ax.tick_params(colors=BLACK)

# Legend
legend_elements = [
    Patch(facecolor=YELLOW, edgecolor='none', alpha=0.35,
          label=f'Top quartile tech workers (≥{top_quartile_threshold:.1f}%)')
]
ax.legend(handles=legend_elements, loc='lower left', frameon=True,
          facecolor=BG_CREAM, edgecolor='none', fontsize=9)

# Source
ax.text(0.01, 0.02, 'Source: Zillow ZHVI (Dec 2025), ACS 2023 5-Year Estimates\nTech = Information sector employment',
        transform=ax.transAxes, fontsize=8, color='#888888', style='italic')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/bay_area_zip_price_map.png',
            dpi=150, bbox_inches='tight', facecolor=BG_CREAM)
plt.savefig(f'{OUTPUT_DIR}/bay_area_zip_price_map.svg',
            bbox_inches='tight', facecolor=BG_CREAM)
print(f"\nMap saved to {OUTPUT_DIR}/bay_area_zip_price_map.png")

# Print summary stats
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"\nZips in TOP QUARTILE tech & POSITIVE price change: {len(gdf_with_data[(gdf_with_data['top_quartile_tech']) & (gdf['change_aug_dec'] > 0)])}")
print(f"Zips in TOP QUARTILE tech & NEGATIVE price change: {len(gdf_with_data[(gdf_with_data['top_quartile_tech']) & (gdf['change_aug_dec'] < 0)])}")
print(f"Zips BELOW top quartile & POSITIVE price change: {len(gdf_with_data[(~gdf_with_data['top_quartile_tech']) & (gdf['change_aug_dec'] > 0)])}")
print(f"Zips BELOW top quartile & NEGATIVE price change: {len(gdf_with_data[(~gdf_with_data['top_quartile_tech']) & (gdf['change_aug_dec'] < 0)])}")
