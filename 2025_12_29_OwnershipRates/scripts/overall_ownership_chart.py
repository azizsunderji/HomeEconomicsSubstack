"""
Unconditional homeownership rate by age: % of ALL people who are
homeowners (head or spouse in an owned unit).
"""

import duckdb
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ── Fonts ──
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# ── Colors ──
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
        CASE WHEN OWNERSHP = 10 AND RELATE IN (101, 201, 202, 203) THEN 1 ELSE 0 END AS is_owner
    FROM '{data}'
    WHERE AGE BETWEEN 20 AND 45
      AND YEAR != 2014
      AND ((YEAR-AGE) BETWEEN 1946 AND 1996)
)
SELECT generation, AGE,
    SUM(CASE WHEN is_owner=1 THEN ASECWT ELSE 0 END)/SUM(ASECWT)*100 as ownership_rate
FROM persons WHERE generation IS NOT NULL
GROUP BY generation, AGE ORDER BY generation, AGE
""".format(data=DATA)

df = con.execute(q).df()

for age in [30, 35, 40]:
    for gen in ['Boomer', 'Millennial']:
        r = df[(df['generation']==gen) & (df['AGE']==age)].iloc[0]
        print(f"Age {age} {gen}: {r['ownership_rate']:.1f}%")

# ── Chart ──
fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

for gen, color, label in [('Boomer', BOOMER_COLOR, 'Boomers'), ('Millennial', BLUE, 'Millennials')]:
    g = df[df['generation'] == gen].sort_values('AGE')
    ax.plot(g['AGE'], g['ownership_rate'], color=color, linewidth=3.0, label=label, zorder=3)

for age in [30, 35, 40]:
    ax.axvline(x=age, color=BLACK, linestyle=':', linewidth=0.8, alpha=0.3, zorder=1)

    vals = {}
    for gen, color in [('Boomer', BOOMER_COLOR), ('Millennial', BLUE)]:
        row = df[(df['generation'] == gen) & (df['AGE'] == age)]
        if not row.empty:
            vals[gen] = row['ownership_rate'].values[0]

    if 'Boomer' in vals and 'Millennial' in vals:
        gap = vals['Boomer'] - vals['Millennial']
        if abs(gap) < 6:
            boomer_offset = 12
            mill_offset = -18
        else:
            boomer_offset = 10
            mill_offset = -16

        for gen, color, offset_y in [('Boomer', BOOMER_COLOR, boomer_offset),
                                      ('Millennial', BLUE, mill_offset)]:
            val = vals[gen]
            ax.plot(age, val, 'o', color=color, markersize=6, zorder=4,
                    markeredgecolor='white', markeredgewidth=1.5)
            ax.annotate(f'{val:.0f}%',
                        xy=(age, val),
                        xytext=(4, offset_y),
                        textcoords='offset points',
                        fontsize=10, fontweight='bold', color=color,
                        zorder=5)

ymin, ymax = ax.get_ylim()
ax.set_ylim(0, min(80, ymax + 5))

yticks = ax.get_yticks()
yticks = [t for t in yticks if t >= ax.get_ylim()[0] and t <= ax.get_ylim()[1]]
ax.set_yticks(yticks)
ylabels = [f'{int(t)}' for t in yticks]
if len(ylabels) > 0:
    ylabels[-1] = f'{int(yticks[-1])}%'
ax.set_yticklabels(ylabels)

ax.set_xlabel('Age', fontsize=11, color=BLACK)
ax.set_xlim(19, 46)

ax.tick_params(axis='y', length=0)
ax.tick_params(axis='x', length=4, color=BLACK)
ax.tick_params(colors=BLACK, labelsize=10)

ax.yaxis.grid(True, color='white', linewidth=0.8)
ax.xaxis.grid(False)
ax.spines['left'].set_visible(False)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_color(BLACK)

ax.set_title('Homeownership rate by age', fontsize=16, fontweight='bold',
             color=BLACK, loc='left', pad=45)
ax.text(0.0, 1.08, 'Share of all people who own or co-own their home',
        transform=ax.transAxes, fontsize=11, color=BLACK, alpha=0.6)

ax.legend(fontsize=11, loc='lower right', frameon=False,
          labelcolor=[BOOMER_COLOR, BLUE])

fig.text(0.1, 0.01, 'Source: CPS ASEC via IPUMS (1976\u20132025, excluding 2014)',
         fontsize=8, color=BLACK, alpha=0.5, style='italic')

plt.tight_layout(rect=[0, 0.03, 1, 0.95])

fig.savefig(f'{OUT}/ownership_rate_all_by_age.png', dpi=150, bbox_inches='tight', facecolor=BG)
plt.rcParams['svg.fonttype'] = 'none'
fig.savefig(f'{OUT}/ownership_rate_all_by_age.svg', bbox_inches='tight', facecolor=BG)
plt.close()
print("Saved ownership_rate_all_by_age")
