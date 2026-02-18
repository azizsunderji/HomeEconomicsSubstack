"""
DFW Dot Density Map — each dot = 50 housing units.
Green dots = pre-2010 stock, Yellow dots = built 2010+.
"""

import os
import requests
import pandas as pd
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D
from shapely.ops import unary_union
from shapely.geometry import Point
import random

PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_31_CityLimits"
DATA = f"{PROJECT}/data"
OUTPUTS = f"{PROJECT}/outputs"
SHAPEFILE_2023 = "/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_us_tract_5m.zip"
ROADS_ZIP = f"{DATA}/tl_2023_us_primaryroads.zip"
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"

for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

DFW_COUNTIES = [
    # Core DFW MSA
    '085', '113', '121', '139', '231', '251', '257', '367', '397', '439', '497',
    # Outer ring
    '097', '147', '181', '221', '349', '213', '425', '467', '379', '223',
    '109', '119', '277',
    # Wider fill — south, west, east
    '217',  # Hill (SW)
    '035',  # Bosque (SW)
    '161',  # Freestone (SE)
    '293',  # Limestone (S)
    '309',  # McLennan (SW — Waco area)
    '337',  # Montague (NW)
    '499',  # Wood (E)
    '237',  # Jack (NW)
    '001',  # Anderson (SE)
    '143',  # Erath (SW)
    '363',  # Palo Pinto (W)
    '423',  # Smith (SE — Tyler area)
    '159',  # Franklin (NE)
    '289',  # Leon (SE)
]

DOWNTOWN_DALLAS_COORD = (-96.797, 32.780)
DOWNTOWN_FTW_COORD = (-97.328, 32.755)

CITY_LABELS = {
    'Dallas': (-96.797, 32.7767),
    'Fort Worth': (-97.3308, 32.7555),
    'Plano': (-96.6989, 33.0198),
    'Frisco': (-96.8236, 33.1507),
    'McKinney': (-96.6153, 33.1972),
    'Arlington': (-97.1081, 32.7357),
    'Denton': (-97.1331, 33.2148),
    'Garland': (-96.6389, 32.9126),
    'Irving': (-96.9489, 32.8140),
}

UNITS_PER_DOT = 20


def random_points_in_polygon(polygon, n):
    """Generate n random points within a polygon."""
    if n <= 0 or polygon.is_empty:
        return []
    points = []
    minx, miny, maxx, maxy = polygon.bounds
    attempts = 0
    max_attempts = n * 50
    while len(points) < n and attempts < max_attempts:
        batch_size = min((n - len(points)) * 3, 5000)
        xs = np.random.uniform(minx, maxx, batch_size)
        ys = np.random.uniform(miny, maxy, batch_size)
        for x, y in zip(xs, ys):
            p = Point(x, y)
            if polygon.contains(p):
                points.append((x, y))
                if len(points) >= n:
                    break
        attempts += batch_size
    return points


CENSUS_API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"

def fetch_housing_2024_wide():
    """Fetch 2024 ACS housing data for the full county set."""
    import requests
    out = f"{DATA}/dfw_housing_2024_wide.parquet"
    if os.path.exists(out):
        return pd.read_parquet(out)
    print("Fetching 2024 ACS for wider county set...")
    rows = []
    for county in DFW_COUNTIES:
        url = (f"https://api.census.gov/data/2024/acs/acs5"
               f"?get=B25001_001E,B25034_002E,B25034_003E"
               f"&for=tract:*&in=state:48&in=county:{county}"
               f"&key={CENSUS_API_KEY}")
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            for row in data[1:]:
                rows.append(dict(zip(data[0], row)))
            print(f"  {county}: {len(data)-1} tracts")
        else:
            print(f"  {county}: FAILED {r.status_code}")
    df = pd.DataFrame(rows)
    df['GEOID'] = df['state'] + df['county'] + df['tract']
    for col in ['B25001_001E', 'B25034_002E', 'B25034_003E']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df.loc[df[col] < 0, col] = np.nan
    df['housing_units'] = df['B25001_001E']
    df['built_2010_later'] = df['B25034_002E'].fillna(0) + df['B25034_003E'].fillna(0)
    df = df[['GEOID', 'housing_units', 'built_2010_later']].copy()
    df.to_parquet(out, index=False)
    print(f"  Saved {len(df)} tracts")
    return df


if __name__ == '__main__':
    np.random.seed(42)

    # ── Load data ──────────────────────────────────────────────────────
    hu = fetch_housing_2024_wide()
    drive = pd.read_parquet(f"{DATA}/dfw_drive_times.parquet")

    gdf = gpd.read_file(f"zip://{SHAPEFILE_2023}")
    gdf = gdf[(gdf['STATEFP'] == '48') & (gdf['COUNTYFP'].isin(DFW_COUNTIES))].copy()
    gdf = gdf.to_crs(ALBERS)
    gdf = gdf.merge(hu, on='GEOID', how='left')

    # Pre-2010 units
    gdf['pre_2010'] = gdf['housing_units'] - gdf['built_2010_later']
    gdf.loc[gdf['pre_2010'] < 0, 'pre_2010'] = 0

    print(f"Total units: {gdf.housing_units.sum():,.0f}")
    print(f"Pre-2010: {gdf.pre_2010.sum():,.0f}")
    print(f"Post-2010: {gdf.built_2010_later.sum():,.0f}")
    print(f"Dots per unit: 1 dot = {UNITS_PER_DOT} units")
    print(f"Expected dots: ~{gdf.housing_units.sum() / UNITS_PER_DOT:,.0f}")

    # ── Generate dot positions ─────────────────────────────────────────
    print("\nGenerating dots (this may take a minute)...")
    green_xs, green_ys = [], []
    yellow_xs, yellow_ys = [], []

    for idx, row in gdf.iterrows():
        if pd.isna(row['housing_units']) or row['housing_units'] <= 0:
            continue
        geom = row['geometry']
        if geom.is_empty:
            continue

        n_green = int(round(row['pre_2010'] / UNITS_PER_DOT)) if not pd.isna(row['pre_2010']) else 0
        n_yellow = int(round(row['built_2010_later'] / UNITS_PER_DOT)) if not pd.isna(row['built_2010_later']) else 0

        total_dots = n_green + n_yellow
        if total_dots == 0:
            continue

        pts = random_points_in_polygon(geom, total_dots)
        # Shuffle so green and yellow are interleaved spatially
        random.shuffle(pts)

        for i, (x, y) in enumerate(pts):
            if i < n_green:
                green_xs.append(x)
                green_ys.append(y)
            else:
                yellow_xs.append(x)
                yellow_ys.append(y)

    print(f"  Green dots: {len(green_xs):,}")
    print(f"  Yellow dots: {len(yellow_xs):,}")

    # ── Commute shed ───────────────────────────────────────────────────
    merged_drive = gdf.merge(drive[['GEOID', 'min_drive_min']], on='GEOID', how='left')
    shed_tracts = merged_drive[merged_drive['min_drive_min'] <= 45]
    raw = unary_union(shed_tracts.geometry)
    shed = raw.buffer(5_000).buffer(-5_000)
    if shed.geom_type == 'MultiPolygon':
        shed = max(shed.geoms, key=lambda g: g.area)

    # ── Roads ──────────────────────────────────────────────────────────
    roads = gpd.read_file(f"zip://{ROADS_ZIP}").to_crs(ALBERS)
    dal_pt = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([DOWNTOWN_DALLAS_COORD[0]], [DOWNTOWN_DALLAS_COORD[1]]),
        crs='EPSG:4326'
    ).to_crs(ALBERS)
    ftw_pt = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([DOWNTOWN_FTW_COORD[0]], [DOWNTOWN_FTW_COORD[1]]),
        crs='EPSG:4326'
    ).to_crs(ALBERS)
    clip_circle = dal_pt.geometry.iloc[0].buffer(160_000)
    roads_clipped = roads[roads.intersects(clip_circle)].clip(clip_circle)
    all_primary = roads_clipped[roads_clipped['MTFCC'] == 'S1100']
    interstates = all_primary[all_primary['FULLNAME'].str.contains(r'^I-\s*\d', na=False, regex=True)]
    us_highways = all_primary[~all_primary['FULLNAME'].str.contains(r'^I-\s*\d', na=False, regex=True)]

    # ── Render ─────────────────────────────────────────────────────────
    print("\nRendering map...")
    fig, ax = plt.subplots(1, 1, figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor('#F6F7F3')
    ax.set_facecolor('#D6E8F0')  # light blue for water/background

    # County fill (slightly darker than before for contrast)
    county_fill = gdf.dissolve(by='COUNTYFP')
    county_fill.plot(ax=ax, color='#EDEEE9', edgecolor='white', linewidth=0.75)

    # Green dots first (underneath), then yellow on top
    ax.scatter(green_xs, green_ys, s=0.4, c='#67A275', alpha=0.6, edgecolors='none',
               rasterized=True, zorder=3)
    ax.scatter(yellow_xs, yellow_ys, s=0.4, c='#FEC439', alpha=0.8, edgecolors='none',
               rasterized=True, zorder=4)

    # Commute shed — deeper cream tint underneath dots
    shed_gdf = gpd.GeoDataFrame(geometry=[shed], crs=gdf.crs)
    shed_gdf.plot(ax=ax, facecolor='#DADFCE', edgecolor='none',
                  alpha=0.55, zorder=2)
    # Boundary on top of everything — dark enough to read over dots
    shed_gdf.boundary.plot(ax=ax, color='#8A8A7A', linewidth=0.9, alpha=1.0, zorder=9)

    # Highways — thin black
    if len(us_highways) > 0:
        us_highways.plot(ax=ax, color='#3D3733', linewidth=0.2, alpha=0.2, zorder=5)
    if len(interstates) > 0:
        interstates.plot(ax=ax, color='#3D3733', linewidth=0.4, alpha=0.3, zorder=5)


    # City labels
    major_labels = {
        'Dallas': (-96.797, 32.777),
        'Fort Worth': (-97.331, 32.755),
        'Plano': (-96.699, 33.020),
        'Frisco': (-96.824, 33.151),
        'McKinney': (-96.615, 33.197),
        'Arlington': (-97.108, 32.736),
        'Denton': (-97.133, 33.215),
        'Garland': (-96.639, 32.913),
        'Irving': (-96.949, 32.814),
    }
    # Places from the NYT article
    nyt_labels = {
        'Celina': (-96.785, 33.295),
        'Princeton': (-96.498, 33.180),
        'Ramble\n(Hillwood)': (-96.83, 33.35),
    }

    for city, (lon, lat) in major_labels.items():
        pt = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([lon], [lat]), crs='EPSG:4326'
        ).to_crs(ALBERS)
        x, y = pt.geometry.iloc[0].x, pt.geometry.iloc[0].y
        ax.annotate(city, (x, y), fontsize=5.5, color='#3D3733',
                    ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.12', facecolor='white',
                              alpha=0.7, edgecolor='none'))

    for city, (lon, lat) in nyt_labels.items():
        pt = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([lon], [lat]), crs='EPSG:4326'
        ).to_crs(ALBERS)
        x, y = pt.geometry.iloc[0].x, pt.geometry.iloc[0].y
        ax.annotate(city, (x, y), fontsize=5, color='#F4743B', fontweight='bold',
                    ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.12', facecolor='white',
                              alpha=0.8, edgecolor='#F4743B', linewidth=0.4))

    # Map extent
    cx = (dal_pt.geometry.iloc[0].x + ftw_pt.geometry.iloc[0].x) / 2
    cy = (dal_pt.geometry.iloc[0].y + ftw_pt.geometry.iloc[0].y) / 2
    radius = 170_000
    ax.set_xlim(cx - radius * 1.15, cx + radius * 1.15)
    ax.set_ylim(cy - radius * 0.95, cy + radius * 0.95)
    ax.set_aspect('equal')
    ax.axis('off')

    # Scale bar — 20 miles, lower right
    miles_to_meters = 1609.34
    bar_length = 20 * miles_to_meters
    bar_x = cx + radius * 0.55
    bar_y = cy - radius * 0.85
    ax.plot([bar_x, bar_x + bar_length], [bar_y, bar_y],
            color='#3D3733', linewidth=1.5, solid_capstyle='butt', zorder=8)
    tick_h = bar_length * 0.04
    ax.plot([bar_x, bar_x], [bar_y - tick_h, bar_y + tick_h],
            color='#3D3733', linewidth=1, zorder=8)
    ax.plot([bar_x + bar_length, bar_x + bar_length], [bar_y - tick_h, bar_y + tick_h],
            color='#3D3733', linewidth=1, zorder=8)
    ax.text(bar_x + bar_length / 2, bar_y + tick_h * 2.5, '20 miles',
            ha='center', va='bottom', fontsize=6, color='#3D3733')

    # Title
    ax.set_title("DFW Built Out to the Commute Frontier",
                 fontsize=14, fontweight='bold', color='#3D3733', pad=20, loc='left')
    ax.text(0.0, 1.01,
            f"1 dot = {UNITS_PER_DOT} housing units. 3.4M total units; 724K built since 2010.",
            transform=ax.transAxes, fontsize=8, color='#666666', va='bottom')

    # Legend
    legend_elements = [
        Line2D([0], [0], marker='o', color='none', markerfacecolor='#67A275',
               markersize=6, alpha=0.7, label='Pre-2010 housing'),
        Line2D([0], [0], marker='o', color='none', markerfacecolor='#FEC439',
               markersize=6, alpha=0.8, label='Built 2010+'),
    ]
    leg = ax.legend(handles=legend_elements, loc='lower left',
                    fontsize=7, frameon=False, bbox_to_anchor=(0.0, -0.01))
    for text in leg.get_texts():
        text.set_color('#3D3733')

    # Source
    fig.text(0.05, 0.02,
             "Source: ACS 2020-2024 5-Year, Tables B25001 & B25034; OSRM drive times (free-flow)",
             fontsize=6, fontstyle='italic', color='#999999')

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(f"{OUTPUTS}/dallas_dot_density.png", dpi=200, bbox_inches='tight', facecolor='#F6F7F3')
    fig.savefig(f"{OUTPUTS}/dallas_dot_density.svg", bbox_inches='tight', facecolor='#F6F7F3')
    plt.close()
    print(f"  Saved: {OUTPUTS}/dallas_dot_density.png")
    print(f"  Saved: {OUTPUTS}/dallas_dot_density.svg")
    print("\nDone!")
