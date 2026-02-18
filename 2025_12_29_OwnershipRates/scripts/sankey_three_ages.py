"""
Three Sankey charts stacked vertically: Age 30, Age 35, Age 40.
Each shows Boomers (left) and Millennials (right) side by side.
"""

import duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = '#0BB4FF'
BLUE_LIGHT = 'rgba(11, 180, 255, 0.5)'
CREAM = '#BBBFAE'
CREAM_LIGHT = 'rgba(187, 191, 174, 0.5)'
BG = '#F6F7F3'
BLACK = '#3D3733'
GREEN = '#67A275'
YELLOW = '#FEC439'
RED = '#F4743B'

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


def build_sankey_for_gen(df_row, x_offset=0, color='blue'):
    """Build node/link data for one generation's Sankey."""
    tot = df_row['total_pop']

    # Convert to percentages
    heads_pct = df_row['heads'] / tot * 100
    not_heads_pct = df_row['not_heads'] / tot * 100
    married_pct = df_row['married_heads'] / tot * 100
    single_pct = df_row['single_heads'] / tot * 100
    m_owner_pct = df_row['married_owner'] / tot * 100
    m_renter_pct = df_row['married_renter'] / tot * 100
    s_owner_pct = df_row['single_owner'] / tot * 100
    s_renter_pct = df_row['single_renter'] / tot * 100

    if color == 'blue':
        node_color = BLUE
        link_color = BLUE_LIGHT
    else:
        node_color = CREAM
        link_color = CREAM_LIGHT

    # Node positions (x: 0=All, 0.33=Head/NotHead, 0.66=Married/Single, 1.0=Final)
    # Final 5 categories add to 100%: Married Owner, Married Renter, Single Owner, Single Renter, Not Head
    nodes = {
        'label': [
            f'All\n100%',
            f'Heads\n{heads_pct:.0f}%',
            f'Not Head\n{not_heads_pct:.0f}%',
            f'Married\n{married_pct:.0f}%',
            f'Single\n{single_pct:.0f}%',
            f'Married\nOwner\n{m_owner_pct:.0f}%',
            f'Married\nRenter\n{m_renter_pct:.0f}%',
            f'Single\nOwner\n{s_owner_pct:.0f}%',
            f'Single\nRenter\n{s_renter_pct:.0f}%',
        ],
        'color': [node_color] * 9,
        'x': [0.01, 0.30, 0.99, 0.60, 0.60, 0.99, 0.99, 0.99, 0.99],
        'y': [0.5, 0.3, 0.92, 0.2, 0.5, 0.08, 0.28, 0.48, 0.68],
    }

    # Links: source -> target with values
    # Final nodes (indices 2, 5, 6, 7, 8) should add to 100%
    links = {
        'source': [0, 0, 1, 1, 3, 3, 4, 4],
        'target': [1, 2, 3, 4, 5, 6, 7, 8],
        'value': [
            heads_pct,           # All -> Heads
            not_heads_pct,       # All -> Not Head (terminal)
            married_pct,         # Heads -> Married
            single_pct,          # Heads -> Single
            m_owner_pct,         # Married -> Married Owner
            m_renter_pct,        # Married -> Married Renter
            s_owner_pct,         # Single -> Single Owner
            s_renter_pct,        # Single -> Single Renter
        ],
        'color': [link_color] * 8,
    }

    return nodes, links


# Create figure with 3 rows, 2 columns (Boomers left, Millennials right)
fig = make_subplots(
    rows=3, cols=2,
    specs=[[{"type": "sankey"}, {"type": "sankey"}],
           [{"type": "sankey"}, {"type": "sankey"}],
           [{"type": "sankey"}, {"type": "sankey"}]],
    subplot_titles=("Boomers at Age 30", "Millennials at Age 30",
                    "Boomers at Age 35", "Millennials at Age 35",
                    "Boomers at Age 40", "Millennials at Age 40"),
    vertical_spacing=0.12,
    horizontal_spacing=0.08,
)

ages = [30, 35, 40]

for row_idx, age in enumerate(ages):
    df = get_sankey_data(age)

    for col_idx, (gen, color) in enumerate([('Boomer', 'cream'), ('Millennial', 'blue')]):
        gen_data = df[df['generation'] == gen].iloc[0]
        nodes, links = build_sankey_for_gen(gen_data, color=color)

        fig.add_trace(
            go.Sankey(
                node=dict(
                    pad=20,
                    thickness=25,
                    line=dict(color=BLACK, width=0.5),
                    label=nodes['label'],
                    color=nodes['color'],
                    x=nodes['x'],
                    y=nodes['y'],
                ),
                link=dict(
                    source=links['source'],
                    target=links['target'],
                    value=links['value'],
                    color=links['color'],
                ),
                arrangement='snap',
            ),
            row=row_idx + 1, col=col_idx + 1
        )

fig.update_layout(
    title=dict(
        text="Path to Homeownership: Boomers vs Millennials at Ages 30, 35, and 40",
        font=dict(size=20, color=BLACK, family="ABC Oracle Edu"),
        x=0.02,
        y=0.98,
    ),
    font=dict(size=11, color=BLACK, family="ABC Oracle Edu"),
    paper_bgcolor=BG,
    height=1800,
    width=1200,
    margin=dict(t=100, b=50, l=50, r=50),
)

# Update subplot titles font
for annotation in fig['layout']['annotations']:
    annotation['font'] = dict(size=14, color=BLACK, family="ABC Oracle Edu")

fig.write_image(f'{OUT}/sankey_three_ages.png', scale=2)
fig.write_image(f'{OUT}/sankey_three_ages.svg')
fig.write_html(f'{OUT}/sankey_three_ages.html')
print("Saved sankey_three_ages.png, .svg, and .html")

# Also save individual ages as separate files
for age in ages:
    df = get_sankey_data(age)

    fig_single = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "sankey"}, {"type": "sankey"}]],
        subplot_titles=(f"Boomers at Age {age}", f"Millennials at Age {age}"),
        horizontal_spacing=0.08,
    )

    for col_idx, (gen, color) in enumerate([('Boomer', 'cream'), ('Millennial', 'blue')]):
        gen_data = df[df['generation'] == gen].iloc[0]
        nodes, links = build_sankey_for_gen(gen_data, color=color)

        fig_single.add_trace(
            go.Sankey(
                node=dict(
                    pad=20,
                    thickness=25,
                    line=dict(color=BLACK, width=0.5),
                    label=nodes['label'],
                    color=nodes['color'],
                    x=nodes['x'],
                    y=nodes['y'],
                ),
                link=dict(
                    source=links['source'],
                    target=links['target'],
                    value=links['value'],
                    color=links['color'],
                ),
                arrangement='snap',
            ),
            row=1, col=col_idx + 1
        )

    fig_single.update_layout(
        title=dict(
            text=f"Path to Homeownership at Age {age}: Boomers vs Millennials",
            font=dict(size=18, color=BLACK, family="ABC Oracle Edu"),
            x=0.02,
        ),
        font=dict(size=11, color=BLACK, family="ABC Oracle Edu"),
        paper_bgcolor=BG,
        height=600,
        width=1200,
        margin=dict(t=80, b=30, l=50, r=50),
    )

    for annotation in fig_single['layout']['annotations']:
        annotation['font'] = dict(size=14, color=BLACK, family="ABC Oracle Edu")

    fig_single.write_image(f'{OUT}/sankey_age_{age}.png', scale=2)
    fig_single.write_html(f'{OUT}/sankey_age_{age}.html')
    print(f"Saved sankey_age_{age}.png and .html")
