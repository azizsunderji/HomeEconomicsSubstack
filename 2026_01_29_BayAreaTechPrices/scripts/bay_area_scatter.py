"""
Scatter plot: 6-month price change vs tech share
Bubble size = population
Labels include major cities
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

# Colors
BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
RED = '#F4743B'

# Load combined data
df = pd.read_csv('/Users/azizsunderji/Dropbox/Home Economics/Explorations/data/bay_area_combined_analysis.csv')

# Population data (FIPS as integers to match CSV)
pop_data = {
    6001: 1622188,
    6013: 1155025,
    6041: 254407,
    6055: 133216,
    6075: 808988,
    6081: 726353,
    6085: 1877592,
    6087: 261547,
    6095: 449218,
    6097: 481812,
}

# Major cities mapping
city_labels = {
    'Alameda': 'Alameda\n(Oakland, Berkeley)',
    'Contra Costa': 'Contra Costa\n(Walnut Creek, Richmond)',
    'Marin': 'Marin\n(Sausalito, Mill Valley)',
    'Napa': 'Napa\n(Wine Country)',
    'San Francisco': 'San Francisco',
    'San Mateo': 'San Mateo\n(Redwood City, Daly City)',
    'Santa Clara': 'Santa Clara\n(San Jose, Palo Alto, Cupertino)',
    'Santa Cruz': 'Santa Cruz',
    'Solano': 'Solano\n(Vallejo, Fairfield)',
    'Sonoma': 'Sonoma\n(Santa Rosa)',
}

# Add population to dataframe
df['population'] = df['fips'].map(pop_data)
df['label'] = df['county'].map(city_labels)

# Create figure
fig, ax = plt.subplots(figsize=(9, 7.5))
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Scale bubble sizes (sqrt scaling for area perception)
min_pop, max_pop = df['population'].min(), df['population'].max()
# Scale to range ~800 to ~4000 for visibility
bubble_sizes = 800 + (df['population'] - min_pop) / (max_pop - min_pop) * 3200

# Plot bubbles
scatter = ax.scatter(
    df['tech_pct'],
    df['change_6mo_pct'],
    s=bubble_sizes,
    c=BLUE,
    alpha=1.0,
    edgecolors=BLACK,
    linewidth=2.5,
    zorder=5
)

# Add labels with smart positioning (adjusted for bubble sizes)
label_offsets = {
    'San Francisco': (3.5, 0.0),
    'Santa Clara': (4.0, 0.3),
    'Marin': (-10, 0.3),
    'San Mateo': (3.5, -0.5),
    'Alameda': (3.5, -0.4),
    'Contra Costa': (3.5, 0.4),
    'Santa Cruz': (2.0, 0.4),
    'Sonoma': (2.5, 0.4),
    'Napa': (2.5, 0.4),
    'Solano': (2.0, 0.4),
}

for _, row in df.iterrows():
    offset = label_offsets.get(row['county'], (1.0, 0.2))
    # Align left if offset is positive, right if negative
    ha = 'left' if offset[0] > 0 else 'right'
    ax.annotate(
        row['label'],
        xy=(row['tech_pct'], row['change_6mo_pct']),
        xytext=(row['tech_pct'] + offset[0], row['change_6mo_pct'] + offset[1]),
        fontsize=9,
        color=BLACK,
        ha=ha,
        va='center',
        zorder=10,
        arrowprops=dict(arrowstyle='-', color='#666666', lw=0.8, zorder=10) if abs(offset[0]) > 1.2 or abs(offset[1]) > 0.5 else None
    )

# Add trend line
z = np.polyfit(df['tech_pct'], df['change_6mo_pct'], 1)
p = np.poly1d(z)
x_line = np.linspace(df['tech_pct'].min() - 2, df['tech_pct'].max() + 2, 100)
ax.plot(x_line, p(x_line), '--', color=RED, alpha=0.7, linewidth=2, label=f'Trend (r={df["tech_pct"].corr(df["change_6mo_pct"]):.2f})')

# Zero line
ax.axhline(y=0, color=BLACK, linewidth=0.8, alpha=0.4)

# Styling
ax.set_xlabel('Tech Employment Share (%)\n(Information + Professional/Scientific/Technical Services)', fontsize=11, color=BLACK)
ax.set_ylabel('Home Price Change, June–Dec 2025 (%)', fontsize=11, color=BLACK)
ax.set_title('Bay Area: Tech Concentration vs Home Price Change', fontsize=14, fontweight='bold', color=BLACK, pad=15)

# Grid
ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
ax.set_axisbelow(True)

# Remove top/right spines, keep left spine hidden for gridline extension
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(colors=BLACK)

# Set axis limits with padding
ax.set_xlim(2, 36)
ax.set_ylim(-3.5, 4.2)

# Add legend for trend line
leg1 = ax.legend(loc='lower right', frameon=False, fontsize=10)

# Add bubble size legend using scatter handles
from matplotlib.lines import Line2D
legend_pops = [250000, 1000000, 1800000]
legend_labels = ['250k', '1M', '1.8M']
legend_handles = []
for pop in legend_pops:
    size = 800 + (pop - min_pop) / (max_pop - min_pop) * 3200
    handle = Line2D([0], [0], marker='o', color='w', markerfacecolor=BLUE,
                    markersize=np.sqrt(size)/2.5, alpha=1.0, markeredgecolor=BLACK, markeredgewidth=2)
    legend_handles.append(handle)

leg2 = ax.legend(legend_handles, legend_labels, title='Population', loc='upper left',
                 frameon=False, fontsize=9, title_fontsize=9, labelspacing=1.2)
ax.add_artist(leg1)  # Add back the trend line legend

# Source
ax.text(0.01, -0.12, 'Source: Zillow ZHVI (Dec 2025), ACS 2023 1-Year Estimates',
        transform=ax.transAxes, fontsize=8, color='#888888', style='italic')

plt.tight_layout()
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/bay_area_tech_vs_prices_scatter.png',
            dpi=100, bbox_inches='tight', facecolor=BG_CREAM)
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/bay_area_tech_vs_prices_scatter.svg',
            bbox_inches='tight', facecolor=BG_CREAM)
print("Saved to outputs/bay_area_tech_vs_prices_scatter.png and .svg")
