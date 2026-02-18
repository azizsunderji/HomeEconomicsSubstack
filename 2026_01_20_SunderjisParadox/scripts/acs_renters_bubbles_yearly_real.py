"""
Generate scatter plot of renter housing burden by income decile over time.
Uses REAL income (2024 dollars) on x-axis.
Each decile traces a horizontal path as income grows but burden stays flat.
"""

import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# Color palette
BLACK = '#3D3733'
BLUE = '#0BB4FF'
BACKGROUND = '#F6F7F3'

# Load data
DATA_PATH = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_20_SunderjisParadox/data/acs_renters_by_decile_yearly.csv"
OUT_PATH = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_20_SunderjisParadox/outputs/acs_renters_bubbles_yearly_real.svg"

df = pd.read_csv(DATA_PATH)

# CPI deflators to convert to 2024 dollars (from FRED CPIAUCSL annual average)
cpi_deflators = {
    2005: 1.606508,
    2006: 1.556366,
    2007: 1.512935,
    2008: 1.457339,
    2009: 1.462019,
    2010: 1.438480,
    2011: 1.394691,
    2012: 1.366364,
    2013: 1.346621,
    2014: 1.325214,
    2015: 1.323609,
    2016: 1.307048,
    2017: 1.279768,
    2018: 1.249295,
    2019: 1.227046,
    2021: 1.157694,
    2022: 1.072014,
    2023: 1.029517,
    2024: 1.000000,
}

# Convert nominal income to real (2024 dollars)
df['real_income'] = df.apply(lambda row: row['median_income'] * cpi_deflators.get(row['year'], 1.0), axis=1)

# Exclude decile 1 (capped at 100%)
df = df[df['decile'] > 1]

# Get year range for color mapping
years = sorted(df['year'].unique())
min_year, max_year = min(years), max(years)

def year_to_color(year):
    """Map year to color gradient from black to blue."""
    t = (year - min_year) / (max_year - min_year)
    # Interpolate RGB
    black_rgb = (0x3D/255, 0x37/255, 0x33/255)
    blue_rgb = (0x0B/255, 0xB4/255, 0xFF/255)
    r = black_rgb[0] + t * (blue_rgb[0] - black_rgb[0])
    g = black_rgb[1] + t * (blue_rgb[1] - black_rgb[1])
    b = black_rgb[2] + t * (blue_rgb[2] - black_rgb[2])
    return (r, g, b)

# Create figure
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BACKGROUND)
ax.set_facecolor(BACKGROUND)

# Plot each decile as connected points
for decile in sorted(df['decile'].unique()):
    decile_df = df[df['decile'] == decile].sort_values('year')

    # Draw connecting lines (thin, light gray)
    ax.plot(decile_df['real_income'], decile_df['median_burden'],
            color='#CCCCCC', linewidth=0.8, zorder=1)

    # Draw points with year-based colors
    for _, row in decile_df.iterrows():
        color = year_to_color(row['year'])
        ax.scatter(row['real_income'], row['median_burden'],
                   s=80, c=[color], edgecolors='none', zorder=2)

    # Add decile label at the end (2024)
    last_row = decile_df[decile_df['year'] == max_year].iloc[0]
    ax.annotate(f'D{decile}',
                xy=(last_row['real_income'], last_row['median_burden']),
                xytext=(8, 0), textcoords='offset points',
                fontsize=9, color=BLACK, va='center')

# Log scale for x-axis
ax.set_xscale('log')

# Format x-axis ticks (adjusted for real income range)
ax.set_xticks([20000, 50000, 100000, 200000])
ax.set_xticklabels(['$20k', '$50k', '$100k', '$200k'])

# Y-axis formatting
ax.set_ylim(10, 70)
yticks = [15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65]
ax.set_yticks(yticks)
ax.set_yticklabels(['15%' if i == 0 else str(y) for i, y in enumerate(yticks)])

# Grid and spines
ax.yaxis.grid(True, color='white', linewidth=1.2)
ax.xaxis.grid(False)
ax.set_axisbelow(True)

for spine in ['top', 'right', 'left']:
    ax.spines[spine].set_visible(False)
ax.spines['bottom'].set_color(BLACK)
ax.spines['bottom'].set_linewidth(0.5)

# Remove y-axis tick marks
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', colors=BLACK)

# Labels
ax.set_xlabel('Household income (2024 dollars)', fontsize=11, color=BLACK)
ax.set_ylabel('Housing cost as % of income', fontsize=11, color=BLACK)

# Title
ax.set_title("Sunderji's Paradox: The rich pay a lower share—but getting richer doesn't help",
             fontsize=13, fontweight='bold', color=BLACK, pad=20)

# Continuous legend with connected dots
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

# Create inset axes for the legend in upper right
legend_ax = inset_axes(ax, width="25%", height="3%", loc='upper right',
                        bbox_to_anchor=(0, -0.02, 1, 1), bbox_transform=ax.transAxes)

# Draw connected dots for years
legend_years = list(range(2005, 2025))
legend_years = [y for y in legend_years if y != 2020]  # exclude 2020
x_positions = np.linspace(0, 1, len(legend_years))

# Draw connecting line
legend_ax.plot(x_positions, [0.5] * len(x_positions), color='#CCCCCC', linewidth=0.8, zorder=1)

# Draw dots
for i, y in enumerate(legend_years):
    color = year_to_color(y)
    legend_ax.scatter(x_positions[i], 0.5, s=30, c=[color], edgecolors='none', zorder=2)

# Add year labels at start and end
legend_ax.text(0, -0.8, '2005', ha='center', va='top', fontsize=8, color=BLACK)
legend_ax.text(1, -0.8, '2024', ha='center', va='top', fontsize=8, color=BLACK)

# Clean up legend axes
legend_ax.set_xlim(-0.05, 1.05)
legend_ax.set_ylim(-1.5, 1.5)
legend_ax.axis('off')

# Source note
fig.text(0.5, 0.02,
         'Source: ACS 1-Year via IPUMS (2005-2024). Incomes adjusted to 2024 dollars using CPI-U. Decile 1 excluded.',
         ha='center', fontsize=8, color='#888888', style='italic')

plt.tight_layout()
plt.subplots_adjust(bottom=0.1)

plt.savefig(OUT_PATH, format='svg', facecolor=BACKGROUND, edgecolor='none', bbox_inches='tight')
print(f"Saved to {OUT_PATH}")

# Print comparison of nominal vs real for D5
d5 = df[df['decile'] == 5][['year', 'median_income', 'real_income', 'median_burden']]
print("\nD5 (median) comparison - nominal vs real income:")
print(d5.to_string(index=False))
