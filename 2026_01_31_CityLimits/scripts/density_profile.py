import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from shapely.geometry import Point

# ── Fonts ──
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# ── Paths ──
SHAPEFILE = '/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_us_tract_5m.zip'
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
DATA = 'data'
OUTPUTS = 'outputs'

# ── Load and compute ──
gdf = gpd.read_file(f"zip://{SHAPEFILE}")
gdf = gdf[gdf['GEOID'].isin(pd.read_parquet(f'{DATA}/atlanta_housing_2024.parquet')['GEOID'])].copy()
gdf = gdf.to_crs(ALBERS)
gdf['area_sqmi'] = gdf.geometry.area / (1609.34 ** 2)

hu = pd.read_parquet(f'{DATA}/atlanta_housing_2024.parquet')
drive = pd.read_parquet(f'{DATA}/atlanta_drive_times.parquet')

gdf = gdf[['GEOID', 'area_sqmi']].merge(hu, on='GEOID').merge(drive, on='GEOID')
gdf['density'] = gdf['housing_units'] / gdf['area_sqmi']
gdf = gdf[gdf['drive_min'].notna() & (gdf['housing_units'] > 0)]

# Bin by drive time (5-minute bins)
gdf['time_bin'] = (gdf['drive_min'] // 5) * 5 + 2.5

profile = gdf.groupby('time_bin').agg(
    median_density=('density', 'median'),
    n_tracts=('GEOID', 'count'),
).reset_index()

# Clip to 90 minutes
profile = profile[profile['time_bin'] <= 90]

# Rolling smooth (3-bin window) to reduce remaining spikiness
profile['median_density'] = profile['median_density'].rolling(3, center=True, min_periods=1).mean()

# ── Chart ──
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

# Use median density
ax.fill_between(profile['time_bin'], profile['median_density'],
                alpha=0.3, color='#67A275', zorder=2)
ax.plot(profile['time_bin'], profile['median_density'],
        color='#67A275', linewidth=2, zorder=3)

# 45-min envelope line
ax.axvline(x=45, color='#3D3733', linewidth=1.2,
           linestyle='--', alpha=0.8, zorder=4)
ax.text(46, profile['median_density'].max() * 0.88,
        '45-minute\ncommute', fontsize=9, color='#3D3733',
        va='top', ha='left')

# Formatting
ax.set_xlabel('Drive time from downtown Atlanta (minutes)', fontsize=10, color='#3D3733')
ax.set_ylabel('', fontsize=10, color='#3D3733')
ax.set_xlim(0, 90)
ax.set_ylim(0, profile['median_density'].max() * 1.1)

# Y-axis formatting: units/sq mi on top label only
from matplotlib.ticker import FuncFormatter
yticks = ax.get_yticks()
def fmt_y(y, pos):
    if pos == len(yticks) - 2:  # top visible tick
        return f'{int(y):,} units/sq mi'
    return f'{int(y):,}'
ax.yaxis.set_major_formatter(FuncFormatter(fmt_y))

# Grid and spines
ax.grid(axis='y', color='#DADFCE', linewidth=0.5, zorder=0)
ax.grid(axis='x', visible=False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', color='#DADFCE')
ax.spines['bottom'].set_color('#DADFCE')

for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_color('#3D3733')

# Title
ax.set_title('Housing Density Falls Off at the Commute Frontier',
             fontsize=14, fontweight='bold', color='#3D3733', pad=20, loc='left')
ax.text(0.0, 1.01,
        'Median housing units per square mile by drive time from downtown Atlanta',
        transform=ax.transAxes, fontsize=9, color='#666666', va='bottom')

# Source
fig.text(0.05, 0.02,
         'Source: ACS 2020-2024 5-Year, Table B25001; OSRM drive times (free-flow)',
         fontsize=6, fontstyle='italic', color='#999999')

plt.tight_layout(rect=[0, 0.04, 1, 1])
fig.savefig(f'{OUTPUTS}/atlanta_density_profile.png', dpi=200, bbox_inches='tight', facecolor='#F6F7F3')
fig.savefig(f'{OUTPUTS}/atlanta_density_profile.svg', bbox_inches='tight', facecolor='#F6F7F3')
plt.close()
print(f'Saved to {OUTPUTS}/atlanta_density_profile.png')
