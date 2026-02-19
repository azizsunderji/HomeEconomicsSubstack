#!/usr/bin/env python3
"""
PhD Bubble Map — 4 cutoff comparison
=====================================
Same map 4 times, each with a different minimum PhD threshold for labels.
Top 15 by per-capita rate among metros meeting the threshold.
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

COLOR_PALE = np.array([209, 237, 255]) / 255
COLOR_BRAND = np.array([11, 180, 255]) / 255
COLOR_CAP = 50

# 4 different minimum PhD thresholds
THRESHOLDS = [500, 1000, 2000, 5000]
N_LABELS = 15

# =============================================================================
# LOAD DATA (once)
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

metro = metro.sort_values('total_pop', ascending=False).reset_index(drop=True)
metro['pop_rank'] = range(1, len(metro) + 1)

# Load geo data
print("Loading shapefiles...")
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

states = gpd.read_file(STATE_SHAPEFILE)
states = states[~states['STATEFP'].isin(EXCLUDE_STATES)]
states = states.to_crs(ALBERS)
bounds = states.total_bounds
map_cx = (bounds[0] + bounds[2]) / 2
map_cy = (bounds[1] + bounds[3]) / 2

# Fonts
oracle_regular = fm.FontProperties(fname=FONT_REGULAR)
oracle_bold = fm.FontProperties(fname=FONT_BOLD)
oracle_light = fm.FontProperties(fname=FONT_LIGHT)
oracle_medium = fm.FontProperties(fname=FONT_MEDIUM)

# Short name lookup
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
    'Gainesville, FL': 'Gainesville',
    'State College, PA': 'State College',
    'College Station-Bryan, TX': 'College Station',
    'Santa Cruz-Watsonville, CA': 'Santa Cruz',
    'Lansing-East Lansing, MI': 'E. Lansing',
    'Champaign-Urbana, IL': 'Champaign',
    'Madison, WI': 'Madison',
    'Durham-Chapel Hill, NC': 'Durham',
    'Corvallis, OR': 'Corvallis',
    'Charlottesville, VA': 'Charlottesville',
    'San Jose-Sunnyvale-Santa Clara, CA': 'San Jose',
    'San Francisco-Oakland-Berkeley, CA': 'San Francisco',
    'Denver-Aurora-Lakewood, CO': 'Denver',
    'Austin-Round Rock-Georgetown, TX': 'Austin',
    'Minneapolis-St. Paul-Bloomington, MN-WI': 'Minneapolis',
    'Chicago-Naperville-Elgin, IL-IN-WI': 'Chicago',
    'Dallas-Fort Worth-Arlington, TX': 'Dallas',
    'Houston-The Woodlands-Sugar Land, TX': 'Houston',
    'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD': 'Philadelphia',
    'Atlanta-Sandy Springs-Alpharetta, GA': 'Atlanta',
    'Detroit-Warren-Dearborn, MI': 'Detroit',
    'Phoenix-Mesa-Chandler, AZ': 'Phoenix',
    'Pittsburgh, PA': 'Pittsburgh',
    'Huntsville, AL': 'Huntsville',
    'Colorado Springs, CO': 'Colorado Springs',
    'Tucson, AZ': 'Tucson',
}

def get_short_name(name):
    if name in SHORT_NAMES:
        return SHORT_NAMES[name]
    return name.split(',')[0].split('-')[0].strip()

# =============================================================================
# HELPER: size and color
# =============================================================================

def rate_to_color(rate):
    t = min(rate / COLOR_CAP, 1.0) ** 1.3
    return COLOR_PALE * (1 - t) + COLOR_BRAND * t

# =============================================================================
# DRAW 4 MAPS
# =============================================================================

fig, axes = plt.subplots(2, 2, figsize=(18, 15), dpi=100)
fig.patch.set_facecolor(BG_CREAM)

for idx, (threshold, ax) in enumerate(zip(THRESHOLDS, axes.flat)):
    ax.set_facecolor(BG_CREAM)

    # Determine label set for this threshold
    labelable = metro[metro['total_phds'] >= threshold]
    label_df = labelable.nlargest(N_LABELS, 'phds_per_10k')
    label_metros = set(label_df['msa_code'])

    # Select metros to show (top 250 + any label metros)
    n_show = min(250, len(metro))
    sel = metro[(metro['pop_rank'] <= n_show) | (metro['msa_code'].isin(label_metros))].copy()
    sel = sel.merge(cbsa_centroids, left_on='msa_code', right_on='CBSAFP', how='inner')

    # Bubble sizing (consistent across all 4)
    max_abs = metro['total_phds'].max()  # use global max for consistent sizing
    MIN_RADIUS = 1.0
    MAX_RADIUS = 18

    def abs_to_radius(total_phds):
        if total_phds <= 0:
            return MIN_RADIUS
        return MIN_RADIUS + (MAX_RADIUS - MIN_RADIUS) * np.sqrt(total_phds / max_abs)

    # Draw states
    states.plot(ax=ax, color=LAND_FILL, edgecolor='white', linewidth=0.5, zorder=1)

    # Draw bubbles (big first)
    sel = sel.sort_values('total_phds', ascending=False)
    for _, r in sel.iterrows():
        radius = abs_to_radius(r['total_phds'])
        area = np.pi * radius**2
        color = rate_to_color(r['phds_per_10k'])
        is_labeled = r['msa_code'] in label_metros

        ax.scatter(r['cx'], r['cy'],
                   s=area, c=[color],
                   edgecolor=BLACK if is_labeled else 'none',
                   linewidth=0.8 if is_labeled else 0.0,
                   alpha=0.85,
                   zorder=4 if is_labeled else 3)

    # Labels
    for _, r in sel.iterrows():
        if r['msa_code'] not in label_metros:
            continue

        short = get_short_name(r['NAME'])
        phds = r['total_phds']

        # Default offset: east if metro is in west half, west if east
        ox = 100000 if r['cx'] < map_cx else -100000
        oy = 40000 if r['cy'] > map_cy else -40000

        lx, ly = r['cx'] + ox, r['cy'] + oy

        ax.plot([r['cx'], lx], [r['cy'], ly],
                color=BLACK, linewidth=0.3, alpha=0.3, zorder=5)

        ha = 'left' if ox > 0 else 'right'
        ax.text(lx, ly, f"{short} ({phds:,.0f})",
                fontproperties=oracle_regular, fontsize=5,
                color=BLACK, ha=ha, va='center', zorder=6)

    # Bounds
    pad_x = 50000
    pad_y = 50000
    ax.set_xlim(bounds[0] - pad_x, bounds[2] + pad_x)
    ax.set_ylim(bounds[1] - pad_y, bounds[3] + pad_y)
    ax.set_aspect('equal')
    ax.axis('off')

    # Panel title
    label_names = [get_short_name(n) for n in label_df.merge(cbsa_centroids, left_on='msa_code', right_on='CBSAFP', how='inner')['NAME']]
    ax.set_title(f"Min {threshold:,} PhDs — top 15 by per-capita",
                 fontproperties=oracle_medium, fontsize=10, color=BLACK, pad=8)

    # Print the label list
    print(f"\n--- Threshold: {threshold:,} PhDs ---")
    for _, r2 in label_df.merge(cbsa_centroids, left_on='msa_code', right_on='CBSAFP', how='inner').iterrows():
        print(f"  {get_short_name(r2['NAME']):20s}  {r2['total_phds']:>8,.0f} PhDs  {r2['phds_per_10k']:>6.1f}/10k")

plt.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.02, hspace=0.08, wspace=0.02)

fig.text(0.5, 0.97, TITLE, ha='center', va='top',
         fontproperties=oracle_bold, fontsize=16, color=BLACK)

output_png = f"{OUTPUT_DIR}/phd_bubble_map_grid.png"
fig.savefig(output_png, format='png', dpi=150, facecolor=BG_CREAM)
print(f"\nSaved: {output_png}")
plt.close()
print("Done.")
