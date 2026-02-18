"""
Dallas Construction Wave + Commute Frontier Map

Choropleth of housing unit density across DFW tracts,
overlaid with the empirical commute shed boundary from LODES8 OD data.
"""

import os
import requests
import pandas as pd
import numpy as np
import geopandas as gpd
import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
from matplotlib.patches import Patch
from shapely.ops import unary_union
from shapely.geometry import Point

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_31_CityLimits"
DATA = f"{PROJECT}/data"
OUTPUTS = f"{PROJECT}/outputs"
SHAPEFILE_ZIP = "/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_us_tract_5m.zip"
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"

# ── Register fonts ─────────────────────────────────────────────────────
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# ── Constants ──────────────────────────────────────────────────────────
CENSUS_API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# Wider DFW region — inner core + outer ring + far ring for visual context
DFW_COUNTIES = {
    # Core DFW MSA (11)
    '085': 'Collin', '113': 'Dallas', '121': 'Denton', '139': 'Ellis',
    '231': 'Hunt', '251': 'Johnson', '257': 'Kaufman', '367': 'Parker',
    '397': 'Rockwall', '439': 'Tarrant', '497': 'Wise',
    # Outer ring — balanced east/west/north/south
    '097': 'Cooke', '147': 'Fannin', '181': 'Grayson', '221': 'Hood',
    '349': 'Navarro', '213': 'Henderson', '425': 'Somervell',
    '467': 'Van Zandt', '379': 'Rains', '223': 'Hopkins',
    '109': 'Hill', '119': 'Delta', '277': 'Lamar',
}

# Downtown Dallas tract GEOIDs — 2020 census vintage
# CBD core + Deep Ellum + Uptown + Cedars + Victory Park / Design District
DOWNTOWN_DALLAS_TRACTS = [
    '48113003103',  # CBD core
    '48113003102',  # CBD
    '48113002100',  # west CBD
    '48113020402',  # Design District / Stemmons
    '48113001705',  # near CBD east
    '48113001902',  # Deep Ellum
    '48113010002',  # south of I-30 / Cedars
    '48113001901',  # Deep Ellum south
    '48113001602',  # east downtown
    '48113020401',  # Victory Park
    '48113002200',  # west of CBD
    '48113001802',  # Fair Park area
    '48113001703',  # east downtown
    '48113001601',  # east
    '48113001801',  # near Fair Park
    '48113002001',  # south CBD
    '48113000704',  # Uptown
    '48113000502',  # Uptown / Arts District
    '48113000801',  # east of 75
    '48113020300',  # Stemmons corridor
]

# Downtown Fort Worth tract GEOIDs (CBD area near Sundance Square / Convention Center)
DOWNTOWN_FTW_TRACTS = [
    '48439123302', '48439123200', '48439101700', '48439123301',
    '48439123600', '48439123100', '48439102000', '48439123700',
    '48439123500', '48439100900', '48439101202', '48439100102',
    '48439100800', '48439104100',
]

DOWNTOWN_TRACTS = DOWNTOWN_DALLAS_TRACTS + DOWNTOWN_FTW_TRACTS

ROADS_ZIP = f"{DATA}/tl_2023_us_primaryroads.zip"
MISSING_COLOR = '#E8E8E8'
DOWNTOWN_DALLAS_COORD = (-96.797, 32.780)
DOWNTOWN_FTW_COORD = (-97.328, 32.755)

# City label positions (lon, lat)
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
    'Sherman': (-96.6089, 33.6357),
    'Waxahachie': (-96.8483, 32.3865),
    'Corsicana': (-96.4689, 32.0954),
    'Gainesville': (-97.1336, 33.6260),
}


# ═══════════════════════════════════════════════════════════════════════
# STEP 1: Fetch ACS B25001 (Total Housing Units) + B25035 (Median Year Built)
# ═══════════════════════════════════════════════════════════════════════
def fetch_housing_data():
    """Fetch housing units and median year built for DFW tracts."""
    out_path = f"{DATA}/dfw_housing_data.parquet"
    if os.path.exists(out_path):
        print(f"  Already have {out_path}")
        return pd.read_parquet(out_path)

    print("Fetching ACS B25001 + B25035 from Census API...")
    all_rows = []
    for county_fips in DFW_COUNTIES:
        url = (
            f"https://api.census.gov/data/2023/acs/acs5"
            f"?get=B25001_001E,B25035_001E,NAME"
            f"&for=tract:*"
            f"&in=state:48&in=county:{county_fips}"
            f"&key={CENSUS_API_KEY}"
        )
        resp = requests.get(url)
        if resp.status_code != 200:
            url = url.replace("/2023/", "/2022/")
            resp = requests.get(url)
        if resp.status_code == 200:
            data = resp.json()
            header = data[0]
            for row in data[1:]:
                all_rows.append(dict(zip(header, row)))
            print(f"  County {county_fips} ({DFW_COUNTIES[county_fips]}): {len(data)-1} tracts")
        else:
            print(f"  County {county_fips}: FAILED ({resp.status_code})")

    df = pd.DataFrame(all_rows)
    df['GEOID'] = df['state'] + df['county'] + df['tract']
    df['housing_units'] = pd.to_numeric(df['B25001_001E'], errors='coerce')
    df['median_year_built'] = pd.to_numeric(df['B25035_001E'], errors='coerce')
    # Census sentinel values for missing data
    df.loc[df['housing_units'] < 0, 'housing_units'] = np.nan
    df.loc[df['median_year_built'] < 1900, 'median_year_built'] = np.nan
    df = df[['GEOID', 'NAME', 'housing_units', 'median_year_built']].copy()
    df.to_parquet(out_path, index=False)
    print(f"  Saved {len(df)} tracts to {out_path}")
    return df


# ═══════════════════════════════════════════════════════════════════════
# STEP 2: Download and process LODES8 OD data
# ═══════════════════════════════════════════════════════════════════════
def fetch_lodes_commuters():
    """Download LODES8 TX OD file, compute separate commuter counts for Dallas and Fort Worth downtowns."""
    out_dallas = f"{DATA}/downtown_dallas_commuters.parquet"
    out_ftw = f"{DATA}/downtown_ftw_commuters.parquet"

    if os.path.exists(out_dallas) and os.path.exists(out_ftw):
        print(f"  Already have LODES commuter data")
        return pd.read_parquet(out_dallas), pd.read_parquet(out_ftw)

    lodes_url = "https://lehd.ces.census.gov/data/lodes/LODES8/tx/od/tx_od_main_JT00_2021.csv.gz"
    lodes_local = f"{DATA}/tx_od_main_JT00_2021.csv.gz"

    if not os.path.exists(lodes_local):
        print("Downloading LODES8 TX OD file...")
        resp = requests.get(lodes_url, stream=True)
        resp.raise_for_status()
        with open(lodes_local, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=1024*1024):
                f.write(chunk)
        print(f"  Downloaded to {lodes_local}")

    con = duckdb.connect()

    # Dallas downtown
    dallas_prefixes = ", ".join(f"'{p}'" for p in DOWNTOWN_DALLAS_TRACTS)
    print("  Processing LODES for Dallas downtown...")
    df_dal = con.execute(f"""
    SELECT
        SUBSTR(CAST(h_geocode AS VARCHAR), 1, 11) AS home_tract,
        SUM(S000) AS total_commuters
    FROM read_csv_auto('{lodes_local}', compression='gzip')
    WHERE SUBSTR(CAST(w_geocode AS VARCHAR), 1, 11) IN ({dallas_prefixes})
    GROUP BY home_tract
    ORDER BY total_commuters DESC
    """).df()
    df_dal.to_parquet(out_dallas, index=False)
    print(f"    {len(df_dal)} tracts, {df_dal.total_commuters.sum():,.0f} commuters")

    # Fort Worth downtown
    ftw_prefixes = ", ".join(f"'{p}'" for p in DOWNTOWN_FTW_TRACTS)
    print("  Processing LODES for Fort Worth downtown...")
    df_ftw = con.execute(f"""
    SELECT
        SUBSTR(CAST(h_geocode AS VARCHAR), 1, 11) AS home_tract,
        SUM(S000) AS total_commuters
    FROM read_csv_auto('{lodes_local}', compression='gzip')
    WHERE SUBSTR(CAST(w_geocode AS VARCHAR), 1, 11) IN ({ftw_prefixes})
    GROUP BY home_tract
    ORDER BY total_commuters DESC
    """).df()
    df_ftw.to_parquet(out_ftw, index=False)
    print(f"    {len(df_ftw)} tracts, {df_ftw.total_commuters.sum():,.0f} commuters")

    con.close()
    return df_dal, df_ftw


# ═══════════════════════════════════════════════════════════════════════
# STEP 3: Load and prepare geometries
# ═══════════════════════════════════════════════════════════════════════
def load_geometries():
    """Load tract shapefiles, filter to DFW counties, reproject."""
    print("Loading tract geometries...")
    gdf = gpd.read_file(f"zip://{SHAPEFILE_ZIP}")
    gdf = gdf[gdf['STATEFP'] == '48']
    gdf = gdf[gdf['COUNTYFP'].isin(DFW_COUNTIES.keys())].copy()
    # Compute land area in square miles before reprojecting
    gdf['land_area_sqmi'] = gdf['ALAND'].astype(float) / 2_589_988.11  # sq meters to sq miles
    gdf = gdf.to_crs(ALBERS)
    print(f"  {len(gdf)} tracts loaded across {gdf['COUNTYFP'].nunique()} counties")
    return gdf


# ═══════════════════════════════════════════════════════════════════════
# STEP 4: Compute commute shed boundary
# ═══════════════════════════════════════════════════════════════════════
def compute_commute_shed(gdf, drive_time_minutes=45):
    """
    Compute the commute shed from OSRM drive-time data.
    Includes all tracts reachable within `drive_time_minutes` of either downtown
    (free-flow time; ~45 min free-flow ≈ 55-60 min rush hour).
    """
    print(f"Computing {drive_time_minutes}-minute drive-time commute shed...")
    drive_df = pd.read_parquet(f"{DATA}/dfw_drive_times.parquet")

    merged = gdf.merge(drive_df[['GEOID', 'min_drive_min']], on='GEOID', how='left')
    shed_tracts = merged[merged['min_drive_min'] <= drive_time_minutes]

    print(f"  {len(shed_tracts)} of {len(merged)} tracts within {drive_time_minutes} min")

    raw_union = unary_union(shed_tracts.geometry)
    # Smooth: buffer out 5km then back 5km
    shed_boundary = raw_union.buffer(5_000).buffer(-5_000)

    # Keep only the largest polygon if multi
    if shed_boundary.geom_type == 'MultiPolygon':
        largest = max(shed_boundary.geoms, key=lambda g: g.area)
        print(f"  Kept largest polygon from {len(shed_boundary.geoms)} pieces")
        shed_boundary = largest

    return shed_boundary


# ═══════════════════════════════════════════════════════════════════════
# STEP 5: Render map
# ═══════════════════════════════════════════════════════════════════════
def render_map(gdf, shed_boundary):
    """Render housing density choropleth + commute shed boundary."""
    print("Rendering map...")

    # Compute housing density (units per square mile)
    gdf['density'] = gdf['housing_units'] / gdf['land_area_sqmi']
    gdf.loc[gdf['land_area_sqmi'] <= 0, 'density'] = np.nan
    gdf.loc[gdf['housing_units'].isna(), 'density'] = np.nan

    valid = gdf[gdf['density'].notna() & (gdf['density'] > 0)]
    print(f"  Density range: {valid['density'].min():.0f} to {valid['density'].max():.0f} units/sq mi")
    print(f"  Density median: {valid['density'].median():.0f}, mean: {valid['density'].mean():.0f}")

    # ── Density color bins — light green to vivid green gradient ────────
    density_bins = [0, 50, 200, 500, 1000, 2000, 4000, 50000]
    density_colors = [
        '#EEF2E9',   # barely there
        '#DADFCE',   # cream/pale green
        '#C6DCCB',   # light green
        '#9FC5A6',   # medium-light green
        '#7DB486',   # medium green
        '#67A275',   # brand green
        '#4E8A5E',   # deep green
    ]
    density_labels = [
        '< 50', '50-200', '200-500', '500-1,000',
        '1,000-2,000', '2,000-4,000', '4,000+'
    ]

    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(density_colors)
    norm = BoundaryNorm(density_bins, cmap.N)

    # Classify each tract
    gdf['density_bin'] = pd.cut(gdf['density'], bins=density_bins, labels=False, include_lowest=True)

    fig, ax = plt.subplots(1, 1, figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor('#F6F7F3')
    ax.set_facecolor('#EDEFE7')

    # Plot missing tracts (gray, no borders)
    missing = gdf[gdf['density'].isna() | (gdf['density'] <= 0)]
    if len(missing) > 0:
        missing.plot(ax=ax, color=MISSING_COLOR, edgecolor='none')

    # Plot density choropleth (no tract borders)
    valid_gdf = gdf[gdf['density'].notna() & (gdf['density'] > 0)]
    valid_gdf.plot(ax=ax, column='density', cmap=cmap, norm=norm,
                   edgecolor='none')

    # County boundaries
    county_boundaries = gdf.dissolve(by='COUNTYFP').boundary
    county_boundaries.plot(ax=ax, color='white', linewidth=0.75)

    # ── Highways overlay (subtle) ──────────────────────────────────────
    print("  Loading highways...")
    roads = gpd.read_file(f"zip://{ROADS_ZIP}")
    roads = roads.to_crs(ALBERS)
    # Clip to map extent using a buffer around Dallas
    dallas_pt = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([DOWNTOWN_DALLAS_COORD[0]], [DOWNTOWN_DALLAS_COORD[1]]),
        crs='EPSG:4326'
    ).to_crs(ALBERS)
    clip_circle = dallas_pt.geometry.iloc[0].buffer(160_000)
    roads_clipped = roads[roads.intersects(clip_circle)].clip(clip_circle)
    # Filter to named interstates only (I-xx) — exclude US/state highways
    all_primary = roads_clipped[roads_clipped['MTFCC'] == 'S1100']
    interstates = all_primary[all_primary['FULLNAME'].str.contains(r'^I-\s*\d', na=False, regex=True)]
    # Also include major US highways but much more subtly
    us_highways = all_primary[~all_primary['FULLNAME'].str.contains(r'^I-\s*\d', na=False, regex=True)]
    if len(us_highways) > 0:
        us_highways.plot(ax=ax, color='#3D3733', linewidth=0.2, alpha=0.08, zorder=3)
    if len(interstates) > 0:
        interstates.plot(ax=ax, color='#3D3733', linewidth=0.6, alpha=0.25, zorder=4)

    # Commute shed — light diagonal hatching over the shed area
    if shed_boundary is not None:
        shed_gdf = gpd.GeoDataFrame(geometry=[shed_boundary], crs=gdf.crs)
        shed_gdf.plot(ax=ax, facecolor='none', edgecolor='#3D3733', linewidth=0.5,
                      hatch='///', alpha=0.12, zorder=6)
        # Thin solid boundary line
        shed_gdf.boundary.plot(ax=ax, color='#3D3733', linewidth=1.0, alpha=0.4, zorder=6)

    # Downtown markers
    for label, coord in [('Downtown\nDallas', DOWNTOWN_DALLAS_COORD),
                         ('Downtown\nFort Worth', DOWNTOWN_FTW_COORD)]:
        pt = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([coord[0]], [coord[1]]),
            crs='EPSG:4326'
        ).to_crs(ALBERS)
        pt.plot(ax=ax, color='#3D3733', markersize=40, zorder=10, marker='o')
        px, py = pt.geometry.iloc[0].x, pt.geometry.iloc[0].y
        ax.annotate(label, (px, py), fontsize=5.5, color='#3D3733',
                    ha='center', va='top', xytext=(0, -6), textcoords='offset points',
                    fontweight='bold')

    # City labels (skip Dallas and Fort Worth since we have downtown markers)
    for city, (lon, lat) in CITY_LABELS.items():
        if city in ('Dallas', 'Fort Worth'):
            continue
        pt = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([lon], [lat]), crs='EPSG:4326'
        ).to_crs(ALBERS)
        x, y = pt.geometry.iloc[0].x, pt.geometry.iloc[0].y
        ax.annotate(city, (x, y), fontsize=6, color='#3D3733',
                    ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                              alpha=0.7, edgecolor='none'))

    # Commute shed label
    if shed_boundary is not None:
        ax.annotate("45-min. drive-time\ncommute shed",
                    xy=(0.78, 0.90), xycoords='axes fraction',
                    fontsize=7, fontstyle='italic', color='#3D3733',
                    ha='center', va='center',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                              alpha=0.85, edgecolor='#3D3733', linewidth=0.5))

    # Center between Dallas and Fort Worth, fixed radius (~120km = ~75 miles)
    radius = 130_000  # meters in Albers
    ftw_pt = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([DOWNTOWN_FTW_COORD[0]], [DOWNTOWN_FTW_COORD[1]]),
        crs='EPSG:4326'
    ).to_crs(ALBERS)
    # Midpoint between the two downtowns
    cx = (dallas_pt.geometry.iloc[0].x + ftw_pt.geometry.iloc[0].x) / 2
    cy = (dallas_pt.geometry.iloc[0].y + ftw_pt.geometry.iloc[0].y) / 2
    # Slightly wider than tall to match 9:7.5 aspect ratio
    ax.set_xlim(cx - radius * 1.15, cx + radius * 1.15)
    ax.set_ylim(cy - radius * 0.95, cy + radius * 0.95)
    ax.set_aspect('equal')
    ax.axis('off')

    # Legend
    legend_elements = [Patch(facecolor=density_colors[i], edgecolor='#CCCCCC',
                             linewidth=0.5, label=density_labels[i])
                       for i in range(len(density_labels))]
    legend_elements.append(Patch(facecolor=MISSING_COLOR, edgecolor='#CCCCCC',
                                 linewidth=0.5, label='No data'))
    leg = ax.legend(handles=legend_elements, loc='lower left', ncol=4,
                    fontsize=6.5, frameon=False, handlelength=1.5, handleheight=1.2,
                    bbox_to_anchor=(0.0, -0.02), title='Housing units per sq. mile',
                    title_fontsize=7)
    for text in leg.get_texts():
        text.set_color('#3D3733')
    leg.get_title().set_color('#3D3733')

    # Title
    ax.set_title("DFW Built Out to the Commute Frontier",
                 fontsize=14, fontweight='bold', color='#3D3733', pad=12, loc='left')

    # Subtitle
    ax.text(0.0, 1.02,
            "Housing density by census tract, with 45-minute drive-time shed from downtown Dallas and Fort Worth",
            transform=ax.transAxes, fontsize=8, color='#666666', va='bottom')

    # Source
    fig.text(0.05, 0.02,
             "Source: ACS 2019-2023 5-Year, Table B25001; OSRM drive times (free-flow)",
             fontsize=6, fontstyle='italic', color='#999999')

    plt.tight_layout(rect=[0, 0.04, 1, 1])

    png_path = f"{OUTPUTS}/dallas_construction_wave.png"
    svg_path = f"{OUTPUTS}/dallas_construction_wave.svg"
    fig.savefig(png_path, dpi=150, bbox_inches='tight', facecolor='#F6F7F3')
    fig.savefig(svg_path, bbox_inches='tight', facecolor='#F6F7F3')
    plt.close()
    print(f"  Saved: {png_path}")
    print(f"  Saved: {svg_path}")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(OUTPUTS, exist_ok=True)

    # 1. Fetch Census data
    housing_df = fetch_housing_data()
    print(f"\nHousing units summary:\n{housing_df['housing_units'].describe()}")
    print(f"\nYear built summary:\n{housing_df['median_year_built'].describe()}\n")

    # 2. Load geometries
    gdf = load_geometries()

    # 3. Merge data
    gdf = gdf.merge(housing_df[['GEOID', 'housing_units', 'median_year_built']], on='GEOID', how='left')

    # 4. Compute commute shed from OSRM drive times
    shed_boundary = compute_commute_shed(gdf, drive_time_minutes=45)

    # 6. Render
    render_map(gdf, shed_boundary)

    print("\nDone!")
