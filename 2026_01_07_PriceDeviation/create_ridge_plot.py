#!/usr/bin/env python3
"""
Ridge plot: Distribution of YoY price changes by ZIP code, one ridge per year
- Continuous gradient: yellow below zero, white at zero, blue above zero
- November snapshots from 2001-2025
- Most recent years (2025) at top, fully layered on top of older years
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import gaussian_kde

# Export text as editable text in SVG
plt.rcParams['svg.fonttype'] = 'none'

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

OUTPUT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_01_07_PriceDeviation"

# Load data
print("Loading ZIP data...")
df = pd.read_parquet("/Users/azizsunderji/Dropbox/Home Economics/Data/Price/Zillow/zillow_zhvi_zip.parquet")

# Get November columns
date_cols = sorted([c for c in df.columns if c.startswith('20') or c.startswith('19')])
nov_cols = [c for c in date_cols if '-11-' in c]

# Compute YoY changes for each November (2001-2025)
years = list(range(2001, 2026))
yoy_data = {}

print("Computing YoY changes...")
for year in years:
    curr_col = f'{year}-11-30'
    prev_col = f'{year-1}-11-30'

    if curr_col in df.columns and prev_col in df.columns:
        curr = df[curr_col]
        prev = df[prev_col]

        # Compute YoY where both values exist
        mask = curr.notna() & prev.notna() & (prev > 0)
        yoy = ((curr[mask] / prev[mask]) - 1) * 100
        yoy_data[year] = yoy.values
        print(f"  {year}: {len(yoy):,} ZIPs, median={yoy.median():.1f}%")

# Determine x-axis bounds
x_min, x_max = -25, 25  # Symmetrical bounds

print(f"\nX-axis bounds: {x_min}% to {x_max}%")

# Create ridge plot
n_years = len(yoy_data)
fig_height = 0.4 * n_years + 2
fig, ax = plt.subplots(figsize=(9, fig_height), dpi=100)
fig.patch.set_facecolor('#F6F7F3')
ax.set_facecolor('#F6F7F3')

# X values for KDE evaluation (more points for smoother gradient)
x_eval = np.linspace(x_min, x_max, 500)

# Ridge parameters
ridge_height = 1.0  # Height multiplier for KDE
ridge_spacing = 1.0  # Vertical spacing between ridges
overlap = 0.3  # Less overlap for cleaner separation

# Continuous gradient: intense yellow -> pale yellow -> pale blue -> intense blue
def get_color_for_x(x_val, x_min, x_max):
    """Map x value to color: yellow on left, blue on right, pale near zero"""
    # Normalize to [-1, 1] where 0 is the center
    if x_val <= 0:
        t = x_val / abs(x_min)  # -1 to 0
    else:
        t = x_val / x_max  # 0 to 1

    # Full yellow: #FEC439 (254, 196, 57)
    # Pale yellow: #FEF0C4 (254, 240, 196)
    # Pale blue: #C4E8FE (196, 232, 254)
    # Full blue: #0BB4FF (11, 180, 255)

    if t <= 0:
        # Yellow side: interpolate from pale yellow (t=0) to full yellow (t=-1)
        intensity = abs(t)  # 0 to 1
        r = int(254 + intensity * (254 - 254))
        g = int(240 + intensity * (196 - 240))
        b = int(196 + intensity * (57 - 196))
    else:
        # Blue side: interpolate from pale blue (t=0) to full blue (t=1)
        intensity = t  # 0 to 1
        r = int(196 + intensity * (11 - 196))
        g = int(232 + intensity * (180 - 232))
        b = int(254 + intensity * (255 - 254))

    return f'#{r:02x}{g:02x}{b:02x}'

# Plot ridges: 2001 at top, 2025 at bottom
# Draw from 2001 to 2025 so newer years layer on top
years_sorted = sorted(yoy_data.keys(), reverse=True)  # [2025, 2024, ..., 2001]

# Store ridge data
ridge_info = []

for i, year in enumerate(years_sorted):
    data = yoy_data[year]

    # Clip data for KDE computation
    data_clipped = data[(data >= x_min) & (data <= x_max)]

    # Compute KDE
    kde = gaussian_kde(data_clipped, bw_method=0.15)
    density = kde(x_eval)

    # Normalize density for consistent ridge height
    density = density / density.max() * ridge_height

    # Y baseline for this ridge (2001 at bottom, 2025 at top)
    y_base = i * (ridge_spacing - overlap)

    # Compute mean and std dev for this year
    mean_val = np.mean(data_clipped)
    std_val = np.std(data_clipped)

    ridge_info.append({
        'year': year,
        'density': density,
        'y_base': y_base,
        'mean': mean_val,
        'std': std_val,
    })

# Draw ridges from 2001 (top) to 2025 (bottom)
# Draw oldest first, newest last so 2025 layers on top
std_line_offset = 0.08  # How far below the baseline to draw the std line

for info in reversed(ridge_info):  # reversed: 2001 first, 2025 last
    y_base = info['y_base']
    density = info['density']
    mean_val = info['mean']
    std_val = info['std']

    # Draw std dev line beneath the ridge
    std_y = y_base - std_line_offset
    ax.plot([mean_val - std_val, mean_val + std_val], [std_y, std_y],
            color='#3D3733', linewidth=1.5, solid_capstyle='round', zorder=5)

    # Draw gradient fill using many thin vertical strips
    for j in range(len(x_eval) - 1):
        x_left = x_eval[j]
        x_right = x_eval[j + 1]
        x_mid = (x_left + x_right) / 2

        color = get_color_for_x(x_mid, x_min, x_max)

        ax.fill_between([x_left, x_right],
                        [y_base, y_base],
                        [y_base + density[j], y_base + density[j + 1]],
                        color=color, linewidth=0)

    # Stroke on top (black outline)
    ax.plot(x_eval, y_base + density, color='#3D3733', linewidth=1.2)

# Year labels (on the left side, aligned with baseline)
for info in ridge_info:
    ax.text(x_min - 1, info['y_base'], str(info['year']),
            ha='right', va='center', fontsize=10, color='#3D3733')

# Styling
ax.set_xlim(x_min - 6, x_max + 2)  # Extra space on left for year labels
ax.set_ylim(-0.5, n_years * (ridge_spacing - overlap) + ridge_height)
ax.set_xlabel('')
ax.set_title('Distribution of Annual Home Price Changes\nAcross U.S. ZIP Codes',
             fontsize=16, fontweight='bold', color='#3D3733', pad=20)

# Remove all spines
ax.set_yticks([])
ax.spines['left'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_visible(False)

# Vertical gridlines
ax.xaxis.grid(True, linestyle='-', alpha=0.3, color='#3D3733', zorder=0)
ax.set_axisbelow(True)

# X-axis styling - just tick labels, no line
ax.tick_params(axis='x', colors='#3D3733', length=0)
ax.set_xticks([-20, -10, 0, 10, 20])
ax.set_xticklabels(['-20%', '-10%', '0%', '+10%', '+20%'])

# Source
fig.text(0.99, 0.01, 'Source: Zillow Home Value Index', ha='right', va='bottom',
         fontsize=9, color='#666666', style='italic')

# Legend - gradient description
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='#0BB4FF', label='Prices Rising'),
    Patch(facecolor='#FEC439', label='Prices Falling'),
]
ax.legend(handles=legend_elements, loc='upper left', frameon=False, fontsize=10)

plt.tight_layout()

# Save PNG
output_png = f"{OUTPUT_DIR}/ridge_plot_yoy_distribution.png"
plt.savefig(output_png, facecolor='#F6F7F3', edgecolor='none', bbox_inches='tight')
print(f"\nSaved: {output_png}")

# Save SVG with editable text
output_svg = f"{OUTPUT_DIR}/ridge_plot_yoy_distribution.svg"
plt.savefig(output_svg, facecolor='#F6F7F3', edgecolor='none', bbox_inches='tight', format='svg')
print(f"Saved: {output_svg}")

plt.close()
