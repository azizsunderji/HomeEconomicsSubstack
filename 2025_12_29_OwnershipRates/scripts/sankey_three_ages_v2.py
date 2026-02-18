"""
Sankey diagrams with aligned nodes and size bars.
- "Live with parents/friends" aligned with "Become household heads"
- Little bars at each node showing the size
"""

import duckdb
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
import numpy as np
import matplotlib.font_manager as fm

# Register Oracle font
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

BLUE = '#0BB4FF'
BLUE_LIGHT = '#0BB4FF'
CREAM = '#BBBFAE'
CREAM_LIGHT = '#BBBFAE'
BG = '#F6F7F3'
BLACK = '#3D3733'

DATA = '/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec.parquet'
OUT = '/Users/azizsunderji/Dropbox/Home Economics/2025_12_29_OwnershipRates/2025_12_29_FirstApproach/outputs'

con = duckdb.connect()


def get_sankey_data(age):
    """Get flow data for a given age."""
    q = f"""
    WITH persons AS (
        SELECT *,
            CASE WHEN (YEAR-AGE) BETWEEN 1946 AND 1964 THEN 'Boomer'
                 WHEN (YEAR-AGE) BETWEEN 1981 AND 1996 THEN 'Millennial' END AS generation,
            CASE WHEN RELATE IN (101, 201, 202, 203) THEN 1 ELSE 0 END AS is_head,
            CASE WHEN MARST IN (1, 2) OR RELATE IN (201, 202, 203) THEN 1 ELSE 0 END AS is_married,
            CASE WHEN OWNERSHP = 10 THEN 1 ELSE 0 END AS is_owner
        FROM '{DATA}'
        WHERE AGE = {age} AND YEAR != 2014
          AND ((YEAR-AGE) BETWEEN 1946 AND 1996)
    )
    SELECT
        generation,
        SUM(ASECWT) AS total_pop,
        SUM(CASE WHEN is_head=1 THEN ASECWT ELSE 0 END) AS heads,
        SUM(CASE WHEN is_head=0 THEN ASECWT ELSE 0 END) AS not_heads,
        SUM(CASE WHEN is_head=1 AND is_married=1 THEN ASECWT ELSE 0 END) AS married_heads,
        SUM(CASE WHEN is_head=1 AND is_married=0 THEN ASECWT ELSE 0 END) AS single_heads,
        SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=1 THEN ASECWT ELSE 0 END) AS married_owner,
        SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=0 THEN ASECWT ELSE 0 END) AS married_renter,
        SUM(CASE WHEN is_head=1 AND is_married=0 AND is_owner=1 THEN ASECWT ELSE 0 END) AS single_owner,
        SUM(CASE WHEN is_head=1 AND is_married=0 AND is_owner=0 THEN ASECWT ELSE 0 END) AS single_renter
    FROM persons WHERE generation IS NOT NULL
    GROUP BY generation ORDER BY generation
    """
    return con.execute(q).df()


def draw_flow(ax, x0, y0, h0, x1, y1, h1, color, alpha=0.5):
    """Draw a curved flow between two rectangles."""
    # Control points for bezier curve
    mid_x = (x0 + x1) / 2

    # Top edge of flow
    verts_top = [
        (x0, y0 + h0),  # start top
        (mid_x, y0 + h0),  # control 1
        (mid_x, y1 + h1),  # control 2
        (x1, y1 + h1),  # end top
    ]

    # Bottom edge of flow (reversed)
    verts_bottom = [
        (x1, y1),  # end bottom
        (mid_x, y1),  # control 2
        (mid_x, y0),  # control 1
        (x0, y0),  # start bottom
    ]

    # Combine into closed path
    verts = verts_top + verts_bottom + [verts_top[0]]
    codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
             Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4,
             Path.CLOSEPOLY]

    path = Path(verts, codes)
    patch = mpatches.PathPatch(path, facecolor=color, edgecolor='none', alpha=alpha)
    ax.add_patch(patch)


def draw_bar(ax, x, y, height, width, color):
    """Draw a node bar."""
    rect = mpatches.Rectangle((x, y), width, height, facecolor=color, edgecolor=BLACK, linewidth=0.5)
    ax.add_patch(rect)


def largest_remainder_round(values, target=100):
    """Round values so they sum exactly to target (largest remainder method)."""
    floored = [int(v) for v in values]
    remainders = [v - f for v, f in zip(values, floored)]
    diff = target - sum(floored)
    # Give extra 1 to the entries with the largest remainders
    indices = sorted(range(len(remainders)), key=lambda i: remainders[i], reverse=True)
    for i in range(diff):
        floored[indices[i]] += 1
    return floored


def draw_sankey(ax, data, color, title):
    """Draw a single Sankey diagram."""
    tot = data['total_pop']

    # Convert to fractions (0-1 scale for positioning)
    heads_frac = data['heads'] / tot
    not_heads_frac = data['not_heads'] / tot
    married_frac = data['married_heads'] / tot
    single_frac = data['single_heads'] / tot
    m_owner_frac = data['married_owner'] / tot
    m_renter_frac = data['married_renter'] / tot
    s_owner_frac = data['single_owner'] / tot
    s_renter_frac = data['single_renter'] / tot

    # Percentages - use largest remainder rounding so final 5 categories sum to 100
    raw_final = [m_owner_frac*100, m_renter_frac*100, s_owner_frac*100, s_renter_frac*100, not_heads_frac*100]
    rounded_final = largest_remainder_round(raw_final, 100)
    m_owner_pct, m_renter_pct, s_owner_pct, s_renter_pct, not_heads_pct = rounded_final

    # Intermediate nodes: heads/not_heads must sum to 100
    raw_split1 = [heads_frac*100, not_heads_frac*100]
    heads_pct, _ = largest_remainder_round(raw_split1, 100)

    # married/single must sum to heads_pct
    raw_split2 = [married_frac*100, single_frac*100]
    married_pct, single_pct = largest_remainder_round(raw_split2, heads_pct)

    # X positions for columns (spaced wider for thicker bars)
    x_birth = 0
    x_head = 1.5
    x_married = 3.0
    x_final = 4.5

    bar_width = 0.35  # much thicker bars to fit labels inside

    # Flow color and label color
    if color == 'blue':
        flow_color = BLUE
        bar_color = BLUE
        label_color = BLACK  # Millennials in black
    else:
        flow_color = CREAM
        bar_color = CREAM
        label_color = '#888888'  # Boomers in grey

    # Total height available
    total_h = 1.0
    gap = 0.06  # gap between stacked elements

    # Column 1: Birth (100%)
    birth_y = 0
    birth_h = total_h
    draw_bar(ax, x_birth, birth_y, birth_h, bar_width, bar_color)
    ax.text(x_birth + bar_width/2, birth_y + birth_h/2, '100%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    # Column 2: Heads (top) and Not Heads (bottom) - ALIGNED in same column
    # Position so that the total height (heads + not_heads + gap) fits in total_h
    # Not heads at bottom
    not_heads_h = not_heads_frac * total_h
    not_heads_y = 0
    draw_bar(ax, x_head, not_heads_y, not_heads_h, bar_width, bar_color)
    ax.text(x_head + bar_width/2, not_heads_y + not_heads_h/2, f'{not_heads_pct:.0f}%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    # Heads above not_heads with gap
    heads_h = heads_frac * total_h
    heads_y = not_heads_h + gap
    draw_bar(ax, x_head, heads_y, heads_h, bar_width, bar_color)
    ax.text(x_head + bar_width/2, heads_y + heads_h/2, f'{heads_pct:.0f}%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    # Column 3: Married (top) and Single (bottom) - only from heads
    # These should align with the heads bar vertically
    single_h = single_frac * total_h
    single_y = heads_y  # align with bottom of heads
    draw_bar(ax, x_married, single_y, single_h, bar_width, bar_color)
    ax.text(x_married + bar_width/2, single_y + single_h/2, f'{single_pct:.0f}%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    # Married above single with small gap
    married_h = married_frac * total_h
    married_y = single_y + single_h + gap * 0.5
    draw_bar(ax, x_married, married_y, married_h, bar_width, bar_color)
    ax.text(x_married + bar_width/2, married_y + married_h/2, f'{married_pct:.0f}%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    # Column 4: Final outcomes (5 bars that add to 100%)
    # Arrange from bottom to top: Single Renter, Single Owner, gap, Married Renter, Married Owner, gap, Not Head at very bottom

    # Calculate positions - stack them with small gaps
    small_gap = gap * 0.3

    # Single outcomes (aligned with single bar)
    s_renter_h = s_renter_frac * total_h
    s_renter_y = single_y
    draw_bar(ax, x_final, s_renter_y, s_renter_h, bar_width, bar_color)
    ax.text(x_final + bar_width/2, s_renter_y + s_renter_h/2, f'{s_renter_pct:.0f}%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    s_owner_h = s_owner_frac * total_h
    s_owner_y = s_renter_y + s_renter_h + small_gap
    draw_bar(ax, x_final, s_owner_y, s_owner_h, bar_width, bar_color)
    ax.text(x_final + bar_width/2, s_owner_y + s_owner_h/2, f'{s_owner_pct:.0f}%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    # Married outcomes (aligned with married bar)
    m_renter_h = m_renter_frac * total_h
    m_renter_y = married_y
    draw_bar(ax, x_final, m_renter_y, m_renter_h, bar_width, bar_color)
    ax.text(x_final + bar_width/2, m_renter_y + m_renter_h/2, f'{m_renter_pct:.0f}%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    m_owner_h = m_owner_frac * total_h
    m_owner_y = m_renter_y + m_renter_h + small_gap
    draw_bar(ax, x_final, m_owner_y, m_owner_h, bar_width, bar_color)
    ax.text(x_final + bar_width/2, m_owner_y + m_owner_h/2, f'{m_owner_pct:.0f}%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    # Draw flows
    # Birth -> Heads (top portion of birth bar)
    birth_heads_bottom = not_heads_frac * total_h
    draw_flow(ax, x_birth + bar_width, birth_heads_bottom, heads_h,
              x_head, heads_y, heads_h, flow_color, alpha=0.5)

    # Birth -> Not Heads (bottom portion of birth bar)
    draw_flow(ax, x_birth + bar_width, 0, not_heads_h,
              x_head, not_heads_y, not_heads_h, flow_color, alpha=0.5)

    # Heads -> Married (top portion of heads)
    heads_married_bottom = heads_y + single_h
    draw_flow(ax, x_head + bar_width, heads_married_bottom, married_h,
              x_married, married_y, married_h, flow_color, alpha=0.5)

    # Heads -> Single (bottom portion of heads)
    draw_flow(ax, x_head + bar_width, heads_y, single_h,
              x_married, single_y, single_h, flow_color, alpha=0.5)

    # Married -> Married Owner (top portion)
    married_owner_bottom = married_y + m_renter_h
    draw_flow(ax, x_married + bar_width, married_owner_bottom, m_owner_h,
              x_final, m_owner_y, m_owner_h, flow_color, alpha=0.5)

    # Married -> Married Renter (bottom portion)
    draw_flow(ax, x_married + bar_width, married_y, m_renter_h,
              x_final, m_renter_y, m_renter_h, flow_color, alpha=0.5)

    # Single -> Single Owner (top portion)
    single_owner_bottom = single_y + s_renter_h
    draw_flow(ax, x_married + bar_width, single_owner_bottom, s_owner_h,
              x_final, s_owner_y, s_owner_h, flow_color, alpha=0.5)

    # Single -> Single Renter (bottom portion)
    draw_flow(ax, x_married + bar_width, single_y, s_renter_h,
              x_final, s_renter_y, s_renter_h, flow_color, alpha=0.5)

    # Not Heads terminal bar in final column (at bottom)
    not_heads_final_h = not_heads_frac * total_h
    not_heads_final_y = not_heads_y
    draw_bar(ax, x_final, not_heads_final_y, not_heads_final_h, bar_width, bar_color)
    ax.text(x_final + bar_width/2, not_heads_final_y + not_heads_final_h/2, f'{not_heads_pct:.0f}%',
            ha='center', va='center', fontsize=9, color=label_color, fontweight='bold')

    # Not Heads -> Not Heads final (straight across)
    draw_flow(ax, x_head + bar_width, not_heads_y, not_heads_h,
              x_final, not_heads_final_y, not_heads_final_h, flow_color, alpha=0.5)

    ax.set_xlim(-0.3, 5.2)
    ax.set_ylim(-0.1, 1.2)
    ax.set_aspect(2.5)  # wider than tall
    ax.axis('off')
    ax.set_title(title, fontsize=14, color=BLACK, pad=10)


# Create the 3x2 grid
fig, axes = plt.subplots(3, 2, figsize=(14, 12))
fig.patch.set_facecolor(BG)

ages = [30, 35, 40]

for row_idx, age in enumerate(ages):
    df = get_sankey_data(age)

    # Boomers (left column)
    boomer_data = df[df['generation'] == 'Boomer'].iloc[0]
    draw_sankey(axes[row_idx, 0], boomer_data, 'cream', f'Boomers at Age {age}')

    # Millennials (right column)
    mill_data = df[df['generation'] == 'Millennial'].iloc[0]
    draw_sankey(axes[row_idx, 1], mill_data, 'blue', f'Millennials at Age {age}')

fig.suptitle("Path to Homeownership: Boomers vs Millennials", fontsize=20, color=BLACK, y=0.98)
plt.tight_layout(rect=[0, 0, 1, 0.96])

plt.savefig(f'{OUT}/sankey_three_ages_v2.svg', format='svg', facecolor=BG, bbox_inches='tight')
plt.savefig(f'{OUT}/sankey_three_ages_v2.png', dpi=200, facecolor=BG, bbox_inches='tight')
print("Saved sankey_three_ages_v2.svg and .png")
