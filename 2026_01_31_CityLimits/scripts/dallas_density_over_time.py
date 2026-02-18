"""
DFW Housing Density Over Time — 3-panel map (2010, 2018, 2023)
Shows density expanding outward toward the 45-minute commute frontier.
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
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
from shapely.ops import unary_union

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_31_CityLimits"
DATA = f"{PROJECT}/data"
OUTPUTS = f"{PROJECT}/outputs"
SHAPEFILE_2023 = "/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_us_tract_5m.zip"
SHAPEFILE_2010 = f"{DATA}/gz_2010_48_140_00_500k.zip"
ROADS_ZIP = f"{DATA}/tl_2023_us_primaryroads.zip"
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"

for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

CENSUS_API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

DFW_COUNTIES = [
    '085', '113', '121', '139', '231', '251', '257', '367', '397', '439', '497',
    '097', '147', '181', '221', '349', '213', '425', '467', '379', '223',
    '109', '119', '277',
]

DOWNTOWN_DALLAS_COORD = (-96.797, 32.780)
DOWNTOWN_FTW_COORD = (-97.328, 32.755)
MISSING_COLOR = '#E8E8E8'

CITY_LABELS = {
    'Dallas': (-96.797, 32.7767),
    'Fort Worth': (-97.3308, 32.7555),
    'Plano': (-96.6989, 33.0198),
    'McKinney': (-96.6153, 33.1972),
    'Denton': (-97.1331, 33.2148),
}

# Density color bins — light to vivid green
DENSITY_BINS = [0, 50, 200, 500, 1000, 2000, 4000, 50000]
DENSITY_COLORS = [
    '#EEF2E9',
    '#DADFCE',
    '#C6DCCB',
    '#9FC5A6',
    '#7DB486',
    '#67A275',
    '#4E8A5E',
]
DENSITY_LABELS = ['< 50', '50-200', '200-500', '500-1k', '1k-2k', '2k-4k', '4k+']


def fetch_housing_units_2010():
    """Fetch 2010 Decennial SF1 housing units by tract (2010 geography)."""
    out = f"{DATA}/dfw_housing_2010.parquet"
    if os.path.exists(out):
        return pd.read_parquet(out)
    print("Fetching 2010 Decennial SF1 housing units...")
    rows = []
    for county in DFW_COUNTIES:
        url = (f"https://api.census.gov/data/2010/dec/sf1"
               f"?get=H001001&for=tract:*&in=state:48&in=county:{county}"
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
    df['housing_units'] = pd.to_numeric(df['H001001'], errors='coerce')
    df = df[['GEOID', 'housing_units']]
    df.to_parquet(out, index=False)
    print(f"  Saved {len(df)} tracts")
    return df


def fetch_housing_units_acs(year):
    """Fetch ACS 5-year housing units by tract."""
    out = f"{DATA}/dfw_housing_{year}.parquet"
    if os.path.exists(out):
        return pd.read_parquet(out)
    print(f"Fetching {year} ACS 5-year housing units...")
    rows = []
    for county in DFW_COUNTIES:
        url = (f"https://api.census.gov/data/{year}/acs/acs5"
               f"?get=B25001_001E&for=tract:*&in=state:48&in=county:{county}"
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
    df['housing_units'] = pd.to_numeric(df['B25001_001E'], errors='coerce')
    df.loc[df['housing_units'] < 0, 'housing_units'] = np.nan
    df = df[['GEOID', 'housing_units']]
    df.to_parquet(out, index=False)
    print(f"  Saved {len(df)} tracts")
    return df


def load_tracts_2010():
    """Load 2010-vintage Texas tract shapefile, filter to DFW."""
    print("Loading 2010 tract geometries...")
    gdf = gpd.read_file(f"zip://{SHAPEFILE_2010}")
    gdf = gdf[gdf['STATE'] == '48']
    gdf = gdf[gdf['COUNTY'].isin(DFW_COUNTIES)].copy()
    gdf['GEOID'] = gdf['GEO_ID'].str[-11:]  # extract 11-digit FIPS
    gdf['land_area_sqmi'] = gdf['CENSUSAREA'].astype(float)
    gdf = gdf.to_crs(ALBERS)
    print(f"  {len(gdf)} tracts")
    return gdf


def load_tracts_2023():
    """Load 2020-vintage tract shapefile (CB 2023), filter to DFW."""
    print("Loading 2020-vintage tract geometries...")
    gdf = gpd.read_file(f"zip://{SHAPEFILE_2023}")
    gdf = gdf[(gdf['STATEFP'] == '48') & (gdf['COUNTYFP'].isin(DFW_COUNTIES))].copy()
    gdf['land_area_sqmi'] = gdf['ALAND'].astype(float) / 2_589_988.11
    gdf = gdf.to_crs(ALBERS)
    print(f"  {len(gdf)} tracts")
    return gdf


def load_commute_shed(gdf_for_bounds):
    """Load precomputed drive times and build 45-min commute shed polygon."""
    drive_df = pd.read_parquet(f"{DATA}/dfw_drive_times.parquet")
    # Need to match against whatever tracts are in gdf_for_bounds
    # Use a spatial approach: build shed from 2020-vintage tracts (drive times use 2020 GEOIDs)
    gdf_2020 = gpd.read_file(f"zip://{SHAPEFILE_2023}")
    gdf_2020 = gdf_2020[(gdf_2020['STATEFP'] == '48') & (gdf_2020['COUNTYFP'].isin(DFW_COUNTIES))].copy()
    gdf_2020 = gdf_2020.to_crs(ALBERS)
    merged = gdf_2020.merge(drive_df[['GEOID', 'min_drive_min']], on='GEOID', how='left')
    shed_tracts = merged[merged['min_drive_min'] <= 45]
    raw = unary_union(shed_tracts.geometry)
    shed = raw.buffer(5_000).buffer(-5_000)
    if shed.geom_type == 'MultiPolygon':
        shed = max(shed.geoms, key=lambda g: g.area)
    return shed


def load_roads():
    """Load and clip interstate highways."""
    roads = gpd.read_file(f"zip://{ROADS_ZIP}")
    roads = roads.to_crs(ALBERS)
    dallas_pt = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([DOWNTOWN_DALLAS_COORD[0]], [DOWNTOWN_DALLAS_COORD[1]]),
        crs='EPSG:4326'
    ).to_crs(ALBERS)
    clip_circle = dallas_pt.geometry.iloc[0].buffer(160_000)
    roads_clipped = roads[roads.intersects(clip_circle)].clip(clip_circle)
    all_primary = roads_clipped[roads_clipped['MTFCC'] == 'S1100']
    interstates = all_primary[all_primary['FULLNAME'].str.contains(r'^I-\s*\d', na=False, regex=True)]
    us_highways = all_primary[~all_primary['FULLNAME'].str.contains(r'^I-\s*\d', na=False, regex=True)]
    return interstates, us_highways


def render_panel(ax, gdf, shed_boundary, interstates, us_highways, year_label,
                 cx, cy, radius, show_legend=False, show_labels=True):
    """Render one density panel."""
    cmap = ListedColormap(DENSITY_COLORS)
    norm = BoundaryNorm(DENSITY_BINS, cmap.N)

    gdf['density'] = gdf['housing_units'] / gdf['land_area_sqmi']
    gdf.loc[gdf['land_area_sqmi'] <= 0, 'density'] = np.nan
    gdf.loc[gdf['housing_units'].isna(), 'density'] = np.nan

    ax.set_facecolor('#EDEFE7')

    # Missing tracts
    missing = gdf[gdf['density'].isna() | (gdf['density'] <= 0)]
    if len(missing) > 0:
        missing.plot(ax=ax, color=MISSING_COLOR, edgecolor='none')

    # Density choropleth
    valid = gdf[gdf['density'].notna() & (gdf['density'] > 0)]
    valid.plot(ax=ax, column='density', cmap=cmap, norm=norm, edgecolor='none')

    # County boundaries
    county_col = 'COUNTYFP' if 'COUNTYFP' in gdf.columns else 'COUNTY'
    county_boundaries = gdf.dissolve(by=county_col).boundary
    county_boundaries.plot(ax=ax, color='white', linewidth=0.75)

    # Commute shed hatching
    if shed_boundary is not None:
        shed_gdf = gpd.GeoDataFrame(geometry=[shed_boundary], crs=gdf.crs)
        shed_gdf.plot(ax=ax, facecolor='none', edgecolor='#3D3733', linewidth=0.5,
                      hatch='///', alpha=0.12, zorder=6)
        shed_gdf.boundary.plot(ax=ax, color='#3D3733', linewidth=1.0, alpha=0.4, zorder=6)

    # Highways
    if len(us_highways) > 0:
        us_highways.plot(ax=ax, color='#3D3733', linewidth=0.2, alpha=0.08, zorder=3)
    if len(interstates) > 0:
        interstates.plot(ax=ax, color='#3D3733', linewidth=0.5, alpha=0.2, zorder=4)

    # Downtown markers
    for coord in [DOWNTOWN_DALLAS_COORD, DOWNTOWN_FTW_COORD]:
        pt = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([coord[0]], [coord[1]]), crs='EPSG:4326'
        ).to_crs(ALBERS)
        pt.plot(ax=ax, color='#3D3733', markersize=20, zorder=10, marker='o')

    # City labels
    if show_labels:
        for city, (lon, lat) in CITY_LABELS.items():
            pt = gpd.GeoDataFrame(
                geometry=gpd.points_from_xy([lon], [lat]), crs='EPSG:4326'
            ).to_crs(ALBERS)
            x, y = pt.geometry.iloc[0].x, pt.geometry.iloc[0].y
            ax.annotate(city, (x, y), fontsize=5, color='#3D3733',
                        ha='center', va='bottom',
                        bbox=dict(boxstyle='round,pad=0.1', facecolor='white',
                                  alpha=0.7, edgecolor='none'))

    # Year label
    ax.set_title(year_label, fontsize=12, fontweight='bold', color='#3D3733', pad=6)

    ax.set_xlim(cx - radius * 1.15, cx + radius * 1.15)
    ax.set_ylim(cy - radius * 0.95, cy + radius * 0.95)
    ax.set_aspect('equal')
    ax.axis('off')


if __name__ == '__main__':
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(OUTPUTS, exist_ok=True)

    # ── Fetch all housing data ─────────────────────────────────────────
    hu_2010 = fetch_housing_units_2010()
    hu_2018 = fetch_housing_units_acs(2018)
    hu_2023 = fetch_housing_units_acs(2023)

    print(f"\n2010: {hu_2010.housing_units.sum():,.0f} total units, {len(hu_2010)} tracts")
    print(f"2018: {hu_2018.housing_units.sum():,.0f} total units, {len(hu_2018)} tracts")
    print(f"2023: {hu_2023.housing_units.sum():,.0f} total units, {len(hu_2023)} tracts\n")

    # ── Load geometries ────────────────────────────────────────────────
    tracts_2010 = load_tracts_2010()
    tracts_2023 = load_tracts_2023()

    # Merge housing data with geometries
    gdf_2010 = tracts_2010.merge(hu_2010, on='GEOID', how='left')
    gdf_2018 = tracts_2010.merge(hu_2018, on='GEOID', how='left')  # 2018 ACS uses 2010 geography
    gdf_2023 = tracts_2023.merge(hu_2023, on='GEOID', how='left')

    # Report match rates
    for label, gdf, hu in [('2010', gdf_2010, hu_2010), ('2018', gdf_2018, hu_2018), ('2023', gdf_2023, hu_2023)]:
        matched = gdf['housing_units'].notna().sum()
        print(f"  {label}: {matched}/{len(gdf)} tracts matched ({matched/len(gdf)*100:.1f}%)")

    # ── Load commute shed and roads ────────────────────────────────────
    print("\nLoading commute shed...")
    shed = load_commute_shed(tracts_2023)

    print("Loading roads...")
    interstates, us_highways = load_roads()

    # ── Compute map center (midpoint of two downtowns) ─────────────────
    dal_pt = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([DOWNTOWN_DALLAS_COORD[0]], [DOWNTOWN_DALLAS_COORD[1]]),
        crs='EPSG:4326'
    ).to_crs(ALBERS)
    ftw_pt = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([DOWNTOWN_FTW_COORD[0]], [DOWNTOWN_FTW_COORD[1]]),
        crs='EPSG:4326'
    ).to_crs(ALBERS)
    cx = (dal_pt.geometry.iloc[0].x + ftw_pt.geometry.iloc[0].x) / 2
    cy = (dal_pt.geometry.iloc[0].y + ftw_pt.geometry.iloc[0].y) / 2
    radius = 130_000

    # ── Render 3-panel figure ──────────────────────────────────────────
    print("\nRendering 3-panel map...")
    fig, axes = plt.subplots(1, 3, figsize=(18, 7.5), dpi=100)
    fig.patch.set_facecolor('#F6F7F3')

    panels = [
        (axes[0], gdf_2010, '2010'),
        (axes[1], gdf_2018, '2018'),
        (axes[2], gdf_2023, '2023'),
    ]

    for ax, gdf, year in panels:
        render_panel(ax, gdf.copy(), shed, interstates, us_highways, year,
                     cx, cy, radius, show_labels=(year == '2018'))

    # Suptitle
    fig.suptitle("DFW Built Out to the Commute Frontier",
                 fontsize=16, fontweight='bold', color='#3D3733', y=0.97)
    fig.text(0.5, 0.93,
             "Housing density by census tract, with 45-minute drive-time shed from downtown Dallas and Fort Worth",
             ha='center', fontsize=9, color='#666666')

    # Legend below panels
    legend_elements = [Patch(facecolor=DENSITY_COLORS[i], edgecolor='#CCCCCC',
                             linewidth=0.5, label=DENSITY_LABELS[i])
                       for i in range(len(DENSITY_LABELS))]
    legend_elements.append(Patch(facecolor=MISSING_COLOR, edgecolor='#CCCCCC',
                                 linewidth=0.5, label='No data'))
    leg = fig.legend(handles=legend_elements, loc='lower center', ncol=8,
                     fontsize=7, frameon=False, handlelength=1.5, handleheight=1.2,
                     bbox_to_anchor=(0.5, 0.02), title='Housing units per sq. mile',
                     title_fontsize=7.5)
    for text in leg.get_texts():
        text.set_color('#3D3733')
    leg.get_title().set_color('#3D3733')

    # Source
    fig.text(0.5, 0.005,
             "Source: 2010 Decennial Census SF1; ACS 2014-2018 & 2019-2023 5-Year, Table B25001; OSRM drive times (free-flow)",
             ha='center', fontsize=5.5, fontstyle='italic', color='#999999')

    plt.subplots_adjust(left=0.01, right=0.99, top=0.90, bottom=0.08, wspace=0.02)

    fig.savefig(f"{OUTPUTS}/dallas_density_over_time.png", dpi=150, bbox_inches='tight', facecolor='#F6F7F3')
    fig.savefig(f"{OUTPUTS}/dallas_density_over_time.svg", bbox_inches='tight', facecolor='#F6F7F3')
    plt.close()
    print(f"  Saved: {OUTPUTS}/dallas_density_over_time.png")
    print(f"  Saved: {OUTPUTS}/dallas_density_over_time.svg")
    print("\nDone!")
