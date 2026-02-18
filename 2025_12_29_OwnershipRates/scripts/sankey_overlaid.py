"""
Overlaid Sankey charts: Boomers (cream, behind) and Millennials (blue, front)
for ages 30, 35, and 40.

Flow structure:
  BIRTH → BECOME HOUSEHOLD HEADS / LIVE WITH PARENTS
       → GET MARRIED / REMAIN SINGLE
       → BUY HOME / RENT
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

# ── Colors ──
BLUE = '#0BB4FF'
BLUE_LIGHT = '#7DD6FF'
CREAM = '#DADFCE'
CREAM_DARK = '#C5C9B8'
BG = '#F6F7F3'
BLACK = '#3D3733'

DATA = '/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec.parquet'
OUT = '/Users/azizsunderji/Dropbox/Home Economics/2025_12_29_OwnershipRates/2025_12_29_FirstApproach/outputs'

con = duckdb.connect()


def get_data(age):
    """Get flow percentages for both generations at a given age."""
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
        SUM(CASE WHEN is_head=1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS heads,
        SUM(CASE WHEN is_head=0 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS not_heads,
        SUM(CASE WHEN is_head=1 AND is_married=1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS married,
        SUM(CASE WHEN is_head=1 AND is_married=0 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS single,
        SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS married_owner,
        SUM(CASE WHEN is_head=1 AND is_married=1 AND is_owner=0 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS married_renter,
        SUM(CASE WHEN is_head=1 AND is_married=0 AND is_owner=1 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS single_owner,
        SUM(CASE WHEN is_head=1 AND is_married=0 AND is_owner=0 THEN ASECWT ELSE 0 END) / SUM(ASECWT) * 100 AS single_renter
    FROM persons WHERE generation IS NOT NULL
    GROUP BY generation ORDER BY generation
    """
    df = con.execute(q).df()
    return {
        'Boomer': df[df['generation'] == 'Boomer'].iloc[0].to_dict(),
        'Millennial': df[df['generation'] == 'Millennial'].iloc[0].to_dict()
    }


def draw_flow(ax, x0, y0_start, y0_end, x1, y1_start, y1_end, color, alpha=1.0, zorder=1):
    """Draw a curved flow between two vertical segments."""
    # Control points for bezier curve
    cx = (x0 + x1) / 2

    verts = [
        (x0, y0_start),  # start top
        (cx, y0_start),  # control 1
        (cx, y1_start),  # control 2
        (x1, y1_start),  # end top
        (x1, y1_end),    # end bottom
        (cx, y1_end),    # control 3
        (cx, y0_end),    # control 4
        (x0, y0_end),    # start bottom
        (x0, y0_start),  # close
    ]

    codes = [
        Path.MOVETO,
        Path.CURVE4, Path.CURVE4, Path.CURVE4,
        Path.LINETO,
        Path.CURVE4, Path.CURVE4, Path.CURVE4,
        Path.CLOSEPOLY,
    ]

    path = Path(verts, codes)
    patch = mpatches.PathPatch(path, facecolor=color, edgecolor='none', alpha=alpha, zorder=zorder)
    ax.add_patch(patch)


def draw_bar(ax, x, y_bottom, y_top, width, color, alpha=1.0, zorder=1):
    """Draw a vertical bar."""
    rect = mpatches.Rectangle((x - width/2, y_bottom), width, y_top - y_bottom,
                                facecolor=color, edgecolor='none', alpha=alpha, zorder=zorder)
    ax.add_patch(rect)


def make_sankey(age, data):
    """Create overlaid Sankey for a given age."""
    fig, ax = plt.subplots(figsize=(11, 11), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Layout: x positions for each stage
    x_birth = 0.05
    x_head = 0.30
    x_married = 0.60
    x_own = 0.90

    bar_width = 0.04

    # Y scale: 0-100, with some padding
    # We'll position flows from top to bottom

    b = data['Boomer']
    m = data['Millennial']

    # For each generation, calculate y positions
    # Structure: Heads on top (split into Married->Own/Rent, Single->Own/Rent), Not Heads on bottom

    def calc_positions(d):
        """Calculate y positions for all nodes given data dict."""
        # All starts at full height
        total = 100

        # Stage 1: Heads vs Not Heads
        heads = d['heads']
        not_heads = d['not_heads']

        # Stage 2: Of Heads -> Married vs Single
        married = d['married']
        single = d['single']

        # Stage 3: Outcomes
        m_own = d['married_owner']
        m_rent = d['married_renter']
        s_own = d['single_owner']
        s_rent = d['single_renter']

        # Y positions (from top, y=100 is top, y=0 is bottom)
        pos = {}

        # Birth bar: full height
        pos['birth'] = (0, 100)

        # Heads bar: top portion
        pos['heads'] = (100 - heads, 100)

        # Not heads bar: bottom portion
        pos['not_heads'] = (0, not_heads)

        # Married: within heads, top portion
        # Single: within heads, bottom portion
        heads_top = 100
        heads_bottom = 100 - heads
        married_bottom = heads_top - married
        pos['married'] = (married_bottom, heads_top)
        pos['single'] = (heads_bottom, married_bottom)

        # Outcomes for married
        pos['m_own'] = (100 - m_own, 100)
        pos['m_rent'] = (100 - m_own - m_rent, 100 - m_own)

        # Outcomes for single
        single_top = 100 - m_own - m_rent
        pos['s_own'] = (single_top - s_own, single_top)
        pos['s_rent'] = (single_top - s_own - s_rent, single_top - s_own)

        # Not heads flow to renter
        pos['nh_rent'] = (0, not_heads)

        return pos

    b_pos = calc_positions(b)
    m_pos = calc_positions(m)

    # Draw Boomers first (behind, cream, semi-transparent)
    boomer_alpha = 0.55
    boomer_color = CREAM_DARK

    # Birth bar
    draw_bar(ax, x_birth, 0, 100, bar_width, boomer_color, boomer_alpha, zorder=1)

    # Birth -> Heads
    draw_flow(ax, x_birth + bar_width/2, b_pos['heads'][0], b_pos['heads'][1],
              x_head - bar_width/2, b_pos['heads'][0], b_pos['heads'][1],
              boomer_color, boomer_alpha, zorder=1)

    # Birth -> Not Heads
    draw_flow(ax, x_birth + bar_width/2, b_pos['not_heads'][0], b_pos['not_heads'][1],
              x_head - bar_width/2, b_pos['not_heads'][0], b_pos['not_heads'][1],
              boomer_color, boomer_alpha, zorder=1)

    # Heads bar
    draw_bar(ax, x_head, b_pos['heads'][0], b_pos['heads'][1], bar_width, boomer_color, boomer_alpha, zorder=1)
    # Not heads bar
    draw_bar(ax, x_head, b_pos['not_heads'][0], b_pos['not_heads'][1], bar_width, boomer_color, boomer_alpha, zorder=1)

    # Heads -> Married
    draw_flow(ax, x_head + bar_width/2, b_pos['married'][0], b_pos['married'][1],
              x_married - bar_width/2, b_pos['m_own'][0], b_pos['m_rent'][1],
              boomer_color, boomer_alpha, zorder=1)

    # Heads -> Single
    draw_flow(ax, x_head + bar_width/2, b_pos['single'][0], b_pos['single'][1],
              x_married - bar_width/2, b_pos['s_own'][0], b_pos['s_rent'][1],
              boomer_color, boomer_alpha, zorder=1)

    # Married bar
    draw_bar(ax, x_married, b_pos['m_own'][0], b_pos['m_rent'][1], bar_width, boomer_color, boomer_alpha, zorder=1)
    # Single bar
    draw_bar(ax, x_married, b_pos['s_own'][0], b_pos['s_rent'][1], bar_width, boomer_color, boomer_alpha, zorder=1)

    # Married -> Own
    draw_flow(ax, x_married + bar_width/2, b_pos['m_own'][0], b_pos['m_own'][1],
              x_own - bar_width/2, b_pos['m_own'][0], b_pos['m_own'][1],
              boomer_color, boomer_alpha, zorder=1)
    # Married -> Rent
    draw_flow(ax, x_married + bar_width/2, b_pos['m_rent'][0], b_pos['m_rent'][1],
              x_own - bar_width/2, b_pos['m_rent'][0], b_pos['m_rent'][1],
              boomer_color, boomer_alpha, zorder=1)
    # Single -> Own
    draw_flow(ax, x_married + bar_width/2, b_pos['s_own'][0], b_pos['s_own'][1],
              x_own - bar_width/2, b_pos['s_own'][0], b_pos['s_own'][1],
              boomer_color, boomer_alpha, zorder=1)
    # Single -> Rent
    draw_flow(ax, x_married + bar_width/2, b_pos['s_rent'][0], b_pos['s_rent'][1],
              x_own - bar_width/2, b_pos['s_rent'][0], b_pos['s_rent'][1],
              boomer_color, boomer_alpha, zorder=1)

    # Not Heads -> Rent (bottom)
    draw_flow(ax, x_head + bar_width/2, b_pos['not_heads'][0], b_pos['not_heads'][1],
              x_own - bar_width/2, b_pos['nh_rent'][0], b_pos['nh_rent'][1],
              boomer_color, boomer_alpha, zorder=1)

    # Final bars for Boomers
    draw_bar(ax, x_own, b_pos['m_own'][0], b_pos['m_own'][1], bar_width, boomer_color, boomer_alpha, zorder=1)
    draw_bar(ax, x_own, b_pos['m_rent'][0], b_pos['m_rent'][1], bar_width, boomer_color, boomer_alpha, zorder=1)
    draw_bar(ax, x_own, b_pos['s_own'][0], b_pos['s_own'][1], bar_width, boomer_color, boomer_alpha, zorder=1)
    draw_bar(ax, x_own, b_pos['s_rent'][0], b_pos['s_rent'][1], bar_width, boomer_color, boomer_alpha, zorder=1)
    draw_bar(ax, x_own, b_pos['nh_rent'][0], b_pos['nh_rent'][1], bar_width, boomer_color, boomer_alpha, zorder=1)

    # Now draw Millennials (front, blue)
    mill_alpha = 0.85
    mill_color = BLUE

    # Birth bar
    draw_bar(ax, x_birth, 0, 100, bar_width, mill_color, mill_alpha, zorder=2)

    # Birth -> Heads
    draw_flow(ax, x_birth + bar_width/2, m_pos['heads'][0], m_pos['heads'][1],
              x_head - bar_width/2, m_pos['heads'][0], m_pos['heads'][1],
              mill_color, mill_alpha, zorder=2)

    # Birth -> Not Heads
    draw_flow(ax, x_birth + bar_width/2, m_pos['not_heads'][0], m_pos['not_heads'][1],
              x_head - bar_width/2, m_pos['not_heads'][0], m_pos['not_heads'][1],
              mill_color, mill_alpha, zorder=2)

    # Heads bar
    draw_bar(ax, x_head, m_pos['heads'][0], m_pos['heads'][1], bar_width, mill_color, mill_alpha, zorder=2)
    # Not heads bar
    draw_bar(ax, x_head, m_pos['not_heads'][0], m_pos['not_heads'][1], bar_width, mill_color, mill_alpha, zorder=2)

    # Heads -> Married
    draw_flow(ax, x_head + bar_width/2, m_pos['married'][0], m_pos['married'][1],
              x_married - bar_width/2, m_pos['m_own'][0], m_pos['m_rent'][1],
              mill_color, mill_alpha, zorder=2)

    # Heads -> Single
    draw_flow(ax, x_head + bar_width/2, m_pos['single'][0], m_pos['single'][1],
              x_married - bar_width/2, m_pos['s_own'][0], m_pos['s_rent'][1],
              mill_color, mill_alpha, zorder=2)

    # Married bar
    draw_bar(ax, x_married, m_pos['m_own'][0], m_pos['m_rent'][1], bar_width, mill_color, mill_alpha, zorder=2)
    # Single bar
    draw_bar(ax, x_married, m_pos['s_own'][0], m_pos['s_rent'][1], bar_width, mill_color, mill_alpha, zorder=2)

    # Married -> Own
    draw_flow(ax, x_married + bar_width/2, m_pos['m_own'][0], m_pos['m_own'][1],
              x_own - bar_width/2, m_pos['m_own'][0], m_pos['m_own'][1],
              mill_color, mill_alpha, zorder=2)
    # Married -> Rent
    draw_flow(ax, x_married + bar_width/2, m_pos['m_rent'][0], m_pos['m_rent'][1],
              x_own - bar_width/2, m_pos['m_rent'][0], m_pos['m_rent'][1],
              mill_color, mill_alpha, zorder=2)
    # Single -> Own
    draw_flow(ax, x_married + bar_width/2, m_pos['s_own'][0], m_pos['s_own'][1],
              x_own - bar_width/2, m_pos['s_own'][0], m_pos['s_own'][1],
              mill_color, mill_alpha, zorder=2)
    # Single -> Rent
    draw_flow(ax, x_married + bar_width/2, m_pos['s_rent'][0], m_pos['s_rent'][1],
              x_own - bar_width/2, m_pos['s_rent'][0], m_pos['s_rent'][1],
              mill_color, mill_alpha, zorder=2)

    # Not Heads -> Rent (bottom)
    draw_flow(ax, x_head + bar_width/2, m_pos['not_heads'][0], m_pos['not_heads'][1],
              x_own - bar_width/2, m_pos['nh_rent'][0], m_pos['nh_rent'][1],
              mill_color, mill_alpha, zorder=2)

    # Final bars for Millennials
    draw_bar(ax, x_own, m_pos['m_own'][0], m_pos['m_own'][1], bar_width, mill_color, mill_alpha, zorder=2)
    draw_bar(ax, x_own, m_pos['m_rent'][0], m_pos['m_rent'][1], bar_width, mill_color, mill_alpha, zorder=2)
    draw_bar(ax, x_own, m_pos['s_own'][0], m_pos['s_own'][1], bar_width, mill_color, mill_alpha, zorder=2)
    draw_bar(ax, x_own, m_pos['s_rent'][0], m_pos['s_rent'][1], bar_width, mill_color, mill_alpha, zorder=2)
    draw_bar(ax, x_own, m_pos['nh_rent'][0], m_pos['nh_rent'][1], bar_width, mill_color, mill_alpha, zorder=2)

    # ── Labels ──
    # Stage labels (centered in flows)
    ax.text(x_birth, -5, 'BIRTH', ha='center', va='top', fontsize=10, fontweight='bold', color=BLACK)

    ax.text((x_birth + x_head)/2, (m_pos['heads'][0] + m_pos['heads'][1])/2,
            'BECOME\nHOUSEHOLD\nHEADS', ha='center', va='center', fontsize=9, fontweight='bold', color=BLACK)

    ax.text((x_birth + x_head)/2, m_pos['not_heads'][1]/2,
            'LIVE WITH\nPARENTS / FRIENDS', ha='center', va='center', fontsize=9, fontweight='bold', color=BLACK)

    ax.text((x_head + x_married)/2, (m_pos['m_own'][0] + m_pos['m_rent'][1])/2,
            'GET\nMARRIED', ha='center', va='center', fontsize=9, fontweight='bold', color=BLACK)

    ax.text((x_head + x_married)/2, (m_pos['s_own'][0] + m_pos['s_rent'][1])/2,
            'REMAIN\nSINGLE', ha='center', va='center', fontsize=9, fontweight='bold', color=BLACK)

    # Outcome labels (right side)
    ax.text(x_own + bar_width/2 + 0.02, (m_pos['m_own'][0] + m_pos['m_own'][1])/2,
            'BUY\nHOME', ha='left', va='center', fontsize=9, fontweight='bold', color=BLACK)

    ax.text(x_own + bar_width/2 + 0.02, (m_pos['m_rent'][0] + m_pos['m_rent'][1])/2,
            'RENT', ha='left', va='center', fontsize=9, fontweight='bold', color=BLACK)

    ax.text(x_own + bar_width/2 + 0.02, (m_pos['s_own'][0] + m_pos['s_own'][1])/2,
            'BUY\nHOME', ha='left', va='center', fontsize=9, fontweight='bold', color=BLACK)

    ax.text(x_own + bar_width/2 + 0.02, (m_pos['s_rent'][0] + m_pos['nh_rent'][1])/2,
            'RENT', ha='left', va='center', fontsize=9, fontweight='bold', color=BLACK)

    # Percentage labels on right edge
    label_x = 0.98

    # Married owner
    ax.text(label_x, (b_pos['m_own'][0] + b_pos['m_own'][1])/2,
            f"{b['married_owner']:.0f}%", ha='right', va='center', fontsize=10, color=CREAM_DARK, fontweight='bold')
    ax.text(label_x, (m_pos['m_own'][0] + m_pos['m_own'][1])/2 - 5,
            f"{m['married_owner']:.0f}%", ha='right', va='center', fontsize=10, color=BLUE, fontweight='bold')

    # Married renter
    ax.text(label_x, (b_pos['m_rent'][0] + b_pos['m_rent'][1])/2,
            f"{b['married_renter']:.0f}%", ha='right', va='center', fontsize=10, color=CREAM_DARK, fontweight='bold')
    ax.text(label_x, (m_pos['m_rent'][0] + m_pos['m_rent'][1])/2 - 3,
            f"{m['married_renter']:.0f}%", ha='right', va='center', fontsize=10, color=BLUE, fontweight='bold')

    # Single owner
    ax.text(label_x, (b_pos['s_own'][0] + b_pos['s_own'][1])/2 + 2,
            f"{b['single_owner']:.0f}%", ha='right', va='center', fontsize=10, color=CREAM_DARK, fontweight='bold')
    ax.text(label_x, (m_pos['s_own'][0] + m_pos['s_own'][1])/2 - 2,
            f"{m['single_owner']:.0f}%", ha='right', va='center', fontsize=10, color=BLUE, fontweight='bold')

    # Bottom renter (single renter + not heads)
    b_bottom_rent = b['single_renter'] + b['not_heads']
    m_bottom_rent = m['single_renter'] + m['not_heads']
    ax.text(label_x, b['not_heads']/2 + 5,
            f"{b_bottom_rent:.0f}%", ha='right', va='center', fontsize=10, color=CREAM_DARK, fontweight='bold')
    ax.text(label_x, m['not_heads']/2 - 2,
            f"{m_bottom_rent:.0f}%", ha='right', va='center', fontsize=10, color=BLUE, fontweight='bold')

    # Not head percentages (left side, below the not-heads bar)
    ax.text(x_head + bar_width/2 + 0.02, m['not_heads'] + 2,
            f"{m['not_heads']:.0f}%", ha='left', va='bottom', fontsize=10, color=BLUE, fontweight='bold')
    ax.text(x_head + bar_width/2 + 0.02, b['not_heads'] - 2,
            f"{b['not_heads']:.0f}%", ha='left', va='top', fontsize=10, color=CREAM_DARK, fontweight='bold')

    # ── Legend ──
    ax.add_patch(mpatches.Rectangle((0.05, 108), 0.04, 3, facecolor=CREAM_DARK, alpha=0.6))
    ax.text(0.10, 109.5, 'Boomers', va='center', fontsize=10, color=BLACK)
    ax.add_patch(mpatches.Rectangle((0.05, 103), 0.04, 3, facecolor=BLUE, alpha=0.85))
    ax.text(0.10, 104.5, 'Millennials', va='center', fontsize=10, color=BLACK)

    # ── Title ──
    ax.text(0.02, 118, f'Lower rates of household formation and marriage explain a lot of\nthe Millennial-Boomer homeownership gap at age {age}',
            fontsize=14, fontweight='bold', color=BLACK, va='top')

    # ── Source ──
    ax.text(0.02, -10, 'Source: CPS ASEC via IPUMS', fontsize=9, color=BLACK, alpha=0.6, style='italic')

    # Axis setup
    ax.set_xlim(0, 1)
    ax.set_ylim(-15, 125)
    ax.axis('off')

    return fig


# Generate charts for all three ages
for age in [30, 35, 40]:
    data = get_data(age)
    fig = make_sankey(age, data)

    fig.savefig(f'{OUT}/sankey_overlaid_age_{age}.png', dpi=150, bbox_inches='tight', facecolor=BG)
    plt.rcParams['svg.fonttype'] = 'none'
    fig.savefig(f'{OUT}/sankey_overlaid_age_{age}.svg', bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"Saved sankey_overlaid_age_{age}")

print("Done!")
