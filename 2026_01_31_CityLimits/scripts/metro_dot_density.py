"""
Dot density maps for multiple metros — generalized version of the Dallas script.
Each dot = 20 housing units. Green = pre-2010, Yellow = built 2010+.
Red boundary = 45-minute drive-time commute shed.
"""

import os
import sys
import requests
import time
import random
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

PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_31_CityLimits"
DATA = f"{PROJECT}/data"
OUTPUTS = f"{PROJECT}/outputs"
SHAPEFILE = "/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_us_tract_5m.zip"
ROADS_ZIP = f"{DATA}/tl_2023_us_primaryroads.zip"
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"

for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
CENSUS_API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"
UNITS_PER_DOT = 20
MISSING_COLOR = '#E8E8E8'

# ── Metro definitions ──────────────────────────────────────────────────
METROS = {
    'atlanta': {
        'name': 'Atlanta',
        'state_fips': '13',
        'downtown': (-84.388, 33.749),
        'state_counties': {
            '13': [  # Georgia — Atlanta metro + surrounding ring
                '121', '089', '067', '135', '063', '097', '113', '151', '247',
                '057', '117', '013', '045', '077', '085', '143', '149',
                '159', '171', '211', '217', '223', '227', '231', '255', '297',
                '015', '035', '199',
                '139', '187', '311', '157',
                '115', '169', '195', '233', '219', '285', '293',
                '241', '155', '129', '153', '137', '075',
                '257', '011', '213',
                '207', '123', '059', '263', '237', '079', '111', '145',
                '291', '021', '269', '055', '313', '133',
                '225', '221', '119', '009', '215', '281', '295',
                '047', '197', '193', '289', '053', '141', '249',
                '083', '259', '239', '243', '061', '099', '253',
                '201', '307', '037', '087', '273', '007', '261',
            ],
            '01': [  # Alabama — eastern border counties
                '029', '111', '019', '017', '015', '027', '049', '055',
                '081', '123', '121',
            ],
        },
        'radius': 220_000,
    },
    'miami': {
        'name': 'Miami',
        'state_fips': '12',
        'downtown': (-80.192, 25.775),
        'counties': [
            '086',  # Miami-Dade
            '011',  # Broward
            '099',  # Palm Beach
            '085',  # Martin
            '093',  # Okeechobee
            '071',  # Lee (Fort Myers side)
            '021',  # Collier
            '051',  # Hendry
        ],
        'radius': 150_000,
    },
    'phoenix': {
        'name': 'Phoenix',
        'state_fips': '04',
        'downtown': (-112.074, 33.449),
        'counties': [
            '013',  # Maricopa
            '021',  # Pinal
            '007',  # Gila
            '025',  # Yavapai
            '027',  # Yuma
            '011',  # Greenlee
            '009',  # Graham
        ],
        'radius': 200_000,
    },
}


def get_state_counties(metro):
    """Return list of (state_fips, county_fips) tuples for a metro."""
    if 'state_counties' in metro:
        pairs = []
        for st, counties in metro['state_counties'].items():
            for c in counties:
                pairs.append((st, c))
        return pairs
    return [(metro['state_fips'], c) for c in metro['counties']]


def fetch_housing(metro_key):
    """Fetch 2024 ACS housing data for a metro."""
    metro = METROS[metro_key]
    out = f"{DATA}/{metro_key}_housing_2024.parquet"
    if os.path.exists(out):
        return pd.read_parquet(out)

    print(f"Fetching 2024 ACS for {metro['name']}...")
    rows = []
    for state_fips, county in get_state_counties(metro):
        url = (f"https://api.census.gov/data/2024/acs/acs5"
               f"?get=B25001_001E,B25034_002E,B25034_003E"
               f"&for=tract:*&in=state:{state_fips}&in=county:{county}"
               f"&key={CENSUS_API_KEY}")
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            for row in data[1:]:
                rows.append(dict(zip(data[0], row)))
            print(f"  {state_fips}-{county}: {len(data)-1} tracts")
        else:
            print(f"  {state_fips}-{county}: FAILED {r.status_code}")

    df = pd.DataFrame(rows)
    df['GEOID'] = df['state'] + df['county'] + df['tract']
    for col in ['B25001_001E', 'B25034_002E', 'B25034_003E']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        df.loc[df[col] < 0, col] = np.nan
    df['housing_units'] = df['B25001_001E']
    df['built_2010_later'] = df['B25034_002E'].fillna(0) + df['B25034_003E'].fillna(0)
    df = df[['GEOID', 'housing_units', 'built_2010_later']].copy()
    df.to_parquet(out, index=False)
    print(f"  Saved {len(df)} tracts, {df.housing_units.sum():,.0f} total units")
    return df


def fetch_drive_times(metro_key):
    """Compute OSRM drive times from downtown to all tract centroids."""
    metro = METROS[metro_key]
    out = f"{DATA}/{metro_key}_drive_times.parquet"
    if os.path.exists(out):
        return pd.read_parquet(out)

    print(f"Computing drive times for {metro['name']}...")
    gdf = gpd.read_file(f"zip://{SHAPEFILE}")
    pairs = get_state_counties(metro)
    mask = pd.Series(False, index=gdf.index)
    for st, co in pairs:
        mask |= (gdf['STATEFP'] == st) & (gdf['COUNTYFP'] == co)
    gdf = gdf[mask].copy()
    centroids = gdf.geometry.centroid
    geoids = gdf['GEOID'].tolist()
    lons = centroids.x.tolist()
    lats = centroids.y.tolist()

    origin = metro['downtown']
    BATCH_SIZE = 80
    results = []

    n_batches = (len(geoids) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"  {len(geoids)} tracts, {n_batches} batches...")

    for i in range(0, len(geoids), BATCH_SIZE):
        batch_end = min(i + BATCH_SIZE, len(geoids))
        batch_geoids = geoids[i:batch_end]
        batch_lons = lons[i:batch_end]
        batch_lats = lats[i:batch_end]

        coords_parts = [f"{origin[0]},{origin[1]}"]
        for lon, lat in zip(batch_lons, batch_lats):
            coords_parts.append(f"{lon},{lat}")

        coords_str = ";".join(coords_parts)
        dest_indices = ";".join(str(j) for j in range(1, 1 + len(batch_geoids)))

        url = f"http://router.project-osrm.org/table/v1/driving/{coords_str}?sources=0&destinations={dest_indices}&annotations=duration"

        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=30)
                data = resp.json()
                if data.get('code') == 'Ok':
                    break
            except:
                time.sleep(2)
        else:
            print(f"  Batch {i//BATCH_SIZE} FAILED")
            continue

        times = data['durations'][0]
        for j, geoid in enumerate(batch_geoids):
            drive_min = times[j] / 60 if times[j] is not None else None
            results.append({'GEOID': geoid, 'drive_min': drive_min})

        if (i // BATCH_SIZE) % 5 == 0:
            print(f"  Batch {i//BATCH_SIZE}/{n_batches}")
        time.sleep(0.3)

    df = pd.DataFrame(results)
    df.to_parquet(out, index=False)
    within_45 = (df['drive_min'] <= 45).sum()
    print(f"  Saved {len(df)} tracts, {within_45} within 45 min")
    return df


def random_points_in_polygon(polygon, n):
    if n <= 0 or polygon.is_empty:
        return []
    points = []
    minx, miny, maxx, maxy = polygon.bounds
    max_attempts = n * 50
    attempts = 0
    while len(points) < n and attempts < max_attempts:
        batch_size = min((n - len(points)) * 3, 5000)
        xs = np.random.uniform(minx, maxx, batch_size)
        ys = np.random.uniform(miny, maxy, batch_size)
        for x, y in zip(xs, ys):
            if polygon.contains(Point(x, y)):
                points.append((x, y))
                if len(points) >= n:
                    break
        attempts += batch_size
    return points


def render_metro(metro_key):
    """Render dot density map for a single metro."""
    metro = METROS[metro_key]
    np.random.seed(42)

    hu = fetch_housing(metro_key)
    drive = fetch_drive_times(metro_key)

    # Load tracts
    print(f"Loading tracts for {metro['name']}...")
    gdf = gpd.read_file(f"zip://{SHAPEFILE}")
    pairs = get_state_counties(metro)
    mask = pd.Series(False, index=gdf.index)
    for st, co in pairs:
        mask |= (gdf['STATEFP'] == st) & (gdf['COUNTYFP'] == co)
    gdf = gdf[mask].copy()
    gdf = gdf.to_crs(ALBERS)
    gdf = gdf.merge(hu, on='GEOID', how='left')
    gdf['pre_2010'] = gdf['housing_units'] - gdf['built_2010_later']
    gdf.loc[gdf['pre_2010'] < 0, 'pre_2010'] = 0

    matched = gdf['housing_units'].notna().sum()
    print(f"  {matched}/{len(gdf)} tracts matched ({matched/len(gdf)*100:.1f}%)")
    print(f"  Total: {gdf.housing_units.sum():,.0f}, Pre-2010: {gdf.pre_2010.sum():,.0f}, Post-2010: {gdf.built_2010_later.sum():,.0f}")

    # Commute shed
    merged_drive = gdf.merge(drive, on='GEOID', how='left')
    shed_tracts = merged_drive[merged_drive['drive_min'] <= 45]
    raw = unary_union(shed_tracts.geometry)
    shed = raw.buffer(5_000).buffer(-5_000)
    if shed.geom_type == 'MultiPolygon':
        shed = max(shed.geoms, key=lambda g: g.area)
    print(f"  Commute shed: {len(shed_tracts)} tracts within 45 min")

    # Generate dots
    print("  Generating dots...")
    green_xs, green_ys = [], []
    yellow_xs, yellow_ys = [], []

    for _, row in gdf.iterrows():
        if pd.isna(row['housing_units']) or row['housing_units'] <= 0:
            continue
        geom = row['geometry']
        if geom.is_empty:
            continue

        n_green = int(round(row['pre_2010'] / UNITS_PER_DOT)) if not pd.isna(row['pre_2010']) else 0
        n_yellow = int(round(row['built_2010_later'] / UNITS_PER_DOT)) if not pd.isna(row['built_2010_later']) else 0
        total = n_green + n_yellow
        if total == 0:
            continue

        pts = random_points_in_polygon(geom, total)
        random.shuffle(pts)
        for i, (x, y) in enumerate(pts):
            if i < n_green:
                green_xs.append(x)
                green_ys.append(y)
            else:
                yellow_xs.append(x)
                yellow_ys.append(y)

    print(f"  Green: {len(green_xs):,}, Yellow: {len(yellow_xs):,}")

    # Roads
    print("  Loading roads...")
    roads = gpd.read_file(f"zip://{ROADS_ZIP}").to_crs(ALBERS)
    center_pt = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([metro['downtown'][0]], [metro['downtown'][1]]),
        crs='EPSG:4326'
    ).to_crs(ALBERS)
    clip_circle = center_pt.geometry.iloc[0].buffer(200_000)
    roads_clipped = roads[roads.intersects(clip_circle)].clip(clip_circle)
    all_primary = roads_clipped[roads_clipped['MTFCC'] == 'S1100']
    interstates = all_primary[all_primary['FULLNAME'].str.contains(r'^I-\s*\d', na=False, regex=True)]
    us_highways = all_primary[~all_primary['FULLNAME'].str.contains(r'^I-\s*\d', na=False, regex=True)]

    # ── Render ─────────────────────────────────────────────────────────
    print("  Rendering...")
    fig, ax = plt.subplots(1, 1, figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor('#F6F7F3')
    ax.set_facecolor('#D6E8F0')  # light blue for water/background

    # County fill (lighter to contrast with commute shed cream)
    county_fill = gdf.dissolve(by='COUNTYFP')
    county_fill.plot(ax=ax, color='#EDEEE9', edgecolor='white', linewidth=0.75)

    # Dots — low alpha so overlapping dots in dense areas appear more intense
    # rasterized=True keeps SVG small while text/lines stay vector-editable
    ax.scatter(green_xs, green_ys, s=0.4, c='#67A275', alpha=0.15,
               edgecolors='none', rasterized=True, zorder=3)
    ax.scatter(yellow_xs, yellow_ys, s=0.4, c='#FEC439', alpha=0.25,
               edgecolors='none', rasterized=True, zorder=4)

    # Highways — thin black
    if len(us_highways) > 0:
        us_highways.plot(ax=ax, color='#3D3733', linewidth=0.2, alpha=0.2, zorder=5)
    if len(interstates) > 0:
        interstates.plot(ax=ax, color='#3D3733', linewidth=0.4, alpha=0.3, zorder=5)

    # Commute shed — cream tint underneath dots, subtle boundary on top
    shed_gdf = gpd.GeoDataFrame(geometry=[shed], crs=gdf.crs)
    shed_gdf.plot(ax=ax, facecolor='#DADFCE', edgecolor='none',
                  alpha=0.55, zorder=2)
    shed_gdf.boundary.plot(ax=ax, color='#8A8A7A', linewidth=0.9, alpha=1.0, zorder=9)

    # Map extent — fit to data bounds with padding
    cx, cy = center_pt.geometry.iloc[0].x, center_pt.geometry.iloc[0].y
    bounds = gdf.total_bounds  # minx, miny, maxx, maxy
    pad = 15_000  # 15km padding
    ax.set_xlim(bounds[0] - pad, bounds[2] + pad)
    ax.set_ylim(bounds[1] - pad, bounds[3] + pad)
    ax.set_aspect('equal')
    ax.axis('off')

    # Scale bar — 20 miles, lower right
    miles_to_meters = 1609.34
    bar_length = 20 * miles_to_meters
    bar_x = bounds[2] - 80_000
    bar_y = bounds[1] + 20_000
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
    total_units = gdf.housing_units.sum()
    new_units = gdf.built_2010_later.sum()
    ax.set_title(f"{metro['name']} Built Out to the Commute Frontier",
                 fontsize=14, fontweight='bold', color='#3D3733', pad=20, loc='left')
    ax.text(0.0, 1.01,
            f"1 dot = {UNITS_PER_DOT} housing units. {total_units/1e6:.1f}M total; {new_units/1e3:.0f}K built since 2010.",
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
    fig.savefig(f"{OUTPUTS}/{metro_key}_dot_density.png", dpi=200, bbox_inches='tight', facecolor='#F6F7F3')
    fig.savefig(f"{OUTPUTS}/{metro_key}_dot_density.svg", dpi=300, bbox_inches='tight', facecolor='#F6F7F3')
    plt.close()
    print(f"  Saved: {OUTPUTS}/{metro_key}_dot_density.png")

    # ── Cropped "_small" version: tight view around metro core ────────
    # Large figsize + high dpi so the rasterized dots are crisp when zoomed
    print("  Rendering _small version...")
    fig2, ax2 = plt.subplots(1, 1, figsize=(18, 15), dpi=100)
    fig2.patch.set_facecolor('#F6F7F3')
    ax2.set_facecolor('#D6E8F0')

    county_fill.plot(ax=ax2, color='#EDEEE9', edgecolor='white', linewidth=0.75)
    ax2.scatter(green_xs, green_ys, s=0.6, c='#67A275', alpha=0.15,
                edgecolors='none', rasterized=True, zorder=3)
    ax2.scatter(yellow_xs, yellow_ys, s=0.6, c='#FEC439', alpha=0.25,
                edgecolors='none', rasterized=True, zorder=4)
    if len(us_highways) > 0:
        us_highways.plot(ax=ax2, color='#3D3733', linewidth=0.2, alpha=0.2, zorder=5)
    if len(interstates) > 0:
        interstates.plot(ax=ax2, color='#3D3733', linewidth=0.4, alpha=0.3, zorder=5)
    shed_gdf.plot(ax=ax2, facecolor='#DADFCE', edgecolor='none', alpha=0.55, zorder=2)
    shed_gdf.boundary.plot(ax=ax2, color='#8A8A7A', linewidth=0.9, alpha=1.0, zorder=9)

    # Crop to ~150km around downtown
    crop_r = 150_000
    ax2.set_xlim(cx - crop_r * 1.15, cx + crop_r * 1.15)
    ax2.set_ylim(cy - crop_r * 0.95, cy + crop_r * 0.95)
    ax2.set_aspect('equal')
    ax2.axis('off')

    # Scale bar
    bar_x2 = cx + crop_r * 0.55
    bar_y2 = cy - crop_r * 0.85
    ax2.plot([bar_x2, bar_x2 + bar_length], [bar_y2, bar_y2],
             color='#3D3733', linewidth=1.5, solid_capstyle='butt', zorder=8)
    ax2.plot([bar_x2, bar_x2], [bar_y2 - tick_h, bar_y2 + tick_h],
             color='#3D3733', linewidth=1, zorder=8)
    ax2.plot([bar_x2 + bar_length, bar_x2 + bar_length], [bar_y2 - tick_h, bar_y2 + tick_h],
             color='#3D3733', linewidth=1, zorder=8)
    ax2.text(bar_x2 + bar_length / 2, bar_y2 + tick_h * 2.5, '20 miles',
             ha='center', va='bottom', fontsize=6, color='#3D3733')

    ax2.set_title(f"{metro['name']} Built Out to the Commute Frontier",
                  fontsize=14, fontweight='bold', color='#3D3733', pad=20, loc='left')
    ax2.text(0.0, 1.01,
             f"1 dot = {UNITS_PER_DOT} housing units. {total_units/1e6:.1f}M total; {new_units/1e3:.0f}K built since 2010.",
             transform=ax2.transAxes, fontsize=8, color='#666666', va='bottom')
    leg2 = ax2.legend(handles=legend_elements, loc='lower left',
                      fontsize=7, frameon=False, bbox_to_anchor=(0.0, -0.01))
    for text in leg2.get_texts():
        text.set_color('#3D3733')
    fig2.text(0.05, 0.02,
              "Source: ACS 2020-2024 5-Year, Tables B25001 & B25034; OSRM drive times (free-flow)",
              fontsize=6, fontstyle='italic', color='#999999')

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig2.savefig(f"{OUTPUTS}/{metro_key}_dot_density_small.png", dpi=300, bbox_inches='tight', facecolor='#F6F7F3')
    fig2.savefig(f"{OUTPUTS}/{metro_key}_dot_density_small.svg", dpi=600, bbox_inches='tight', facecolor='#F6F7F3')
    plt.close()
    print(f"  Saved: {OUTPUTS}/{metro_key}_dot_density_small.png")


if __name__ == '__main__':
    targets = sys.argv[1:] if len(sys.argv) > 1 else ['atlanta', 'miami', 'phoenix']
    for metro_key in targets:
        print(f"\n{'='*60}")
        print(f"  {METROS[metro_key]['name']}")
        print(f"{'='*60}")
        render_metro(metro_key)
    print("\nAll done!")
