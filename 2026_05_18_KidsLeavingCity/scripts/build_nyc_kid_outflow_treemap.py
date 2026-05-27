"""
WSJ-style hierarchical treemap of where NYC KIDS (AGE<18) moved to,
by county, IPUMS USA ACS 1-year PUMS pooled 2021-2024.

Universe: persons under 18 whose state-1-yr-ago was NY (MIGPLAC1=36) and
whose MIGPUMA1 was a NYC borough (3700, 3800, 3900, 4000, 4100), who
moved (MIGRATE1 in {2,3,4}) and are NOT currently in a NYC borough.

Counties are computed from current PUMA via the data lake's
PUMA→county crosswalk (2022 PUMA vintage); 2021 PUMAs (2010 vintage)
are first harmonized to 2020/2022 vintage. Where a PUMA spans multiple
counties, person-weight is split by the allocation factor.

Output:
  outputs/nyc_kid_outflow_treemap.svg
  outputs/nyc_kid_outflow_treemap.html

Style: WSJ Epstein-correspondents layout. Top-level regions
color-coded; sub-cells per county; white separators; total at the bottom.
"""
from __future__ import annotations
from pathlib import Path

import duckdb
import pandas as pd
import squarify

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
OUT = PROJECT / "outputs"
LAKE = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/IPUMS/acs_1y_degfield_migration.csv.gz")
XW_PATH = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/Crosswalks/PUMA_County_MigPUMA_Crosswalk.xlsx")
XW10_20 = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/Crosswalks/PUMA10_to_PUMA20_best.parquet")

NYC_BOROUGH_NAMES = {'Kings NY', 'Queens NY', 'Bronx NY', 'New York NY', 'Richmond NY'}
NYC_PUMA_PREFIX = {37, 38, 39, 40, 41}

# ---- 1. Pull NYC-borough-origin KID movers, 2021-2024 ----
con = duckdb.connect()
q = f"""
SELECT YEAR, SERIAL, AGE, STATEFIP, PUMA, MIGRATE1, MIGPLAC1, MIGPUMA1, PERWT
FROM read_csv_auto('{LAKE}')
WHERE MIGPLAC1 = 36
  AND MIGPUMA1 IN (3700, 3800, 3900, 4000, 4100)
  AND MIGRATE1 IN (2, 3, 4)
  AND AGE < 18
  AND YEAR IN (2021, 2022, 2023, 2024)
"""
kids = con.execute(q).df()

# Drop kids who stayed within the 5 boroughs
kids['cons'] = kids['PUMA'] // 100
kids = kids[~((kids['STATEFIP'] == 36) & kids['cons'].isin(NYC_PUMA_PREFIX))].copy()
print(f"Kid movers leaving NYC, 2021-2024 pooled: {kids['PERWT'].sum():,.0f} weighted ({len(kids)} unweighted)")
print(kids.groupby('YEAR')['PERWT'].sum().astype(int))

# ---- 2. Harmonize 2021 PUMA10 -> PUMA20 ----
xw10_20 = pd.read_parquet(XW10_20).drop_duplicates(['STATEFIP', 'PUMA10'])
kids_2021 = kids[kids['YEAR'] == 2021].merge(
    xw10_20.rename(columns={'PUMA10': 'PUMA'}),
    on=['STATEFIP', 'PUMA'], how='left')
kids_2021['PUMA_HARM'] = kids_2021['PUMA20'].fillna(kids_2021['PUMA']).astype(int)
kids_post = kids[kids['YEAR'] >= 2022].copy()
kids_post['PUMA_HARM'] = kids_post['PUMA']
kids = pd.concat([kids_2021.drop(columns=['PUMA20']), kids_post],
                 ignore_index=True, sort=False)

# ---- 3. PUMA → county crosswalk ----
xw = pd.read_excel(XW_PATH, sheet_name='PUMA_County_Crosswalk')
xw = xw.rename(columns={
    'State code': 'STATEFIP', 'PUMA (2022)': 'PUMA_HARM',
    'County code': 'COUNTYFIP', 'County name': 'COUNTY_NAME',
    'State abbr.': 'STATE_ABBR',
    'puma22-to-county allocation factor': 'alloc'})[
    ['STATEFIP', 'PUMA_HARM', 'COUNTYFIP', 'COUNTY_NAME', 'STATE_ABBR', 'alloc']]

m = kids.merge(xw, on=['STATEFIP', 'PUMA_HARM'], how='left')
m['weighted'] = m['PERWT'] * m['alloc'].fillna(1.0)
m['COUNTY_NAME'] = m['COUNTY_NAME'].fillna('Other')
m['STATE_ABBR'] = m['STATE_ABBR'].fillna('?')

# Exclude PUMA-allocation noise back to NYC boroughs
m_clean = m[~m['COUNTY_NAME'].isin(NYC_BOROUGH_NAMES)].copy()
TOTAL = m_clean['weighted'].sum()
print(f"\nAfter excluding PUMA-allocation noise back to NYC: {TOTAL:,.0f} weighted kid movers")

# ---- 4. Region classification for treemap top-level ----
NYC_NY_SUBURB = {'Nassau NY', 'Suffolk NY', 'Westchester NY', 'Rockland NY', 'Putnam NY'}
NYC_NJ_SUBURB = {'Bergen NJ', 'Essex NJ', 'Hudson NJ', 'Hunterdon NJ', 'Middlesex NJ',
                 'Monmouth NJ', 'Morris NJ', 'Ocean NJ', 'Passaic NJ', 'Somerset NJ',
                 'Sussex NJ', 'Union NJ'}
SOUTHEAST = {'GA', 'NC', 'SC', 'TN', 'VA', 'WV', 'KY', 'MD', 'DC', 'AL', 'LA', 'AR', 'MS', 'DE'}
MIDWEST = {'IL', 'IN', 'MI', 'OH', 'WI', 'IA', 'MN', 'MO', 'NE', 'ND', 'SD', 'KS'}
WEST = {'AZ', 'CO', 'NV', 'NM', 'UT', 'MT', 'ID', 'OR', 'WA', 'WY', 'HI', 'AK'}
NORTHEAST_OTHER = {'MA', 'NH', 'VT', 'ME', 'RI'}


def region(row):
    name = row['COUNTY_NAME']
    st = row['STATE_ABBR']
    if name in NYC_NY_SUBURB: return 'NY MSA suburb'
    if name in NYC_NJ_SUBURB: return 'NJ MSA suburb'
    if st == 'NY': return 'Other New York State'
    if st == 'NJ': return 'Other New Jersey'
    if st == 'CT': return 'Connecticut'
    if st == 'PA': return 'Pennsylvania'
    if st == 'FL': return 'Florida'
    if st == 'CA': return 'California'
    if st == 'TX': return 'Texas'
    if st in SOUTHEAST: return 'Other Southeast'
    if st in MIDWEST: return 'Midwest'
    if st in WEST: return 'Other West'
    if st in NORTHEAST_OTHER: return 'Other Northeast'
    return 'Other US'


m_clean['region'] = m_clean.apply(region, axis=1)

# Aggregate by county
county_agg = (m_clean.groupby(['region', 'COUNTY_NAME', 'STATE_ABBR'])['weighted'].sum()
              .reset_index().sort_values('weighted', ascending=False))
county_agg['label'] = county_agg['COUNTY_NAME']  # already includes state abbr

# Group small counties within each region into "Other <region>"
THRESHOLD = TOTAL * 0.006  # cells < 0.6% get merged into "Other within region"
small = county_agg[county_agg['weighted'] < THRESHOLD]
big = county_agg[county_agg['weighted'] >= THRESHOLD].copy()
other_per_region = small.groupby('region')['weighted'].sum().reset_index()
other_per_region['COUNTY_NAME'] = other_per_region['region'].apply(lambda r: f'Other ({r})')
other_per_region['STATE_ABBR'] = ''
other_per_region['label'] = other_per_region['COUNTY_NAME']
county_agg = pd.concat([big, other_per_region], ignore_index=True, sort=False)
county_agg = county_agg.sort_values('weighted', ascending=False)

# Region totals
region_totals = county_agg.groupby('region')['weighted'].sum().sort_values(ascending=False)
print("\nRegion totals:")
for r, v in region_totals.items():
    print(f"  {r:30s} {v:8,.0f} ({v / TOTAL * 100:.1f}%)")

# ---- 5. Treemap layout ----
WIDTH = 1200
HEIGHT = 1300
TITLE_H = 105
FOOTER_H = 55
PLOT_X = 24
PLOT_Y = TITLE_H + 6
PLOT_W = WIDTH - 2 * PLOT_X
PLOT_H = HEIGHT - TITLE_H - FOOTER_H - 12

# Color per region
REGION_COLOR = {
    'NY MSA suburb':         '#0BB4FF',  # HE blue
    'NJ MSA suburb':         '#7BC2E0',  # lighter blue
    'Other New York State':  '#67A275',  # HE green
    'Other New Jersey':      '#C6DCCB',  # HE light green
    'Connecticut':           '#9CB39E',  # muted green
    'Pennsylvania':          '#FEC439',  # HE yellow
    'Florida':               '#D03A2E',  # WSJ red
    'Other Southeast':       '#E8806C',  # lighter red
    'California':            '#1E5A8C',  # deep blue
    'Texas':                 '#A0531D',  # rust
    'Midwest':               '#B9A78A',  # warm tan
    'Other Northeast':       '#9CA68F',  # sage
    'Other West':            '#7E89C7',  # cool blue
    'Other US':              '#BAB3AC',  # grey
}

region_order = region_totals.index.tolist()
region_values = [int(region_totals[r]) for r in region_order]
region_rects = squarify.padded_squarify(
    squarify.normalize_sizes(region_values, PLOT_W, PLOT_H),
    PLOT_X, PLOT_Y, PLOT_W, PLOT_H,
)


def shade(hex_color: str, factor: float) -> str:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

    def adj(c):
        return int(c * factor) if factor < 1 else int(c + (255 - c) * (factor - 1))
    return f"#{adj(r):02X}{adj(g):02X}{adj(b):02X}"


# ---- 6. Build SVG ----
svg_parts = []
svg_parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
    f'style="background:#FFFFFF;font-family:\'ABC Oracle Edu\',Arial,sans-serif">'
)
svg_parts.append('<rect x="24" y="20" width="40" height="3" fill="#D03A2E"/>')
svg_parts.append(
    '<text x="24" y="48" font-size="24" font-weight="700" fill="#3D3733">'
    'Where the kids went: county-level destinations of NYC out-migrant children'
    '</text>')
svg_parts.append(
    '<text x="24" y="72" font-size="13" fill="#7F7570">'
    'Persons under 18 who lived in a NYC borough one year prior, by destination county. '
    'IPUMS USA ACS 1-year PUMS pooled 2021 + 2022 + 2023 + 2024.'
    '</text>')

for region_name, rect in zip(region_order, region_rects):
    rcolor = REGION_COLOR.get(region_name, '#999999')
    x, y, w, h = rect['x'], rect['y'], rect['dx'], rect['dy']

    # Sub-cells: counties within this region
    sub = county_agg[county_agg['region'] == region_name].sort_values('weighted', ascending=False)
    sub_vals = sub['weighted'].tolist()
    sub_names = sub['label'].tolist()

    HEADER_H = min(26, h * 0.18)
    inner_x = x + 1
    inner_y = y + HEADER_H
    inner_w = w - 2
    inner_h = h - HEADER_H - 1

    if inner_h < 10 or inner_w < 10:
        svg_parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{rcolor}" '
            f'stroke="#FFFFFF" stroke-width="2"/>')
        svg_parts.append(
            f'<text x="{x + 5}" y="{y + 14}" font-size="10" font-weight="700" fill="#1A1A1A">{region_name}</text>')
        continue

    svg_parts.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{rcolor}" '
        f'stroke="#FFFFFF" stroke-width="2"/>')

    if sub_vals:
        sub_rects = squarify.padded_squarify(
            squarify.normalize_sizes(sub_vals, inner_w, inner_h),
            inner_x, inner_y, inner_w, inner_h)
        for i, (name, val, r) in enumerate(zip(sub_names, sub_vals, sub_rects)):
            t = i / max(1, len(sub_vals) - 1)
            sf = 1.0 + t * 0.55
            fill = shade(rcolor, sf)
            rx, ry, rw, rh = r['x'], r['y'], r['dx'], r['dy']
            svg_parts.append(
                f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="{fill}" '
                f'stroke="#FFFFFF" stroke-width="1"/>')
            short = name.split(',')[0]
            num = f"{int(val):,}"
            pct = val / TOTAL * 100
            if rw > 70 and rh > 36:
                svg_parts.append(
                    f'<text x="{rx + 5}" y="{ry + 15}" font-size="11" font-weight="700" '
                    f'fill="#1A1A1A">{short}</text>')
                svg_parts.append(
                    f'<text x="{rx + 5}" y="{ry + 29}" font-size="10.5" fill="#1A1A1A">'
                    f'{num} · {pct:.1f}%</text>')
            elif rw > 50 and rh > 20:
                svg_parts.append(
                    f'<text x="{rx + 4}" y="{ry + 12}" font-size="9.5" font-weight="700" '
                    f'fill="#1A1A1A">{short}</text>')
                if rh > 26:
                    svg_parts.append(
                        f'<text x="{rx + 4}" y="{ry + 23}" font-size="9" fill="#1A1A1A">'
                        f'{pct:.1f}%</text>')

    region_pct = region_totals[region_name] / TOTAL * 100
    header_fill = '#FFFFFF' if region_name in {'NY MSA suburb', 'Florida', 'California', 'Texas'} else '#1A1A1A'
    svg_parts.append(
        f'<text x="{x + 8}" y="{y + 18}" font-size="13" font-weight="700" '
        f'fill="{header_fill}">{region_name}</text>')
    svg_parts.append(
        f'<text x="{x + w - 8}" y="{y + 18}" font-size="11" '
        f'fill="{header_fill}" text-anchor="end">'
        f'{int(region_totals[region_name]):,} · {region_pct:.1f}%</text>')

svg_parts.append(
    f'<text x="{WIDTH / 2}" y="{HEIGHT - 26}" font-size="15" font-weight="700" '
    f'fill="#3D3733" text-anchor="middle">'
    f'{int(TOTAL):,} weighted kid movers leaving the 5 NYC boroughs · '
    f'ACS PUMS 2021 + 2022 + 2023 + 2024 pooled</text>')
svg_parts.append(
    f'<text x="24" y="{HEIGHT - 8}" font-size="9" fill="#7F7570" font-style="italic">'
    'Source: U.S. Census Bureau ACS 1-year via IPUMS USA. PUMS persons aged 0-17 with MIGPLAC1=NY and '
    'MIGPUMA1 in NYC borough (3700-4100). Counties computed via PUMA-county crosswalk with allocation '
    'factors for cross-county PUMAs; 2021 (2010-vintage) PUMAs harmonized to 2020 vintage first.'
    '</text>')
svg_parts.append('</svg>')
svg_text = '\n'.join(svg_parts)

(OUT / 'nyc_kid_outflow_treemap.svg').write_text(svg_text)
html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC kid out-migration destinations by county</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Bold.otf') format('opentype'); font-weight:700; }}
body {{ margin:0; padding:20px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; }}
</style></head><body>{svg_text}</body></html>"""
(OUT / 'nyc_kid_outflow_treemap.html').write_text(html)
print(f"\nWrote {OUT / 'nyc_kid_outflow_treemap.svg'}")
print(f"Wrote {OUT / 'nyc_kid_outflow_treemap.html'}")
