"""
More granular occupation analysis for Bay Area counties
Focus on Computer/Mathematical occupations specifically
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D

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
GREEN = '#67A275'
YELLOW = '#FEC439'

# Occupation data from ACS 2023
# S2401_C01_001E - Total employed
# S2401_C01_006E - Computer, engineering, and science occupations (total)
# S2401_C01_007E - Computer and mathematical occupations
# S2401_C01_008E - Architecture and engineering occupations
# S2401_C01_009E - Life, physical, and social science occupations

occupation_data = [
    {"county": "Alameda", "fips": 6001, "total_emp": 850555, "comp_eng_sci": 143643, "computer_math": 82114, "arch_eng": 36882, "life_phys_sci": 24647},
    {"county": "Contra Costa", "fips": 6013, "total_emp": 578596, "comp_eng_sci": 62135, "computer_math": 34735, "arch_eng": 17633, "life_phys_sci": 9767},
    {"county": "Marin", "fips": 6041, "total_emp": 122942, "comp_eng_sci": 11049, "computer_math": 6214, "arch_eng": 2414, "life_phys_sci": 2421},
    {"county": "Napa", "fips": 6055, "total_emp": 70166, "comp_eng_sci": 3745, "computer_math": 1656, "arch_eng": 1071, "life_phys_sci": 1018},
    {"county": "San Francisco", "fips": 6075, "total_emp": 469220, "comp_eng_sci": 79646, "computer_math": 50522, "arch_eng": 14737, "life_phys_sci": 14387},
    {"county": "San Mateo", "fips": 6081, "total_emp": 386517, "comp_eng_sci": 56607, "computer_math": 30830, "arch_eng": 12141, "life_phys_sci": 13636},
    {"county": "Santa Clara", "fips": 6085, "total_emp": 1011709, "comp_eng_sci": 246259, "computer_math": 144198, "arch_eng": 80862, "life_phys_sci": 21199},
    {"county": "Santa Cruz", "fips": 6087, "total_emp": 130190, "comp_eng_sci": 10333, "computer_math": 4864, "arch_eng": 2477, "life_phys_sci": 2992},
    {"county": "Solano", "fips": 6095, "total_emp": 210417, "comp_eng_sci": 12735, "computer_math": 6166, "arch_eng": 4317, "life_phys_sci": 2252},
    {"county": "Sonoma", "fips": 6097, "total_emp": 251796, "comp_eng_sci": 16010, "computer_math": 6869, "arch_eng": 5531, "life_phys_sci": 3610},
]

# Industry data (Information sector)
industry_data = {
    6001: 32259,  # Alameda
    6013: 11761,  # Contra Costa
    6041: 5183,   # Marin
    6055: 769,    # Napa
    6075: 29589,  # San Francisco
    6081: 17710,  # San Mateo
    6085: 64861,  # Santa Clara
    6087: 2701,   # Santa Cruz
    6095: 3483,   # Solano
    6097: 4973,   # Sonoma
}

# Population data
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

# Create dataframe
df = pd.DataFrame(occupation_data)

# Calculate percentages
df['computer_math_pct'] = df['computer_math'] / df['total_emp'] * 100
df['arch_eng_pct'] = df['arch_eng'] / df['total_emp'] * 100
df['life_phys_sci_pct'] = df['life_phys_sci'] / df['total_emp'] * 100
df['comp_eng_sci_pct'] = df['comp_eng_sci'] / df['total_emp'] * 100

# Add Information sector
df['info_emp'] = df['fips'].map(industry_data)
df['info_pct'] = df['info_emp'] / df['total_emp'] * 100

# Add population
df['population'] = df['fips'].map(pop_data)

# Add labels
df['label'] = df['county'].map(city_labels)

# Load price data
price_df = pd.read_csv('/Users/azizsunderji/Dropbox/Home Economics/Explorations/data/bay_area_price_changes.csv')
price_df['fips'] = price_df['fips'].astype(str).str.zfill(5).astype(int)
df = df.merge(price_df[['fips', 'change_6mo_pct', 'change_12mo_pct', 'current_price']], on='fips')

# Print detailed breakdown
print("=" * 80)
print("DETAILED OCCUPATION BREAKDOWN BY COUNTY")
print("=" * 80)
print(f"\n{'County':15} {'Comp/Math':>10} {'Arch/Eng':>10} {'Info Ind':>10} {'6mo Δ':>10}")
print("-" * 60)
for _, row in df.sort_values('computer_math_pct', ascending=False).iterrows():
    print(f"{row['county']:15} {row['computer_math_pct']:9.1f}% {row['arch_eng_pct']:9.1f}% {row['info_pct']:9.1f}% {row['change_6mo_pct']:+9.1f}%")

# Correlation analysis
print("\n" + "=" * 80)
print("CORRELATION WITH 6-MONTH PRICE CHANGE")
print("=" * 80)
print(f"  Computer/Mathematical occupations:  r = {df['computer_math_pct'].corr(df['change_6mo_pct']):.3f}")
print(f"  Architecture/Engineering:           r = {df['arch_eng_pct'].corr(df['change_6mo_pct']):.3f}")
print(f"  Information sector (industry):      r = {df['info_pct'].corr(df['change_6mo_pct']):.3f}")
print(f"  Comp/Eng/Sci (combined):            r = {df['comp_eng_sci_pct'].corr(df['change_6mo_pct']):.3f}")

# Create scatter plot using Computer/Math occupations
fig, ax = plt.subplots(figsize=(9, 7.5))
fig.patch.set_facecolor(BG_CREAM)
ax.set_facecolor(BG_CREAM)

# Scale bubble sizes
min_pop, max_pop = df['population'].min(), df['population'].max()
bubble_sizes = 800 + (df['population'] - min_pop) / (max_pop - min_pop) * 3200

# Plot bubbles
scatter = ax.scatter(
    df['computer_math_pct'],
    df['change_6mo_pct'],
    s=bubble_sizes,
    c=BLUE,
    alpha=1.0,
    edgecolors=BLACK,
    linewidth=2.5,
    zorder=5
)

# Add labels with smart positioning
label_offsets = {
    'San Francisco': (2.5, 0.0),
    'Santa Clara': (3.0, 0.3),
    'Marin': (-4, 0.8),
    'San Mateo': (2.5, -0.5),
    'Alameda': (2.5, -0.4),
    'Contra Costa': (2.5, 0.4),
    'Santa Cruz': (1.5, 0.4),
    'Sonoma': (1.5, 0.4),
    'Napa': (1.5, 0.4),
    'Solano': (1.5, 0.4),
}

for _, row in df.iterrows():
    offset = label_offsets.get(row['county'], (1.0, 0.2))
    ha = 'left' if offset[0] > 0 else 'right'
    ax.annotate(
        row['label'],
        xy=(row['computer_math_pct'], row['change_6mo_pct']),
        xytext=(row['computer_math_pct'] + offset[0], row['change_6mo_pct'] + offset[1]),
        fontsize=9,
        color=BLACK,
        ha=ha,
        va='center',
        zorder=10,
        arrowprops=dict(arrowstyle='-', color='#666666', lw=0.8, zorder=10) if abs(offset[0]) > 2 or abs(offset[1]) > 0.5 else None
    )

# Add trend line
z = np.polyfit(df['computer_math_pct'], df['change_6mo_pct'], 1)
p = np.poly1d(z)
x_line = np.linspace(df['computer_math_pct'].min() - 1, df['computer_math_pct'].max() + 1, 100)
corr = df['computer_math_pct'].corr(df['change_6mo_pct'])
ax.plot(x_line, p(x_line), '--', color=RED, alpha=0.7, linewidth=2, label=f'Trend (r={corr:.2f})')

# Zero line
ax.axhline(y=0, color=BLACK, linewidth=0.8, alpha=0.4)

# Styling
ax.set_xlabel('Computer & Mathematical Occupations (%)\n(Software developers, data scientists, IT, etc.)', fontsize=11, color=BLACK)
ax.set_ylabel('Home Price Change, June–Dec 2025 (%)', fontsize=11, color=BLACK)
ax.set_title('Bay Area: Software/Tech Jobs vs Home Price Change', fontsize=14, fontweight='bold', color=BLACK, pad=15)

# Grid
ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
ax.set_axisbelow(True)

# Spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.tick_params(colors=BLACK)

# Set axis limits
ax.set_xlim(0, 18)
ax.set_ylim(-3.5, 4.2)

# Add legends
leg1 = ax.legend(loc='lower right', frameon=False, fontsize=10)

# Population legend
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

# Source
ax.text(0.01, -0.12, 'Source: Zillow ZHVI (Dec 2025), ACS 2023 1-Year Estimates (S2401: Occupation by Sex)',
        transform=ax.transAxes, fontsize=8, color='#888888', style='italic')

plt.tight_layout()
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/bay_area_computer_jobs_vs_prices.png',
            dpi=100, bbox_inches='tight', facecolor=BG_CREAM)
plt.savefig('/Users/azizsunderji/Dropbox/Home Economics/Explorations/outputs/bay_area_computer_jobs_vs_prices.svg',
            bbox_inches='tight', facecolor=BG_CREAM)
print("\n\nChart saved to outputs/bay_area_computer_jobs_vs_prices.png")

# Save data
df.to_csv('/Users/azizsunderji/Dropbox/Home Economics/Explorations/data/bay_area_detailed_occupations.csv', index=False)
print("Data saved to data/bay_area_detailed_occupations.csv")
