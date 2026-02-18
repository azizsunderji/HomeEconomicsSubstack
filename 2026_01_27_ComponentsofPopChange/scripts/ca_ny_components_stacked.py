"""
Stacked Bar Charts: Components of Population Change for California and New York
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from pathlib import Path

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# Paths
DATA_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates")
OUTPUT_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Explorations/2026_01_27_ComponentsofPopChange/outputs")

# Load data
df_2020s = pd.read_parquet(DATA_DIR / "state_v2025.parquet")
df_2010s = pd.read_parquet(DATA_DIR / "state_2010s.parquet")

def get_state_components(state_name):
    """Get component time series for a state (as % of population)"""
    s_2010s = df_2010s[df_2010s['NAME'] == state_name].iloc[0]
    s_2020s = df_2020s[df_2020s['NAME'] == state_name].iloc[0]

    data = {'year': [], 'natural': [], 'domestic': [], 'international': []}

    # 2010s vintage: 2011-2019
    for year in range(2011, 2020):
        pop_col = f'POPESTIMATE{year-1}'
        nat_col = f'BIRTHS{year}' if f'BIRTHS{year}' in s_2010s.index else None

        # The 2010s file has component data
        if f'NATURALINC{year}' in s_2010s.index:
            pop = s_2010s[f'POPESTIMATE{year-1}']
            data['year'].append(year)
            data['natural'].append(s_2010s[f'NATURALINC{year}'] / pop * 100)
            data['domestic'].append(s_2010s[f'DOMESTICMIG{year}'] / pop * 100)
            data['international'].append(s_2010s[f'INTERNATIONALMIG{year}'] / pop * 100)

    # 2020s vintage: 2021-2025
    for year in range(2021, 2026):
        if f'NATURALCHG{year}' in s_2020s.index:
            pop = s_2020s[f'POPESTIMATE{year-1}']
            data['year'].append(year)
            data['natural'].append(s_2020s[f'NATURALCHG{year}'] / pop * 100)
            data['domestic'].append(s_2020s[f'DOMESTICMIG{year}'] / pop * 100)
            data['international'].append(s_2020s[f'INTERNATIONALMIG{year}'] / pop * 100)

    return pd.DataFrame(data)

ca_df = get_state_components('California')
ny_df = get_state_components('New York')

print("California components:")
print(ca_df.round(2))
print("\nNew York components:")
print(ny_df.round(2))

# Colors
NATURAL_COLOR = '#67A275'      # Green
DOMESTIC_COLOR = '#0BB4FF'     # Blue
INTERNATIONAL_COLOR = '#FEC439' # Yellow
NEGATIVE_NATURAL = '#C6DCCB'   # Light green for negative
NEGATIVE_DOMESTIC = '#F4743B'  # Red for negative domestic
NEGATIVE_INTL = '#FBCAB5'      # Light red

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7), dpi=100)
fig.patch.set_facecolor('#F6F7F3')

def plot_stacked_bars(ax, df, title):
    ax.set_facecolor('#F6F7F3')

    years = df['year'].values
    x = np.arange(len(years))
    width = 0.7

    # We need to handle positive and negative values separately for proper stacking
    natural = df['natural'].values
    domestic = df['domestic'].values
    international = df['international'].values

    # Plot each component
    # For stacked bars with mixed signs, we need to track positive and negative bottoms

    # Start with natural change
    bars_natural = ax.bar(x, natural, width, label='Natural change',
                          color=[NATURAL_COLOR if v >= 0 else '#C6DCCB' for v in natural])

    # Domestic migration - stack on top of natural (or below if negative)
    bottom_domestic = np.where(domestic >= 0,
                               np.maximum(natural, 0),  # positive domestic starts at max(natural, 0)
                               np.minimum(natural, 0))  # negative domestic starts at min(natural, 0)

    # Actually, for a true stacked bar showing components, let's do it differently
    # Stack positives together, stack negatives together

    ax.clear()
    ax.set_facecolor('#F6F7F3')

    # Separate positive and negative components
    pos_bottom = np.zeros(len(years))
    neg_bottom = np.zeros(len(years))

    # Natural change
    nat_pos = np.where(natural > 0, natural, 0)
    nat_neg = np.where(natural < 0, natural, 0)
    ax.bar(x, nat_pos, width, bottom=pos_bottom, label='Natural change', color=NATURAL_COLOR)
    ax.bar(x, nat_neg, width, bottom=neg_bottom, color=NATURAL_COLOR)
    pos_bottom += nat_pos
    neg_bottom += nat_neg

    # International migration (typically positive)
    intl_pos = np.where(international > 0, international, 0)
    intl_neg = np.where(international < 0, international, 0)
    ax.bar(x, intl_pos, width, bottom=pos_bottom, label='International migration', color=INTERNATIONAL_COLOR)
    ax.bar(x, intl_neg, width, bottom=neg_bottom, color=INTERNATIONAL_COLOR)
    pos_bottom += intl_pos
    neg_bottom += intl_neg

    # Domestic migration (use red since it's negative for both CA and NY)
    dom_pos = np.where(domestic > 0, domestic, 0)
    dom_neg = np.where(domestic < 0, domestic, 0)
    ax.bar(x, dom_pos, width, bottom=pos_bottom, color=NEGATIVE_DOMESTIC)
    ax.bar(x, dom_neg, width, bottom=neg_bottom, label='Domestic migration', color=NEGATIVE_DOMESTIC)

    # Zero line
    ax.axhline(y=0, color='#3D3733', linewidth=1)

    # Add total line
    total = natural + domestic + international
    ax.plot(x, total, color='#3D3733', linewidth=2, marker='o', markersize=4, label='Total')

    # Styling
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(y)) for y in years], rotation=45, ha='right', color='#3D3733')
    ax.set_title(title, fontsize=16, fontweight='bold', color='#3D3733', pad=15)

    # Y-axis
    ax.yaxis.grid(True, color='#DADFCE', linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0)

    # Y-axis label on top tick only
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1f}%'))

    return ax

plot_stacked_bars(ax1, ca_df, 'California')
plot_stacked_bars(ax2, ny_df, 'New York')

# Shared legend at bottom
handles, labels = ax1.get_legend_handles_labels()
fig.legend(handles, labels, loc='lower center', ncol=4, frameon=False, fontsize=11,
           bbox_to_anchor=(0.5, 0.02))

# Main title
fig.suptitle('Components of Population Change\n(as % of population)',
             fontsize=18, fontweight='bold', color='#3D3733', y=0.98)

# Source
fig.text(0.02, 0.02, 'Source: Census Bureau Population Estimates, Vintage 2025',
         fontsize=9, color='#888888', style='italic')

plt.tight_layout()
plt.subplots_adjust(bottom=0.15, top=0.88)

# Save
plt.savefig(OUTPUT_DIR / "ca_ny_components_stacked.png", facecolor='#F6F7F3',
            bbox_inches='tight', dpi=150)
plt.savefig(OUTPUT_DIR / "ca_ny_components_stacked.svg", facecolor='#F6F7F3',
            bbox_inches='tight')
print(f"\nSaved to {OUTPUT_DIR / 'ca_ny_components_stacked.png'}")
