"""
Generate static SVG/PNG India choropleth of LLM language coverage.
Uses admin1-level boundaries with 3 discrete tiers from LanguageBench scores.
Output: outputs/llm_language_map_india.svg + .png
"""
import os
import json
import geopandas as gpd
import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import Patch

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
OUTPUT_SVG = os.path.join(BASE_DIR, "outputs", "llm_language_map_india.svg")
OUTPUT_PNG = os.path.join(BASE_DIR, "outputs", "llm_language_map_india.png")

# Load admin1 scores
with open(ADMIN1_SCORES) as f:
    admin1_scores = json.load(f)

# Load admin1 shapefile — filter to India only
print("Loading admin1 shapefile...")
gdf = gpd.read_file(ADMIN1_SHP)
gdf = gdf[gdf["iso_a2"] == "IN"]
print(f"  {len(gdf)} Indian states/territories loaded")

# Match tiers
def get_tier(row):
    iso_code = row.get("iso_3166_2", "")
    iso2 = row.get("iso_a2", "")
    name = row.get("name", "Unknown")
    key = iso_code if iso_code else f"{iso2}-{name}"
    if key in admin1_scores:
        return admin1_scores[key].get("tier")
    return None

def get_language(row):
    iso_code = row.get("iso_3166_2", "")
    iso2 = row.get("iso_a2", "")
    name = row.get("name", "Unknown")
    key = iso_code if iso_code else f"{iso2}-{name}"
    if key in admin1_scores:
        return admin1_scores[key].get("language", "Unknown")
    return "Unknown"

gdf["tier"] = gdf.apply(get_tier, axis=1)
gdf["language"] = gdf.apply(get_language, axis=1)

def tier_color(tier):
    if tier in TIER_COLORS:
        return TIER_COLORS[tier]
    return NO_DATA_COLOR

gdf["color"] = gdf["tier"].apply(tier_color)

# Stats
for t in [1, 2, 3]:
    count = (gdf["tier"] == t).sum()
    regions = gdf[gdf["tier"] == t]
    langs = regions["language"].unique()
    print(f"  Tier {t} ({TIER_LABELS[t]}): {count} — {', '.join(sorted(langs))}")
no_data = gdf["tier"].isna().sum()
print(f"  No data: {no_data}")

# Reproject to a conic projection centered on India
INDIA_CRS = "+proj=lcc +lat_1=15 +lat_2=30 +lat_0=22 +lon_0=82 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
gdf = gdf.to_crs(INDIA_CRS)

def render_map(output_path, fmt, dpi):
    fig, ax = plt.subplots(1, 1, figsize=(9, 10), dpi=dpi)
    fig.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Draw admin1 regions with thin white borders between states
    gdf.plot(ax=ax, color=gdf["color"], edgecolor="white", linewidth=0.5)

    # Add state labels
    for idx, row in gdf.iterrows():
        centroid = row.geometry.centroid
        name = row.get("name", "")
        lang = row.get("language", "")
        if name and row.geometry.area > 5e9:  # Only label large enough states
            ax.annotate(name, xy=(centroid.x, centroid.y),
                       fontsize=5.5, fontweight='regular', color=BLACK,
                       ha='center', va='center', alpha=0.8)

    ax.set_axis_off()
    xmin, ymin, xmax, ymax = gdf.total_bounds
    x_pad = (xmax - xmin) * 0.05
    y_pad = (ymax - ymin) * 0.05
    ax.set_xlim(xmin - x_pad, xmax + x_pad)
    ax.set_ylim(ymin - y_pad, ymax + y_pad)
    ax.set_aspect("equal")

    # Title and subtitle
    fig.text(0.06, 0.96, "India's Linguistic Divide in AI",
             fontsize=22, fontweight='bold', color=BLACK, va='top')
    fig.text(0.06, 0.935,
             "LLM language performance by state, based on LanguageBench scores across 34 models",
             fontsize=12, fontweight='light', color=BLACK, alpha=0.7, va='top')

    # Legend
    legend_patches = [
        Patch(facecolor=TIER_COLORS[1], edgecolor="white", label=TIER_LABELS[1]),
        Patch(facecolor=TIER_COLORS[2], edgecolor="white", label=TIER_LABELS[2]),
        Patch(facecolor=TIER_COLORS[3], edgecolor="white", label=TIER_LABELS[3]),
        Patch(facecolor=NO_DATA_COLOR, edgecolor="white", label="No data"),
    ]
    leg = ax.legend(handles=legend_patches, loc='lower left',
                    fontsize=10, frameon=False, ncol=2,
                    bbox_to_anchor=(0.0, -0.02))
    for text in leg.get_texts():
        text.set_color(BLACK)

    # Source
    fig.text(0.06, 0.02,
             "Sources: LanguageBench (fair-forward, 2025), Unicode CLDR, Natural Earth",
             fontsize=8, fontstyle='italic', color='#999', va='bottom')

    plt.subplots_adjust(left=0.02, right=0.98, top=0.92, bottom=0.06)

    fig.savefig(output_path, format=fmt, bbox_inches='tight', facecolor=BG,
                dpi=dpi, pad_inches=0.3)
    plt.close()
    size = os.path.getsize(output_path) / 1e6
    print(f"  {output_path}: {size:.1f} MB")

print("\nRendering SVG...")
render_map(OUTPUT_SVG, 'svg', 100)

print("Rendering PNG...")
render_map(OUTPUT_PNG, 'png', 200)
