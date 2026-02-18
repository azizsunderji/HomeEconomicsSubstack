"""
Population Growth Rate: California vs New York (2010-2025)
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# Paths
DATA_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates")
OUTPUT_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Explorations/2026_01_27_ComponentsofPopChange/outputs")

# Load data - use each vintage separately to avoid Census 2020 discontinuity
df_2020s = pd.read_parquet(DATA_DIR / "state_v2025.parquet")
df_2010s = pd.read_parquet(DATA_DIR / "state_2010s.parquet")

# Extract CA and NY - calculate growth within each vintage
def get_state_growth_series(state_name):
    """Get population growth rate time series for a state"""
    s_2010s = df_2010s[df_2010s['NAME'] == state_name].iloc[0]
    s_2020s = df_2020s[df_2020s['NAME'] == state_name].iloc[0]

    growth = {}

    # 2010s vintage: 2011-2019 (year-over-year within same vintage)
    for year in range(2011, 2020):
        prev_col = f'POPESTIMATE{year-1}'
        curr_col = f'POPESTIMATE{year}'
        if prev_col in s_2010s.index and curr_col in s_2010s.index:
            growth[year] = (s_2010s[curr_col] - s_2010s[prev_col]) / s_2010s[prev_col] * 100

    # 2020s vintage: 2021-2025 (year-over-year within same vintage)
    # Skip 2020 as it's the base year
    for year in range(2021, 2026):
        prev_col = f'POPESTIMATE{year-1}'
        curr_col = f'POPESTIMATE{year}'
        if prev_col in s_2020s.index and curr_col in s_2020s.index:
            growth[year] = (s_2020s[curr_col] - s_2020s[prev_col]) / s_2020s[prev_col] * 100

    return pd.Series(growth)

ca_growth = get_state_growth_series('California')
ny_growth = get_state_growth_series('New York')

print("California growth rates:")
print(ca_growth)
print("\nNew York growth rates:")
print(ny_growth)

# Create chart
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

# Plot lines
ax.plot(ca_growth.index, ca_growth.values, color='#0BB4FF', linewidth=2.5,
        marker='o', markersize=5, label='California')
ax.plot(ny_growth.index, ny_growth.values, color='#F4743B', linewidth=2.5,
        marker='o', markersize=5, label='New York')

# Add zero line
ax.axhline(y=0, color='#3D3733', linewidth=1, linestyle='-', alpha=0.5)

# Styling
ax.set_xlabel('')
ax.set_ylabel('')
ax.set_title('Population Growth Rate\nCalifornia vs. New York', fontsize=18, fontweight='bold',
             color='#3D3733', pad=20)

# Y-axis formatting
ax.set_ylim(min(ca_growth.min(), ny_growth.min()) - 0.2, max(ca_growth.max(), ny_growth.max()) + 0.2)
yticks = ax.get_yticks()
ax.set_yticklabels([f'{y:.1f}%' if i == len(yticks)-1 else f'{y:.1f}'
                    for i, y in enumerate(yticks)], color='#3D3733')

# X-axis
ax.set_xticks(ca_growth.index)
ax.set_xticklabels([str(int(y)) for y in ca_growth.index], color='#3D3733')

# Grid
ax.yaxis.grid(True, color='#DADFCE', linewidth=0.8)
ax.xaxis.grid(False)
ax.set_axisbelow(True)

# Spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#3D3733')

# Remove y-axis tick marks
ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', colors='#3D3733')

# Legend
ax.legend(loc='upper right', frameon=False, fontsize=11)

# Add vertical line for Census 2020 break
ax.axvline(x=2020, color='#888888', linewidth=1, linestyle='--', alpha=0.5)
ax.text(2020, ax.get_ylim()[1] * 0.9, 'Census\n2020', fontsize=8, color='#888888', ha='center')

# Add annotation for COVID exodus
ax.annotate('COVID exodus', xy=(2021, ca_growth[2021]), xytext=(2022.5, -1.2),
            fontsize=9, color='#0BB4FF', ha='center',
            arrowprops=dict(arrowstyle='->', color='#0BB4FF', lw=1))

# Source
ax.text(0.0, -0.1, 'Source: Census Bureau Population Estimates, Vintage 2025',
        transform=ax.transAxes, fontsize=9, color='#888888', style='italic')

plt.tight_layout()

# Save
plt.savefig(OUTPUT_DIR / "ca_ny_population_growth.png", facecolor='#F6F7F3',
            bbox_inches='tight', dpi=150)
plt.savefig(OUTPUT_DIR / "ca_ny_population_growth.svg", facecolor='#F6F7F3',
            bbox_inches='tight')
print(f"\nSaved to {OUTPUT_DIR / 'ca_ny_population_growth.png'}")
