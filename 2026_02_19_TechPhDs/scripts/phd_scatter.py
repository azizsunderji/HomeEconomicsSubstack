#!/usr/bin/env python3
"""
PhD Scatter: Metro Population vs Total PhDs
============================================
X = metro population, Y = total technical PhDs.
Bay Area should be a clear outlier above the trend line.
"""

import duckdb
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

OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs"
OUTPUT_SVG = f"{OUTPUT_DIR}/phd_scatter.svg"
OUTPUT_PNG = f"{OUTPUT_DIR}/phd_scatter.png"

BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
FONT_REGULAR = f"{FONT_DIR}/ABCOracle-Regular.otf"
FONT_BOLD = f"{FONT_DIR}/ABCOracle-Bold.otf"
FONT_LIGHT = f"{FONT_DIR}/ABCOracle-Light.otf"
FONT_MEDIUM = f"{FONT_DIR}/ABCOracle-Medium.otf"

IPUMS_5YR = '/tmp/ipums_degfield_5yr.csv.gz'
BAY_AREA_MSAS = [41940, 41860]

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

# CBSA names
import geopandas as gpd
CBSA_SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_cbsa/cb_2023_us_cbsa_5m.shp'
cbsas = gpd.read_file(CBSA_SHAPEFILE)[['CBSAFP', 'NAME']]
cbsas['CBSAFP'] = cbsas['CBSAFP'].astype(int)

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

# Add names
metro = metro.merge(cbsas, left_on='msa_code', right_on='CBSAFP', how='left')
metro.loc[metro['msa_code'] == 99999, 'NAME'] = 'Bay Area'

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
    'Chicago-Naperville-Elgin, IL-IN-WI': 'Chicago',
    'Dallas-Fort Worth-Arlington, TX': 'Dallas',
    'Houston-The Woodlands-Sugar Land, TX': 'Houston',
    'Philadelphia-Camden-Wilmington, PA-NJ-DE-MD': 'Philadelphia',
    'Atlanta-Sandy Springs-Alpharetta, GA': 'Atlanta',
    'Minneapolis-St. Paul-Bloomington, MN-WI': 'Minneapolis',
    'Austin-Round Rock-Georgetown, TX': 'Austin',
    'Denver-Aurora-Lakewood, CO': 'Denver',
    'Detroit-Warren-Dearborn, MI': 'Detroit',
    'Phoenix-Mesa-Chandler, AZ': 'Phoenix',
    'Pittsburgh, PA': 'Pittsburgh',
    'Baltimore-Columbia-Towson, MD': 'Baltimore',
}

def get_short(name):
    if pd.isna(name):
        return ''
    if name in SHORT_NAMES:
        return SHORT_NAMES[name]
    return name.split(',')[0].split('-')[0].strip()

metro['short_name'] = metro['NAME'].apply(get_short)

# Filter to metros with at least some PhDs and reasonable pop
plot_df = metro[(metro['total_phds'] > 0) & (metro['total_pop'] > 50000)].copy()
plot_df = plot_df.sort_values('total_pop', ascending=False)

print(f"Plotting {len(plot_df)} metros")

# =============================================================================
# FIT TREND LINE (log-log OLS)
# =============================================================================

log_pop = np.log10(plot_df['total_pop'].values)
log_phds = np.log10(plot_df['total_phds'].values.clip(1))
coeffs = np.polyfit(log_pop, log_phds, 1)
trend_x = np.linspace(log_pop.min(), log_pop.max(), 100)
trend_y = np.polyval(coeffs, trend_x)

# Residuals for identifying outliers
plot_df['predicted_log_phds'] = np.polyval(coeffs, np.log10(plot_df['total_pop']))
plot_df['residual'] = np.log10(plot_df['total_phds'].clip(1)) - plot_df['predicted_log_phds']

print(f"\nTrend line: log10(PhDs) = {coeffs[0]:.3f} * log10(pop) + ({coeffs[1]:.3f})")
print(f"Power law exponent: {coeffs[0]:.3f}")

# =============================================================================
# PLOT
# =============================================================================

oracle_regular = fm.FontProperties(fname=FONT_REGULAR)
oracle_bold = fm.FontProperties(fname=FONT_BOLD)
oracle_light = fm.FontProperties(fname=FONT_LIGHT)
oracle_medium = fm.FontProperties(fname=FONT_MEDIUM)

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Trend line
ax.plot(10**trend_x, 10**trend_y, color='#CCCCCC', linewidth=1.5, zorder=1, linestyle='--')

# All dots
ax.scatter(plot_df['total_pop'], plot_df['total_phds'],
           s=25, c=BLUE, alpha=0.5, edgecolor='none', zorder=3)

# Label outliers: top residuals (above trend) and biggest metros
# Above trend: top 8 by residual
above = plot_df.nlargest(8, 'residual')
# Biggest metros: top 5 by pop
biggest = plot_df.nlargest(5, 'total_pop')
# Combine
to_label = pd.concat([above, biggest]).drop_duplicates(subset='msa_code')

# Highlight labeled dots
ax.scatter(to_label['total_pop'], to_label['total_phds'],
           s=40, c=BLUE, alpha=0.85, edgecolor=BLACK, linewidth=0.8, zorder=4)

# Labels with collision avoidance
label_positions = []

for _, r in to_label.iterrows():
    name = r['short_name']
    x, y = r['total_pop'], r['total_phds']

    # Default offset direction
    if name == 'Bay Area':
        ox, oy = -0.08, 0.12
    elif name == 'New York':
        ox, oy = 0.06, -0.10
    elif name == 'Los Angeles':
        ox, oy = 0.06, 0.08
    elif name == 'Washington DC':
        ox, oy = 0.06, 0.06
    elif name == 'Boston':
        ox, oy = 0.06, 0.06
    elif name == 'Chicago':
        ox, oy = 0.06, -0.08
    elif name == 'Seattle':
        ox, oy = -0.10, 0.06
    elif name in ('Ithaca', 'State College', 'Ann Arbor', 'Princeton'):
        ox, oy = 0.06, 0.10
    else:
        ox, oy = 0.06, 0.06

    # In log space
    lx = 10**(np.log10(x) + ox)
    ly = 10**(np.log10(y) + oy)

    ax.annotate(name,
                xy=(x, y), xytext=(lx, ly),
                fontproperties=oracle_regular, fontsize=7, color=BLACK,
                arrowprops=dict(arrowstyle='-', color=BLACK, lw=0.4, alpha=0.35),
                ha='left' if ox > 0 else 'right', va='center', zorder=6)

# Log scales
ax.set_xscale('log')
ax.set_yscale('log')

# Axis formatting
ax.set_xlabel('Metro population', fontproperties=oracle_medium, fontsize=9, color=BLACK, labelpad=8)
ax.set_ylabel('Technical PhDs', fontproperties=oracle_medium, fontsize=9, color=BLACK, labelpad=8)

# Gridlines
ax.grid(True, which='major', axis='both', color='#DDDDDD', linewidth=0.5, zorder=0)
ax.grid(True, which='minor', axis='both', color='#EEEEEE', linewidth=0.3, zorder=0)

# Spines
for spine in ['top', 'right']:
    ax.spines[spine].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#CCCCCC')
ax.tick_params(axis='both', which='both', colors='#888888', labelsize=7)
ax.tick_params(axis='y', length=0)

# Custom tick labels
from matplotlib.ticker import FuncFormatter

def pop_fmt(x, p):
    if x >= 1e6:
        return f'{x/1e6:.0f}M'
    elif x >= 1e3:
        return f'{x/1e3:.0f}k'
    return f'{x:.0f}'

def phd_fmt(x, p):
    if x >= 1e3:
        return f'{x/1e3:.0f}k'
    return f'{x:.0f}'

ax.xaxis.set_major_formatter(FuncFormatter(pop_fmt))
ax.yaxis.set_major_formatter(FuncFormatter(phd_fmt))

for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontproperties(oracle_light)

# Title
fig.text(0.5, 0.96, "Metro Population vs. Technical PhDs",
         ha='center', va='top',
         fontproperties=oracle_bold, fontsize=14, color=BLACK)
fig.text(0.5, 0.925, "Each dot is a metro area. Dashed line = power-law fit.",
         ha='center', va='top',
         fontproperties=oracle_light, fontsize=8, color='#888')

# Source
fig.text(0.96, 0.02,
         "Source: ACS 5-Year (2019–2023) via IPUMS. CS, math, EE, physics doctoral holders.",
         ha='right', va='bottom',
         fontproperties=oracle_light, fontsize=6, fontstyle='italic', color='#aaa')

plt.subplots_adjust(left=0.08, right=0.96, top=0.89, bottom=0.08)

plt.savefig(OUTPUT_SVG, format='svg', facecolor=BG_CREAM)
print(f"\nSaved SVG: {OUTPUT_SVG}")
fig.savefig(OUTPUT_PNG, format='png', dpi=200, facecolor=BG_CREAM)
print(f"Saved PNG: {OUTPUT_PNG}")
plt.close()
print("Done.")
