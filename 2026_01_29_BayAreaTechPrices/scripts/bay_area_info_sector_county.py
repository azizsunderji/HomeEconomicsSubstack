"""
County-level chart using Information sector only
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG_CREAM = '#F6F7F3'
RED = '#F4743B'

# Load detailed occupation data which has info_pct
df = pd.read_csv('/Users/azizsunderji/Dropbox/Home Economics/Explorations/data/bay_area_detailed_occupations.csv')

# City labels
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
df['label'] = df['county'].map(city_labels)

# Correlation
corr = df['info_pct'].corr(df['change_6mo_pct'])
print(f"Correlation (Info sector vs 6-mo price change): r = {corr:.3f}")

print("\nRanked by Information sector:")
print(f"{'County':15} {'Info%':>8} {'6mo Δ':>10}")
print("-" * 35)
for _, row in df.sort_values('info_pct', ascending=False).iterrows():
    print(f"{row['county']:15} {row['info_pct']:7.1f}% {row['change_6mo_pct']:+9.1f}%")

# Create scatter
fig, ax = plt.subplots(figsize=(9, 7.5))
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Population for bubble sizing
min_pop, max_pop = df['population'].min(), df['population'].max()
bubble_sizes = 800 + (df['population'] - min_pop) / (max_pop - min_pop) * 3200

scatter = ax.scatter(
    df['info_pct'],
    df['change_6mo_pct'],
    s=bubble_sizes,
    c=BLUE,
    alpha=1.0,
    edgecolors=BLACK,
    linewidth=2.5,
    zorder=5
)

# Labels
label_offsets = {
    'San Francisco': (0.8, 0.0),
    'Santa Clara': (0.8, 0.3),
    'Marin': (-2.5, 0.8),
    'San Mateo': (0.8, -0.5),
    'Alameda': (0.8, -0.4),
    'Contra Costa': (0.5, 0.4),
    'Santa Cruz': (0.5, 0.4),
    'Sonoma': (0.5, 0.4),
    'Napa': (0.3, 0.4),
    'Solano': (0.4, 0.4),
}

for _, row in df.iterrows():
    offset = label_offsets.get(row['county'], (0.5, 0.2))
    ha = 'left' if offset[0] > 0 else 'right'
    ax.annotate(
        row['label'],
        xy=(row['info_pct'], row['change_6mo_pct']),
        xytext=(row['info_pct'] + offset[0], row['change_6mo_pct'] + offset[1]),
        fontsize=9,
        color=BLACK,
        ha=ha,
        va='center',
        zorder=10,
        arrowprops=dict(arrowstyle='-', color='#666666', lw=0.8) if abs(offset[0]) > 0.6 or abs(offset[1]) > 0.5 else None
    )

# Trend line
z = np.polyfit(df['info_pct'], df['change_6mo_pct'], 1)
p = np.poly1d(z)
x_line = np.linspace(0, df['info_pct'].max() + 1, 100)
ax.plot(x_line, p(x_line), '--', color=RED, alpha=0.7, linewidth=2, label=f'Trend (r={corr:.2f})')

ax.axhline(y=0, color=BLACK, linewidth=0.8, alpha=0.4)

# Styling
ax.set_xlabel('Information Sector Employment (%)\n(Software, Internet, Media, Telecom)', fontsize=11, color=BLACK)
ax.set_ylabel('Home Price Change, June–Dec 2025 (%)', fontsize=11, color=BLACK)
ax.set_title('Bay Area Counties: Information Industry vs Home Prices', fontsize=14, fontweight='bold', color=BLACK, pad=15)

ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
ax.set_axisbelow(True)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(colors=BLACK)
ax.set_xlim(0, 8)
ax.set_ylim(-3.5, 4.2)

# Legends
leg1 = ax.legend(loc='lower right', frameon=False, fontsize=10)

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
ax.add_artist(leg1)

ax.text(0.01, -0.10, 'Source: Zillow ZHVI (Dec 2025), ACS 2023 1-Year Estimates',
        transform=ax.transAxes, fontsize=8, color='#888888', style='italic')

plt.tight_layout()
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/bay_area_info_sector_county.png',
            dpi=100, bbox_inches='tight', facecolor=BG_CREAM)
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/bay_area_info_sector_county.svg',
            bbox_inches='tight', facecolor=BG_CREAM)
print("\nChart saved to outputs/bay_area_info_sector_county.png")
