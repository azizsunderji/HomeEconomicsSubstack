"""
Option 2 (revised): Stacked area funnel chart — side by side, Boomers vs Millennials.
Stacking order (bottom to top):
  1. Married heads, own home (green)
  2. Married heads, renting (yellow)
  3. Single heads, own home (light green)
  4. Single heads, renting (light red)
  5. Non-heads / live with parents (cream)

Annotate conditional ownership rate among married heads at ages 30, 35, 40.
"""

import duckdb
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# ── Fonts ──
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG = '#F6F7F3'
GREEN = '#67A275'
LIGHT_GREEN = '#C6DCCB'
YELLOW = '#FEC439'
LIGHT_RED = '#FBCAB5'
RED = '#F4743B'
CREAM = '#DADFCE'

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
    -- 1. Married heads who own
    SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=1 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100
        AS married_owner,
    -- 2. Married heads who rent
    SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=0 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100
        AS married_renter,
    -- 3. Single heads who own
    SUM(CASE WHEN is_head=1 AND is_married=0 AND is_owner=1 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100
        AS single_owner,
    -- 4. Single heads who rent
    SUM(CASE WHEN is_head=1 AND is_married=0 AND is_owner=0 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100
        AS single_renter,
    -- 5. Non-heads
    SUM(CASE WHEN is_head=0 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100
        AS non_head
FROM persons WHERE generation IS NOT NULL
GROUP BY generation, AGE ORDER BY generation, AGE
""".format(data=DATA)

df = con.execute(q).df()

# Stack order: married_owner, married_renter, single_owner, single_renter, non_head
colors = [GREEN, YELLOW, LIGHT_GREEN, LIGHT_RED, CREAM]
labels = ['Married heads,\nown home', 'Married heads,\nrenting', 'Single heads,\nown home',
          'Single heads,\nrenting', 'Live with\nparents/friends']

fig, axes = plt.subplots(1, 2, figsize=(9, 7.5), dpi=100, sharey=True)
fig.patch.set_facecolor(BG)

for idx, (gen, ax, panel_title) in enumerate([
    ('Boomer', axes[0], 'Boomers'),
    ('Millennial', axes[1], 'Millennials')
]):
    ax.set_facecolor(BG)
    g = df[df['generation'] == gen].sort_values('AGE')
    ages = g['AGE'].values

    y1 = g['married_owner'].values
    y2 = g['married_renter'].values
    y3 = g['single_owner'].values
    y4 = g['single_renter'].values
    y5 = g['non_head'].values

    ax.stackplot(ages, y1, y2, y3, y4, y5,
                 colors=colors, labels=labels if idx == 0 else [None]*5,
                 alpha=0.85)

    # Annotate at key ages
    for age in [30, 35, 40]:
        row = g[g['AGE'] == age]
        if not row.empty:
            mo = row['married_owner'].values[0]
            mr = row['married_renter'].values[0]
            so = row['single_owner'].values[0]
            sr = row['single_renter'].values[0]
            nh = row['non_head'].values[0]

            total_own = mo + so
            married_total = mo + mr
            cond_rate = mo / married_total * 100 if married_total > 0 else 0

            # Vertical guide
            ax.axvline(x=age, color=BLACK, linestyle=':', linewidth=0.6, alpha=0.2)

            # ── Annotation 1: total ownership % in the green zone ──
            ax.annotate(f'{total_own:.0f}%\nown',
                        xy=(age, total_own / 2),
                        fontsize=8, fontweight='bold', color='white',
                        ha='center', va='center', zorder=5)

            # ── Annotation 2: conditional rate — bracket spanning married band ──
            # Draw a small bracket on the right side of the married band
            bracket_x = age + 1.2
            y_bottom = 0
            y_top = married_total
            y_mid = married_total / 2

            # Bracket lines
            ax.plot([bracket_x - 0.3, bracket_x], [y_bottom + 0.5, y_bottom + 0.5],
                    color=BLACK, linewidth=0.8, alpha=0.6, zorder=5, clip_on=False)
            ax.plot([bracket_x, bracket_x], [y_bottom + 0.5, y_top - 0.5],
                    color=BLACK, linewidth=0.8, alpha=0.6, zorder=5, clip_on=False)
            ax.plot([bracket_x - 0.3, bracket_x], [y_top - 0.5, y_top - 0.5],
                    color=BLACK, linewidth=0.8, alpha=0.6, zorder=5, clip_on=False)

            # Conditional rate label
            ax.annotate(f'{cond_rate:.0f}%\nown',
                        xy=(bracket_x + 0.3, y_mid),
                        fontsize=7, color=BLACK, alpha=0.7,
                        ha='left', va='center', zorder=5)

            # ── Annotation 3: non-head % at top ──
            if nh > 12:  # only label if big enough to read
                y_nh_mid = 100 - nh / 2
                ax.annotate(f'{nh:.0f}%',
                            xy=(age, y_nh_mid),
                            fontsize=8, fontweight='bold', color=BLACK, alpha=0.5,
                            ha='center', va='center', zorder=5)

    ax.set_xlim(20, 45)
    ax.set_ylim(0, 100)
    ax.set_xlabel('Age', fontsize=10, color=BLACK)
    ax.set_title(panel_title, fontsize=14, fontweight='bold', color=BLACK, pad=10)

    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', length=4, color=BLACK)
    ax.tick_params(colors=BLACK, labelsize=9)

    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(BLACK)

# Y-axis label on left panel only
yticks = [0, 20, 40, 60, 80, 100]
axes[0].set_yticks(yticks)
ylabels = [f'{int(t)}' for t in yticks]
ylabels[-1] = '100%'
axes[0].set_yticklabels(ylabels)

# Suptitle
fig.suptitle('Path to homeownership by age', fontsize=16, fontweight='bold',
             color=BLACK, x=0.08, ha='left', y=0.98)
fig.text(0.08, 0.935, 'How each generation splits into household status and tenure',
         fontsize=11, color=BLACK, alpha=0.6)

# Legend at bottom
handles, lbls = axes[0].get_legend_handles_labels()
fig.legend(handles, lbls, loc='lower center', ncol=5, frameon=False,
           fontsize=8, labelcolor=BLACK, bbox_to_anchor=(0.5, -0.02))

fig.text(0.08, 0.02, 'Source: CPS ASEC via IPUMS (1976\u20132025, excluding 2014)',
         fontsize=8, color=BLACK, alpha=0.5, style='italic')

plt.tight_layout(rect=[0, 0.10, 1, 0.92])

fig.savefig(f'{OUT}/option2_stacked_area.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.rcParams['svg.fonttype'] = 'none'
fig.savefig(f'{OUT}/option2_stacked_area.svg', bbox_inches='tight', facecolor=BG)
plt.close()
print("Saved option2_stacked_area")
