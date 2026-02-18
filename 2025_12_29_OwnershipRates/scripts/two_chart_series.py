"""
Two-chart series:
A) % of all people who are married household heads (by age, Boomers vs Millennials)
B) Of married household heads, % who own (by age, Boomers vs Millennials)

Head = RELATE in (101, 201, 202, 203)
Married = MARST in (1, 2) OR RELATE in (201, 202, 203)
Owner = OWNERSHP = 10
"""

import duckdb
import pandas as pd
import numpy as np
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

ts_query = """
WITH persons AS (
    SELECT *,
        CASE
            WHEN (YEAR - AGE) BETWEEN 1946 AND 1964 THEN 'Boomer'
            WHEN (YEAR - AGE) BETWEEN 1981 AND 1996 THEN 'Millennial'
        END AS generation,
        CASE WHEN RELATE IN (101, 201, 202, 203) THEN 1 ELSE 0 END AS is_head,
        CASE WHEN MARST IN (1, 2) OR RELATE IN (201, 202, 203) THEN 1 ELSE 0 END AS is_married,
        CASE WHEN OWNERSHP = 10 THEN 1 ELSE 0 END AS is_owner
    FROM '{data}'
    WHERE AGE BETWEEN 20 AND 45
      AND YEAR != 2014
      AND ((YEAR - AGE) BETWEEN 1946 AND 1996)
)
SELECT
    generation,
    AGE,
    -- Chart A: % of ALL people who are married heads
    SUM(CASE WHEN is_head = 1 AND is_married = 1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100
        AS married_head_rate,
    -- Chart B: of married heads, % who own
    SUM(CASE WHEN is_head = 1 AND is_married = 1 AND is_owner = 1 THEN ASECWT ELSE 0 END) /
        NULLIF(SUM(CASE WHEN is_head = 1 AND is_married = 1 THEN ASECWT ELSE 0 END), 0) * 100
        AS ownership_rate_married_heads
FROM persons
WHERE generation IS NOT NULL
GROUP BY generation, AGE
ORDER BY generation, AGE
""".format(data=DATA)

df = con.execute(ts_query).df()

# Print key ages
print("Key values:")
for age in [30, 35, 40]:
    print(f"\n  Age {age}:")
    for gen in ['Boomer', 'Millennial']:
        row = df[(df['generation'] == gen) & (df['AGE'] == age)]
        if not row.empty:
            r = row.iloc[0]
            print(f"    {gen}: married heads = {r['married_head_rate']:.1f}%, ownership of married heads = {r['ownership_rate_married_heads']:.1f}%")


def make_chart(df, col, title, subtitle, filename):
    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Plot lines
    for gen, color, label in [
        ('Boomer', BOOMER_COLOR, 'Boomers'),
        ('Millennial', BLUE, 'Millennials')
    ]:
        g = df[df['generation'] == gen].sort_values('AGE')
        ax.plot(g['AGE'], g[col], color=color, linewidth=3.0, label=label, zorder=3)

    # Vertical dotted lines and annotations at 30, 35, 40
    for age in [30, 35, 40]:
        ax.axvline(x=age, color=BLACK, linestyle=':', linewidth=0.8, alpha=0.3, zorder=1)

        vals = {}
        for gen, color in [('Boomer', BOOMER_COLOR), ('Millennial', BLUE)]:
            g = df[df['generation'] == gen]
            row = g[g['AGE'] == age]
            if not row.empty:
                vals[gen] = row[col].values[0]

        # Determine annotation offsets to avoid overlap
        if 'Boomer' in vals and 'Millennial' in vals:
            gap = vals['Boomer'] - vals['Millennial']
            if abs(gap) < 6:
                # Lines are close — push annotations apart
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

    # Y-axis formatting
    ymin, ymax = ax.get_ylim()
    ax.set_ylim(max(0, ymin - 3), min(100, ymax + 5))

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

    ax.set_title(title, fontsize=16, fontweight='bold', color=BLACK,
                 loc='left', pad=45)
    ax.text(0.0, 1.08, subtitle, transform=ax.transAxes,
            fontsize=11, color=BLACK, alpha=0.6)

    ax.legend(fontsize=11, loc='lower right', frameon=False,
              labelcolor=[BOOMER_COLOR, BLUE])

    fig.text(0.1, 0.01, 'Source: CPS ASEC via IPUMS (1976\u20132025, excluding 2014)',
             fontsize=8, color=BLACK, alpha=0.5, style='italic')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    fig.savefig(f'{OUT}/{filename}.png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.rcParams['svg.fonttype'] = 'none'
    fig.savefig(f'{OUT}/{filename}.svg', bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"Saved {filename}")


# ── Chart A: Married head rate (of all people) ──
make_chart(df, 'married_head_rate',
           'Married household heads as share of all people',
           'Includes spouses/partners of household heads',
           'married_head_rate_by_age')

# ── Chart B: Ownership rate (of married heads) ──
make_chart(df, 'ownership_rate_married_heads',
           'Homeownership among married household heads',
           'Share of married/partnered heads who own their home',
           'ownership_rate_married_heads_by_age')

print("\nDone!")
