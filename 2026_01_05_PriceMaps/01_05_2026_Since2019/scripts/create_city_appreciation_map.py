#!/usr/bin/env python3
"""
City Appreciation Map Generator
Creates zip-code level choropleth maps showing home price appreciation
from January 2020 to November 2025, with radar circles showing urban/suburban/exurban zones.

Design specifications:
- Color scheme: Black (#3D3733) → White → Blue (#0BB4FF) for low to high appreciation
- No borders between zip codes (cleaner at small sizes)
- Water: Brand blue (#0BB4FF) at 20% opacity, using Natural Earth ocean + lakes shapefiles
- Ocean/lakes buffered 2km to fill gaps with land boundaries
- Radar circles: Red (#F4743B), dotted, 80% opacity, linewidth 2.0
- Distance bands: 10mi (urban), 30mi (suburban)
- Fade effect: 45-55mi radius
- Background: Brand cream (#F6F7F3)
- Projection: Albers Equal Area for accurate distances

Data sources:
- Zillow ZHVI (zip code level)
- Census ZCTA boundaries
- Natural Earth ocean and lakes shapefiles

Usage:
    python create_city_appreciation_map.py [city_name] [--svg]

    If no city specified, defaults to New York.
    Add --svg flag to output SVG with editable text.
"""

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Circle, Wedge
from matplotlib.colors import LinearSegmentedColormap
import geopandas as gpd
import numpy as np
import duckdb
from shapely.geometry import Point, box
import warnings
import sys
import os

warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION - Brand colors and settings
# =============================================================================

# Brand colors
BG_CREAM = '#F6F7F3'
RED = '#F4743B'
GREEN = '#67A275'
BLACK = '#3D3733'
BLUE = '#0BB4FF'

# Map settings
RADAR_CIRCLE_COLOR = RED
RADAR_CIRCLE_OPACITY = 0.8
RADAR_CIRCLE_LINEWIDTH = 2.0
RADAR_CIRCLE_STYLE = 'dotted'
WATER_OPACITY = 0.2
WATER_BUFFER_M = 2000  # Buffer water by 2km to fill gaps with land

# Distance bands (miles)
URBAN_RADIUS_MI = 10
SUBURBAN_RADIUS_MI = 30
VIEW_RADIUS_MI = 50
FADE_START_MI = 45
FADE_END_MI = 55
MI_TO_M = 1609.34

# Default appreciation color scale (can be overridden per city)
DEFAULT_VMIN, DEFAULT_VMAX = 0, 80

# Albers Equal Area projection (for accurate distance circles)
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# Font settings
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"

# Data paths
ZCTA_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/UnzippedShapefiles/ZCTA/tl_2020_us_zcta520.shp"
ANALYSIS_DATA_PATH = "analysis_dataset.parquet"
OCEAN_PATH = "data/ne_10m_ocean.shp"
LAKES_PATH = "data/ne_10m_lakes.shp"

# City configurations: center (lon, lat), zip prefixes, and optional scale override
CITY_CONFIG = {
    'New York': {
        'center': (-73.9857, 40.7484),
        'zip_prefixes': ['10', '11', '12', '13', '06', '07', '08', '18', '19'],
        'vmin': 0, 'vmax': 80,
    },
    'San Francisco': {
        'center': (-122.4194, 37.7749),
        'zip_prefixes': ['94', '95'],
        'vmin': -20, 'vmax': 60,  # Narrower scale for more intense colors
    },
    'Philadelphia': {
        'center': (-75.1652, 39.9526),
        'zip_prefixes': ['19', '08', '18', '17'],
    },
    'Boston': {
        'center': (-71.0589, 42.3601),
        'zip_prefixes': ['01', '02', '03'],
    },
    'Chicago': {
        'center': (-87.6298, 41.8781),
        'zip_prefixes': ['60', '61', '46', '49', '53'],
    },
    'St. Louis': {
        'center': (-90.1994, 38.6270),
        'zip_prefixes': ['63', '62', '65'],
    },
    'Minneapolis': {
        'center': (-93.2650, 44.9778),
        'zip_prefixes': ['55', '56', '54'],
    },
    'Houston': {
        'center': (-95.3698, 29.7604),
        'zip_prefixes': ['77', '78', '76'],
    },
    'Atlanta': {
        'center': (-84.3880, 33.7490),
        'zip_prefixes': ['30', '31'],
    },
    'Tampa': {
        'center': (-82.4572, 27.9506),
        'zip_prefixes': ['33', '34'],
    },
    'Los Angeles': {
        'center': (-118.2437, 34.0522),
        'zip_prefixes': ['90', '91', '92', '93'],
    },
    'Seattle': {
        'center': (-122.3321, 47.6062),
        'zip_prefixes': ['98', '99'],
    },
}


def register_fonts():
    """Register Oracle brand fonts with matplotlib."""
    for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf',
                      'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
        font_path = f"{FONT_DIR}/{font_file}"
        if os.path.exists(font_path):
            fm.fontManager.addfont(font_path)
    plt.rcParams['font.family'] = 'ABC Oracle Edu'


def create_colormap():
    """Create black → white → blue colormap for appreciation."""
    black_rgb = [0x3D/255, 0x37/255, 0x33/255]
    white_rgb = [1.0, 1.0, 1.0]
    blue_rgb = [0x0B/255, 0xB4/255, 0xFF/255]
    return LinearSegmentedColormap.from_list('black_white_blue', [black_rgb, white_rgb, blue_rgb])


def load_housing_data(zip_prefixes):
    """Load housing appreciation data for all ZIPs matching the prefixes.

    Note: We load ALL ZIPs in the geographic area (by prefix), not just those
    assigned to a specific city. This ensures we don't have gaps where ZIPs
    are assigned to neighboring cities (e.g., Palo Alto assigned to San Jose
    instead of San Francisco).
    """
    # Build SQL condition for zip prefixes
    prefix_conditions = " OR ".join([f"zip LIKE '{p}%'" for p in zip_prefixes])
    query = f"SELECT zip, appreciation FROM '{ANALYSIS_DATA_PATH}' WHERE {prefix_conditions}"
    df = duckdb.connect().execute(query).df()
    df['zip'] = df['zip'].astype(str).str.zfill(5)
    return df


def load_zcta(zip_prefixes):
    """Load and filter ZCTA shapefile."""
    zcta = gpd.read_file(ZCTA_PATH)
    zcta['prefix'] = zcta['ZCTA5CE20'].str[:2]
    zcta_filtered = zcta[zcta['prefix'].isin(zip_prefixes)].copy()
    return zcta_filtered.to_crs(ALBERS)


def load_water(view_bounds):
    """Load and clip ocean + lakes shapefiles, with buffer to fill gaps."""
    view_gdf = gpd.GeoDataFrame(geometry=[view_bounds], crs=ALBERS)
    water_gdfs = []

    for path in [OCEAN_PATH, LAKES_PATH]:
        if os.path.exists(path):
            try:
                water = gpd.read_file(path).to_crs(ALBERS)
                water_clip = gpd.clip(water, view_gdf)
                if len(water_clip) > 0:
                    water_clip['geometry'] = water_clip.geometry.buffer(WATER_BUFFER_M)
                    water_gdfs.append(water_clip)
            except:
                pass

    return water_gdfs


def add_fade_effect(ax, center, bg_color):
    """Add fade effect from 45mi to 55mi radius."""
    r_fade_start = FADE_START_MI * MI_TO_M
    r_fade_end = FADE_END_MI * MI_TO_M
    n_rings = 25

    for i in range(n_rings):
        r_inner = r_fade_start + (r_fade_end - r_fade_start) * i / n_rings
        r_outer = r_fade_start + (r_fade_end - r_fade_start) * (i + 1) / n_rings
        alpha = (i + 1) / n_rings
        ring = Wedge((center.x, center.y), r_outer, 0, 360, width=r_outer-r_inner,
                     facecolor=bg_color, edgecolor='none', alpha=alpha, zorder=10)
        ax.add_patch(ring)

    # Solid outer ring
    outer_ring = Wedge((center.x, center.y), r_fade_end * 2, 0, 360,
                       width=r_fade_end * 2 - r_fade_end,
                       facecolor=bg_color, edgecolor='none', alpha=1.0, zorder=10)
    ax.add_patch(outer_ring)


def create_city_map(city_name, output_path=None, svg=False):
    """
    Create appreciation map for a city.

    Args:
        city_name: Name of city (must be in CITY_CONFIG)
        output_path: Output file path (defaults to {city_name}_zipcode_map.png/svg)
        svg: If True, output SVG with editable text
    """
    if city_name not in CITY_CONFIG:
        raise ValueError(f"City '{city_name}' not configured. Available: {list(CITY_CONFIG.keys())}")

    config = CITY_CONFIG[city_name]
    vmin = config.get('vmin', DEFAULT_VMIN)
    vmax = config.get('vmax', DEFAULT_VMAX)

    print(f"Creating map for {city_name}...")

    # Set up for SVG if requested
    if svg:
        matplotlib.use('svg')
        plt.rcParams['svg.fonttype'] = 'none'

    # Register fonts
    register_fonts()

    # Load data (all ZIPs in the area, regardless of city assignment)
    print("  Loading housing data...")
    city_df = load_housing_data(config['zip_prefixes'])

    print("  Loading ZCTA boundaries...")
    zcta = load_zcta(config['zip_prefixes'])

    # Get city center in Albers
    center_latlon = Point(config['center'])
    center = gpd.GeoSeries([center_latlon], crs='EPSG:4326').to_crs(ALBERS)[0]

    # Calculate radii in meters
    r_urban = URBAN_RADIUS_MI * MI_TO_M
    r_suburban = SUBURBAN_RADIUS_MI * MI_TO_M
    r_view = VIEW_RADIUS_MI * MI_TO_M
    padding = 15000

    # Filter ZCTAs by distance
    zcta['centroid'] = zcta.geometry.centroid
    zcta['dist_to_center'] = zcta['centroid'].apply(lambda p: center.distance(p))
    zcta_nearby = zcta[zcta['dist_to_center'] < r_view].copy()

    # Merge with appreciation data
    zcta_nearby = zcta_nearby.merge(city_df[['zip', 'appreciation']],
                                     left_on='ZCTA5CE20', right_on='zip', how='left')

    # Define view bounds
    xmin = center.x - r_view - padding
    xmax = center.x + r_view + padding
    ymin = center.y - r_view - padding
    ymax = center.y + r_view + padding
    view_bounds = box(xmin, ymin, xmax, ymax)

    # Load water
    print("  Loading water...")
    water_gdfs = load_water(view_bounds)

    # Create figure
    print("  Rendering map...")
    fig, ax = plt.subplots(figsize=(9, 7.5), facecolor=BG_CREAM)
    ax.set_facecolor(BG_CREAM)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)

    # Draw water (underneath everything)
    for water_gdf in water_gdfs:
        water_gdf.plot(ax=ax, facecolor=BLUE, edgecolor='none', alpha=WATER_OPACITY, zorder=0)

    # Draw zip codes without data
    no_data = zcta_nearby[zcta_nearby['appreciation'].isna()]
    if len(no_data) > 0:
        no_data.plot(ax=ax, facecolor='#EDEFE7', edgecolor='none', linewidth=0, zorder=1)

    # Draw zip codes with data (choropleth)
    cmap = create_colormap()
    has_data = zcta_nearby[zcta_nearby['appreciation'].notna()].copy()
    if len(has_data) > 0:
        has_data.plot(ax=ax, column='appreciation', cmap=cmap, vmin=vmin, vmax=vmax,
                      edgecolor='none', linewidth=0, zorder=2)

    # Draw radar circles
    for r in [r_urban, r_suburban]:
        circle = Circle((center.x, center.y), r,
                        fill=False, edgecolor=RADAR_CIRCLE_COLOR,
                        linewidth=RADAR_CIRCLE_LINEWIDTH,
                        alpha=RADAR_CIRCLE_OPACITY,
                        linestyle=RADAR_CIRCLE_STYLE, zorder=5)
        ax.add_patch(circle)

    # Add fade effect
    add_fade_effect(ax, center, BG_CREAM)

    ax.set_aspect('equal')
    ax.axis('off')

    # Title
    ax.set_title(city_name.upper(), fontsize=14, fontweight='bold', color=BLACK, pad=8)

    # Colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.6, aspect=20, pad=0.02)
    cbar.set_label('Price Appreciation (%)', fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    # Set colorbar ticks based on scale
    if vmin < 0:
        ticks = [vmin, vmin//2, 0, vmax//2, vmax]
        ticklabels = [f'{t}%' for t in ticks]
    else:
        ticks = [vmin, (vmin+vmax)//2, vmax]
        ticklabels = [f'{t}%' for t in ticks]
    cbar.set_ticks(ticks)
    cbar.set_ticklabels(ticklabels)

    # Save
    if output_path is None:
        ext = 'svg' if svg else 'png'
        output_path = f"{city_name.lower().replace(' ', '_')}_zipcode_map.{ext}"

    if svg:
        plt.savefig(output_path, bbox_inches='tight', facecolor=BG_CREAM)
    else:
        plt.savefig(output_path, bbox_inches='tight', facecolor=BG_CREAM, dpi=150)
    plt.close()

    print(f"  Saved: {output_path}")
    return output_path


if __name__ == '__main__':
    city = 'New York'
    svg = False

    for arg in sys.argv[1:]:
        if arg == '--svg':
            svg = True
        else:
            city = arg

    create_city_map(city, svg=svg)
