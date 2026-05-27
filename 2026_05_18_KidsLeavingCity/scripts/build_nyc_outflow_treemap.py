"""
Hierarchical treemap of where people leaving the 5 NYC boroughs went, pooled
IRS county-to-county outflow data 2020-21 + 2021-22 + 2022-23.

Top-level categories (sized by people):
  NYC MSA suburbs (17 counties) · Florida · Other Southeast · Pennsylvania ·
  Other New York State · California · Connecticut · Midwest · Texas ·
  Other Northeast · Other West · Other NJ · Other US

Within each category, sub-cells for individual destination counties
(Florida → Miami-Dade, Broward, Palm Beach, …; NYC MSA suburbs → Nassau,
Westchester, Suffolk, …). Intra-borough moves (Brooklyn → Queens etc.) are
excluded — we want OUT of NYC.

Output:
  outputs/nyc_outflow_treemap.svg   (editable in Illustrator — text is <text>)
  outputs/nyc_outflow_treemap.html  (browser preview)

Style: WSJ Epstein-correspondents look. Bold category headers, color-coded
category blocks, white separators, total at bottom.
"""
from __future__ import annotations
import json
from pathlib import Path

import pandas as pd
import squarify

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
OUT = PROJECT / "outputs"
IRS_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_04_21_MiamiRise/data/irs_soi_migration/county")

BOROUGHS = {'36005', '36047', '36061', '36081', '36085'}
SUBURB_FIPS = {
    '34003': 'Bergen',    '34013': 'Essex',     '34017': 'Hudson NJ', '34019': 'Hunterdon',
    '34023': 'Middlesex', '34025': 'Monmouth',  '34027': 'Morris',    '34029': 'Ocean',
    '34031': 'Passaic',   '34035': 'Somerset',  '34037': 'Sussex',    '34039': 'Union',
    '36059': 'Nassau',    '36079': 'Putnam',    '36087': 'Rockland',  '36103': 'Suffolk',
    '36119': 'Westchester',
}
SOUTHEAST = {'13', '37', '45', '47', '51', '54', '21', '24', '11', '01', '22', '05', '28'}
MIDWEST = {'17', '18', '26', '39', '55', '19', '27', '29', '31', '38', '46', '20'}
WEST = {'04', '08', '32', '35', '49', '30', '16', '41', '53', '56', '15', '02'}
NORTHEAST_NON_PA_CT = {'25', '23', '33', '50', '44'}  # MA, ME, NH, VT, RI


def categorize(state: str, to_fips: str) -> str:
    if to_fips in SUBURB_FIPS:
        return 'NYC MSA suburbs'
    if state == '12': return 'Florida'
    if state == '42': return 'Pennsylvania'
    if state == '36': return 'Other New York State'
    if state == '09': return 'Connecticut'
    if state == '34': return 'Other New Jersey'
    if state == '06': return 'California'
    if state == '48': return 'Texas'
    if state in SOUTHEAST: return 'Other Southeast'
    if state in MIDWEST: return 'Midwest'
    if state in WEST: return 'Other West'
    if state in NORTHEAST_NON_PA_CT: return 'Other Northeast'
    return 'Other US'


def shorten(name: str) -> str:
    return (name.replace(' County', '')
                .replace(' Planning Region', '')
                .replace(' Planning Regio', '')
                .replace(' Planning Regi', '')
                .strip())


# ---- Load + prep data ----
dfs = []
for yr in ['2021', '2122', '2223']:
    d = pd.read_csv(IRS_DIR / f"countyoutflow{yr}.csv",
                    dtype={'y1_statefips': str, 'y1_countyfips': str,
                           'y2_statefips': str, 'y2_countyfips': str},
                    encoding='latin-1')
    dfs.append(d)
df = pd.concat(dfs)
df['from_fips'] = df['y1_statefips'] + df['y1_countyfips']
df['to_fips']   = df['y2_statefips'] + df['y2_countyfips']

bor = df[df['from_fips'].isin(BOROUGHS)].copy()
bor = bor[~bor['y2_countyname'].str.contains(
    'Non-migrants|Total Migration|Other flows|Foreign', case=False, na=False)]
bor = bor[bor['from_fips'] != bor['to_fips']]
bor = bor[bor['y2_statefips'] != '57']
bor = bor[~bor['to_fips'].isin(BOROUGHS)]  # exclude intra-NYC

bor['category'] = bor.apply(lambda r: categorize(r['y2_statefips'], r['to_fips']), axis=1)
bor['dest_name'] = bor.apply(
    lambda r: SUBURB_FIPS[r['to_fips']] if r['to_fips'] in SUBURB_FIPS
    else f"{shorten(r['y2_countyname'])}, {r['y2_state']}", axis=1)

dest_agg = bor.groupby(['category', 'dest_name']).agg(people=('n2', 'sum')).reset_index()
TOTAL = dest_agg['people'].sum()
print(f"Total people: {TOTAL:,}")

# Within each category, sum and order
cat_totals = dest_agg.groupby('category')['people'].sum().sort_values(ascending=False)
print("\nCategory totals:")
for c, v in cat_totals.items():
    print(f"  {c:30s} {v:8,} ({v/TOTAL*100:.1f}%)")

# ---- Treemap layout ----
WIDTH = 1100
HEIGHT = 1300
TITLE_HEIGHT = 95
FOOTER_HEIGHT = 50
PLOT_X = 24
PLOT_Y = TITLE_HEIGHT + 6
PLOT_W = WIDTH - 2 * PLOT_X
PLOT_H = HEIGHT - TITLE_HEIGHT - FOOTER_HEIGHT - 12

# Category colors — distinct but cohesive (warm reds/oranges for distant
# destinations, cool blues for in-MSA suburbs, neutrals for the rest)
CATEGORY_COLOR = {
    'NYC MSA suburbs':       '#0BB4FF',   # HE blue — they stayed in the metro
    'Florida':               '#D03A2E',   # WSJ red — biggest external destination
    'Other Southeast':       '#E8806C',   # lighter red — Southeast cluster
    'Pennsylvania':          '#FEC439',   # HE yellow — adjacent state
    'Other New York State':  '#67A275',   # HE green — Hudson Valley + upstate
    'California':            '#1E5A8C',   # deep blue — far destination
    'Connecticut':           '#7BA7C6',   # light blue — Northeast adjacent
    'Midwest':               '#B9A78A',   # warm tan
    'Texas':                 '#A0531D',   # rust — Sun Belt
    'Other Northeast':       '#9CA68F',   # muted sage
    'Other West':            '#7E89C7',   # cool muted blue
    'Other New Jersey':      '#C6DCCB',   # HE light green
    'Other US':              '#BAB3AC',   # grey
}

# Sort categories by size (largest first)
cat_order = cat_totals.index.tolist()
cat_values = [int(cat_totals[c]) for c in cat_order]

# First pass: layout categories
cat_rects = squarify.padded_squarify(
    squarify.normalize_sizes(cat_values, PLOT_W, PLOT_H),
    PLOT_X, PLOT_Y, PLOT_W, PLOT_H,
)

# Each category gets a header strip with bold label; rest filled with sub-cells.
def shade(hex_color: str, factor: float) -> str:
    """Lighten (factor>1) or darken (<1) a hex color."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    def adj(c):
        if factor < 1: return int(c * factor)
        return int(c + (255 - c) * (factor - 1))
    return f"#{adj(r):02X}{adj(g):02X}{adj(b):02X}"


# Build SVG
svg_parts = []
svg_parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
    f'style="background:#FFFFFF;font-family:\'ABC Oracle Edu\',Arial,sans-serif">'
)

# Title block — red accent bar + bold title + subtitle
svg_parts.append(f'<rect x="{PLOT_X}" y="20" width="36" height="3" fill="#D03A2E"/>')
svg_parts.append(
    f'<text x="{PLOT_X}" y="46" font-size="24" font-weight="700" fill="#3D3733">'
    'Where New Yorkers went when they left the 5 boroughs'
    '</text>'
)
svg_parts.append(
    f'<text x="{PLOT_X}" y="72" font-size="13" fill="#7F7570">'
    'IRS county-to-county migration, pooled 2020–21 + 2021–22 + 2022–23. '
    'All people moving out of Bronx, Brooklyn, Manhattan, Queens, Staten Island, '
    'excluding intra-borough moves.'
    '</text>'
)

# Layout & render each category
for cat, rect in zip(cat_order, cat_rects):
    cat_color = CATEGORY_COLOR.get(cat, '#999999')
    x, y, w, h = rect['x'], rect['y'], rect['dx'], rect['dy']

    # Cells inside this category
    sub = dest_agg[dest_agg['category'] == cat].sort_values('people', ascending=False)
    sub_names = sub['dest_name'].tolist()
    sub_values = sub['people'].tolist()

    # Reserve top area for category header
    HEADER_H = min(28, h * 0.18)
    inner_x = x + 1
    inner_y = y + HEADER_H
    inner_w = w - 2
    inner_h = h - HEADER_H - 1
    if inner_h < 10 or inner_w < 10:
        # Too small — just show the category alone
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{cat_color}" '
            f'stroke="#FFFFFF" stroke-width="2"/>'
        )
        svg_parts.append(
            f'<text x="{x + 6}" y="{y + 16}" font-size="11" font-weight="700" '
            f'fill="#FFFFFF">{cat}</text>'
        )
        continue

    # Base color block for the whole category region
    svg_parts.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{cat_color}" '
        f'stroke="#FFFFFF" stroke-width="2"/>'
    )

    # Sub-cells laid out inside inner area
    if sub_values:
        sub_rects = squarify.padded_squarify(
            squarify.normalize_sizes(sub_values, inner_w, inner_h),
            inner_x, inner_y, inner_w, inner_h,
        )
        # Use shading variants on top of the category color for sub-cells
        for i, (name, val, r) in enumerate(zip(sub_names, sub_values, sub_rects)):
            # Shade: largest in pure category color; smaller get progressively lighter
            t = i / max(1, len(sub_values) - 1)
            shade_factor = 1.0 + t * 0.55  # 1.0 to 1.55 (lighter)
            fill = shade(cat_color, shade_factor)
            rx, ry, rw, rh = r['x'], r['y'], r['dx'], r['dy']
            svg_parts.append(
                f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="{fill}" '
                f'stroke="#FFFFFF" stroke-width="1"/>'
            )
            # Sub-label if cell is big enough
            label_short = name.split(',')[0]  # drop state suffix in label
            number_txt = f"{int(val):,}"
            # Decide what fits
            cell_area = rw * rh
            if rw > 70 and rh > 36 and cell_area > 4500:
                svg_parts.append(
                    f'<text x="{rx + 5}" y="{ry + 16}" font-size="11.5" '
                    f'font-weight="700" fill="#1A1A1A">{label_short}</text>'
                )
                svg_parts.append(
                    f'<text x="{rx + 5}" y="{ry + 30}" font-size="11" '
                    f'fill="#1A1A1A">{number_txt}</text>'
                )
            elif rw > 48 and rh > 22:
                svg_parts.append(
                    f'<text x="{rx + 4}" y="{ry + 13}" font-size="10" '
                    f'font-weight="700" fill="#1A1A1A">{label_short}</text>'
                )
                if rh > 28:
                    svg_parts.append(
                        f'<text x="{rx + 4}" y="{ry + 25}" font-size="9.5" '
                        f'fill="#1A1A1A">{number_txt}</text>'
                    )

    # Category header label (over the colored block at the top of the region)
    cat_pct = cat_totals[cat] / TOTAL * 100
    header_fill = '#FFFFFF' if cat in {'Florida', 'California', 'Texas', 'NYC MSA suburbs', 'Other West'} else '#1A1A1A'
    svg_parts.append(
        f'<text x="{x + 8}" y="{y + 19}" font-size="13.5" font-weight="700" '
        f'fill="{header_fill}">{cat}</text>'
    )
    svg_parts.append(
        f'<text x="{x + w - 8}" y="{y + 19}" font-size="11" '
        f'fill="{header_fill}" text-anchor="end">'
        f'{int(cat_totals[cat]):,} · {cat_pct:.1f}%</text>'
    )

# Total footer
svg_parts.append(
    f'<text x="{WIDTH/2}" y="{HEIGHT - 18}" font-size="16" font-weight="700" '
    f'fill="#3D3733" text-anchor="middle">'
    f'{int(TOTAL):,} total people · 2020–21 + 2021–22 + 2022–23 pooled'
    '</text>'
)
svg_parts.append(
    f'<text x="{PLOT_X}" y="{HEIGHT - 5}" font-size="9" fill="#7F7570" '
    'font-style="italic">'
    'Source: IRS SOI county-to-county migration outflows (n2 = total exemptions). '
    'Categories: "Other Southeast" = GA/NC/VA/MD/SC/TN/etc.; "Other Northeast" = MA/NH/VT/ME/RI; '
    '"Other West" = AZ/CO/NV/WA/OR/etc.; "Other US" = remainder + unspecified.'
    '</text>'
)

svg_parts.append('</svg>')
svg_text = '\n'.join(svg_parts)

svg_path = OUT / 'nyc_outflow_treemap.svg'
svg_path.write_text(svg_text)
print(f"Wrote {svg_path}")

# Also write an HTML wrapper for browser viewing
html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Where NYC movers went — treemap</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Bold.otf') format('opentype'); font-weight:700; }}
body {{ margin:0; padding:20px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; }}
</style></head><body>{svg_text}</body></html>"""
html_path = OUT / 'nyc_outflow_treemap.html'
html_path.write_text(html)
print(f"Wrote {html_path}")
