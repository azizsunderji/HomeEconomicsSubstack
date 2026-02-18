"""
Overlaid Sankey v3: Draw Boomer "halo" (excess over Millennials) separately.
This creates the visual effect where cream shows where Boomers exceed Millennials.
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
CREAM_DARK = '#C5C9B8'
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


def smooth_flow(ax, x0, x1, y0_top, y0_bot, y1_top, y1_bot, color, alpha, zorder):
    """Draw smooth flow between two vertical segments."""
    n = 60
    t = np.linspace(0, 1, n)
    ease = 3*t**2 - 2*t**3  # ease in-out

    x = x0 + (x1 - x0) * ease
    top = y0_top + (y1_top - y0_top) * ease
    bot = y0_bot + (y1_bot - y0_bot) * ease

    verts = list(zip(x, top)) + list(zip(x[::-1], bot[::-1]))
    poly = mpatches.Polygon(verts, facecolor=color, edgecolor='none', alpha=alpha, zorder=zorder)
    ax.add_patch(poly)


def bar(ax, x, w, y_top, y_bot, color, alpha, zorder):
    """Draw vertical bar."""
    rect = mpatches.Rectangle((x - w/2, y_bot), w, y_top - y_bot,
                               facecolor=color, edgecolor='none', alpha=alpha, zorder=zorder)
    ax.add_patch(rect)


def make_sankey(age, data):
    fig, ax = plt.subplots(figsize=(11, 10), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    b = data['Boomer']
    m = data['Millennial']

    # X positions
    x0, x1, x2, x3 = 0.08, 0.32, 0.62, 0.92
    w = 0.035

    # Calculate cumulative y positions (from top=100 going down)
    def get_ys(d):
        y = {}
        # Stage 1: heads top, not_heads bottom
        y['heads_top'] = 100
        y['heads_bot'] = 100 - d['heads']
        y['nh_top'] = d['not_heads']
        y['nh_bot'] = 0

        # Stage 2: married top of heads area, single below
        y['mar_top'] = 100
        y['mar_bot'] = 100 - d['married']
        y['sin_top'] = y['mar_bot']
        y['sin_bot'] = 100 - d['heads']

        # Stage 3: cumulative from top
        c = 0
        y['mo_top'] = 100 - c; c += d['m_own']; y['mo_bot'] = 100 - c
        y['mr_top'] = 100 - c; c += d['m_rent']; y['mr_bot'] = 100 - c
        y['so_top'] = 100 - c; c += d['s_own']; y['so_bot'] = 100 - c
        y['sr_top'] = 100 - c; c += d['s_rent']; y['sr_bot'] = 100 - c
        y['nhr_top'] = 100 - c; y['nhr_bot'] = 0

        return y

    yb = get_ys(b)
    ym = get_ys(m)

    # === LAYER 1: Boomer background (full, semi-transparent) ===
    ba = 0.45  # Boomer alpha
    bz = 1     # Boomer z-order

    # Birth
    bar(ax, x0, w, 100, 0, CREAM, ba, bz)

    # Birth -> Heads
    smooth_flow(ax, x0+w/2, x1-w/2, 100, yb['heads_bot'], 100, yb['heads_bot'], CREAM, ba, bz)
    # Birth -> Not-heads
    smooth_flow(ax, x0+w/2, x1-w/2, yb['nh_top'], 0, yb['nh_top'], 0, CREAM, ba, bz)

    # Stage 1 bars
    bar(ax, x1, w, 100, yb['heads_bot'], CREAM, ba, bz)
    bar(ax, x1, w, yb['nh_top'], 0, CREAM, ba, bz)

    # Heads -> Married/Single
    smooth_flow(ax, x1+w/2, x2-w/2, 100, yb['mar_bot'], 100, yb['mar_bot'], CREAM, ba, bz)
    smooth_flow(ax, x1+w/2, x2-w/2, yb['sin_top'], yb['sin_bot'], yb['sin_top'], yb['sin_bot'], CREAM, ba, bz)

    # Stage 2 bars
    bar(ax, x2, w, 100, yb['mar_bot'], CREAM, ba, bz)
    bar(ax, x2, w, yb['sin_top'], yb['sin_bot'], CREAM, ba, bz)

    # Married -> Own/Rent
    smooth_flow(ax, x2+w/2, x3-w/2, 100, yb['mo_bot'], 100, yb['mo_bot'], CREAM, ba, bz)
    smooth_flow(ax, x2+w/2, x3-w/2, yb['mr_top'], yb['mar_bot'], yb['mr_top'], yb['mr_bot'], CREAM, ba, bz)

    # Single -> Own/Rent
    smooth_flow(ax, x2+w/2, x3-w/2, yb['sin_top'], yb['so_bot'], yb['so_top'], yb['so_bot'], CREAM, ba, bz)
    smooth_flow(ax, x2+w/2, x3-w/2, yb['so_bot'], yb['sin_bot'], yb['sr_top'], yb['sr_bot'], CREAM, ba, bz)

    # Not-heads -> Rent
    smooth_flow(ax, x1+w/2, x3-w/2, yb['nh_top'], 0, yb['nhr_top'], 0, CREAM, ba, bz)

    # Stage 3 bars
    bar(ax, x3, w, yb['mo_top'], yb['mo_bot'], CREAM, ba, bz)
    bar(ax, x3, w, yb['mr_top'], yb['mr_bot'], CREAM, ba, bz)
    bar(ax, x3, w, yb['so_top'], yb['so_bot'], CREAM, ba, bz)
    bar(ax, x3, w, yb['sr_top'], yb['sr_bot'], CREAM, ba, bz)
    bar(ax, x3, w, yb['nhr_top'], yb['nhr_bot'], CREAM, ba, bz)

    # === LAYER 2: Millennial foreground ===
    ma = 0.85
    mz = 2

    # Birth
    bar(ax, x0, w, 100, 0, BLUE, ma, mz)

    # Birth -> Heads
    smooth_flow(ax, x0+w/2, x1-w/2, 100, ym['heads_bot'], 100, ym['heads_bot'], BLUE, ma, mz)
    # Birth -> Not-heads
    smooth_flow(ax, x0+w/2, x1-w/2, ym['nh_top'], 0, ym['nh_top'], 0, BLUE, ma, mz)

    # Stage 1 bars
    bar(ax, x1, w, 100, ym['heads_bot'], BLUE, ma, mz)
    bar(ax, x1, w, ym['nh_top'], 0, BLUE, ma, mz)

    # Heads -> Married/Single
    smooth_flow(ax, x1+w/2, x2-w/2, 100, ym['mar_bot'], 100, ym['mar_bot'], BLUE, ma, mz)
    smooth_flow(ax, x1+w/2, x2-w/2, ym['sin_top'], ym['sin_bot'], ym['sin_top'], ym['sin_bot'], BLUE, ma, mz)

    # Stage 2 bars
    bar(ax, x2, w, 100, ym['mar_bot'], BLUE, ma, mz)
    bar(ax, x2, w, ym['sin_top'], ym['sin_bot'], BLUE, ma, mz)

    # Married -> Own/Rent
    smooth_flow(ax, x2+w/2, x3-w/2, 100, ym['mo_bot'], 100, ym['mo_bot'], BLUE, ma, mz)
    smooth_flow(ax, x2+w/2, x3-w/2, ym['mr_top'], ym['mar_bot'], ym['mr_top'], ym['mr_bot'], BLUE, ma, mz)

    # Single -> Own/Rent
    smooth_flow(ax, x2+w/2, x3-w/2, ym['sin_top'], ym['so_bot'], ym['so_top'], ym['so_bot'], BLUE, ma, mz)
    smooth_flow(ax, x2+w/2, x3-w/2, ym['so_bot'], ym['sin_bot'], ym['sr_top'], ym['sr_bot'], BLUE, ma, mz)

    # Not-heads -> Rent
    smooth_flow(ax, x1+w/2, x3-w/2, ym['nh_top'], 0, ym['nhr_top'], 0, BLUE, ma, mz)

    # Stage 3 bars
    bar(ax, x3, w, ym['mo_top'], ym['mo_bot'], BLUE, ma, mz)
    bar(ax, x3, w, ym['mr_top'], ym['mr_bot'], BLUE, ma, mz)
    bar(ax, x3, w, ym['so_top'], ym['so_bot'], BLUE, ma, mz)
    bar(ax, x3, w, ym['sr_top'], ym['sr_bot'], BLUE, ma, mz)
    bar(ax, x3, w, ym['nhr_top'], ym['nhr_bot'], BLUE, ma, mz)

    # === LABELS ===
    # Stage labels
    ax.text(x0, -5, 'BIRTH', ha='center', va='top', fontsize=11, fontweight='bold', color=BLACK)

    ax.text((x0+x1)/2, (100 + ym['heads_bot'])/2 + 3, 'BECOME\nHOUSEHOLD\nHEADS',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    ax.text((x0+x1)/2, ym['nh_top']/2, 'LIVE WITH\nPARENTS / FRIENDS',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    ax.text((x1+x2)/2, (100 + ym['mar_bot'])/2, 'GET\nMARRIED',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    ax.text((x1+x2)/2, (ym['sin_top'] + ym['sin_bot'])/2, 'REMAIN\nSINGLE',
            ha='center', va='center', fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    # Outcome labels
    ax.text(x3 + w/2 + 0.015, (ym['mo_top'] + yb['mo_bot'])/2, 'BUY\nHOME',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)
    ax.text(x3 + w/2 + 0.015, (ym['mr_top'] + yb['mr_bot'])/2, 'RENT',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)
    ax.text(x3 + w/2 + 0.015, (ym['so_top'] + yb['so_bot'])/2, 'BUY\nHOME',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)
    ax.text(x3 + w/2 + 0.015, 12, 'RENT',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)

    # Percentage labels (right edge)
    lx = 0.995

    # Married owners
    ax.text(lx, (yb['mo_top'] + yb['mo_bot'])/2, f"{b['m_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=CREAM_DARK)
    ax.text(lx, (ym['mo_top'] + ym['mo_bot'])/2 - 5, f"{m['m_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    # Married renters
    ax.text(lx, (yb['mr_top'] + yb['mr_bot'])/2, f"{b['m_rent']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=CREAM_DARK)
    ax.text(lx, (ym['mr_top'] + ym['mr_bot'])/2 - 3, f"{m['m_rent']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    # Single owners
    ax.text(lx, (yb['so_top'] + yb['so_bot'])/2 + 2, f"{b['s_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=CREAM_DARK)
    ax.text(lx, (ym['so_top'] + ym['so_bot'])/2 - 2, f"{m['s_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    # Bottom rent
    b_bot = b['s_rent'] + b['not_heads']
    m_bot = m['s_rent'] + m['not_heads']
    ax.text(lx, yb['nhr_top']/2 + 4, f"{b_bot:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=CREAM_DARK)
    ax.text(lx, ym['nhr_top']/2 - 2, f"{m_bot:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    # Not-head %s
    ax.text(x1 + w/2 + 0.015, ym['nh_top'] + 2, f"{m['not_heads']:.0f}%",
            ha='left', va='bottom', fontsize=11, fontweight='bold', color=BLUE)
    ax.text(x1 + w/2 + 0.015, yb['nh_top'] - 2, f"{b['not_heads']:.0f}%",
            ha='left', va='top', fontsize=11, fontweight='bold', color=CREAM_DARK)

    # Legend
    ly = 107
    ax.add_patch(mpatches.Rectangle((0.08, ly), 0.04, 3, facecolor=CREAM, alpha=0.6))
    ax.text(0.13, ly + 1.5, 'Boomers', va='center', fontsize=11, color=BLACK)
    ax.add_patch(mpatches.Rectangle((0.08, ly - 5), 0.04, 3, facecolor=BLUE, alpha=0.85))
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
    fig.savefig(f'{OUT}/sankey_overlaid_v3_age_{age}.png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.rcParams['svg.fonttype'] = 'none'
    fig.savefig(f'{OUT}/sankey_overlaid_v3_age_{age}.svg', bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"Saved sankey_overlaid_v3_age_{age}")

print("Done!")
