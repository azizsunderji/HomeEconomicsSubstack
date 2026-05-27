"""
Static map: NYC MSA (22 counties — 5 boroughs + 17 suburbs) shaded by
% change in under-18 population from 2020 to 2024.

Styled to MATCH 2026_01_29_BayAreaTechPrices/scripts/bay_area_zip_map.py exactly:
- Sequential 5-step GREEN palette ['#EDEFE7','#DADFCE','#B5CFBA','#67A275','#2D5A3F']
  with quantile breaks (pale = worst decline, dark green = best growth).
- Cream county boundaries (0.5pt), no heavy outline.
- 5 NYC boroughs flagged via a YELLOW HATCHED OVERLAY (dissolved into a single
  polygon), exactly like Bay Area's "top quartile tech workers" overlay.
- Water (ocean + lakes) from Natural Earth in light blue, low opacity.
- Oracle font, BG_CREAM background, title bold, colorbar on right.
- SVG output with editable text (fonttype='none').
"""
import os
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib
import matplotlib.font_manager as fm
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
from shapely.geometry import Point, box

warnings.filterwarnings('ignore')
matplotlib.use('svg')

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
GEO = DATA / "geo"
OUT = PROJECT / "outputs"
WATER_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_01_05_PriceMaps/01_05_2026_Since2019/data")

# ---- Brand colors (matched to Bay Area map) ----
BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
YELLOW = '#FEC439'
DARK_CREAM = '#DADFCE'

# ---- Fonts ----
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

BOROUGHS = {"36005", "36047", "36061", "36081", "36085"}

# Albers Equal Area (CONUS)
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

# ---- Load data ----
df = pd.read_csv(DATA / "nyc_county_under18_pep_seamless.csv", dtype={"county_fips": str})
pivot = df[df['year'].isin([2020, 2024])].pivot_table(
    values='under18', index=['county_fips', 'county_name'], columns='year').reset_index()
pivot['pct'] = (pivot[2024] / pivot[2020] - 1) * 100
pivot['is_borough'] = pivot['county_fips'].isin(BOROUGHS)

# ---- Load NYC MSA county geometry ----
import json
with open(GEO / "metro10_counties.geojson") as f:
    g = json.load(f)
features = [f for f in g['features'] if f['properties'].get('cbsa_code') == 35620]
nyc_gdf = gpd.GeoDataFrame.from_features(features, crs='EPSG:4326')
nyc_gdf['county_fips'] = nyc_gdf['county_fips'].astype(str)
nyc_gdf = nyc_gdf.merge(
    pivot[['county_fips', 'county_name', 'pct', 'is_borough', 2020, 2024]],
    on='county_fips', how='left')
nyc_gdf = nyc_gdf.to_crs(ALBERS)
print(f"Loaded {len(nyc_gdf)} counties; pct range {nyc_gdf['pct'].min():.1f}% to {nyc_gdf['pct'].max():.1f}%")

# ---- Color scale: 5-step sequential GREEN, quantile breaks (Bay Area style) ----
# Palette #1 — RED + BLUE (Economist classic diverging).
# Index 0 = strongest decline (dark red); Index 4 = strongest growth (deep blue).
step_colors = [
    '#D03A2E',   # Dark red (strongest decline)
    '#F0A39A',   # Light red
    '#F4F0E7',   # Cream (≈ 0)
    '#7BA7C6',   # Light blue
    '#1E5A8C',   # Deep blue (strongest growth)
]
cmap = ListedColormap(step_colors)

# Diverging fixed breaks (chosen to bracket the data: -9.5% .. +7.1%)
diverging_breaks = [-10, -5, -1, 1, 4, 10]
bounds = list(diverging_breaks)
norm = BoundaryNorm(bounds, cmap.N)
quantile_breaks = np.array(diverging_breaks)  # reused for colorbar tick labels
print(f"Diverging breaks: {[f'{b:+.0f}%' for b in diverging_breaks]}")

# ---- View bounds ----
b = nyc_gdf.total_bounds
xmin, ymin, xmax, ymax = b
pad = 12000
xmin -= pad; xmax += pad; ymin -= pad; ymax += pad

# ---- Load water ----
view_geom = box(xmin, ymin, xmax, ymax)
view_gdf = gpd.GeoDataFrame(geometry=[view_geom], crs=ALBERS)
water_gdfs = []
for path in [WATER_DIR / "ne_10m_ocean.shp", WATER_DIR / "ne_10m_lakes.shp"]:
    if path.exists():
        try:
            w = gpd.read_file(path).to_crs(ALBERS)
            w_clip = gpd.clip(w, view_gdf)
            if len(w_clip) > 0:
                w_clip['geometry'] = w_clip.geometry.buffer(800)
                water_gdfs.append(w_clip)
        except Exception as e:
            print(f"  Warning loading {path}: {e}")

# ---- Render ----
fig, ax = plt.subplots(figsize=(9, 7.5), facecolor=BG_CREAM)
ax.set_facecolor(BG_CREAM)
ax.set_xlim(xmin, xmax)
ax.set_ylim(ymin, ymax)

# Water (flat light blue — gradient added in Illustrator)
for w in water_gdfs:
    w.plot(ax=ax, facecolor=BLUE, edgecolor='none', alpha=0.10, zorder=0)

# Counties filled by % change
nyc_gdf.plot(ax=ax, column='pct', cmap=cmap, norm=norm,
             edgecolor='none', linewidth=0, legend=False, zorder=2)

# Cream county boundaries (0.5pt)
nyc_gdf.boundary.plot(ax=ax, color=BG_CREAM, linewidth=0.5, zorder=3)

# ---- City labels ----
# Boroughs use leader lines because the cluster is tight; suburbs at centroid.
nyc_gdf['cx'] = nyc_gdf.geometry.representative_point().x
nyc_gdf['cy'] = nyc_gdf.geometry.representative_point().y

borough_offsets = {
    "Bronx":                     (  4000,  18000),
    "New York (Manhattan)":      (-34000,   6000),
    "Kings (Brooklyn)":          (-10000, -26000),
    "Queens":                    ( 34000,  -4000),
    "Richmond (Staten Island)":  (-30000, -20000),
}
borough_short = {
    "Bronx": "Bronx", "New York (Manhattan)": "Manhattan",
    "Kings (Brooklyn)": "Brooklyn", "Queens": "Queens",
    "Richmond (Staten Island)": "Staten Island",
}
# Use bbox (creates an SVG <rect> behind the text) for readability instead of
# path_effects.withStroke — the latter forces matplotlib to render text as
# Bezier paths, breaking editability in Illustrator.
LABEL_BBOX = dict(facecolor=BG_CREAM, edgecolor='none',
                  boxstyle='square,pad=0.18', alpha=0.85)

# Manual offsets for tight pairs (Albers meters)
suburb_offsets = {
    "Rockland":    ( -6000,  4000),
    "Westchester": ( 14000, -3000),
    "Bergen":      (  0,     5000),
    "Hudson":      ( -4000, -1000),
    "Passaic":     ( -2000,  3000),
}
for _, row in nyc_gdf[~nyc_gdf['is_borough']].iterrows():
    name = row['county_name']
    dx, dy = suburb_offsets.get(name, (0, 0))
    ax.text(row['cx'] + dx, row['cy'] + dy, name,
            fontsize=8.5, fontweight='bold', color=BLACK,
            ha='center', va='center', bbox=LABEL_BBOX, zorder=20)

for _, row in nyc_gdf[nyc_gdf['is_borough']].iterrows():
    name = row['county_name']
    dx, dy = borough_offsets[name]
    lx, ly = row['cx'] + dx, row['cy'] + dy
    ax.plot([row['cx'], lx], [row['cy'], ly],
            color=BLACK, linewidth=0.5, zorder=19, alpha=0.85)
    ax.plot(row['cx'], row['cy'], 'o', color=BLACK, markersize=2.2, zorder=19)
    ha = 'left' if dx > 0 else ('right' if dx < 0 else 'center')
    ax.text(lx, ly, borough_short[name],
            fontsize=9.5, fontweight='bold', color=BLACK,
            ha=ha, va='center', bbox=LABEL_BBOX, zorder=21)

ax.set_aspect('equal')
ax.axis('off')

# ---- Title ----
ax.set_title("NYC's kid population fell faster than the suburbs after 2020",
             fontsize=14, fontweight='bold', color=BLACK, pad=15)

# ---- Colorbar (right side, shrink/aspect/pad matched to Bay Area) ----
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, shrink=0.5, aspect=20, pad=0.02,
                    ticks=quantile_breaks)
def _fmt(v):
    sign = '+' if v > 0 else ('' if v == 0 else '−')
    return f"{sign}{abs(v):.1f}%"
cbar.ax.set_yticklabels([_fmt(v) for v in quantile_breaks])
cbar.set_label('% change in under-18 population, 2020–2024',
               fontsize=10, color=BLACK)
cbar.ax.tick_params(colors=BLACK, labelsize=8.5)

# ---- Source ----
ax.text(0.01, -0.04,
        "Source: U.S. Census Bureau PEP (intercensal 2010-2020 + V2024). "
        "NYC MSA = OMB 2023 CBSA 35620, 22 counties.",
        transform=ax.transAxes, fontsize=8, color='#888888', style='italic')

plt.tight_layout()
out_png = OUT / "nyc_pct_change_2020_map.png"
out_svg = OUT / "nyc_pct_change_2020_map.svg"
plt.savefig(out_png, dpi=150, bbox_inches='tight', facecolor=BG_CREAM)
plt.savefig(out_svg, bbox_inches='tight', facecolor=BG_CREAM)
print(f"Wrote {out_png}")
print(f"Wrote {out_svg}")
print("\n% change 2020→2024 per county:")
for _, r in nyc_gdf.sort_values('pct').iterrows():
    marker = ' [BOROUGH]' if r['is_borough'] else ''
    print(f"  {r['county_name']:30s} {r['pct']:+6.2f}%{marker}")
