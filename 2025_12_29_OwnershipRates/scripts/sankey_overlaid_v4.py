"""
Overlaid Sankey v4: Draw Boomer "excess" areas explicitly (where B > M),
then Millennial areas. This creates the halo effect properly.
"""

import duckdb
import numpy as np
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

BLUE = '#0BB4FF'
CREAM = '#DADFCE'
BG = '#F6F7F3'
BLACK = '#3D3733'

DATA = '/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec.parquet'
OUT = '/Users/azizsunderji/Dropbox/Home Economics/2025_12_29_OwnershipRates/2025_12_29_FirstApproach/outputs'

con = duckdb.connect()


def get_data(age):
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
        SUM(CASE WHEN is_head=1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS heads,
        SUM(CASE WHEN is_head=0 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS not_heads,
        SUM(CASE WHEN is_head=1 AND is_married=1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS married,
        SUM(CASE WHEN is_head=1 AND is_married=0 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS single,
        SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS m_own,
        SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=0 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS m_rent,
        SUM(CASE WHEN is_head=1 AND is_married=0 AND is_owner=1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS s_own,
        SUM(CASE WHEN is_head=1 AND is_married=0 AND is_owner=0 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS s_rent
    FROM persons WHERE generation IS NOT NULL
    GROUP BY generation ORDER BY generation
    """
    df = con.execute(q).df()
    return {
        'Boomer': df[df['generation'] == 'Boomer'].iloc[0].to_dict(),
        'Millennial': df[df['generation'] == 'Millennial'].iloc[0].to_dict()
    }


def flow(ax, x0, x1, y0_top, y0_bot, y1_top, y1_bot, color, alpha, zorder):
    """Draw smooth S-curve flow."""
    if y0_top <= y0_bot or y1_top <= y1_bot:
        return  # Skip invalid flows

    n = 50
    t = np.linspace(0, 1, n)
    ease = 3*t**2 - 2*t**3

    x = x0 + (x1 - x0) * ease
    top = y0_top + (y1_top - y0_top) * ease
    bot = y0_bot + (y1_bot - y0_bot) * ease

    verts = list(zip(x, top)) + list(zip(x[::-1], bot[::-1]))
    poly = mpatches.Polygon(verts, facecolor=color, edgecolor='none', alpha=alpha, zorder=zorder)
    ax.add_patch(poly)


def bar(ax, x, w, y_top, y_bot, color, alpha, zorder):
    if y_top <= y_bot:
        return
    rect = mpatches.Rectangle((x - w/2, y_bot), w, y_top - y_bot,
                               facecolor=color, edgecolor='none', alpha=alpha, zorder=zorder)
    ax.add_patch(rect)


def make_sankey(age, data):
    fig, ax = plt.subplots(figsize=(11, 10), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    b = data['Boomer']
    m = data['Millennial']

    x0, x1, x2, x3 = 0.08, 0.32, 0.62, 0.92
    w = 0.035

    # Calculate y positions for each segment (from top=100 down)
    # For each segment: (top_y, bottom_y)

    # Boomer positions
    b_heads = (100, 100 - b['heads'])
    b_nh = (b['not_heads'], 0)
    b_married = (100, 100 - b['married'])
    b_single = (100 - b['married'], 100 - b['married'] - b['single'])

    bc = 0  # cumulative
    b_mo = (100 - bc, 100 - bc - b['m_own']); bc += b['m_own']
    b_mr = (100 - bc, 100 - bc - b['m_rent']); bc += b['m_rent']
    b_so = (100 - bc, 100 - bc - b['s_own']); bc += b['s_own']
    b_sr = (100 - bc, 100 - bc - b['s_rent']); bc += b['s_rent']
    b_nhr = (100 - bc, 0)

    # Millennial positions
    m_heads = (100, 100 - m['heads'])
    m_nh = (m['not_heads'], 0)
    m_married = (100, 100 - m['married'])
    m_single = (100 - m['married'], 100 - m['married'] - m['single'])

    mc = 0
    m_mo = (100 - mc, 100 - mc - m['m_own']); mc += m['m_own']
    m_mr = (100 - mc, 100 - mc - m['m_rent']); mc += m['m_rent']
    m_so = (100 - mc, 100 - mc - m['s_own']); mc += m['s_own']
    m_sr = (100 - mc, 100 - mc - m['s_rent']); mc += m['s_rent']
    m_nhr = (100 - mc, 0)

    cream_a = 0.55
    blue_a = 0.9

    # === STAGE 0: BIRTH BAR ===
    # Draw both generations (cream behind, blue in front)
    bar(ax, x0, w, 100, 0, CREAM, cream_a, 1)
    bar(ax, x0, w, 100, 0, BLUE, blue_a, 2)

    # === STAGE 0->1: BIRTH TO HEADS/NOT-HEADS ===

    # HEADS flow: Both start at top (100), Boomers go lower (to b_heads[1]), Millennials higher (to m_heads[1])
    # Boomer excess (cream halo): from Millennial bottom to Boomer bottom
    if b_heads[1] < m_heads[1]:  # Boomers have more heads
        flow(ax, x0+w/2, x1-w/2, m_heads[1], b_heads[1], m_heads[1], b_heads[1], CREAM, cream_a, 1)
    # Millennial heads
    flow(ax, x0+w/2, x1-w/2, m_heads[0], m_heads[1], m_heads[0], m_heads[1], BLUE, blue_a, 2)

    # NOT-HEADS flow: Both start at bottom (0), Millennials go higher (to m_nh[0]), Boomers lower (to b_nh[0])
    # Millennial excess (blue larger): from Boomer top to Millennial top
    if m_nh[0] > b_nh[0]:  # Millennials have more not-heads
        flow(ax, x0+w/2, x1-w/2, m_nh[0], b_nh[0], m_nh[0], b_nh[0], BLUE, blue_a, 2)
    # Boomer not-heads (cream)
    flow(ax, x0+w/2, x1-w/2, b_nh[0], 0, b_nh[0], 0, CREAM, cream_a, 1)

    # Stage 1 bars
    # Heads bars
    bar(ax, x1, w, m_heads[0], b_heads[1], CREAM, cream_a, 1)  # Full boomer extent
    bar(ax, x1, w, m_heads[0], m_heads[1], BLUE, blue_a, 2)    # Millennial

    # Not-heads bars
    bar(ax, x1, w, m_nh[0], 0, BLUE, blue_a, 2)  # Millennial (larger)
    bar(ax, x1, w, b_nh[0], 0, CREAM, cream_a, 1)  # Boomer (smaller, behind)

    # === STAGE 1->2: HEADS TO MARRIED/SINGLE ===

    # MARRIED: Boomers have more married
    if b_married[1] < m_married[1]:
        flow(ax, x1+w/2, x2-w/2, m_married[1], b_married[1], m_married[1], b_married[1], CREAM, cream_a, 1)
    flow(ax, x1+w/2, x2-w/2, m_married[0], m_married[1], m_married[0], m_married[1], BLUE, blue_a, 2)

    # SINGLE: flows from bottom of married to bottom of heads
    # This is trickier - need to show both generations
    # Draw Boomer single flow
    flow(ax, x1+w/2, x2-w/2, b_single[0], b_single[1], b_single[0], b_single[1], CREAM, cream_a, 1)
    # Draw Millennial single flow
    flow(ax, x1+w/2, x2-w/2, m_single[0], m_single[1], m_single[0], m_single[1], BLUE, blue_a, 2)

    # Stage 2 bars
    bar(ax, x2, w, 100, b_married[1], CREAM, cream_a, 1)
    bar(ax, x2, w, 100, m_married[1], BLUE, blue_a, 2)

    bar(ax, x2, w, b_single[0], b_single[1], CREAM, cream_a, 1)
    bar(ax, x2, w, m_single[0], m_single[1], BLUE, blue_a, 2)

    # === STAGE 2->3: TO OWNERSHIP OUTCOMES ===

    # Married -> Own
    if b_mo[1] < m_mo[1]:  # Boomers own more
        flow(ax, x2+w/2, x3-w/2, m_mo[1], b_mo[1], m_mo[1], b_mo[1], CREAM, cream_a, 1)
    flow(ax, x2+w/2, x3-w/2, m_mo[0], m_mo[1], m_mo[0], m_mo[1], BLUE, blue_a, 2)

    # Married -> Rent
    flow(ax, x2+w/2, x3-w/2, b_mr[0], b_mr[1], b_mr[0], b_mr[1], CREAM, cream_a, 1)
    flow(ax, x2+w/2, x3-w/2, m_mr[0], m_mr[1], m_mr[0], m_mr[1], BLUE, blue_a, 2)

    # Single -> Own
    flow(ax, x2+w/2, x3-w/2, b_so[0], b_so[1], b_so[0], b_so[1], CREAM, cream_a, 1)
    flow(ax, x2+w/2, x3-w/2, m_so[0], m_so[1], m_so[0], m_so[1], BLUE, blue_a, 2)

    # Single -> Rent
    flow(ax, x2+w/2, x3-w/2, b_sr[0], b_sr[1], b_sr[0], b_sr[1], CREAM, cream_a, 1)
    flow(ax, x2+w/2, x3-w/2, m_sr[0], m_sr[1], m_sr[0], m_sr[1], BLUE, blue_a, 2)

    # Not-heads -> Rent (bottom)
    flow(ax, x1+w/2, x3-w/2, m_nh[0], 0, m_nhr[0], 0, BLUE, blue_a, 2)
    flow(ax, x1+w/2, x3-w/2, b_nh[0], 0, b_nhr[0], 0, CREAM, cream_a, 1)

    # Stage 3 bars - draw both with proper layering
    # Married owners
    bar(ax, x3, w, b_mo[0], b_mo[1], CREAM, cream_a, 1)
    bar(ax, x3, w, m_mo[0], m_mo[1], BLUE, blue_a, 2)

    # Married renters
    bar(ax, x3, w, b_mr[0], b_mr[1], CREAM, cream_a, 1)
    bar(ax, x3, w, m_mr[0], m_mr[1], BLUE, blue_a, 2)

    # Single owners
    bar(ax, x3, w, b_so[0], b_so[1], CREAM, cream_a, 1)
    bar(ax, x3, w, m_so[0], m_so[1], BLUE, blue_a, 2)

    # Single renters
    bar(ax, x3, w, b_sr[0], b_sr[1], CREAM, cream_a, 1)
    bar(ax, x3, w, m_sr[0], m_sr[1], BLUE, blue_a, 2)

    # Bottom renters (not-heads)
    bar(ax, x3, w, m_nhr[0], 0, BLUE, blue_a, 2)
    bar(ax, x3, w, b_nhr[0], 0, CREAM, cream_a, 1)

    # === LABELS ===
    ax.text(x0, -5, 'BIRTH', ha='center', va='top', fontsize=11, fontweight='bold', color=BLACK)

    ax.text((x0+x1)/2, (100 + m_heads[1])/2, 'BECOME\nHOUSEHOLD\nHEADS',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    ax.text((x0+x1)/2, m_nh[0]/2, 'LIVE WITH\nPARENTS / FRIENDS',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    ax.text((x1+x2)/2, (100 + m_married[1])/2, 'GET\nMARRIED',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    ax.text((x1+x2)/2, (m_single[0] + m_single[1])/2, 'REMAIN\nSINGLE',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    # Outcome labels
    ax.text(x3 + w/2 + 0.015, (m_mo[0] + b_mo[1])/2, 'BUY\nHOME',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)
    ax.text(x3 + w/2 + 0.015, (m_mr[0] + b_mr[1])/2, 'RENT',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)
    ax.text(x3 + w/2 + 0.015, (m_so[0] + b_so[1])/2, 'BUY\nHOME',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)
    ax.text(x3 + w/2 + 0.015, 12, 'RENT',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)

    # Percentage labels
    lx = 0.995

    ax.text(lx, (b_mo[0] + b_mo[1])/2, f"{b['m_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color='#8B8B7A')
    ax.text(lx, (m_mo[0] + m_mo[1])/2 - 4, f"{m['m_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    ax.text(lx, (b_mr[0] + b_mr[1])/2, f"{b['m_rent']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color='#8B8B7A')
    ax.text(lx, (m_mr[0] + m_mr[1])/2, f"{m['m_rent']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    ax.text(lx, (b_so[0] + b_so[1])/2 + 2, f"{b['s_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color='#8B8B7A')
    ax.text(lx, (m_so[0] + m_so[1])/2 - 2, f"{m['s_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    b_bot = b['s_rent'] + b['not_heads']
    m_bot = m['s_rent'] + m['not_heads']
    ax.text(lx, b_nhr[0]/2 + 5, f"{b_bot:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color='#8B8B7A')
    ax.text(lx, m_nhr[0]/2, f"{m_bot:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    ax.text(x1 + w/2 + 0.015, m_nh[0] + 2, f"{m['not_heads']:.0f}%",
            ha='left', va='bottom', fontsize=11, fontweight='bold', color=BLUE)
    ax.text(x1 + w/2 + 0.015, b_nh[0] - 1, f"{b['not_heads']:.0f}%",
            ha='left', va='top', fontsize=11, fontweight='bold', color='#8B8B7A')

    # Legend
    ly = 107
    ax.add_patch(mpatches.Rectangle((0.08, ly), 0.04, 3, facecolor=CREAM, alpha=0.7))
    ax.text(0.13, ly + 1.5, 'Boomers', va='center', fontsize=11, color=BLACK)
    ax.add_patch(mpatches.Rectangle((0.08, ly - 5), 0.04, 3, facecolor=BLUE, alpha=0.9))
    ax.text(0.13, ly - 3.5, 'Millennials', va='center', fontsize=11, color=BLACK)

    ax.text(0.02, 120, f'Lower rates of household formation and marriage explain a lot of\nthe Millennial-Boomer homeownership gap at age {age}',
            fontsize=15, fontweight='bold', color=BLACK, va='top')

    ax.text(0.02, -8, 'Source: CPS ASEC via IPUMS', fontsize=9, color=BLACK, alpha=0.6, style='italic')

    ax.set_xlim(0, 1.05)
    ax.set_ylim(-12, 125)
    ax.axis('off')

    return fig


for age in [30, 35, 40]:
    data = get_data(age)
    fig = make_sankey(age, data)
    fig.savefig(f'{OUT}/sankey_overlaid_v4_age_{age}.png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.rcParams['svg.fonttype'] = 'none'
    fig.savefig(f'{OUT}/sankey_overlaid_v4_age_{age}.svg', bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"Saved sankey_overlaid_v4_age_{age}")

print("Done!")
