"""
Overlaid Sankey v5: BOTTOM-ALIGNED, matching the user's Illustrator technique.
- Both generations start at y=0 (bottom) and extend upward
- Nodes/bars are fully opaque
- Flows have reduced opacity to show overlap
- Cream (Boomers) drawn first, Blue (Millennials) on top
- Excess shows at TOP where one generation exceeds the other
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


def flow(ax, x0, x1, y0_bot, y0_top, y1_bot, y1_top, color, alpha, zorder):
    """Draw smooth S-curve flow. Coordinates are (bottom, top) for each end."""
    if y0_top <= y0_bot or y1_top <= y1_bot:
        return

    n = 50
    t = np.linspace(0, 1, n)
    ease = 3*t**2 - 2*t**3

    x = x0 + (x1 - x0) * ease
    top = y0_top + (y1_top - y0_top) * ease
    bot = y0_bot + (y1_bot - y0_bot) * ease

    verts = list(zip(x, top)) + list(zip(x[::-1], bot[::-1]))
    poly = mpatches.Polygon(verts, facecolor=color, edgecolor='none', alpha=alpha, zorder=zorder)
    ax.add_patch(poly)


def bar(ax, x, w, y_bot, y_top, color, alpha, zorder):
    """Draw vertical bar from y_bot to y_top."""
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

    # BOTTOM-ALIGNED positions
    # Stage 0 (Birth): 0 to 100 for both
    # Stage 1: Heads on top (from not_heads height to 100), Not-heads on bottom (0 to not_heads)
    # Within Heads: Single at bottom, Married above
    # Stage 3: Stack from bottom: not_heads_rent, single_rent, single_own, married_rent, married_own

    # The split point between heads and not-heads
    # Use max(not_heads) as the split so both fit
    split = max(b['not_heads'], m['not_heads'])

    # Scale factors to fit everything in 0-100
    # Heads section: from split to 100
    # Not-heads section: from 0 to split

    heads_height = 100 - split

    # Within heads section, bottom-align married and single
    # Single at bottom of heads section, married above

    # Boomer positions (bottom, top)
    b_birth = (0, 100)
    b_heads_bot = split
    b_heads_top = split + b['heads'] * heads_height / max(b['heads'], m['heads'])
    b_nh_bot = 0
    b_nh_top = b['not_heads'] * split / max(b['not_heads'], m['not_heads'])

    # Actually, let's simplify: use the actual percentages directly
    # and let the visual overlap show the difference

    # Simpler approach: both generations use same coordinate system
    # Bars are positioned based on cumulative percentages from bottom

    # Stage 1 positions (from bottom up)
    # Not-heads: 0 to not_heads%
    # Heads: not_heads% to 100%

    # For Boomer:
    b_nh = (0, b['not_heads'])
    b_heads = (b['not_heads'], 100)

    # For Millennial:
    m_nh = (0, m['not_heads'])
    m_heads = (m['not_heads'], 100)

    # Stage 2: Within heads area
    # Single at bottom of heads, Married at top
    # Boomer:
    b_single = (b['not_heads'], b['not_heads'] + b['single'])
    b_married = (b['not_heads'] + b['single'], 100)

    # Millennial:
    m_single = (m['not_heads'], m['not_heads'] + m['single'])
    m_married = (m['not_heads'] + m['single'], 100)

    # Stage 3: Final outcomes, stacked from bottom
    # Order: not_heads_rent, single_rent, single_own, married_rent, married_own
    # Boomer:
    bc = 0
    b_nhr = (bc, bc + b['not_heads']); bc += b['not_heads']
    b_sr = (bc, bc + b['s_rent']); bc += b['s_rent']
    b_so = (bc, bc + b['s_own']); bc += b['s_own']
    b_mr = (bc, bc + b['m_rent']); bc += b['m_rent']
    b_mo = (bc, bc + b['m_own'])

    # Millennial:
    mc = 0
    m_nhr = (mc, mc + m['not_heads']); mc += m['not_heads']
    m_sr = (mc, mc + m['s_rent']); mc += m['s_rent']
    m_so = (mc, mc + m['s_own']); mc += m['s_own']
    m_mr = (mc, mc + m['m_rent']); mc += m['m_rent']
    m_mo = (mc, mc + m['m_own'])

    # Drawing: Bars opaque, flows semi-transparent
    bar_alpha = 1.0
    flow_alpha = 0.7

    # === DRAW BOOMERS FIRST (cream, behind) ===
    bz = 1  # z-order

    # Birth bar
    bar(ax, x0, w, 0, 100, CREAM, bar_alpha, bz)

    # Birth -> Heads flow
    flow(ax, x0+w/2, x1-w/2, b_heads[0], b_heads[1], b_heads[0], b_heads[1], CREAM, flow_alpha, bz)
    # Birth -> Not-heads flow
    flow(ax, x0+w/2, x1-w/2, b_nh[0], b_nh[1], b_nh[0], b_nh[1], CREAM, flow_alpha, bz)

    # Stage 1 bars
    bar(ax, x1, w, b_heads[0], b_heads[1], CREAM, bar_alpha, bz)
    bar(ax, x1, w, b_nh[0], b_nh[1], CREAM, bar_alpha, bz)

    # Heads -> Married flow
    flow(ax, x1+w/2, x2-w/2, b_married[0], b_married[1], b_married[0], b_married[1], CREAM, flow_alpha, bz)
    # Heads -> Single flow
    flow(ax, x1+w/2, x2-w/2, b_single[0], b_single[1], b_single[0], b_single[1], CREAM, flow_alpha, bz)

    # Stage 2 bars
    bar(ax, x2, w, b_married[0], b_married[1], CREAM, bar_alpha, bz)
    bar(ax, x2, w, b_single[0], b_single[1], CREAM, bar_alpha, bz)

    # Married -> Own/Rent flows
    flow(ax, x2+w/2, x3-w/2, b_mo[0], b_mo[1], b_mo[0], b_mo[1], CREAM, flow_alpha, bz)
    flow(ax, x2+w/2, x3-w/2, b_mr[0], b_mr[1], b_mr[0], b_mr[1], CREAM, flow_alpha, bz)

    # Single -> Own/Rent flows
    flow(ax, x2+w/2, x3-w/2, b_so[0], b_so[1], b_so[0], b_so[1], CREAM, flow_alpha, bz)
    flow(ax, x2+w/2, x3-w/2, b_sr[0], b_sr[1], b_sr[0], b_sr[1], CREAM, flow_alpha, bz)

    # Not-heads -> Rent flow
    flow(ax, x1+w/2, x3-w/2, b_nhr[0], b_nhr[1], b_nhr[0], b_nhr[1], CREAM, flow_alpha, bz)

    # Stage 3 bars
    bar(ax, x3, w, b_mo[0], b_mo[1], CREAM, bar_alpha, bz)
    bar(ax, x3, w, b_mr[0], b_mr[1], CREAM, bar_alpha, bz)
    bar(ax, x3, w, b_so[0], b_so[1], CREAM, bar_alpha, bz)
    bar(ax, x3, w, b_sr[0], b_sr[1], CREAM, bar_alpha, bz)
    bar(ax, x3, w, b_nhr[0], b_nhr[1], CREAM, bar_alpha, bz)

    # === DRAW MILLENNIALS (blue, in front) ===
    mz = 2

    # Birth bar
    bar(ax, x0, w, 0, 100, BLUE, bar_alpha, mz)

    # Birth -> Heads flow
    flow(ax, x0+w/2, x1-w/2, m_heads[0], m_heads[1], m_heads[0], m_heads[1], BLUE, flow_alpha, mz)
    # Birth -> Not-heads flow
    flow(ax, x0+w/2, x1-w/2, m_nh[0], m_nh[1], m_nh[0], m_nh[1], BLUE, flow_alpha, mz)

    # Stage 1 bars
    bar(ax, x1, w, m_heads[0], m_heads[1], BLUE, bar_alpha, mz)
    bar(ax, x1, w, m_nh[0], m_nh[1], BLUE, bar_alpha, mz)

    # Heads -> Married flow
    flow(ax, x1+w/2, x2-w/2, m_married[0], m_married[1], m_married[0], m_married[1], BLUE, flow_alpha, mz)
    # Heads -> Single flow
    flow(ax, x1+w/2, x2-w/2, m_single[0], m_single[1], m_single[0], m_single[1], BLUE, flow_alpha, mz)

    # Stage 2 bars
    bar(ax, x2, w, m_married[0], m_married[1], BLUE, bar_alpha, mz)
    bar(ax, x2, w, m_single[0], m_single[1], BLUE, bar_alpha, mz)

    # Married -> Own/Rent flows
    flow(ax, x2+w/2, x3-w/2, m_mo[0], m_mo[1], m_mo[0], m_mo[1], BLUE, flow_alpha, mz)
    flow(ax, x2+w/2, x3-w/2, m_mr[0], m_mr[1], m_mr[0], m_mr[1], BLUE, flow_alpha, mz)

    # Single -> Own/Rent flows
    flow(ax, x2+w/2, x3-w/2, m_so[0], m_so[1], m_so[0], m_so[1], BLUE, flow_alpha, mz)
    flow(ax, x2+w/2, x3-w/2, m_sr[0], m_sr[1], m_sr[0], m_sr[1], BLUE, flow_alpha, mz)

    # Not-heads -> Rent flow
    flow(ax, x1+w/2, x3-w/2, m_nhr[0], m_nhr[1], m_nhr[0], m_nhr[1], BLUE, flow_alpha, mz)

    # Stage 3 bars
    bar(ax, x3, w, m_mo[0], m_mo[1], BLUE, bar_alpha, mz)
    bar(ax, x3, w, m_mr[0], m_mr[1], BLUE, bar_alpha, mz)
    bar(ax, x3, w, m_so[0], m_so[1], BLUE, bar_alpha, mz)
    bar(ax, x3, w, m_sr[0], m_sr[1], BLUE, bar_alpha, mz)
    bar(ax, x3, w, m_nhr[0], m_nhr[1], BLUE, bar_alpha, mz)

    # === LABELS ===
    ax.text(x0, -5, 'BIRTH', ha='center', va='top', fontsize=11, fontweight='bold', color=BLACK)

    ax.text((x0+x1)/2, (m_heads[0] + m_heads[1])/2 + 3, 'BECOME\nHOUSEHOLD\nHEADS',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    ax.text((x0+x1)/2, m_nh[1]/2, 'LIVE WITH\nPARENTS / FRIENDS',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    ax.text((x1+x2)/2, (m_married[0] + m_married[1])/2, 'GET\nMARRIED',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    ax.text((x1+x2)/2, (m_single[0] + m_single[1])/2, 'REMAIN\nSINGLE',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    # Outcome labels (right side)
    ax.text(x3 + w/2 + 0.015, (m_mo[0] + b_mo[1])/2, 'BUY\nHOME',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)
    ax.text(x3 + w/2 + 0.015, (m_mr[0] + b_mr[1])/2, 'RENT',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)
    ax.text(x3 + w/2 + 0.015, (m_so[0] + b_so[1])/2, 'BUY\nHOME',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)
    ax.text(x3 + w/2 + 0.015, m_nhr[1]/2, 'RENT',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)

    # Percentage labels (right edge)
    lx = 0.995
    label_color = '#7A7A6A'

    # Married owners (top)
    ax.text(lx, b_mo[1], f"{b['m_own']:.0f}%", ha='right', va='bottom',
            fontsize=11, fontweight='bold', color=label_color)
    ax.text(lx, m_mo[1] - 5, f"{m['m_own']:.0f}%", ha='right', va='top',
            fontsize=11, fontweight='bold', color=BLUE)

    # Married renters
    ax.text(lx, b_mr[1], f"{b['m_rent']:.0f}%", ha='right', va='bottom',
            fontsize=11, fontweight='bold', color=label_color)
    ax.text(lx, m_mr[1] - 2, f"{m['m_rent']:.0f}%", ha='right', va='top',
            fontsize=11, fontweight='bold', color=BLUE)

    # Single owners
    ax.text(lx, b_so[1] + 1, f"{b['s_own']:.0f}%", ha='right', va='bottom',
            fontsize=11, fontweight='bold', color=label_color)
    ax.text(lx, m_so[1] - 1, f"{m['s_own']:.0f}%", ha='right', va='top',
            fontsize=11, fontweight='bold', color=BLUE)

    # Bottom rent
    b_bot = b['s_rent'] + b['not_heads']
    m_bot = m['s_rent'] + m['not_heads']
    ax.text(lx, b_sr[0] - 1, f"{b_bot:.0f}%", ha='right', va='top',
            fontsize=11, fontweight='bold', color=label_color)
    ax.text(lx, m_nhr[1] + 1, f"{m_bot:.0f}%", ha='right', va='bottom',
            fontsize=11, fontweight='bold', color=BLUE)

    # Not-heads % (at stage 1)
    ax.text(x1 + w/2 + 0.015, m_nh[1] + 1, f"{m['not_heads']:.0f}%",
            ha='left', va='bottom', fontsize=11, fontweight='bold', color=BLUE)
    ax.text(x1 + w/2 + 0.015, b_nh[1] - 1, f"{b['not_heads']:.0f}%",
            ha='left', va='top', fontsize=11, fontweight='bold', color=label_color)

    # Legend
    ly = 107
    ax.add_patch(mpatches.Rectangle((0.08, ly), 0.04, 3, facecolor=CREAM, alpha=1))
    ax.text(0.13, ly + 1.5, 'Boomers', va='center', fontsize=11, color=BLACK)
    ax.add_patch(mpatches.Rectangle((0.08, ly - 5), 0.04, 3, facecolor=BLUE, alpha=1))
    ax.text(0.13, ly - 3.5, 'Millennials', va='center', fontsize=11, color=BLACK)

    # Title
    ax.text(0.02, 120, f'Lower rates of household formation and marriage explain a lot of\nthe Millennial-Boomer homeownership gap at age {age}',
            fontsize=15, fontweight='bold', color=BLACK, va='top')

    # Source
    ax.text(0.02, -8, 'Source: CPS ASEC via IPUMS', fontsize=9, color=BLACK, alpha=0.6, style='italic')

    ax.set_xlim(0, 1.05)
    ax.set_ylim(-12, 125)
    ax.axis('off')

    return fig


for age in [30, 35, 40]:
    data = get_data(age)
    fig = make_sankey(age, data)
    fig.savefig(f'{OUT}/sankey_overlaid_v5_age_{age}.png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.rcParams['svg.fonttype'] = 'none'
    fig.savefig(f'{OUT}/sankey_overlaid_v5_age_{age}.svg', bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"Saved sankey_overlaid_v5_age_{age}")

print("Done!")
