"""
Option 3: Gap chart — single chart showing the Boomer-Millennial gap (in pp)
for three metrics by age.
"""

import duckdb
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

BLUE = '#0BB4FF'
BLACK = '#3D3733'
BG = '#F6F7F3'
RED = '#F4743B'
GREEN = '#67A275'
YELLOW = '#FEC439'

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
    -- Overall ownership (head/spouse in owned unit)
    SUM(CASE WHEN is_head=1 AND is_owner=1 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100
        AS overall_ownership,
    -- Married head rate (of all people)
    SUM(CASE WHEN is_head=1 AND is_married=1 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100
        AS married_head_rate,
    -- Ownership among married heads
    SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=1 THEN ASECWT ELSE 0 END) /
        NULLIF(SUM(CASE WHEN is_head=1 AND is_married=1 THEN ASECWT ELSE 0 END), 0) * 100
        AS ownership_married_heads
FROM persons WHERE generation IS NOT NULL
GROUP BY generation, AGE ORDER BY generation, AGE
""".format(data=DATA)

df = con.execute(q).df()

# Pivot to compute gaps
import pandas as pd
boomers = df[df['generation'] == 'Boomer'].set_index('AGE')
millennials = df[df['generation'] == 'Millennial'].set_index('AGE')

# Only ages where both exist
common_ages = sorted(set(boomers.index) & set(millennials.index))
gaps = pd.DataFrame(index=common_ages)
gaps['Overall ownership gap'] = [boomers.loc[a, 'overall_ownership'] - millennials.loc[a, 'overall_ownership'] for a in common_ages]
gaps['Married head share gap'] = [boomers.loc[a, 'married_head_rate'] - millennials.loc[a, 'married_head_rate'] for a in common_ages]
gaps['Ownership | married heads gap'] = [boomers.loc[a, 'ownership_married_heads'] - millennials.loc[a, 'ownership_married_heads'] for a in common_ages]

# Chart
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

lines = [
    ('Married head share gap', RED, 'Share who are married heads', 3.0),
    ('Overall ownership gap', BLUE, 'Overall ownership rate', 3.0),
    ('Ownership | married heads gap', GREEN, 'Ownership among married heads', 3.0),
]

for col, color, label, lw in lines:
    ax.plot(gaps.index, gaps[col], color=color, linewidth=lw, label=label, zorder=3)

# Zero line
ax.axhline(y=0, color=BLACK, linewidth=0.5, alpha=0.3)

# Annotations at 30, 35, 40
for age in [30, 35, 40]:
    ax.axvline(x=age, color=BLACK, linestyle=':', linewidth=0.8, alpha=0.3, zorder=1)

    for col, color, offset_y in [
        ('Married head share gap', RED, 10),
        ('Overall ownership gap', BLUE, -16),
        ('Ownership | married heads gap', GREEN, -16)
    ]:
        if age in gaps.index:
            val = gaps.loc[age, col]
            ax.plot(age, val, 'o', color=color, markersize=5, zorder=4,
                    markeredgecolor='white', markeredgewidth=1.2)
            ax.annotate(f'{val:.0f}pp',
                        xy=(age, val),
                        xytext=(4, offset_y),
                        textcoords='offset points',
                        fontsize=9, fontweight='bold', color=color,
                        zorder=5)

ax.set_xlim(22, 44)
ymin, ymax = ax.get_ylim()
ax.set_ylim(-5, max(30, ymax + 3))

yticks = ax.get_yticks()
yticks = [t for t in yticks if t >= ax.get_ylim()[0] and t <= ax.get_ylim()[1]]
ax.set_yticks(yticks)
ylabels = [f'{int(t)}' for t in yticks]
if len(ylabels) > 0:
    ylabels[-1] = f'{int(yticks[-1])}pp'
ax.set_yticklabels(ylabels)

ax.set_xlabel('Age', fontsize=11, color=BLACK)

ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=4, color=BLACK)
ax.tick_params(colors=BLACK, labelsize=10)

ax.yaxis.grid(True, color='white', linewidth=0.8)
ax.xaxis.grid(False)
ax.spines['left'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_color(BLACK)

ax.set_title('Boomer\u2013Millennial gap by age', fontsize=16, fontweight='bold',
             color=BLACK, loc='left', pad=45)
ax.text(0.0, 1.08, 'Gap in percentage points (Boomer rate minus Millennial rate)',
        transform=ax.transAxes, fontsize=11, color=BLACK, alpha=0.6)

ax.legend(fontsize=10, loc='upper right', frameon=False)

fig.text(0.1, 0.01, 'Source: CPS ASEC via IPUMS (1976\u20132025, excluding 2014)',
         fontsize=8, color=BLACK, alpha=0.5, style='italic')

plt.tight_layout(rect=[0, 0.03, 1, 0.95])

fig.savefig(f'{OUT}/option3_gap_chart.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.rcParams['svg.fonttype'] = 'none'
fig.savefig(f'{OUT}/option3_gap_chart.svg', bbox_inches='tight', facecolor=BG)
plt.close()
print("Saved option3_gap_chart")
