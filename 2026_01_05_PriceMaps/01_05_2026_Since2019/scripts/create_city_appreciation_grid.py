#!/usr/bin/env python3
"""
City Appreciation Grid Generator
Creates a 4x3 grid of city appreciation maps showing home price changes
from January 2020 to November 2025.

Final Configuration:
- Northeast: New York, Philadelphia, Boston
- Midwest: Chicago, St. Louis, Minneapolis  
- South: Houston, Atlanta, Tampa
- West: Los Angeles, San Francisco, Seattle

Design Specifications:
- Color scheme: Red (#F4743B) → White → Green (#67A275)
- No borders between zip codes
- Water: Brand blue (#0BB4FF) at 20% opacity (ocean + lakes)
- Radar circles: Black at 30% opacity, 10mi and 30mi
- Fade effect: 45-55mi radius
- Rows ordered by regional performance (Northeast strongest → West weakest)

Usage:
    python create_city_appreciation_grid.py
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Circle, Wedge
from matplotlib.colors import LinearSegmentedColormap
import geopandas as gpd
import numpy as np
import duckdb
from shapely.geometry import Point, box
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

# Brand colors
BG_CREAM = '#F6F7F3'
RED = '#F4743B'
GREEN = '#67A275'
BLACK = '#3D3733'
BLUE = '#0BB4FF'

# Paths
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
ZCTA_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/UnzippedShapefiles/ZCTA/tl_2020_us_zcta520.shp"
OCEAN_PATH = "data/ne_10m_ocean.shp"
LAKES_PATH = "data/ne_10m_lakes.shp"
DATA_PATH = "analysis_dataset.parquet"

# Projection
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# City configurations: center (lon, lat) and zip prefixes
CITY_CONFIG = {
    'New York': {'center': (-73.9857, 40.7484), 'zip_prefixes': ['10', '11', '12', '13', '06', '07', '08', '18', '19']},
    'Philadelphia': {'center': (-75.1652, 39.9526), 'zip_prefixes': ['19', '08', '18', '17']},
    'Boston': {'center': (-71.0589, 42.3601), 'zip_prefixes': ['01', '02', '03']},
    'Chicago': {'center': (-87.6298, 41.8781), 'zip_prefixes': ['60', '61', '46', '49', '53']},
    'St. Louis': {'center': (-90.1994, 38.6270), 'zip_prefixes': ['63', '62', '65']},
    'Minneapolis': {'center': (-93.2650, 44.9778), 'zip_prefixes': ['55', '56', '54']},
    'Houston': {'center': (-95.3698, 29.7604), 'zip_prefixes': ['77', '78', '76']},
    'Atlanta': {'center': (-84.3880, 33.7490), 'zip_prefixes': ['30', '31']},
    'Tampa': {'center': (-82.4572, 27.9506), 'zip_prefixes': ['33', '34']},
    'Los Angeles': {'center': (-118.2437, 34.0522), 'zip_prefixes': ['90', '91', '92', '93']},
    'San Francisco': {'center': (-122.4194, 37.7749), 'zip_prefixes': ['94', '95']},
    'Seattle': {'center': (-122.3321, 47.6062), 'zip_prefixes': ['98', '99']},
}

# Regions ordered by performance (strongest to weakest)
REGIONS = [
    ('Northeast', ['New York', 'Philadelphia', 'Boston']),
    ('Midwest', ['Chicago', 'St. Louis', 'Minneapolis']),
    ('South', ['Houston', 'Atlanta', 'Tampa']),
    ('West', ['Los Angeles', 'San Francisco', 'Seattle']),
]

# Map settings
MI_TO_M = 1609.34
R_URBAN = 10 * MI_TO_M
R_SUBURBAN = 30 * MI_TO_M
R_VIEW = 50 * MI_TO_M
R_FADE_START = 45 * MI_TO_M
R_FADE_END = 55 * MI_TO_M
PADDING = 15000
VMIN, VMAX = 0, 80

# =============================================================================
# FUNCTIONS
# =============================================================================

def register_fonts():
    for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
        fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
    plt.rcParams['font.family'] = 'ABC Oracle Edu'

def create_colormap():
    red = [0xF4/255, 0x74/255, 0x3B/255]
    white = [1.0, 1.0, 1.0]
    green = [0x67/255, 0xA2/255, 0x75/255]
    return LinearSegmentedColormap.from_list('red_white_green', [red, white, green])

def plot_city(ax, city_name, df, zcta_full, ocean_full, lakes_full, cmap):
    config = CITY_CONFIG[city_name]
    center_latlon = Point(config['center'])
    center = gpd.GeoSeries([center_latlon], crs='EPSG:4326').to_crs(ALBERS)[0]
    
    # Filter ZCTA
    zcta = zcta_full[zcta_full['prefix'].isin(config['zip_prefixes'])].copy()
    zcta['centroid'] = zcta.geometry.centroid
    zcta['dist'] = zcta['centroid'].apply(lambda p: center.distance(p))
    zcta_nearby = zcta[zcta['dist'] < R_VIEW].copy()
    
    # Merge with data
    city_df = df[df['nearest_city'] == city_name]
    zcta_nearby = zcta_nearby.merge(city_df[['zip', 'appreciation']], 
                                     left_on='ZCTA5CE20', right_on='zip', how='left')
    
    # View bounds
    xmin = center.x - R_VIEW - PADDING
    xmax = center.x + R_VIEW + PADDING
    ymin = center.y - R_VIEW - PADDING
    ymax = center.y + R_VIEW + PADDING
    
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_facecolor(BG_CREAM)
    
    view_bounds = box(xmin, ymin, xmax, ymax)
    view_gdf = gpd.GeoDataFrame(geometry=[view_bounds], crs=ALBERS)
    
    # Water (ocean + lakes)
    for water_gdf in [ocean_full, lakes_full]:
        try:
            water_clip = gpd.clip(water_gdf, view_gdf)
            if len(water_clip) > 0:
                water_clip['geometry'] = water_clip.geometry.buffer(2000)
                water_clip.plot(ax=ax, facecolor=BLUE, edgecolor='none', alpha=0.2, zorder=0)
        except:
            pass
    
    # Zip codes
    no_data = zcta_nearby[zcta_nearby['appreciation'].isna()]
    if len(no_data) > 0:
        no_data.plot(ax=ax, facecolor='#EDEFE7', edgecolor='none', linewidth=0, zorder=1)
    
    has_data = zcta_nearby[zcta_nearby['appreciation'].notna()]
    if len(has_data) > 0:
        has_data.plot(ax=ax, column='appreciation', cmap=cmap, vmin=VMIN, vmax=VMAX,
                      edgecolor='none', linewidth=0, zorder=2)
    
    # Radar circles
    for r in [R_URBAN, R_SUBURBAN]:
        circle = Circle((center.x, center.y), r, fill=False, edgecolor=BLACK, 
                        linewidth=0.8, alpha=0.3, zorder=5)
        ax.add_patch(circle)
    
    # Fade effect
    n_rings = 25
    for i in range(n_rings):
        r_inner = R_FADE_START + (R_FADE_END - R_FADE_START) * i / n_rings
        r_outer = R_FADE_START + (R_FADE_END - R_FADE_START) * (i + 1) / n_rings
        alpha = (i + 1) / n_rings
        ring = Wedge((center.x, center.y), r_outer, 0, 360, width=r_outer-r_inner,
                     facecolor=BG_CREAM, edgecolor='none', alpha=alpha, zorder=10)
        ax.add_patch(ring)
    
    outer_ring = Wedge((center.x, center.y), R_FADE_END * 2, 0, 360, 
                       width=R_FADE_END * 2 - R_FADE_END,
                       facecolor=BG_CREAM, edgecolor='none', alpha=1.0, zorder=10)
    ax.add_patch(outer_ring)
    
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(city_name.upper(), fontsize=9, fontweight='bold', color=BLACK, pad=3)

def create_grid(output_path='city_appreciation_grid.png'):
    register_fonts()
    cmap = create_colormap()
    
    print("Loading data...")
    df = duckdb.connect().execute(f"SELECT * FROM '{DATA_PATH}'").df()
    df['zip'] = df['zip'].astype(str).str.zfill(5)
    
    print("Loading ZCTA shapefile...")
    zcta_full = gpd.read_file(ZCTA_PATH).to_crs(ALBERS)
    zcta_full['prefix'] = zcta_full['ZCTA5CE20'].str[:2]
    
    print("Loading water...")
    ocean_full = gpd.read_file(OCEAN_PATH).to_crs(ALBERS)
    lakes_full = gpd.read_file(LAKES_PATH).to_crs(ALBERS)
    
    print("Creating grid...")
    fig = plt.figure(figsize=(9.6, 14), facecolor=BG_CREAM, dpi=100)
    
    gs = fig.add_gridspec(4, 4, left=0.06, right=0.98, top=0.96, bottom=0.01,
                          wspace=0.01, hspace=0.04, width_ratios=[0.1, 1, 1, 1])
    
    # Colorbar
    cbar_ax = fig.add_axes([0.25, 0.975, 0.5, 0.012])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=VMIN, vmax=VMAX))
    sm.set_array([])
    cbar = plt.colorbar(sm, cax=cbar_ax, orientation='horizontal')
    cbar.ax.tick_params(labelsize=8)
    cbar.set_ticks([0, 40, 80])
    cbar.set_ticklabels(['0%', '40%', '80%'])
    cbar.outline.set_visible(False)
    
    for row_idx, (region_name, cities) in enumerate(REGIONS):
        print(f"  {region_name}...")
        
        # Region label
        label_ax = fig.add_subplot(gs[row_idx, 0])
        label_ax.set_facecolor(BG_CREAM)
        label_ax.axis('off')
        label_ax.text(0.5, 0.5, region_name.upper(), fontsize=9, fontweight='bold', 
                      color=BLACK, ha='center', va='center', rotation=90)
        
        # City maps
        for col_idx, city in enumerate(cities):
            ax = fig.add_subplot(gs[row_idx, col_idx + 1])
            plot_city(ax, city, df, zcta_full, ocean_full, lakes_full, cmap)
    
    plt.savefig(output_path, facecolor=BG_CREAM, dpi=100, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")

def create_single_city(city_name, output_path=None):
    """Generate a standalone map for a single city."""
    register_fonts()
    cmap = create_colormap()
    
    if output_path is None:
        output_path = f"{city_name.lower().replace(' ', '_')}_map.png"
    
    print(f"Creating map for {city_name}...")
    df = duckdb.connect().execute(f"SELECT * FROM '{DATA_PATH}'").df()
    df['zip'] = df['zip'].astype(str).str.zfill(5)
    
    zcta_full = gpd.read_file(ZCTA_PATH).to_crs(ALBERS)
    zcta_full['prefix'] = zcta_full['ZCTA5CE20'].str[:2]
    ocean_full = gpd.read_file(OCEAN_PATH).to_crs(ALBERS)
    lakes_full = gpd.read_file(LAKES_PATH).to_crs(ALBERS)
    
    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100, facecolor=BG_CREAM)
    plot_city(ax, city_name, df, zcta_full, ocean_full, lakes_full, cmap)
    ax.set_title(city_name.upper(), fontsize=14, fontweight='bold', color=BLACK, pad=8)
    
    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=VMIN, vmax=VMAX))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.02)
    cbar.set_label('Price Appreciation (%)', fontsize=10)
    cbar.ax.tick_params(labelsize=9)
    
    plt.savefig(output_path, facecolor=BG_CREAM, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_path}")

if __name__ == '__main__':
    create_grid()
