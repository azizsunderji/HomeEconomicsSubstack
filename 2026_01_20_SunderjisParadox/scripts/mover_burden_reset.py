"""
Mover burden reset analysis for Austin.
Key prediction: movers always reset to ~30% regardless of market conditions.
Non-movers drift below 30% as incomes rise. Movers reset upward when they move.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# === Font setup ===
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# === Colors ===
BLUE = '#0BB4FF'
BLACK = '#3D3733'
RED = '#F4743B'
CREAM_BG = '#F6F7F3'
GREEN = '#67A275'
LIGHT_RED = '#FBCAB5'
LIGHT_GREEN = '#C6DCCB'

# === Load data ===
df = pd.read_csv('data/austin_movers_vs_nonmovers.csv')

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(CREAM_BG)
ax.set_facecolor(CREAM_BG)

# Mover burden band
ax.fill_between(df['year'], df['mover_median_burden'] - 1, df['mover_median_burden'] + 1,
                color=LIGHT_RED, alpha=0.4, zorder=1)
ax.plot(df['year'], df['mover_median_burden'], color=RED, linewidth=2.5, marker='o',
        markersize=6, label='Movers', zorder=3)

# Non-mover burden band
ax.fill_between(df['year'], df['non_mover_median_burden'] - 1, df['non_mover_median_burden'] + 1,
                color=LIGHT_GREEN, alpha=0.4, zorder=1)
ax.plot(df['year'], df['non_mover_median_burden'], color=GREEN, linewidth=2.5, marker='s',
        markersize=6, label='Non-movers', zorder=3)

# 30% reference line
ax.axhline(30, color=BLACK, linewidth=1, linestyle='--', alpha=0.4, zorder=2)
ax.text(2024.3, 30, '30%', fontsize=9, color=BLACK, va='center', alpha=0.6)

# Rent decline shading
ax.axvspan(2022, 2024, alpha=0.08, color=BLUE, zorder=0)
ax.text(2023, ax.get_ylim()[1] - 0.5, 'Rent\ndecline', fontsize=8, color=BLUE,
        ha='center', va='top', alpha=0.7)

# Annotations
ax.annotate('Movers always reset\nto ~30% burden',
            xy=(2019, 30.0), xytext=(2013, 34),
            fontsize=9, color=RED,
            arrowprops=dict(arrowstyle='->', color=RED, lw=1.2),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'))

ax.annotate('Non-movers drift\nbelow 30%',
            xy=(2019, 26.9), xytext=(2013, 24),
            fontsize=9, color=GREEN,
            arrowprops=dict(arrowstyle='->', color=GREEN, lw=1.2),
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'))

# Summary stats
mover_mean = df['mover_median_burden'].mean()
mover_std = df['mover_median_burden'].std()
nonmover_mean = df['non_mover_median_burden'].mean()
nonmover_std = df['non_mover_median_burden'].std()
gap = mover_mean - nonmover_mean

stats_text = (f"Mover avg: {mover_mean:.1f}% (±{mover_std:.1f})\n"
              f"Non-mover avg: {nonmover_mean:.1f}% (±{nonmover_std:.1f})\n"
              f"Gap: {gap:+.1f} pp")
ax.text(0.97, 0.03, stats_text, transform=ax.transAxes, fontsize=9, color=BLACK,
        va='bottom', ha='right', fontstyle='italic',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.8, edgecolor='#CCCCCC'))

# Styling
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='y', length=0)
ax.grid(axis='y', color='white', linewidth=0.8)
ax.set_xlabel('', fontsize=10)
ax.set_ylabel('Median Rent-to-Income Ratio (%)', fontsize=11, color=BLACK)
ax.legend(frameon=False, fontsize=11, loc='upper left')

# Ensure full y range visible
ymin = min(df['non_mover_median_burden'].min(), df['mover_median_burden'].min()) - 2
ymax = max(df['non_mover_median_burden'].max(), df['mover_median_burden'].max()) + 2
ax.set_ylim(ymin, ymax)

# Title
ax.set_title('The Mover Reset: Austin Renter Burden', fontsize=14, fontweight='bold',
             color=BLACK, pad=30, loc='left')
ax.text(0, 1.02, 'Movers consistently pay 2-3 pp more than non-movers — they trade up to equilibrium',
        transform=ax.transAxes, fontsize=10, color='#888888', va='bottom')

ax.text(0.5, -0.08, 'Source: ACS 1-Year PUMS (2005-2024, excl. 2020)',
        transform=ax.transAxes, fontsize=8, color='#999999', fontstyle='italic', ha='center')

plt.tight_layout()
plt.savefig('outputs/mover_burden_reset.png', dpi=150, bbox_inches='tight', facecolor=CREAM_BG)
plt.rcParams['svg.fonttype'] = 'none'
plt.savefig('outputs/mover_burden_reset.svg', bbox_inches='tight', facecolor=CREAM_BG)
plt.close()
print("Saved mover_burden_reset.svg/png")
print(f"\nMover median burden range: {df['mover_median_burden'].min():.1f}% - {df['mover_median_burden'].max():.1f}%")
print(f"Non-mover median burden range: {df['non_mover_median_burden'].min():.1f}% - {df['non_mover_median_burden'].max():.1f}%")
print(f"Average gap: {gap:.1f} pp (movers higher)")
