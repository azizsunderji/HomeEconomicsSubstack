#!/usr/bin/env python3
"""
PhD Bubble Map
==============
Bubble on each metro centroid. Size = total PhDs. Color = per-capita quintile.
Top 250 metros by population. Top 10 by absolute PhDs get labels + black outline.
"""

import duckdb
import geopandas as gpd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

matplotlib.use('svg')
plt.rcParams['svg.fonttype'] = 'none'

# =============================================================================
# CONFIG
# =============================================================================

TITLE = "Where America's AI-Ready PhDs Live"
SUBTITLE = "CS, math, EE, and physics doctoral holders. Bubble size = total PhDs. Color = per-capita concentration."
SOURCE = "Source: ACS 5-Year (2019–2023) via IPUMS. Employed, not in school, doctoral degree holders."

OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs"
OUTPUT_SVG = f"{OUTPUT_DIR}/phd_bubble_map.svg"
OUTPUT_PNG = f"{OUTPUT_DIR}/phd_bubble_map.png"

BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
LAND_FILL = '#EDEFE7'

ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
EXCLUDE_STATES = ['02', '15', '60', '66', '69', '72', '78']

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
FONT_REGULAR = f"{FONT_DIR}/ABCOracle-Regular.otf"
FONT_BOLD = f"{FONT_DIR}/ABCOracle-Bold.otf"
FONT_LIGHT = f"{FONT_DIR}/ABCOracle-Light.otf"
FONT_MEDIUM = f"{FONT_DIR}/ABCOracle-Medium.otf"

IPUMS_5YR = '/tmp/ipums_degfield_5yr.csv.gz'
CBSA_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_cbsa/cb_2023_us_cbsa_5m.shp'
STATE_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp'

BAY_AREA_MSAS = [41940, 41860]

# Color endpoints: pale blue → brand blue
COLOR_PALE = np.array([209, 237, 255]) / 255   # #D1EDFF
COLOR_BRAND = np.array([11, 180, 255]) / 255    # #0BB4FF

# =============================================================================
# LOAD DATA
# =============================================================================

print("Loading data...")
conn = duckdb.connect()

phd_metro = conn.execute("""
    SELECT MET2013 as msa_code,
        SUM(PERWT) as total_phds
    FROM read_csv_auto('{path}')
    WHERE EDUCD = 116 AND EMPSTAT = 1 AND SCHOOL = 1
      AND MET2013 > 0
      AND (DEGFIELD IN (21, 37) OR DEGFIELDD IN (2407, 2408, 5007))
    GROUP BY MET2013
""".format(path=IPUMS_5YR)).df()

pop_metro = conn.execute("""
    SELECT MET2013 as msa_code,
        SUM(CASE WHEN AGE >= 25 THEN PERWT ELSE 0 END) as pop_25plus,
        SUM(PERWT) as total_pop
    FROM read_csv_auto('{path}')
    WHERE MET2013 > 0
    GROUP BY MET2013
""".format(path=IPUMS_5YR)).df()

metro = pop_metro.merge(phd_metro, on='msa_code', how='left')
metro['total_phds'] = metro['total_phds'].fillna(0)
metro['phds_per_10k'] = np.where(
    metro['pop_25plus'] > 0,
    metro['total_phds'] / metro['pop_25plus'] * 10000, 0
)

print(f"Total metros: {len(metro)}")

# Combine Bay Area
bay = metro[metro['msa_code'].isin(BAY_AREA_MSAS)]
non_bay = metro[~metro['msa_code'].isin(BAY_AREA_MSAS)].copy()

if len(bay) > 0:
    bay_combined = pd.DataFrame([{
        'msa_code': 99999,
        'total_phds': bay['total_phds'].sum(),
        'pop_25plus': bay['pop_25plus'].sum(),
        'total_pop': bay['total_pop'].sum(),
        'phds_per_10k': bay['total_phds'].sum() / bay['pop_25plus'].sum() * 10000,
    }])
    metro = pd.concat([non_bay, bay_combined], ignore_index=True)
    print(f"Bay Area combined: {bay_combined['total_phds'].iloc[0]:,.0f} PhDs, "
          f"{bay_combined['phds_per_10k'].iloc[0]:.1f}/10k")

# Rank by population, take top 250
metro = metro.sort_values('total_pop', ascending=False).reset_index(drop=True)
metro['pop_rank'] = range(1, len(metro) + 1)

n_show = min(250, len(metro))

# Label selection: top 15 by per-capita rate among metros with >= 1,000 total PhDs
MIN_PHDS_FOR_LABEL = 1000
N_LABELS = 15

labelable = metro[metro['total_phds'] >= MIN_PHDS_FOR_LABEL]
label_df = labelable.nlargest(N_LABELS, 'phds_per_10k')
LABEL_METROS = set(label_df['msa_code'])

print(f"\nLabel metros (top {N_LABELS} by per-capita, >= {MIN_PHDS_FOR_LABEL} PhDs):")
for _, r in label_df.iterrows():
    print(f"  MSA {int(r['msa_code'])}: {r['total_phds']:,.0f} PhDs, {r['phds_per_10k']:.1f}/10k")

# Include top 250 by pop PLUS any label metros that might be outside top 250
selected = metro[(metro['pop_rank'] <= n_show) | (metro['msa_code'].isin(LABEL_METROS))].copy()

print(f"\nShowing {len(selected)} metros")
print(f"PhD per 10k range: {selected['phds_per_10k'].min():.1f} – {selected['phds_per_10k'].max():.1f}")

# =============================================================================
# GET CENTROIDS
# =============================================================================

print("\nLoading CBSA shapefile for centroids...")
cbsas = gpd.read_file(CBSA_SHAPEFILE)
cbsas['CBSAFP'] = cbsas['CBSAFP'].astype(int)
cbsas = cbsas.to_crs(ALBERS)
cbsas['cx'] = cbsas.geometry.centroid.x
cbsas['cy'] = cbsas.geometry.centroid.y

sj = cbsas[cbsas['CBSAFP'] == 41940]
sf = cbsas[cbsas['CBSAFP'] == 41860]
if len(sj) > 0 and len(sf) > 0:
    bay_row = pd.DataFrame([{
        'CBSAFP': 99999, 'NAME': 'Bay Area',
        'cx': (sj['cx'].iloc[0] + sf['cx'].iloc[0]) / 2,
        'cy': (sj['cy'].iloc[0] + sf['cy'].iloc[0]) / 2,
    }])
    cbsa_centroids = pd.concat([cbsas[['CBSAFP', 'NAME', 'cx', 'cy']], bay_row], ignore_index=True)
else:
    cbsa_centroids = cbsas[['CBSAFP', 'NAME', 'cx', 'cy']].copy()

selected = selected.merge(cbsa_centroids, left_on='msa_code', right_on='CBSAFP', how='inner')
print(f"Matched: {len(selected)} metros with centroids")

# =============================================================================
# LOAD STATES
# =============================================================================

print("Loading states...")
states = gpd.read_file(STATE_SHAPEFILE)
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)

# =============================================================================
# PLOT
# =============================================================================

print("Plotting...")

oracle_regular = fm.FontProperties(fname=FONT_REGULAR)
oracle_bold = fm.FontProperties(fname=FONT_BOLD)
oracle_light = fm.FontProperties(fname=FONT_LIGHT)
oracle_medium = fm.FontProperties(fname=FONT_MEDIUM)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# State boundaries
states.plot(ax=ax, color=LAND_FILL, edgecolor='white', linewidth=0.75, zorder=1)

# Bubble size: sqrt scaling, smaller overall
max_abs = selected['total_phds'].max()
MIN_RADIUS = 1.2
MAX_RADIUS = 22

def abs_to_radius(total_phds):
    if total_phds <= 0:
        return MIN_RADIUS
    return MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * np.sqrt(total_phds / max_abs)

# Continuous color: cap at 50/10k so top metros get full intensity
COLOR_CAP = 50  # anything above this gets full brand blue

def rate_to_color(rate):
    t = min(rate / COLOR_CAP, 1.0) ** 1.3
    rgb = COLOR_PALE * (1 - t) + COLOR_BRAND * t
    return rgb

# Sort descending by total PhDs so big bubbles draw first
selected = selected.sort_values('total_phds', ascending=False)

for _, r in selected.iterrows():
    radius = abs_to_radius(r['total_phds'])
    area = np.pi * radius**2
    color = rate_to_color(r['phds_per_10k'])
    is_top10 = r['msa_code'] in LABEL_METROS

    ax.scatter(r['cx'], r['cy'],
               s=area,
               c=[color],
               edgecolor=BLACK if is_top10 else 'none',
               linewidth=1.0 if is_top10 else 0.0,
               alpha=0.85,
               zorder=4 if is_top10 else 3)

# =============================================================================
# LABELS — top 15 by per-capita rate (>= 500 total PhDs)
# =============================================================================

SHORT_NAMES = {
    'Bay Area': 'Bay Area',
    'Boston-Cambridge-Newton, MA-NH': 'Boston',
    'Seattle-Tacoma-Bellevue, WA': 'Seattle',
    'Washington-Arlington-Alexandria, DC-VA-MD-WV': 'Washington DC',
    'San Diego-Chula Vista-Carlsbad, CA': 'San Diego',
    'Portland-Vancouver-Hillsboro, OR-WA': 'Portland',
    'New York-Newark-Jersey City, NY-NJ-PA': 'New York',
    'Los Angeles-Long Beach-Anaheim, CA': 'Los Angeles',
    'Ithaca, NY': 'Ithaca',
    'Ann Arbor, MI': 'Ann Arbor',
    'Trenton-Princeton, NJ': 'Princeton',
    'Albuquerque, NM': 'Albuquerque',
    'Santa Barbara-Santa Maria-Goleta, CA': 'Santa Barbara',
    'Boulder, CO': 'Boulder',
    'Raleigh-Cary, NC': 'Raleigh',
    'Lansing-East Lansing, MI': 'E. Lansing',
    'Austin-Round Rock-Georgetown, TX': 'Austin',
    'Knoxville, TN': 'Knoxville',
    'Albany-Schenectady-Troy, NY': 'Albany',
    'Baltimore-Columbia-Towson, MD': 'Baltimore',
}

def get_short_name(name):
    if name in SHORT_NAMES:
        return SHORT_NAMES[name]
    return name.split(',')[0].split('-')[0].strip()

bounds = states.total_bounds
map_cx = (bounds[0] + bounds[2]) / 2
map_cy = (bounds[1] + bounds[3]) / 2

LABEL_OFFSETS = {
    'Bay Area': (-180000, 70000),
    'Boston': (130000, 55000),
    'New York': (160000, -15000),
    'Seattle': (-160000, 50000),
    'Washington DC': (170000, -30000),
    'Los Angeles': (-180000, -40000),
    'San Diego': (-170000, -35000),
    'Portland': (-170000, 30000),
    'Ann Arbor': (110000, 55000),
    'Princeton': (140000, -50000),
    'Albuquerque': (-150000, -30000),
    'Santa Barbara': (-180000, 30000),
    'E. Lansing': (120000, 30000),
    'Austin': (-140000, -40000),
    'Knoxville': (120000, -30000),
    'Albany': (120000, 40000),
    'Baltimore': (150000, -50000),
}

for _, r in selected.iterrows():
    if r['msa_code'] not in LABEL_METROS:
        continue

    short = get_short_name(r['NAME'])
    phds = r['total_phds']
    rate = r['phds_per_10k']

    if short in LABEL_OFFSETS:
        ox, oy = LABEL_OFFSETS[short]
    else:
        ox = 130000 if r['cx'] > map_cx else -130000
        oy = 50000 if r['cy'] > map_cy else -50000

    lx, ly = r['cx'] + ox, r['cy'] + oy

    ax.plot([r['cx'], lx], [r['cy'], ly],
            color=BLACK, linewidth=0.4, alpha=0.35, zorder=5)

    ha = 'left' if ox > 0 else 'right'
    label_text = f"{short} ({phds:,.0f})"
    ax.text(lx, ly, label_text,
            fontproperties=oracle_regular, fontsize=6,
            color=BLACK, ha=ha, va='center', zorder=6)

# =============================================================================
# BOUNDS — shrink map to leave room for legends/title
# =============================================================================

pad_x = 50000
pad_y = 50000
ax.set_xlim(bounds[0] - pad_x, bounds[2] + pad_x)
ax.set_ylim(bounds[1] - pad_y, bounds[3] + pad_y)
ax.set_aspect('equal')
ax.axis('off')

# Position map in upper portion, leave bottom for legends
plt.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.14)

# =============================================================================
# TITLE / SUBTITLE (above map in figure space)
# =============================================================================

fig.text(0.5, 0.95, TITLE,
         ha='center', va='top',
         fontproperties=oracle_bold, fontsize=14, color=BLACK)

fig.text(0.5, 0.915, SUBTITLE,
         ha='center', va='top',
         fontproperties=oracle_light, fontsize=8, color='#888')

fig.text(0.96, 0.02, SOURCE,
         ha='right', va='bottom',
         fontproperties=oracle_light, fontsize=6, fontstyle='italic', color='#aaa')

# =============================================================================
# LEGENDS (below map in figure space)
# =============================================================================

# --- Size legend (bottom left) ---
legend_abs = [500, 5000, 20000, 44000]
legend_abs_labels = ['500', '5k', '20k', '44k']

fig.text(0.05, 0.10, 'Total PhDs (size)',
         fontproperties=oracle_medium, fontsize=7, color=BLACK)

cx_pos = 0.07
for val, lbl in zip(legend_abs, legend_abs_labels):
    rad = abs_to_radius(val)
    area = np.pi * rad**2
    ax.scatter([cx_pos], [0.055],
               s=area, c=BLUE, alpha=0.85,
               edgecolor='none',
               transform=fig.transFigure, zorder=10, clip_on=False)
    fig.text(cx_pos, 0.02, lbl,
             fontproperties=oracle_light, fontsize=5.5, color='#888', ha='center')
    cx_pos += 0.03 + (rad / MAX_RADIUS) * 0.04

# --- Color legend (bottom right): continuous gradient bar ---
fig.text(0.60, 0.10, 'PhDs per 10k adults (color)',
         fontproperties=oracle_medium, fontsize=7, color=BLACK)

n_steps = 50
bar_x = 0.62
bar_w_total = 0.30
step_w = bar_w_total / n_steps
bar_y = 0.05
bar_h = 0.025

for i in range(n_steps):
    t = (i / (n_steps - 1)) ** 1.3
    rgb = COLOR_PALE * (1 - t) + COLOR_BRAND * t
    x = bar_x + i * step_w
    rect = plt.Rectangle((x, bar_y), step_w + 0.001, bar_h,
                          facecolor=rgb, edgecolor='none',
                          transform=fig.transFigure, clip_on=False, zorder=10)
    fig.patches.append(rect)

# Tick labels
tick_vals = [0, 5, 15, 30, 50]
for tv in tick_vals:
    t = min(tv / COLOR_CAP, 1.0) ** 1.3
    x = bar_x + t * bar_w_total
    fig.text(x, bar_y - 0.01, str(int(tv)),
             fontproperties=oracle_light, fontsize=5.5, color='#888',
             ha='center', va='top')

# =============================================================================
# SAVE
# =============================================================================

plt.savefig(OUTPUT_SVG, format='svg', facecolor=BG_CREAM)
print(f"\nSaved SVG: {OUTPUT_SVG}")

fig.savefig(OUTPUT_PNG, format='png', dpi=200, facecolor=BG_CREAM)
print(f"Saved PNG: {OUTPUT_PNG}")

plt.close()
print("Done.")
