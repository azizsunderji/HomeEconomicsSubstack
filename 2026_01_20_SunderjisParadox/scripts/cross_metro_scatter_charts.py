"""
Cross-metro scatter plots: ZORI rent change (2022->2024) vs ACS renter outcomes.
Four charts:
  1. Δ Mover rate vs rent change
  2. Δ Avg bedrooms (movers) vs rent change
  3. Δ Mover median burden vs rent change
  4. Δ Commute time (movers) vs rent change
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from scipy import stats

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
YELLOW = '#FEC439'
LIGHT_RED = '#FBCAB5'

# === Load data ===
df = pd.read_csv('data/metro_year_panel.csv')
print(f"Loaded {len(df)} metros")

# Label key metros
LABEL_METROS = {
    12420: 'Austin',
    19100: 'Dallas',
    26420: 'Houston',
    35620: 'New York',
    33100: 'Miami',
    41860: 'San Francisco',
    38060: 'Phoenix',
    14460: 'Boston',
    31080: 'Los Angeles',
    42660: 'Seattle',
    16980: 'Chicago',
    12060: 'Atlanta',
}

def make_scatter(ax, x, y, df, xlabel, ylabel, title, subtitle):
    """Make a single scatter plot with fit line."""
    # All dots in light grey
    ax.scatter(x, y, s=40, color='#CCCCCC', alpha=0.6, edgecolors='white', linewidth=0.5, zorder=2)

    # Highlight Austin in blue
    austin = df[df['MET2013'] == 12420]
    if len(austin) > 0:
        ax.scatter(austin[x.name].values if hasattr(x, 'name') else [x[austin.index[0]]],
                   austin[y.name].values if hasattr(y, 'name') else [y[austin.index[0]]],
                   s=120, color=BLUE, edgecolors='white', linewidth=1.5, zorder=5)

    # Fit line
    mask = ~(np.isnan(x) | np.isnan(y))
    slope, intercept, r_value, p_value, std_err = stats.linregress(x[mask], y[mask])
    x_line = np.linspace(x[mask].min(), x[mask].max(), 100)
    y_line = slope * x_line + intercept
    ax.plot(x_line, y_line, color=RED, linewidth=2, alpha=0.8, zorder=3)

    # R² annotation
    r2_text = f"R² = {r_value**2:.3f}"
    slope_text = f"slope = {slope:.3f}"
    if p_value < 0.001:
        p_text = "p < 0.001"
    elif p_value < 0.01:
        p_text = f"p = {p_value:.3f}"
    elif p_value < 0.05:
        p_text = f"p = {p_value:.2f}"
    else:
        p_text = f"p = {p_value:.2f} (n.s.)"

    ax.text(0.03, 0.97, f"{r2_text}\n{slope_text}\n{p_text}",
            transform=ax.transAxes, va='top', ha='left',
            fontsize=10, color=BLACK, fontstyle='italic',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none'))

    # Label key metros
    for idx, row in df.iterrows():
        met = row['MET2013']
        if met in LABEL_METROS:
            x_val = row[x.name] if hasattr(x, 'name') else x[idx]
            y_val = row[y.name] if hasattr(y, 'name') else y[idx]
            label = LABEL_METROS[met]
            fontweight = 'bold' if met == 12420 else 'normal'
            color = BLUE if met == 12420 else BLACK
            ax.annotate(label, (x_val, y_val), fontsize=8, fontweight=fontweight,
                       color=color, textcoords='offset points', xytext=(6, 4),
                       zorder=6)

    # Zero lines
    ax.axhline(0, color=BLACK, linewidth=0.5, alpha=0.3, zorder=1)
    ax.axvline(0, color=BLACK, linewidth=0.5, alpha=0.3, zorder=1)

    # Styling
    ax.set_facecolor(CREAM_BG)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='y', color='white', linewidth=0.8, alpha=0.8)
    ax.set_xlabel(xlabel, fontsize=11, color=BLACK)
    ax.set_ylabel(ylabel, fontsize=11, color=BLACK)

    # Title
    ax.set_title(title, fontsize=14, fontweight='bold', color=BLACK, pad=30, loc='left')
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=10, color='#888888',
            va='bottom', ha='left')

    return slope, r_value**2, p_value


# === Chart 1: Δ Mover Rate vs Rent Change ===
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(CREAM_BG)

slope, r2, p = make_scatter(
    ax, df['zori_pct_change_2022_2024'], df['delta_mover_rate'], df,
    xlabel='ZORI Rent Change, 2022 → 2024 (%)',
    ylabel='Change in Mover Rate (pp)',
    title='Do Falling Rents Cause More Moving?',
    subtitle='Change in renter mobility rate vs. rent growth, 99 large metros'
)

ax.text(0.5, -0.1, 'Source: ACS 1-Year PUMS (2022, 2024), Zillow ZORI',
        transform=ax.transAxes, fontsize=8, color='#999999', fontstyle='italic', ha='center')

plt.tight_layout()
plt.savefig('outputs/scatter_mover_rate_vs_rent_change.png', dpi=150, bbox_inches='tight', facecolor=CREAM_BG)
plt.rcParams['svg.fonttype'] = 'none'
plt.savefig('outputs/scatter_mover_rate_vs_rent_change.svg', bbox_inches='tight', facecolor=CREAM_BG)
plt.close()
print(f"Chart 1: Mover rate — slope={slope:.3f}, R²={r2:.3f}, p={p:.4f}")


# === Chart 2: Δ Avg Bedrooms (Movers) vs Rent Change ===
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(CREAM_BG)

slope, r2, p = make_scatter(
    ax, df['zori_pct_change_2022_2024'], df['delta_mover_avg_bed'], df,
    xlabel='ZORI Rent Change, 2022 → 2024 (%)',
    ylabel='Change in Avg Bedrooms (Movers)',
    title='Do Falling Rents Lead to Bigger Units?',
    subtitle='Change in average bedrooms for movers vs. rent growth, 99 large metros'
)

ax.text(0.5, -0.1, 'Source: ACS 1-Year PUMS (2022, 2024), Zillow ZORI',
        transform=ax.transAxes, fontsize=8, color='#999999', fontstyle='italic', ha='center')

plt.tight_layout()
plt.savefig('outputs/scatter_bedrooms_vs_rent_change.png', dpi=150, bbox_inches='tight', facecolor=CREAM_BG)
plt.rcParams['svg.fonttype'] = 'none'
plt.savefig('outputs/scatter_bedrooms_vs_rent_change.svg', bbox_inches='tight', facecolor=CREAM_BG)
plt.close()
print(f"Chart 2: Bedrooms — slope={slope:.3f}, R²={r2:.3f}, p={p:.4f}")


# === Chart 3: Δ Mover Burden vs Rent Change ===
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(CREAM_BG)

slope, r2, p = make_scatter(
    ax, df['zori_pct_change_2022_2024'], df['delta_mover_burden'], df,
    xlabel='ZORI Rent Change, 2022 → 2024 (%)',
    ylabel='Change in Mover Median Burden (pp)',
    title='Do Movers Always Reset to ~30%?',
    subtitle='Change in mover median rent-to-income ratio vs. rent growth, 99 large metros'
)

ax.text(0.5, -0.1, 'Source: ACS 1-Year PUMS (2022, 2024), Zillow ZORI',
        transform=ax.transAxes, fontsize=8, color='#999999', fontstyle='italic', ha='center')

plt.tight_layout()
plt.savefig('outputs/scatter_burden_vs_rent_change.png', dpi=150, bbox_inches='tight', facecolor=CREAM_BG)
plt.rcParams['svg.fonttype'] = 'none'
plt.savefig('outputs/scatter_burden_vs_rent_change.svg', bbox_inches='tight', facecolor=CREAM_BG)
plt.close()
print(f"Chart 3: Burden — slope={slope:.3f}, R²={r2:.3f}, p={p:.4f}")


# === Chart 4: Δ Commute Time (Movers) vs Rent Change ===
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(CREAM_BG)

# Filter out NaN commute times
df_commute = df.dropna(subset=['delta_mover_trantime']).copy()
print(f"Metros with valid commute data: {len(df_commute)}")

slope, r2, p = make_scatter(
    ax, df_commute['zori_pct_change_2022_2024'], df_commute['delta_mover_trantime'], df_commute,
    xlabel='ZORI Rent Change, 2022 → 2024 (%)',
    ylabel='Change in Mover Avg Commute (min)',
    title='Do Falling Rents Buy Shorter Commutes?',
    subtitle='Change in mover average commute time vs. rent growth, large metros'
)

ax.text(0.5, -0.1, 'Source: ACS 1-Year PUMS (2022, 2024), Zillow ZORI',
        transform=ax.transAxes, fontsize=8, color='#999999', fontstyle='italic', ha='center')

plt.tight_layout()
plt.savefig('outputs/scatter_commute_vs_rent_change.png', dpi=150, bbox_inches='tight', facecolor=CREAM_BG)
plt.rcParams['svg.fonttype'] = 'none'
plt.savefig('outputs/scatter_commute_vs_rent_change.svg', bbox_inches='tight', facecolor=CREAM_BG)
plt.close()
print(f"Chart 4: Commute — slope={slope:.3f}, R²={r2:.3f}, p={p:.4f}")

print("\nAll scatter charts saved to outputs/")
