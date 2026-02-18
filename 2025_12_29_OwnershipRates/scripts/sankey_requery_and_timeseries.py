"""
Re-query CPS ASEC for Sankey numbers and create time series charts.
Boomers: born 1946-1964, Millennials: born 1981-1996
Head = RELATE in (101, 201, 202, 203) — householder + spouse/partner
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
LIGHT_BLUE = '#7DD6FF'
BLACK = '#3D3733'
BG = '#F6F7F3'
CREAM = '#BBBFAE'  # darkened for visibility on light background
LIGHT_CREAM = '#A5A999'

DATA = '/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec.parquet'
OUT = '/Users/azizsunderji/Dropbox/Home Economics/2025_12_29_OwnershipRates/2025_12_29_FirstApproach/outputs'

con = duckdb.connect()

# ══════════════════════════════════════════════════════════════
# Time series by age: headship, marriage (of heads), ownership (of married heads)
# Head = RELATE in (101, 201, 202, 203)
# Married = MARST in (1,2) OR RELATE in (201, 202, 203)
# ══════════════════════════════════════════════════════════════

ts_query = """
WITH persons AS (
    SELECT *,
        YEAR - AGE AS birth_year,
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
    -- Headship rate (of all people)
    SUM(CASE WHEN is_head = 1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS headship_rate,
    -- Marriage rate (of heads only)
    SUM(CASE WHEN is_head = 1 AND is_married = 1 THEN ASECWT ELSE 0 END) /
        NULLIF(SUM(CASE WHEN is_head = 1 THEN ASECWT ELSE 0 END), 0) * 100 AS marriage_rate_of_heads,
    -- Ownership rate (of married heads only)
    SUM(CASE WHEN is_head = 1 AND is_married = 1 AND is_owner = 1 THEN ASECWT ELSE 0 END) /
        NULLIF(SUM(CASE WHEN is_head = 1 AND is_married = 1 THEN ASECWT ELSE 0 END), 0) * 100 AS ownership_rate_married_heads,
    SUM(ASECWT) AS total_pop
FROM persons
WHERE generation IS NOT NULL
GROUP BY generation, AGE
ORDER BY generation, AGE
""".format(data=DATA)

df_ts = con.execute(ts_query).df()

# Print key ages for reference
print("Key values at milestone ages:")
for age in [30, 35, 40]:
    print(f"\n  Age {age}:")
    for gen in ['Boomer', 'Millennial']:
        row = df_ts[(df_ts['generation'] == gen) & (df_ts['AGE'] == age)]
        if not row.empty:
            r = row.iloc[0]
            print(f"    {gen}: headship={r['headship_rate']:.1f}%, marriage(heads)={r['marriage_rate_of_heads']:.1f}%, ownership(married heads)={r['ownership_rate_married_heads']:.1f}%")
        else:
            print(f"    {gen}: no data at this age")

# ── Chart function ──
def make_chart(df, col, title, subtitle, filename):
    fig, ax = plt.subplots(figsize=(9, 7.5), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Plot lines
    for gen, color, lw, label in [
        ('Boomer', CREAM, 3.0, 'Boomers'),
        ('Millennial', BLUE, 3.0, 'Millennials')
    ]:
        g = df[df['generation'] == gen].sort_values('AGE')
        ax.plot(g['AGE'], g[col], color=color, linewidth=lw, label=label, zorder=3)

    # Vertical dotted lines and annotations at 30, 35, 40
    for age in [30, 35, 40]:
        ax.axvline(x=age, color=BLACK, linestyle=':', linewidth=0.8, alpha=0.3, zorder=1)

        for gen, color, offset_y in [('Boomer', CREAM, 10), ('Millennial', BLUE, -16)]:
            g = df[df['generation'] == gen]
            row = g[g['AGE'] == age]
            if not row.empty:
                val = row[col].values[0]
                # Dot on line
                ax.plot(age, val, 'o', color=color, markersize=6, zorder=4,
                        markeredgecolor='white', markeredgewidth=1.5)
                # Annotation - color matches the line
                ax.annotate(f'{val:.0f}%',
                            xy=(age, val),
                            xytext=(4, offset_y),
                            textcoords='offset points',
                            fontsize=10, fontweight='bold', color=color,
                            zorder=5)

    # Y-axis formatting
    ymin, ymax = ax.get_ylim()
    # Add padding
    ax.set_ylim(max(0, ymin - 3), min(100, ymax + 5))

    # Set y ticks with % only on top
    yticks = ax.get_yticks()
    yticks = [t for t in yticks if t >= ax.get_ylim()[0] and t <= ax.get_ylim()[1]]
    ax.set_yticks(yticks)
    ylabels = [f'{int(t)}' for t in yticks]
    if len(ylabels) > 0:
        ylabels[-1] = f'{int(yticks[-1])}%'
    ax.set_yticklabels(ylabels)

    # X-axis
    ax.set_xlabel('Age', fontsize=11, color=BLACK)
    ax.set_xlim(19, 46)

    # Tick styling
    ax.tick_params(axis='y', length=0)
    ax.tick_params(axis='x', length=4, color=BLACK)
    ax.tick_params(colors=BLACK, labelsize=10)

    # Gridlines
    ax.yaxis.grid(True, color='white', linewidth=0.8)
    ax.xaxis.grid(False)
    ax.spines['left'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color(BLACK)

    # Title / subtitle
    ax.set_title(title, fontsize=16, fontweight='bold', color=BLACK,
                 loc='left', pad=45)
    ax.text(0.0, 1.08, subtitle, transform=ax.transAxes,
            fontsize=11, color=BLACK, alpha=0.6)

    # Legend
    ax.legend(fontsize=11, loc='lower right', frameon=False,
              labelcolor=[CREAM, BLUE])

    # Source
    fig.text(0.1, 0.01, 'Source: CPS ASEC via IPUMS (1976\u20132025, excluding 2014)',
             fontsize=8, color=BLACK, alpha=0.5, style='italic')

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    fig.savefig(f'{OUT}/{filename}.png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.rcParams['svg.fonttype'] = 'none'
    fig.savefig(f'{OUT}/{filename}.svg', bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"Saved {filename}")


# ── Chart 1: Headship Rate ──
make_chart(df_ts, 'headship_rate',
           'Headship rate by age',
           'Share of all people who head or co-head a household',
           'headship_rate_by_age')

# ── Chart 2: Marriage Rate (of heads) ──
make_chart(df_ts, 'marriage_rate_of_heads',
           'Marriage rate among household heads',
           'Share of household heads/co-heads who are married or partnered',
           'marriage_rate_heads_by_age')

# ── Chart 3: Ownership Rate (of married heads) ──
make_chart(df_ts, 'ownership_rate_married_heads',
           'Homeownership among married household heads',
           'Share of married/partnered heads who own their home',
           'ownership_rate_married_heads_by_age')

print("\nDone!")
