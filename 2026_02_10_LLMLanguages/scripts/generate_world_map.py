"""
Generate static SVG/PNG world choropleth of LLM language coverage.
Uses admin1-level boundaries with 3 discrete tiers from LanguageBench scores.
Miller projection ("school wall" map).
Output: outputs/llm_language_map.svg + .png
"""
import os
import json
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch
from shapely.geometry import box
import pyproj

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# Brand colors
BG = "#F6F7F3"
BLACK = "#3D3733"
BLUE = "#0BB4FF"
YELLOW = "#FEC439"
RED = "#F4743B"

TIER_COLORS = {1: BLUE, 2: YELLOW, 3: RED}
TIER_LABELS = {1: "Well served", 2: "Partially served", 3: "Poorly served"}
NO_DATA_COLOR = "#E0E0E0"

BASE_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_10_LLMLanguages"
ADMIN1_SCORES = os.path.join(BASE_DIR, "data", "admin1_scores.json")
ADMIN1_SHP = os.path.join(BASE_DIR, "data", "ne_10m_admin_1", "ne_10m_admin_1_states_provinces.shp")
OUTPUT_SVG = os.path.join(BASE_DIR, "outputs", "llm_language_map.svg")
OUTPUT_PNG = os.path.join(BASE_DIR, "outputs", "llm_language_map.png")

# Load admin1 scores with tier assignments
with open(ADMIN1_SCORES) as f:
    admin1_scores = json.load(f)

# Load admin1 shapefile
print("Loading admin1 shapefile...")
gdf = gpd.read_file(ADMIN1_SHP)
print(f"  {len(gdf)} admin1 regions loaded")

# Clip Antarctica
clip_box = box(-180, -56, 180, 84)
gdf = gdf.clip(clip_box)
print(f"  {len(gdf)} after clipping Antarctica")

# Remove tiny islands (won't be visible in email)
gdf = gdf[gdf.geometry.area > 0.1]
print(f"  {len(gdf)} after removing tiny islands")

# Match tiers to admin1 regions
def get_tier(row):
    iso_code = row.get("iso_3166_2", "")
    iso2 = row.get("iso_a2", "")
    name = row.get("name", "Unknown")
    key = iso_code if iso_code else f"{iso2}-{name}"
    if key in admin1_scores:
        return admin1_scores[key].get("tier")
    return None

gdf["tier"] = gdf.apply(get_tier, axis=1)

# Assign colors
def tier_color(tier):
    if tier in TIER_COLORS:
        return TIER_COLORS[tier]
    return NO_DATA_COLOR

gdf["color"] = gdf["tier"].apply(tier_color)

# Stats
for t in [1, 2, 3]:
    count = (gdf["tier"] == t).sum()
    print(f"  Tier {t} ({TIER_LABELS[t]}): {count}")
no_data = gdf["tier"].isna().sum()
print(f"  No data: {no_data}")

# Load country boundaries for borders overlay
COUNTRIES_SHP = os.path.join(BASE_DIR, "data", "ne_110m_countries", "ne_110m_admin_0_countries.shp")
countries = gpd.read_file(COUNTRIES_SHP)
countries = countries.clip(box(-180, -56, 180, 84))

# Reproject to Miller ("school wall" projection)
gdf = gdf.to_crs("+proj=mill +datum=WGS84")
countries = countries.to_crs("+proj=mill +datum=WGS84")

def render_map(output_path, fmt, dpi):
    fig, ax = plt.subplots(1, 1, figsize=(9, 6.5), dpi=dpi)
    fig.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Draw admin1 regions — edge color matches fill to eliminate seams
    gdf.plot(ax=ax, color=gdf["color"], edgecolor=gdf["color"], linewidth=0.3)

    # Overlay country borders only
    countries.plot(ax=ax, facecolor="none", edgecolor="white", linewidth=0.25)

    ax.set_axis_off()
    xmin, ymin, xmax, ymax = gdf.total_bounds
    x_pad = (xmax - xmin) * 0.02
    y_pad = (ymax - ymin) * 0.04
    ax.set_xlim(xmin - x_pad, xmax + x_pad)
    ax.set_ylim(ymin - y_pad, ymax + y_pad)
    ax.set_aspect("equal")

    # Title and subtitle
    fig.text(0.06, 0.96, "Which Countries Are Left Behind by AI?",
             fontsize=20, fontweight='bold', color=BLACK, va='top')
    fig.text(0.06, 0.92,
             "LLM language performance by region, based on LanguageBench scores across 36 models",
             fontsize=11, fontweight='light', color=BLACK, alpha=0.7, va='top')

    # Legend
    legend_patches = [
        Patch(facecolor=TIER_COLORS[1], edgecolor="white", label=TIER_LABELS[1]),
        Patch(facecolor=TIER_COLORS[2], edgecolor="white", label=TIER_LABELS[2]),
        Patch(facecolor=TIER_COLORS[3], edgecolor="white", label=TIER_LABELS[3]),
        Patch(facecolor=NO_DATA_COLOR, edgecolor="white", label="No data"),
    ]
    leg = ax.legend(handles=legend_patches, loc='lower left',
                    fontsize=9, frameon=False, ncol=4,
                    bbox_to_anchor=(0.0, -0.02))
    for text in leg.get_texts():
        text.set_color(BLACK)

    # ── Callouts ──────────────────────────────────────────────────────────────
    # Project lat/lon to Miller for annotation coordinates
    miller = pyproj.Proj("+proj=mill +datum=WGS84")

    # (lon, lat) → region name, language, text offset (dx, dy in projected coords)
    callouts = [
        # ── Americas ──
        (-72, -13.5, "Cusco, Peru", "Quechua", 0.7e6, -1.8e6),
        (-65, -17, "La Paz, Bolivia", "Aymara", -3.0e6, -1.5e6),
        (-91, 15, "Guatemala highlands", "K'iche', Mam", -3.5e6, 1.2e6),
        (-90, 65, "Nunavut, Canada", "Inuktitut", 2.5e6, 1.5e6),
        (-57, -23, "Paraguay", "Guarani", 2.5e6, -1.0e6),
        # ── Europe ──
        (-2.5, 43.3, "Basque Country", "Basque", -2.5e6, 1.5e6),
        (45, 43, "Dagestan", "Avar, Chechen", 1.5e6, 1.5e6),
        (44, 42, "Chechnya", "Chechen", 3.0e6, 0.5e6),
        # ── Russia / Central Asia ──
        (130, 63, "Yakutia", "Yakut", 2.0e6, -2.5e6),
        (95, 52, "Tuva", "Tuvan", 2.0e6, 1.5e6),
        (60, 42, "Turkmenistan", "Turkmen", -2.0e6, -1.5e6),
        # ── Middle East ──
        (40, 38, "SE Turkey", "Kurdish", -2.5e6, -1.8e6),
        (60, 28, "Balochistan, Iran", "Balochi", 2.0e6, -1.2e6),
        # ── Africa ──
        (10, 7, "Southern Nigeria", "Ijaw, Efik, Edo", -3.5e6, -1.5e6),
        (30, 12, "Darfur, Sudan", "Fur", 2.5e6, 1.2e6),
        (29, -2, "Eastern DRC", "Swahili (yellow)", 3.0e6, -0.5e6),
        (25, -4, "Western DRC", "Lingala (red)", -3.0e6, -1.5e6),
        (28, 0, "Western Cape, SA", "Afrikaans (blue)", -3.0e6, -4.5e6),
        # ── South Asia ──
        (93, 25, "NE India", "Meitei, Mizo", 2.5e6, -1.8e6),
        (72, 26, "Chhattisgarh, India", "Chhattisgarhi", -2.5e6, -1.8e6),
        (90, 32, "Tibet", "Tibetan", 2.0e6, -1.5e6),
        # ── Southeast Asia ──
        (97, 25, "Kachin, Myanmar", "Kachin", 2.5e6, 1.0e6),
        (97, 19, "Shan State, Myanmar", "Shan", 3.0e6, -0.5e6),
        (101, 8, "Pattani, Thailand", "Pattani Malay", 2.5e6, -1.5e6),
        # ── East Asia ──
        (113, 23, "Guangdong, China", "Cantonese", 2.5e6, -1.5e6),
        (120, 30, "Zhejiang, China", "Wu Chinese", 3.0e6, 0.5e6),
    ]

    for lon, lat, label, lang, dx, dy in callouts:
        px, py = miller(lon, lat)
        ax.annotate(
            f"{label}\n{lang}",
            xy=(px, py),
            xytext=(px + dx, py + dy),
            fontsize=6, fontweight='regular', color=BLACK,
            ha='center', va='center',
            arrowprops=dict(
                arrowstyle='-',
                color='#666',
                linewidth=0.6,
                shrinkA=0, shrinkB=3,
            ),
            bbox=dict(
                boxstyle='round,pad=0.25',
                facecolor=BG, edgecolor='#999',
                linewidth=0.4, alpha=0.9,
            ),
        )

    # Source
    fig.text(0.06, 0.02,
             "Sources: LanguageBench (fair-forward, 2025), Unicode CLDR, Natural Earth",
             fontsize=8, fontstyle='italic', color='#999', va='bottom')

    plt.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.08)

    fig.savefig(output_path, format=fmt, bbox_inches='tight', facecolor=BG,
                dpi=dpi, pad_inches=0.3)
    plt.close()
    size = os.path.getsize(output_path) / 1e6
    print(f"  {output_path}: {size:.1f} MB")

print("\nRendering SVG...")
render_map(OUTPUT_SVG, 'svg', 100)

print("Rendering PNG...")
render_map(OUTPUT_PNG, 'png', 200)
