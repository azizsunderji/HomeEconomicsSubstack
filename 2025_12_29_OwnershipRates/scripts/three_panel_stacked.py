"""
Three-panel stacked chart:
1. Homeownership by age (all people)
2. Married household heads as share of all people
3. Homeownership among married household heads

Shared y-axis max of 90%, vertical lines at 30/35/40 running through all panels,
x-axis labels only on top and bottom panels.
"""

import duckdb
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.gridspec as gridspec
import numpy as np

# ── Fonts ──
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG = '#F6F7F3'
BOOMER_COLOR = '#BBBFAE'

DATA = '/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec.parquet'
OUT = '/Users/azizsunderji/Dropbox/Home Economics/2025_12_29_OwnershipRates/2025_12_29_FirstApproach/outputs'

con = duckdb.connect()

q = """
WITH persons AS (
    SELECT *,
        CASE WHEN (YEAR-AGE) BETWEEN 1946 AND 1964 THEN 'Boomer'
             WHEN (YEAR-AGE) BETWEEN 1981 AND 1996 THEN 'Millennial' END AS generation,
        CASE WHEN RELATE IN (101, 201, 202, 203) THEN 1 ELSE 0 END AS is_head,
        CASE WHEN MARST IN (1, 2) OR RELATE IN (201, 202, 203) THEN 1 ELSE 0 END AS is_married,
        CASE WHEN OWNERSHP = 10 THEN 1 ELSE 0 END AS is_owner
    FROM '{data}'
    WHERE AGE BETWEEN 20 AND 45
      AND YEAR != 2014
      AND ((YEAR-AGE) BETWEEN 1946 AND 1996)
)
SELECT generation, AGE,
    -- Chart 1: overall ownership (head/spouse in owned unit)
    SUM(CASE WHEN is_head=1 AND is_owner=1 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100
        AS overall_ownership,
    -- Chart 2: married head rate (of all people)
    SUM(CASE WHEN is_head=1 AND is_married=1 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100
        AS married_head_rate,
    -- Chart 3: ownership among married heads
    SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=1 THEN ASECWT ELSE 0 END) /
        NULLIF(SUM(CASE WHEN is_head=1 AND is_married=1 THEN ASECWT ELSE 0 END), 0) * 100
        AS ownership_married_heads
FROM persons WHERE generation IS NOT NULL
GROUP BY generation, AGE ORDER BY generation, AGE
""".format(data=DATA)

df = con.execute(q).df()

# ── Build figure ──
fig = plt.figure(figsize=(12, 24), dpi=100)
gs = fig.add_gridspec(3, 1, hspace=0.15)
axes = [fig.add_subplot(gs[i]) for i in range(3)]
fig.patch.set_facecolor(BG)

charts = [
    ('overall_ownership', 'Homeownership rate by age',
     'Share of all people who own or co-own their home'),
    ('married_head_rate', 'Married household heads as share of all people',
     'Includes spouses/partners of household heads'),
    ('ownership_married_heads', 'Homeownership among married household heads',
     'Share of married/partnered heads who own their home'),
]

for i, (col, title, subtitle) in enumerate(charts):
    ax = axes[i]
    ax.set_facecolor(BG)

    # Plot lines
    for gen, color, label in [('Boomer', BOOMER_COLOR, 'Boomers'),
                               ('Millennial', BLUE, 'Millennials')]:
        g = df[df['generation'] == gen].sort_values('AGE')
        ax.plot(g['AGE'], g[col], color=color, linewidth=3.0, label=label, zorder=3)

    # Vertical lines at 30, 35, 40 with gap annotations
    for age in [30, 35, 40]:
        # Full-height vertical line
        ax.axvline(x=age, color=BLACK, linestyle=':', linewidth=0.8, alpha=0.25, zorder=1)

        boomer_val = df[(df['generation'] == 'Boomer') & (df['AGE'] == age)][col].values
        mill_val = df[(df['generation'] == 'Millennial') & (df['AGE'] == age)][col].values

        if len(boomer_val) > 0 and len(mill_val) > 0:
            bv = boomer_val[0]
            mv = mill_val[0]
            gap = bv - mv

            # Dots on lines
            ax.plot(age, bv, 'o', color=BOOMER_COLOR, markersize=6, zorder=4,
                    markeredgecolor='white', markeredgewidth=1.5)
            ax.plot(age, mv, 'o', color=BLUE, markersize=6, zorder=4,
                    markeredgecolor='white', markeredgewidth=1.5)

            # Vertical gap line between the two values
            ax.plot([age, age], [mv + 1, bv - 1], color=BLACK, linewidth=1.8,
                    alpha=0.35, zorder=2)

            # Gap label — centered on gap line, offset to right
            mid = (bv + mv) / 2
            ax.annotate(f'{gap:.0f}pp',
                        xy=(age, mid), xytext=(12, 0),
                        textcoords='offset points',
                        fontsize=10, fontweight='bold', color=BLACK, alpha=0.65,
                        ha='left', va='center', zorder=5)

            # Boomer value — above and to the left
            ax.annotate(f'{bv:.0f}%',
                        xy=(age, bv), xytext=(-10, 10),
                        textcoords='offset points',
                        fontsize=10, color=BOOMER_COLOR, fontweight='bold',
                        ha='right', va='bottom', zorder=5)

            # Millennial value — below and to the left
            ax.annotate(f'{mv:.0f}%',
                        xy=(age, mv), xytext=(-10, -10),
                        textcoords='offset points',
                        fontsize=10, color=BLUE, fontweight='bold',
                        ha='right', va='top', zorder=5)

    # Y-axis
    ax.set_ylim(0, 90)
    yticks = [0, 20, 40, 60, 80]
    ax.set_yticks(yticks)
    ylabels = [f'{int(t)}' for t in yticks]
    ylabels[-1] = f'{int(yticks[-1])}%'
    ax.set_yticklabels(ylabels)

    ax.set_xlim(20, 40)

    # Tick styling
    ax.tick_params(axis='y', length=0)
    ax.tick_params(colors=BLACK, labelsize=10)

    # Gridlines
    ax.yaxis.grid(True, color='white', linewidth=0.8)
    ax.xaxis.grid(False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(BLACK)

    # Title and subtitle — left-aligned inside each panel
    ax.set_title(title, fontsize=15, fontweight='bold', color=BLACK,
                 loc='left', pad=30)
    ax.text(0.0, 1.06, subtitle, transform=ax.transAxes,
            fontsize=11, color=BLACK, alpha=0.6)

    # X-axis: only show tick labels on top and bottom panels
    ax.set_xticks([20, 25, 30, 35, 40])
    if i == 1:  # middle panel
        ax.tick_params(axis='x', labelbottom=False, labeltop=False, length=0,
                       bottom=False, top=False)
        ax.spines['bottom'].set_visible(False)
    elif i == 0:  # top panel — show labels on top
        ax.tick_params(axis='x', labelbottom=False, labeltop=True, length=4,
                       top=True, bottom=False, color=BLACK)
        ax.spines['bottom'].set_visible(False)
        ax.xaxis.set_label_position('top')
        ax.set_xlabel('Age', fontsize=12, color=BLACK)
    else:  # bottom panel
        ax.tick_params(axis='x', length=4, color=BLACK)
        ax.set_xlabel('Age', fontsize=12, color=BLACK)

    # Legend — only on top panel
    if i == 0:
        ax.legend(fontsize=10, loc='lower right', frameon=False,
                  labelcolor=[BOOMER_COLOR, BLUE])

# Source
fig.text(0.08, 0.005, 'Source: CPS ASEC via IPUMS (1976\u20132025, excluding 2014)',
         fontsize=8, color=BLACK, alpha=0.5, style='italic')

# No tight_layout — gridspec handles spacing

fig.savefig(f'{OUT}/three_panel_stacked.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.rcParams['svg.fonttype'] = 'none'
fig.savefig(f'{OUT}/three_panel_stacked.svg', bbox_inches='tight', facecolor=BG)
plt.close()
print("Saved three_panel_stacked")
