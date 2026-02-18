"""
DFW Housing Density 2024 — single map with new construction (2010+) highlighted in yellow.
Green = overall density gradient. Yellow overlay = tracts where a large share of housing is post-2010.
"""

import os
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
    'Frisco': (-96.8236, 33.1507),
    'McKinney': (-96.6153, 33.1972),
    'Arlington': (-97.1081, 32.7357),
    'Denton': (-97.1331, 33.2148),
    'Garland': (-96.6389, 32.9126),
    'Irving': (-96.9489, 32.8140),
}

# Green density gradient
DENSITY_BINS = [0, 50, 200, 500, 1000, 2000, 4000, 50000]
DENSITY_COLORS = [
    '#EEF2E9', '#DADFCE', '#C6DCCB', '#9FC5A6',
    '#7DB486', '#67A275', '#4E8A5E',
]
DENSITY_LABELS = ['< 50', '50-200', '200-500', '500-1k', '1k-2k', '2k-4k', '4k+']


if __name__ == '__main__':
    # ── Load data ──────────────────────────────────────────────────────
    hu = pd.read_parquet(f"{DATA}/dfw_housing_2024.parquet")
    drive = pd.read_parquet(f"{DATA}/dfw_drive_times.parquet")

    print(f"2024 ACS: {hu.housing_units.sum():,.0f} units, {hu.built_2010_later.sum():,.0f} built 2010+")

    # Load geometries
    gdf = gpd.read_file(f"zip://{SHAPEFILE_2023}")
    gdf = gdf[(gdf['STATEFP'] == '48') & (gdf['COUNTYFP'].isin(DFW_COUNTIES))].copy()
    gdf['land_area_sqmi'] = gdf['ALAND'].astype(float) / 2_589_988.11
    gdf = gdf.to_crs(ALBERS)

    # Merge
    gdf = gdf.merge(hu, on='GEOID', how='left')
    gdf['density'] = gdf['housing_units'] / gdf['land_area_sqmi']
    gdf.loc[gdf['land_area_sqmi'] <= 0, 'density'] = np.nan
    gdf.loc[gdf['housing_units'].isna(), 'density'] = np.nan

    # New construction density (units built 2010+ per sq mile)
    gdf['new_density'] = gdf['built_2010_later'] / gdf['land_area_sqmi']
    gdf.loc[gdf['land_area_sqmi'] <= 0, 'new_density'] = np.nan

    print(f"\nNew construction density stats:")
    valid_new = gdf[gdf['new_density'].notna() & (gdf['new_density'] > 0)]
    print(f"  Range: {valid_new.new_density.min():.0f} - {valid_new.new_density.max():.0f} new units/sq mi")
    print(f"  Median: {valid_new.new_density.median():.0f}, Mean: {valid_new.new_density.mean():.0f}")

    # Commute shed
    merged_drive = gdf.merge(drive[['GEOID', 'min_drive_min']], on='GEOID', how='left')
    shed_tracts = merged_drive[merged_drive['min_drive_min'] <= 45]
    raw = unary_union(shed_tracts.geometry)
    shed = raw.buffer(5_000).buffer(-5_000)
    if shed.geom_type == 'MultiPolygon':
        shed = max(shed.geoms, key=lambda g: g.area)

    # Roads
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
    cmap = ListedColormap(DENSITY_COLORS)
    norm = BoundaryNorm(DENSITY_BINS, cmap.N)

    fig, ax = plt.subplots(1, 1, figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor('#F6F7F3')
    ax.set_facecolor('#EDEFE7')

    # Base layer: green density choropleth (no tract borders)
    missing = gdf[gdf['density'].isna() | (gdf['density'] <= 0)]
    if len(missing) > 0:
        missing.plot(ax=ax, color=MISSING_COLOR, edgecolor='none')

    valid = gdf[gdf['density'].notna() & (gdf['density'] > 0)]
    valid.plot(ax=ax, column='density', cmap=cmap, norm=norm, edgecolor='none')

    # Yellow overlay: tracts with substantial new construction (>50% built 2010+)
    # Use graduated yellow alpha based on pct_new
    new_thresholds = [
        (gdf['pct_new'] >= 75, '#FEC439', 0.7),   # very new: strong yellow
        ((gdf['pct_new'] >= 50) & (gdf['pct_new'] < 75), '#FEC439', 0.5),  # mostly new
        ((gdf['pct_new'] >= 30) & (gdf['pct_new'] < 50), '#FEC439', 0.3),  # mixed
    ]
    for mask, color, alpha in new_thresholds:
        subset = gdf[mask]
        if len(subset) > 0:
            subset.plot(ax=ax, color=color, alpha=alpha, edgecolor='none', zorder=5)

    # County boundaries
    county_boundaries = gdf.dissolve(by='COUNTYFP').boundary
    county_boundaries.plot(ax=ax, color='white', linewidth=0.75)

    # Commute shed hatching
    shed_gdf = gpd.GeoDataFrame(geometry=[shed], crs=gdf.crs)
    shed_gdf.plot(ax=ax, facecolor='none', edgecolor='#3D3733', linewidth=0.5,
                  hatch='///', alpha=0.12, zorder=6)
    shed_gdf.boundary.plot(ax=ax, color='#3D3733', linewidth=1.0, alpha=0.4, zorder=6)

    # Highways
    if len(us_highways) > 0:
        us_highways.plot(ax=ax, color='#3D3733', linewidth=0.2, alpha=0.08, zorder=3)
    if len(interstates) > 0:
        interstates.plot(ax=ax, color='#3D3733', linewidth=0.6, alpha=0.25, zorder=4)

    # Downtown markers
    for label, coord in [('Downtown\nDallas', DOWNTOWN_DALLAS_COORD),
                         ('Downtown\nFort Worth', DOWNTOWN_FTW_COORD)]:
        pt = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy([coord[0]], [coord[1]]), crs='EPSG:4326'
        ).to_crs(ALBERS)
        pt.plot(ax=ax, color='#3D3733', markersize=40, zorder=10, marker='o')
        px, py = pt.geometry.iloc[0].x, pt.geometry.iloc[0].y
        ax.annotate(label, (px, py), fontsize=5.5, color='#3D3733',
                    ha='center', va='top', xytext=(0, -6), textcoords='offset points',
                    fontweight='bold')

    # City labels
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
    ax.annotate("45-min. drive-time\ncommute shed",
                xy=(0.78, 0.90), xycoords='axes fraction',
                fontsize=7, fontstyle='italic', color='#3D3733',
                ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                          alpha=0.85, edgecolor='#3D3733', linewidth=0.5))

    # Map extent
    cx = (dal_pt.geometry.iloc[0].x + ftw_pt.geometry.iloc[0].x) / 2
    cy = (dal_pt.geometry.iloc[0].y + ftw_pt.geometry.iloc[0].y) / 2
    radius = 130_000
    ax.set_xlim(cx - radius * 1.15, cx + radius * 1.15)
    ax.set_ylim(cy - radius * 0.95, cy + radius * 0.95)
    ax.set_aspect('equal')
    ax.axis('off')

    # Title
    ax.set_title("DFW Built Out to the Commute Frontier",
                 fontsize=14, fontweight='bold', color='#3D3733', pad=12, loc='left')
    ax.text(0.0, 1.02,
            "Housing density (2024 ACS), with post-2010 construction highlighted in yellow",
            transform=ax.transAxes, fontsize=8, color='#666666', va='bottom')

    # Legend
    legend_elements = [Patch(facecolor=DENSITY_COLORS[i], edgecolor='#CCCCCC',
                             linewidth=0.5, label=DENSITY_LABELS[i])
                       for i in range(len(DENSITY_LABELS))]
    legend_elements.append(Patch(facecolor=MISSING_COLOR, edgecolor='#CCCCCC',
                                 linewidth=0.5, label='No data'))
    legend_elements.append(Patch(facecolor='#FEC439', edgecolor='#CCCCCC',
                                 linewidth=0.5, label='Built 2010+', alpha=0.6))
    leg = ax.legend(handles=legend_elements, loc='lower left', ncol=5,
                    fontsize=6.5, frameon=False, handlelength=1.5, handleheight=1.2,
                    bbox_to_anchor=(0.0, -0.02), title='Housing units per sq. mile',
                    title_fontsize=7)
    for text in leg.get_texts():
        text.set_color('#3D3733')
    leg.get_title().set_color('#3D3733')

    # Source
    fig.text(0.05, 0.02,
             "Source: ACS 2020-2024 5-Year, Tables B25001 & B25034; OSRM drive times (free-flow)",
             fontsize=6, fontstyle='italic', color='#999999')

    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(f"{OUTPUTS}/dallas_density_2024.png", dpi=150, bbox_inches='tight', facecolor='#F6F7F3')
    fig.savefig(f"{OUTPUTS}/dallas_density_2024.svg", bbox_inches='tight', facecolor='#F6F7F3')
    plt.close()
    print(f"  Saved: {OUTPUTS}/dallas_density_2024.png")

    # Summary stats
    new_tracts = gdf[gdf['pct_new'] >= 30]
    print(f"\nTracts with >=30% post-2010 construction: {len(new_tracts)}")
    print(f"  Total new units in those tracts: {new_tracts.built_2010_later.sum():,.0f}")
    print(f"\nDone!")
