"""
Homeownership among single (unmarried) household heads by age.
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
    WHERE AGE BETWEEN 20 AND 40
      AND YEAR != 2014
      AND ((YEAR-AGE) BETWEEN 1946 AND 1996)
)
SELECT generation, AGE,
    SUM(CASE WHEN is_head=1 AND is_married=0 AND is_owner=1 THEN ASECWT ELSE 0 END) /
        NULLIF(SUM(CASE WHEN is_head=1 AND is_married=0 THEN ASECWT ELSE 0 END), 0) * 100
        AS ownership_single_heads
FROM persons WHERE generation IS NOT NULL
GROUP BY generation, AGE ORDER BY generation, AGE
""".format(data=DATA)

df = con.execute(q).df()

fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

for gen, color, label in [('Boomer', BOOMER_COLOR, 'Boomers'), ('Millennial', BLUE, 'Millennials')]:
    g = df[df['generation'] == gen].sort_values('AGE')
    ax.plot(g['AGE'], g['ownership_single_heads'], color=color, linewidth=3.0, label=label, zorder=3)

for age in [30, 35, 40]:
    ax.axvline(x=age, color=BLACK, linestyle=':', linewidth=0.8, alpha=0.3, zorder=1)

    bv = df[(df['generation'] == 'Boomer') & (df['AGE'] == age)]['ownership_single_heads'].values
    mv = df[(df['generation'] == 'Millennial') & (df['AGE'] == age)]['ownership_single_heads'].values

    if len(bv) > 0 and len(mv) > 0:
        bv, mv = bv[0], mv[0]
        gap = bv - mv

        ax.plot(age, bv, 'o', color=BOOMER_COLOR, markersize=6, zorder=4,
                markeredgecolor='white', markeredgewidth=1.5)
        ax.plot(age, mv, 'o', color=BLUE, markersize=6, zorder=4,
                markeredgecolor='white', markeredgewidth=1.5)

        # Gap line and label
        ax.plot([age, age], [mv + 0.5, bv - 0.5], color=BLACK, linewidth=1.8,
                alpha=0.35, zorder=2)
        mid = (bv + mv) / 2
        ax.annotate(f'{gap:.0f}pp',
                    xy=(age, mid), xytext=(12, 0),
                    textcoords='offset points',
                    fontsize=10, fontweight='bold', color=BLACK, alpha=0.65,
                    ha='left', va='center', zorder=5)

        ax.annotate(f'{bv:.0f}%',
                    xy=(age, bv), xytext=(-10, 10),
                    textcoords='offset points',
                    fontsize=10, color=BOOMER_COLOR, fontweight='bold',
                    ha='right', va='bottom', zorder=5)
        ax.annotate(f'{mv:.0f}%',
                    xy=(age, mv), xytext=(-10, -10),
                    textcoords='offset points',
                    fontsize=10, color=BLUE, fontweight='bold',
                    ha='right', va='top', zorder=5)

ax.set_ylim(0, 90)
yticks = [0, 20, 40, 60, 80]
ax.set_yticks(yticks)
ylabels = [f'{int(t)}' for t in yticks]
ylabels[-1] = f'{int(yticks[-1])}%'
ax.set_yticklabels(ylabels)

ax.set_xlim(20, 40)
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

ax.set_title('Homeownership among single household heads', fontsize=16,
             fontweight='bold', color=BLACK, loc='left', pad=45)
ax.text(0.0, 1.08, 'Share of unmarried heads who own their home',
        transform=ax.transAxes, fontsize=11, color=BLACK, alpha=0.6)

ax.legend(fontsize=11, loc='lower right', frameon=False,
          labelcolor=[BOOMER_COLOR, BLUE])

fig.text(0.1, 0.01, 'Source: CPS ASEC via IPUMS (1976\u20132025, excluding 2014)',
         fontsize=8, color=BLACK, alpha=0.5, style='italic')

plt.tight_layout(rect=[0, 0.03, 1, 0.95])

fig.savefig(f'{OUT}/ownership_single_heads_by_age.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.rcParams['svg.fonttype'] = 'none'
fig.savefig(f'{OUT}/ownership_single_heads_by_age.svg', bbox_inches='tight', facecolor=BG)
plt.close()
print("Saved ownership_single_heads_by_age")
