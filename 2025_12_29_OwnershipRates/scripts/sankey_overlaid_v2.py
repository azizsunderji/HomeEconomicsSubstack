"""
Overlaid Sankey v2: Correct geometry where both generations share TOP alignment.
Boomers (cream) behind, Millennials (blue) in front.
Cream shows through where Boomers exceed Millennials.
"""

import duckdb
import numpy as np
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
import matplotlib.font_manager as fm

# ── Fonts ──
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for f in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{f}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

# ── Colors (matching reference) ──
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


def make_flow(ax, x0, x1, y0_top, y0_bot, y1_top, y1_bot, color, alpha, zorder):
    """Draw a smooth flow between two vertical segments."""
    # Use cubic bezier for smooth S-curve
    n_points = 50
    t = np.linspace(0, 1, n_points)

    # Smooth interpolation for x (ease in-out)
    x_interp = x0 + (x1 - x0) * (3*t**2 - 2*t**3)

    # Top edge
    top_interp = y0_top + (y1_top - y0_top) * (3*t**2 - 2*t**3)
    # Bottom edge
    bot_interp = y0_bot + (y1_bot - y0_bot) * (3*t**2 - 2*t**3)

    # Create polygon
    verts = list(zip(x_interp, top_interp)) + list(zip(x_interp[::-1], bot_interp[::-1]))
    poly = mpatches.Polygon(verts, facecolor=color, edgecolor='none', alpha=alpha, zorder=zorder)
    ax.add_patch(poly)


def make_bar(ax, x, width, y_top, y_bot, color, alpha, zorder):
    """Draw a vertical bar."""
    rect = mpatches.Rectangle((x - width/2, y_bot), width, y_top - y_bot,
                                facecolor=color, edgecolor='none', alpha=alpha, zorder=zorder)
    ax.add_patch(rect)


def make_sankey(age, data):
    """Create overlaid Sankey for given age."""
    fig, ax = plt.subplots(figsize=(11, 10), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    b = data['Boomer']
    m = data['Millennial']

    # X positions for stages
    x0 = 0.08   # Birth
    x1 = 0.32   # Heads/Not-heads
    x2 = 0.62   # Married/Single
    x3 = 0.92   # Own/Rent
    bar_w = 0.035

    # Calculate y-positions for each generation
    # All measured from TOP (100) going DOWN
    # Y ranges: 0 = bottom, 100 = top

    def calc_y(d):
        """Calculate y-positions (top, bottom) for each segment."""
        y = {}
        # Stage 0: Birth (everyone)
        y['birth'] = (100, 0)

        # Stage 1: Heads (top), Not-heads (bottom)
        y['heads'] = (100, 100 - d['heads'])
        y['not_heads'] = (d['not_heads'], 0)

        # Stage 2: Married (top of heads), Single (bottom of heads)
        y['married'] = (100, 100 - d['married'])
        y['single'] = (100 - d['married'], 100 - d['married'] - d['single'])

        # Stage 3: Final outcomes (from top to bottom)
        # married_own, married_rent, single_own, single_rent, not_heads_rent
        cumsum = 0
        y['m_own'] = (100 - cumsum, 100 - cumsum - d['m_own'])
        cumsum += d['m_own']
        y['m_rent'] = (100 - cumsum, 100 - cumsum - d['m_rent'])
        cumsum += d['m_rent']
        y['s_own'] = (100 - cumsum, 100 - cumsum - d['s_own'])
        cumsum += d['s_own']
        y['s_rent'] = (100 - cumsum, 100 - cumsum - d['s_rent'])
        cumsum += d['s_rent']
        y['nh_rent'] = (100 - cumsum, 0)  # remaining is not_heads

        return y

    yb = calc_y(b)
    ym = calc_y(m)

    # Draw Boomers first (behind)
    b_alpha = 0.6
    b_z = 1

    # Birth bar
    make_bar(ax, x0, bar_w, 100, 0, CREAM, b_alpha, b_z)

    # Birth -> Heads flow
    make_flow(ax, x0+bar_w/2, x1-bar_w/2, yb['birth'][0], yb['heads'][1], yb['heads'][0], yb['heads'][1], CREAM, b_alpha, b_z)
    # Birth -> Not-heads flow
    make_flow(ax, x0+bar_w/2, x1-bar_w/2, yb['not_heads'][0], yb['birth'][1], yb['not_heads'][0], yb['not_heads'][1], CREAM, b_alpha, b_z)

    # Stage 1 bars
    make_bar(ax, x1, bar_w, yb['heads'][0], yb['heads'][1], CREAM, b_alpha, b_z)
    make_bar(ax, x1, bar_w, yb['not_heads'][0], yb['not_heads'][1], CREAM, b_alpha, b_z)

    # Heads -> Married flow
    make_flow(ax, x1+bar_w/2, x2-bar_w/2, yb['heads'][0], yb['married'][1], yb['married'][0], yb['married'][1], CREAM, b_alpha, b_z)
    # Heads -> Single flow
    make_flow(ax, x1+bar_w/2, x2-bar_w/2, yb['single'][0], yb['heads'][1], yb['single'][0], yb['single'][1], CREAM, b_alpha, b_z)

    # Stage 2 bars
    make_bar(ax, x2, bar_w, yb['married'][0], yb['married'][1], CREAM, b_alpha, b_z)
    make_bar(ax, x2, bar_w, yb['single'][0], yb['single'][1], CREAM, b_alpha, b_z)

    # Married -> Own/Rent flows
    make_flow(ax, x2+bar_w/2, x3-bar_w/2, yb['married'][0], yb['m_own'][1], yb['m_own'][0], yb['m_own'][1], CREAM, b_alpha, b_z)
    make_flow(ax, x2+bar_w/2, x3-bar_w/2, yb['m_own'][1], yb['married'][1], yb['m_rent'][0], yb['m_rent'][1], CREAM, b_alpha, b_z)

    # Single -> Own/Rent flows
    make_flow(ax, x2+bar_w/2, x3-bar_w/2, yb['single'][0], yb['s_own'][1], yb['s_own'][0], yb['s_own'][1], CREAM, b_alpha, b_z)
    make_flow(ax, x2+bar_w/2, x3-bar_w/2, yb['s_own'][1], yb['single'][1], yb['s_rent'][0], yb['s_rent'][1], CREAM, b_alpha, b_z)

    # Not-heads -> Rent flow
    make_flow(ax, x1+bar_w/2, x3-bar_w/2, yb['not_heads'][0], yb['not_heads'][1], yb['nh_rent'][0], yb['nh_rent'][1], CREAM, b_alpha, b_z)

    # Stage 3 bars (Boomers)
    make_bar(ax, x3, bar_w, yb['m_own'][0], yb['m_own'][1], CREAM, b_alpha, b_z)
    make_bar(ax, x3, bar_w, yb['m_rent'][0], yb['m_rent'][1], CREAM, b_alpha, b_z)
    make_bar(ax, x3, bar_w, yb['s_own'][0], yb['s_own'][1], CREAM, b_alpha, b_z)
    make_bar(ax, x3, bar_w, yb['s_rent'][0], yb['s_rent'][1], CREAM, b_alpha, b_z)
    make_bar(ax, x3, bar_w, yb['nh_rent'][0], yb['nh_rent'][1], CREAM, b_alpha, b_z)

    # Now draw Millennials (in front)
    m_alpha = 0.85
    m_z = 2

    # Birth bar
    make_bar(ax, x0, bar_w, 100, 0, BLUE, m_alpha, m_z)

    # Birth -> Heads flow
    make_flow(ax, x0+bar_w/2, x1-bar_w/2, ym['birth'][0], ym['heads'][1], ym['heads'][0], ym['heads'][1], BLUE, m_alpha, m_z)
    # Birth -> Not-heads flow
    make_flow(ax, x0+bar_w/2, x1-bar_w/2, ym['not_heads'][0], ym['birth'][1], ym['not_heads'][0], ym['not_heads'][1], BLUE, m_alpha, m_z)

    # Stage 1 bars
    make_bar(ax, x1, bar_w, ym['heads'][0], ym['heads'][1], BLUE, m_alpha, m_z)
    make_bar(ax, x1, bar_w, ym['not_heads'][0], ym['not_heads'][1], BLUE, m_alpha, m_z)

    # Heads -> Married flow
    make_flow(ax, x1+bar_w/2, x2-bar_w/2, ym['heads'][0], ym['married'][1], ym['married'][0], ym['married'][1], BLUE, m_alpha, m_z)
    # Heads -> Single flow
    make_flow(ax, x1+bar_w/2, x2-bar_w/2, ym['single'][0], ym['heads'][1], ym['single'][0], ym['single'][1], BLUE, m_alpha, m_z)

    # Stage 2 bars
    make_bar(ax, x2, bar_w, ym['married'][0], ym['married'][1], BLUE, m_alpha, m_z)
    make_bar(ax, x2, bar_w, ym['single'][0], ym['single'][1], BLUE, m_alpha, m_z)

    # Married -> Own/Rent flows
    make_flow(ax, x2+bar_w/2, x3-bar_w/2, ym['married'][0], ym['m_own'][1], ym['m_own'][0], ym['m_own'][1], BLUE, m_alpha, m_z)
    make_flow(ax, x2+bar_w/2, x3-bar_w/2, ym['m_own'][1], ym['married'][1], ym['m_rent'][0], ym['m_rent'][1], BLUE, m_alpha, m_z)

    # Single -> Own/Rent flows
    make_flow(ax, x2+bar_w/2, x3-bar_w/2, ym['single'][0], ym['s_own'][1], ym['s_own'][0], ym['s_own'][1], BLUE, m_alpha, m_z)
    make_flow(ax, x2+bar_w/2, x3-bar_w/2, ym['s_own'][1], ym['single'][1], ym['s_rent'][0], ym['s_rent'][1], BLUE, m_alpha, m_z)

    # Not-heads -> Rent flow
    make_flow(ax, x1+bar_w/2, x3-bar_w/2, ym['not_heads'][0], ym['not_heads'][1], ym['nh_rent'][0], ym['nh_rent'][1], BLUE, m_alpha, m_z)

    # Stage 3 bars (Millennials)
    make_bar(ax, x3, bar_w, ym['m_own'][0], ym['m_own'][1], BLUE, m_alpha, m_z)
    make_bar(ax, x3, bar_w, ym['m_rent'][0], ym['m_rent'][1], BLUE, m_alpha, m_z)
    make_bar(ax, x3, bar_w, ym['s_own'][0], ym['s_own'][1], BLUE, m_alpha, m_z)
    make_bar(ax, x3, bar_w, ym['s_rent'][0], ym['s_rent'][1], BLUE, m_alpha, m_z)
    make_bar(ax, x3, bar_w, ym['nh_rent'][0], ym['nh_rent'][1], BLUE, m_alpha, m_z)

    # ── LABELS ──
    # Stage names (in the flows)
    ax.text(x0, -4, 'BIRTH', ha='center', va='top', fontsize=11, fontweight='bold', color=BLACK)

    # "Become household heads" - in the heads flow area
    heads_mid = (ym['heads'][0] + ym['heads'][1]) / 2 + 5
    ax.text((x0+x1)/2, heads_mid, 'BECOME\nHOUSEHOLD\nHEADS', ha='center', va='center',
            fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    # "Live with parents" - in the not-heads area
    nh_mid = (max(ym['not_heads'][0], yb['not_heads'][0])) / 2
    ax.text((x0+x1)/2, nh_mid, 'LIVE WITH\nPARENTS / FRIENDS', ha='center', va='center',
            fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    # "Get married"
    married_mid = (ym['married'][0] + ym['married'][1]) / 2 + 3
    ax.text((x1+x2)/2, married_mid, 'GET\nMARRIED', ha='center', va='center',
            fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    # "Remain single"
    single_mid = (ym['single'][0] + ym['single'][1]) / 2
    ax.text((x1+x2)/2, single_mid, 'REMAIN\nSINGLE', ha='center', va='center',
            fontsize=10, fontweight='bold', color=BLACK, zorder=10)

    # Outcome labels (right side)
    ax.text(x3 + bar_w/2 + 0.015, (ym['m_own'][0] + yb['m_own'][1])/2, 'BUY\nHOME',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)

    ax.text(x3 + bar_w/2 + 0.015, (ym['m_rent'][0] + yb['m_rent'][1])/2, 'RENT',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)

    ax.text(x3 + bar_w/2 + 0.015, (ym['s_own'][0] + yb['s_own'][1])/2, 'BUY\nHOME',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)

    ax.text(x3 + bar_w/2 + 0.015, (ym['nh_rent'][0] + 5), 'RENT',
            ha='left', va='center', fontsize=10, fontweight='bold', color=BLACK)

    # Percentage labels (right edge)
    lx = 0.995

    # Married owners
    ax.text(lx, (yb['m_own'][0] + yb['m_own'][1])/2, f"{b['m_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color='#8B8B7A')
    ax.text(lx, (ym['m_own'][0] + ym['m_own'][1])/2, f"{m['m_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    # Married renters
    ax.text(lx, (yb['m_rent'][0] + yb['m_rent'][1])/2, f"{b['m_rent']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color='#8B8B7A')
    ax.text(lx, (ym['m_rent'][0] + ym['m_rent'][1])/2, f"{m['m_rent']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    # Single owners
    ax.text(lx, (yb['s_own'][0] + yb['s_own'][1])/2 + 1.5, f"{b['s_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color='#8B8B7A')
    ax.text(lx, (ym['s_own'][0] + ym['s_own'][1])/2 - 1.5, f"{m['s_own']:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    # Bottom rent (single rent + not heads)
    b_bot = b['s_rent'] + b['not_heads']
    m_bot = m['s_rent'] + m['not_heads']
    ax.text(lx, yb['not_heads'][0]/2 + 3, f"{b_bot:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color='#8B8B7A')
    ax.text(lx, ym['not_heads'][0]/2, f"{m_bot:.0f}%",
            ha='right', va='center', fontsize=11, fontweight='bold', color=BLUE)

    # Not-heads percentages (at stage 1)
    ax.text(x1 + bar_w/2 + 0.015, ym['not_heads'][0] + 2, f"{m['not_heads']:.0f}%",
            ha='left', va='bottom', fontsize=11, fontweight='bold', color=BLUE)
    ax.text(x1 + bar_w/2 + 0.015, yb['not_heads'][0] - 1, f"{b['not_heads']:.0f}%",
            ha='left', va='top', fontsize=11, fontweight='bold', color='#8B8B7A')

    # ── Legend ──
    leg_y = 107
    ax.add_patch(mpatches.Rectangle((0.08, leg_y), 0.04, 3, facecolor=CREAM, alpha=0.7, zorder=5))
    ax.text(0.13, leg_y + 1.5, 'Boomers', va='center', fontsize=11, color=BLACK)
    ax.add_patch(mpatches.Rectangle((0.08, leg_y - 5), 0.04, 3, facecolor=BLUE, alpha=0.85, zorder=5))
    ax.text(0.13, leg_y - 3.5, 'Millennials', va='center', fontsize=11, color=BLACK)

    # ── Title ──
    ax.text(0.02, 120, f'Lower rates of household formation and marriage explain a lot of\nthe Millennial-Boomer homeownership gap at age {age}',
            fontsize=15, fontweight='bold', color=BLACK, va='top')

    # ── Source ──
    ax.text(0.02, -8, 'Source: CPS ASEC via IPUMS', fontsize=9, color=BLACK, alpha=0.6, style='italic')

    ax.set_xlim(0, 1.05)
    ax.set_ylim(-12, 125)
    ax.axis('off')

    return fig


# Generate for all ages
for age in [30, 35, 40]:
    data = get_data(age)
    fig = make_sankey(age, data)

    fig.savefig(f'{OUT}/sankey_overlaid_v2_age_{age}.png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.rcParams['svg.fonttype'] = 'none'
    fig.savefig(f'{OUT}/sankey_overlaid_v2_age_{age}.svg', bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"Saved sankey_overlaid_v2_age_{age}")

print("Done!")
