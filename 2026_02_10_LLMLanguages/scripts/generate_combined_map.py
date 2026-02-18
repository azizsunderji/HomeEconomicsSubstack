"""
Generate combined world + India inset map of LLM language coverage.
Winkel Tripel projection for world (more curvature), circular India inset bottom-right.
Wide rectangular format.
Output: outputs/llm_language_map_combined.svg + .png
"""
import os
import json
import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patches as mpatches
from matplotlib.patches import Patch
from shapely.geometry import box
import pyproj

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# Meta color palette
META_BLUE = "#1877F2"
META_LIGHT_BLUE = "#A2C4FF"
META_GRAY300 = "#BCC0C4"
META_PINK = "#FF3C8E"
META_GRAY600 = "#65778A"
META_DARK = "#1C2B42"

BG = "#FFFFFF"
BLACK = META_DARK

# 3-tier scheme: no data → poorly served (pink)
TIER_COLORS = {1: META_BLUE, 2: META_LIGHT_BLUE, 3: META_PINK}
TIER_LABELS = {1: "Well served", 2: "Partially served", 3: "Poorly served"}
NO_DATA_COLOR = META_PINK  # No data = poorly served

BASE_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_10_LLMLanguages"
ADMIN1_SCORES = os.path.join(BASE_DIR, "data", "admin1_scores.json")
ADMIN1_SHP = os.path.join(BASE_DIR, "data", "ne_10m_admin_1", "ne_10m_admin_1_states_provinces.shp")
OUTPUT_SVG = os.path.join(BASE_DIR, "outputs", "llm_language_map_combined.svg")
OUTPUT_PNG = os.path.join(BASE_DIR, "outputs", "llm_language_map_combined.png")

# Projections
# Robinson with central meridian shifted east — good curvature for wide format
WORLD_PROJ = "+proj=robin +lon_0=15 +datum=WGS84"
# Equirectangular for India inset (flat "school wall" style)
INDIA_CRS = "EPSG:4326"

# Load admin1 scores
with open(ADMIN1_SCORES) as f:
    admin1_scores = json.load(f)

# Load admin1 shapefile
print("Loading admin1 shapefile...")
gdf_raw = gpd.read_file(ADMIN1_SHP)
print(f"  {len(gdf_raw)} admin1 regions loaded")

# Match tiers
def get_tier(row):
    iso_code = row.get("iso_3166_2", "")
    iso2 = row.get("iso_a2", "")
    name = row.get("name", "Unknown")
    key = iso_code if iso_code else f"{iso2}-{name}"
    if key in admin1_scores:
        return admin1_scores[key].get("tier")
    return None

gdf_raw["tier"] = gdf_raw.apply(get_tier, axis=1)
gdf_raw["color"] = gdf_raw["tier"].apply(lambda t: TIER_COLORS.get(t, NO_DATA_COLOR))

# Load country boundaries
COUNTRIES_SHP = os.path.join(BASE_DIR, "data", "ne_110m_countries", "ne_110m_admin_0_countries.shp")
countries_raw = gpd.read_file(COUNTRIES_SHP)

# Stats
for t in [1, 2, 3]:
    count = (gdf_raw["tier"] == t).sum()
    print(f"  Tier {t} ({TIER_LABELS[t]}): {count}")
print(f"  No data: {gdf_raw['tier'].isna().sum()}")

# ── Prepare world data ───────────────────────────────────────────────────────
print("\nPreparing world map (Robinson projection, lon_0=15)...")
gdf_world = gdf_raw.copy()
countries_world = countries_raw.copy()

# Clip to avoid antimeridian artifacts:
# With lon_0=15, antimeridian is at -165°W. Clip just inside to prevent wrapping.
clip_box = box(-164, -57, 180, 84)
gdf_world = gdf_world.clip(clip_box)
countries_world = countries_world.clip(clip_box)

# Only remove truly invisible slivers (keep small countries/admin1 regions)
gdf_world = gdf_world[gdf_world.geometry.area > 0.01]

# Reproject to Robinson
gdf_world = gdf_world.to_crs(WORLD_PROJ)
countries_world = countries_world.to_crs(WORLD_PROJ)

# Remove antimeridian stretch artifacts after reprojection
gdf_world = gdf_world.explode(index_parts=True)
def not_stretched(geom):
    if geom.is_empty:
        return False
    b = geom.bounds
    w, h = b[2] - b[0], b[3] - b[1]
    return h < 1 or (w / h) < 50 or w < 1e6
gdf_world = gdf_world[gdf_world.geometry.apply(not_stretched)]

# Explode country base layer for rendering (no area filtering — clean specks in Illustrator)
countries_world = countries_world.explode(index_parts=True)

print(f"  {len(gdf_world)} admin1 parts, {len(countries_world)} country parts after cleaning specks")

# ── Prepare South Asia inset (geographic circle clip) ─────────────────────────
from shapely.geometry import Point

print("Preparing South/SE Asia inset...")
INSET_CENTER = (83, 23)  # lon, lat — centered on India, includes Myanmar/Tibet
INSET_RADIUS = 20        # degrees — captures India, Myanmar, Tibet, Pakistan, Bangladesh
INSET_CRS = "EPSG:4326"

# Create circular clip region in geographic coordinates
clip_geom = Point(INSET_CENTER).buffer(INSET_RADIUS)

# Clip ALL admin1 regions to this circle (not limited to any country)
gdf_inset = gdf_raw.copy().to_crs(INSET_CRS)
gdf_inset = gdf_inset.clip(clip_geom)
gdf_inset = gdf_inset[~gdf_inset.geometry.is_empty]

# Also clip country boundaries for base layer
countries_inset = countries_raw.copy().to_crs(INSET_CRS)
countries_inset = countries_inset.clip(clip_geom)
countries_inset = countries_inset[~countries_inset.geometry.is_empty]

print(f"  {len(gdf_inset)} admin1 regions in inset circle")


def render_map(output_path, fmt, dpi):
    # Wide rectangular format
    fig = plt.figure(figsize=(16, 8), dpi=dpi)
    fig.set_facecolor(BG)

    # Main world map — positioned LEFT, leaving space on right for India inset
    ax_world = fig.add_axes([0.01, 0.07, 0.73, 0.83])
    ax_world.set_facecolor(BG)

    # ── Draw world map ────────────────────────────────────────────────────────
    # Base layer: fill ALL countries pink (poorly served default)
    # This ensures no white gaps where admin1 coverage is missing
    countries_world.plot(ax=ax_world, facecolor=META_PINK,
                         edgecolor=META_PINK, linewidth=0.3)
    # Admin1 regions on top — edge color matches fill to cover seams
    gdf_world.plot(ax=ax_world, color=gdf_world["color"],
                   edgecolor=gdf_world["color"], linewidth=0.3)
    # Country borders on top (white)
    countries_world.plot(ax=ax_world, facecolor="none",
                         edgecolor="white", linewidth=0.3)

    ax_world.set_axis_off()
    xmin, ymin, xmax, ymax = gdf_world.total_bounds
    x_range = xmax - xmin
    y_range = ymax - ymin
    # Natural bounds with slight padding — no hard crop
    ax_world.set_xlim(xmin - x_range * 0.01, xmax + x_range * 0.01)
    ax_world.set_ylim(ymin - y_range * 0.03, ymax + y_range * 0.03)
    ax_world.set_aspect("equal")

    # ── Callouts ──────────────────────────────────────────────────────────────
    world_proj = pyproj.Proj(WORLD_PROJ)

    # Verified speaker numbers:
    # Quechua: ~7-10M (Ethnologue/Wikipedia) → "~8M"
    # Kurdish: ~25-30M native (Ethnologue) → "~30M"
    # Pashto: ~40-60M (Ethnologue/Wikipedia) → "~50M"
    # Basque: ~800K (Basque Institute) → "~800K"
    # Dagestan: 3M+ people, 30+ languages
    callouts = [
        # ── Minority language populations within countries ──
        (-2.5, 43.3, "Basque Country", "Basque (~800K speakers)", -3.0e6, 1.5e6),
        (-72, -14, "Peru highlands", "Quechua (~8M speakers)", -3.8e6, -1.2e6),
        (90, 32, "Tibet", "Tibetan (~6M speakers)", -2.5e6, 2.0e6),
        (47, 42, "Dagestan", "30+ languages, 3M people", 2.5e6, 2.0e6),
        (40, 38, "Kurdistan", "Kurdish (~30M speakers)", -3.5e6, -0.5e6),

        # ── Large poorly-served populations ──
        (67, 33, "Pashto belt", "Af/Pak (~50M speakers)", 2.5e6, -2.0e6),
        (6, 5, "S. Nigeria", "Ijaw, Edo, Efik", -3.5e6, -1.5e6),
    ]

    for lon, lat, label, lang, dx, dy in callouts:
        px, py = world_proj(lon, lat)
        ax_world.annotate(
            f"{label}\n{lang}",
            xy=(px, py),
            xytext=(px + dx, py + dy),
            fontsize=8, fontweight='regular', color=BLACK,
            ha='center', va='center',
            arrowprops=dict(
                arrowstyle='-',
                color='#666',
                linewidth=0.6,
                shrinkA=0, shrinkB=3,
            ),
            bbox=dict(
                boxstyle='round,pad=0.25',
                facecolor='white', edgecolor=META_GRAY300,
                linewidth=0.4, alpha=0.92,
            ),
        )

    # ── Circular South Asia inset — larger, vertically centered ─────────────
    # For 16x8 figure, square axes: h_frac = 2 * w_frac
    inset_w = 0.24
    inset_h = inset_w * (16 / 8)  # = 0.48
    inset_x = 0.75
    inset_y = (1.0 - inset_h) / 2  # vertically centered
    ax_inset = fig.add_axes([inset_x, inset_y, inset_w, inset_h])
    ax_inset.set_facecolor('none')
    ax_inset.set_frame_on(False)

    # Background circle (opaque white, covers world map beneath)
    bg_circle = mpatches.Circle((0.5, 0.5), 0.5, transform=ax_inset.transAxes,
                                 facecolor='white', edgecolor='none',
                                 zorder=0, clip_on=False)
    ax_inset.add_patch(bg_circle)

    # Country base layer (pink default) for the inset region
    countries_inset.plot(ax=ax_inset, facecolor=META_PINK,
                         edgecolor=META_PINK, linewidth=0.3, zorder=1)

    # Admin1 regions — all land within the circle
    gdf_inset.plot(ax=ax_inset, color=gdf_inset["color"],
                   edgecolor=gdf_inset["color"], linewidth=0.3, zorder=2)

    # Country borders (white)
    countries_inset.plot(ax=ax_inset, facecolor="none",
                         edgecolor="white", linewidth=0.3, zorder=3)

    # Set limits to match the geographic circle
    cx, cy = INSET_CENTER
    r = INSET_RADIUS
    ax_inset.set_xlim(cx - r, cx + r)
    ax_inset.set_ylim(cy - r, cy + r)
    ax_inset.set_aspect("equal")
    ax_inset.set_xticks([])
    ax_inset.set_yticks([])

    # Circular clip on all plotted elements
    clip_circle = mpatches.Circle((0.5, 0.5), 0.5, transform=ax_inset.transAxes)
    for coll in ax_inset.collections:
        coll.set_clip_path(clip_circle)

    # Border circle
    border_circle = mpatches.Circle((0.5, 0.5), 0.5, transform=ax_inset.transAxes,
                                     fill=False, edgecolor=META_GRAY300, linewidth=1.5,
                                     clip_on=False, zorder=100)
    ax_inset.add_patch(border_circle)

    # ── Regional labels (coordinates are lon, lat) ────────────────────────────
    # India — Hindi belt
    ax_inset.annotate("Hindi", xy=(80, 26), fontsize=8, fontweight='bold',
                       color='white', ha='center', va='center', zorder=10)

    # India — Dravidian south
    ax_inset.annotate("Dravidian", xy=(78, 13), fontsize=7,
                       fontweight='regular', color=BLACK, ha='center', va='center',
                       zorder=10, alpha=0.85)

    # Myanmar — ethnic states (pink)
    ax_inset.annotate("Myanmar", xy=(97, 19), fontsize=7,
                       fontweight='regular', color='white', ha='center', va='center',
                       zorder=10)

    # Tibet
    ax_inset.annotate("Tibet", xy=(88, 33), fontsize=7,
                       fontweight='regular', color='white', ha='center', va='center',
                       zorder=10)

    # Pakistan
    ax_inset.annotate("Pakistan", xy=(69, 30), fontsize=6.5,
                       fontweight='regular', color=BLACK, ha='center', va='center',
                       zorder=10, alpha=0.85)

    # Clip regional labels
    for text in ax_inset.texts:
        text.set_clip_path(clip_circle)

    # Inset title — above the circle
    fig.text(inset_x + inset_w / 2, inset_y + inset_h + 0.015,
             "South & Southeast Asia", fontsize=14, fontweight='bold', color=BLACK,
             ha='center', va='bottom')

    # ── Title and subtitle ────────────────────────────────────────────────────
    fig.text(0.03, 0.96, "Which Countries Are Left Behind by AI?",
             fontsize=28, fontweight='bold', color=BLACK, va='top')
    fig.text(0.03, 0.915,
             "LLM language performance by region, based on LanguageBench scores across 36 models",
             fontsize=14, fontweight='light', color=BLACK, alpha=0.7, va='top')

    # ── Legend — bottom left ──────────────────────────────────────────────────
    legend_patches = [
        Patch(facecolor=TIER_COLORS[1], edgecolor="white", label=TIER_LABELS[1]),
        Patch(facecolor=TIER_COLORS[2], edgecolor="white", label=TIER_LABELS[2]),
        Patch(facecolor=TIER_COLORS[3], edgecolor="white", label=TIER_LABELS[3]),
    ]
    leg = ax_world.legend(handles=legend_patches, loc='lower left',
                          fontsize=11, frameon=False, ncol=3,
                          bbox_to_anchor=(0.0, -0.02))
    for text in leg.get_texts():
        text.set_color(BLACK)

    # ── Source ────────────────────────────────────────────────────────────────
    fig.text(0.03, 0.02,
             "Sources: LanguageBench (fair-forward, 2025), Unicode CLDR, Natural Earth",
             fontsize=10, fontstyle='italic', color=META_GRAY600, va='bottom')

    fig.savefig(output_path, format=fmt, bbox_inches='tight', facecolor=BG,
                dpi=dpi, pad_inches=0.3)
    plt.close()
    size = os.path.getsize(output_path) / 1e6
    print(f"  {output_path}: {size:.1f} MB")


print("\nRendering SVG...")
render_map(OUTPUT_SVG, 'svg', 100)

print("Rendering PNG...")
render_map(OUTPUT_PNG, 'png', 200)

print("\nDone!")
