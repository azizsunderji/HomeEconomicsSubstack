"""
WSJ-style treemap of where NYC KIDS (AGE<18) moved to — at the COUNTY level.
Top-level cells are individual counties (no regional grouping).
Cells are colored by region so the eye still groups Northeast / Florida / etc.

IPUMS USA ACS 1-year PUMS pooled 2021-2024. PUMA-allocation noise back to
NYC boroughs filtered.

Output:
  outputs/nyc_kid_outflow_treemap_counties.svg
  outputs/nyc_kid_outflow_treemap_counties.html
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

# ---- Pull data ----
con = duckdb.connect()
q = f"""
SELECT YEAR, AGE, STATEFIP, PUMA, MIGRATE1, MIGPLAC1, MIGPUMA1, PERWT
FROM read_csv_auto('{LAKE}')
WHERE MIGPLAC1 = 36 AND MIGPUMA1 IN (3700,3800,3900,4000,4100)
  AND MIGRATE1 IN (2,3,4) AND AGE<18
  AND YEAR IN (2021,2022,2023,2024)
"""
kids = con.execute(q).df()
kids['cons'] = kids['PUMA'] // 100
kids = kids[~((kids['STATEFIP']==36) & kids['cons'].isin(NYC_PUMA_PREFIX))].copy()

# Harmonize PUMA10 -> PUMA20
xw10_20 = pd.read_parquet(XW10_20).drop_duplicates(['STATEFIP','PUMA10'])
k21 = kids[kids['YEAR']==2021].merge(xw10_20.rename(columns={'PUMA10':'PUMA'}),
                                      on=['STATEFIP','PUMA'], how='left')
k21['PUMA_HARM'] = k21['PUMA20'].fillna(k21['PUMA']).astype(int)
kpost = kids[kids['YEAR']>=2022].copy(); kpost['PUMA_HARM']=kpost['PUMA']
kids = pd.concat([k21.drop(columns=['PUMA20']), kpost], ignore_index=True, sort=False)

xw = pd.read_excel(XW_PATH, sheet_name='PUMA_County_Crosswalk')
xw = xw.rename(columns={'State code':'STATEFIP','PUMA (2022)':'PUMA_HARM',
                        'County name':'COUNTY_NAME','State abbr.':'STATE_ABBR',
                        'puma22-to-county allocation factor':'alloc'})[
    ['STATEFIP','PUMA_HARM','COUNTY_NAME','STATE_ABBR','alloc']]
m = kids.merge(xw, on=['STATEFIP','PUMA_HARM'], how='left')
m['weighted'] = m['PERWT'] * m['alloc'].fillna(1.0)
m['COUNTY_NAME'] = m['COUNTY_NAME'].fillna('Other').str.strip()
m['STATE_ABBR'] = m['STATE_ABBR'].fillna('?')
m = m[~m['COUNTY_NAME'].isin(NYC_BOROUGH_NAMES)].copy()
TOTAL = m['weighted'].sum()
print(f"Total weighted kid movers leaving NYC, 4 yrs: {TOTAL:,.0f}")

# Region for COLOR (not for grouping)
NYC_NY_SUB = {'Nassau NY','Suffolk NY','Westchester NY','Rockland NY','Putnam NY'}
NYC_NJ_SUB = {'Bergen NJ','Essex NJ','Hudson NJ','Hunterdon NJ','Middlesex NJ',
              'Monmouth NJ','Morris NJ','Ocean NJ','Passaic NJ','Somerset NJ',
              'Sussex NJ','Union NJ'}
SOUTHEAST_STATES = {'GA','NC','SC','TN','VA','WV','KY','MD','DC','AL','LA','AR','MS','DE'}
MIDWEST_STATES = {'IL','IN','MI','OH','WI','IA','MN','MO','NE','ND','SD','KS'}
WEST_STATES = {'AZ','CO','NV','NM','UT','MT','ID','OR','WA','WY','HI','AK'}
NORTHEAST_OTHER = {'MA','NH','VT','ME','RI'}

def region(row):
    name, st = row['COUNTY_NAME'], row['STATE_ABBR']
    if name in NYC_NY_SUB: return 'NYC MSA — Long Island / Lower Hudson'
    if name in NYC_NJ_SUB: return 'NYC MSA — New Jersey'
    if st == 'NY': return 'Other New York State'
    if st == 'NJ': return 'Other New Jersey'
    if st == 'CT': return 'Connecticut'
    if st == 'PA': return 'Pennsylvania'
    if st == 'FL': return 'Florida'
    if st == 'CA': return 'California'
    if st == 'TX': return 'Texas'
    if st in SOUTHEAST_STATES: return 'Other Southeast'
    if st in MIDWEST_STATES: return 'Midwest'
    if st in WEST_STATES: return 'Other West'
    if st in NORTHEAST_OTHER: return 'Other Northeast'
    return 'Other US'

REGION_COLOR = {
    'NYC MSA — Long Island / Lower Hudson': '#0BB4FF',
    'NYC MSA — New Jersey':                 '#7BC2E0',
    'Other New York State':                 '#67A275',
    'Other New Jersey':                     '#C6DCCB',
    'Connecticut':                          '#9CB39E',
    'Pennsylvania':                         '#FEC439',
    'Florida':                              '#D03A2E',
    'Other Southeast':                      '#E8806C',
    'California':                           '#1E5A8C',
    'Texas':                                '#A0531D',
    'Midwest':                              '#B9A78A',
    'Other Northeast':                      '#9CA68F',
    'Other West':                           '#7E89C7',
    'Other US':                             '#BAB3AC',
}

# Aggregate to county
county = m.groupby(['COUNTY_NAME','STATE_ABBR'])['weighted'].sum().reset_index()
county['region'] = county.apply(region, axis=1)
county['color'] = county['region'].map(REGION_COLOR)
county = county.sort_values('weighted', ascending=False).reset_index(drop=True)

# Merge tail of small counties into "Other ..." buckets per region — but keep
# the top ~40 as their own cells. Anything below ~0.4% gets lumped.
THRESHOLD = TOTAL * 0.004
big = county[county['weighted'] >= THRESHOLD].copy()
small = county[county['weighted'] < THRESHOLD]
print(f"Top counties shown individually: {len(big)}")
print(f"Small counties merged: {len(small)} ({small['weighted'].sum()/TOTAL*100:.1f}% of total)")
# Bucket small counties by region into "Other (region)" rows
other_rows = (small.groupby('region')['weighted'].sum().reset_index())
other_rows['COUNTY_NAME'] = other_rows['region'].apply(lambda r: f'Other in {r}')
other_rows['STATE_ABBR'] = ''
other_rows['color'] = other_rows['region'].map(REGION_COLOR)
big = pd.concat([big, other_rows], ignore_index=True, sort=False)
big = big.sort_values('weighted', ascending=False).reset_index(drop=True)
print(big[['COUNTY_NAME','STATE_ABBR','region','weighted']].head(20))

# ---- Treemap layout (counties as top-level) ----
WIDTH = 1400
HEIGHT = 1100
TITLE_H = 105
FOOTER_H = 70
PLOT_X = 24
PLOT_Y = TITLE_H + 6
PLOT_W = WIDTH - 2*PLOT_X
PLOT_H = HEIGHT - TITLE_H - FOOTER_H - 12

vals = big['weighted'].tolist()
rects = squarify.padded_squarify(squarify.normalize_sizes(vals, PLOT_W, PLOT_H),
                                  PLOT_X, PLOT_Y, PLOT_W, PLOT_H)

# Build SVG
svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
           f'width="{WIDTH}" height="{HEIGHT}" '
           f'style="background:#FFFFFF;font-family:\'ABC Oracle Edu\',Arial,sans-serif">')
svg.append('<rect x="24" y="20" width="40" height="3" fill="#D03A2E"/>')
svg.append('<text x="24" y="48" font-size="24" font-weight="700" fill="#3D3733">'
           'Where the kids went: destination counties for NYC out-migrant children</text>')
svg.append('<text x="24" y="72" font-size="13" fill="#7F7570">'
           'Persons under 18 who lived in a NYC borough one year prior, by destination county. '
           'IPUMS USA ACS 1-year PUMS pooled 2021 + 2022 + 2023 + 2024. '
           'Color groups counties by region.</text>')

for i, (_, row) in enumerate(big.iterrows()):
    r = rects[i]
    x, y, w, h = r['x'], r['y'], r['dx'], r['dy']
    name = row['COUNTY_NAME']
    state = row['STATE_ABBR']
    val = int(row['weighted'])
    pct = row['weighted'] / TOTAL * 100
    color = row['color']
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" '
               f'stroke="#FFFFFF" stroke-width="1.5"/>')
    # Trim trailing state from county name if present (we have STATE_ABBR separately)
    short = name.replace(f' {state}', '') if state else name
    num = f"{val:,}"
    if w > 110 and h > 50:
        svg.append(f'<text x="{x+8}" y="{y+19}" font-size="14" font-weight="700" fill="#1A1A1A">{short}</text>')
        if state:
            svg.append(f'<text x="{x+8}" y="{y+34}" font-size="11" fill="#3D3733">{state}</text>')
        svg.append(f'<text x="{x+8}" y="{y+50}" font-size="11.5" fill="#1A1A1A">{num} · {pct:.1f}%</text>')
    elif w > 75 and h > 32:
        svg.append(f'<text x="{x+5}" y="{y+14}" font-size="11" font-weight="700" fill="#1A1A1A">{short}</text>')
        if state and h > 42:
            svg.append(f'<text x="{x+5}" y="{y+26}" font-size="9.5" fill="#3D3733">{state}</text>')
        svg.append(f'<text x="{x+5}" y="{y+(38 if h>42 else 27)}" font-size="9.5" fill="#1A1A1A">{pct:.1f}%</text>')
    elif w > 45 and h > 22:
        svg.append(f'<text x="{x+3}" y="{y+12}" font-size="9" font-weight="700" fill="#1A1A1A">{short}</text>')
        if h > 22:
            svg.append(f'<text x="{x+3}" y="{y+22}" font-size="8.5" fill="#1A1A1A">{pct:.1f}%</text>')

# Color legend at bottom
LEGEND_Y = HEIGHT - FOOTER_H + 8
svg.append(f'<text x="24" y="{LEGEND_Y - 2}" font-size="11" font-weight="700" fill="#3D3733">Region color key:</text>')
legend_x = 130
for r_name, r_col in REGION_COLOR.items():
    sw_w = 12
    label_w = len(r_name) * 6 + 24
    if legend_x + label_w > WIDTH - 30:
        legend_x = 130
        LEGEND_Y += 14
    svg.append(f'<rect x="{legend_x}" y="{LEGEND_Y-9}" width="{sw_w}" height="9" fill="{r_col}"/>')
    svg.append(f'<text x="{legend_x+sw_w+4}" y="{LEGEND_Y-1}" font-size="9.5" fill="#3D3733">{r_name}</text>')
    legend_x += label_w + 4

svg.append(f'<text x="{WIDTH/2}" y="{HEIGHT - 18}" font-size="14" font-weight="700" '
           f'fill="#3D3733" text-anchor="middle">'
           f'{int(TOTAL):,} weighted kids leaving the 5 NYC boroughs · '
           f'ACS PUMS 2021-2024 pooled</text>')
svg.append(f'<text x="24" y="{HEIGHT - 4}" font-size="8.5" fill="#7F7570" font-style="italic">'
           'Source: U.S. Census Bureau ACS 1-year via IPUMS USA. Counties from PUMA via crosswalk; '
           '2021 PUMAs harmonized 2010→2020 vintage. PUMA-allocation noise back to NYC boroughs filtered.'
           '</text>')
svg.append('</svg>')

svg_text = '\n'.join(svg)
(OUT / 'nyc_kid_outflow_treemap_counties.svg').write_text(svg_text)
html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC kid out-migration — counties</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Bold.otf') format('opentype'); font-weight:700; }}
body {{ margin:0; padding:20px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; }}
</style></head><body>{svg_text}</body></html>"""
(OUT / 'nyc_kid_outflow_treemap_counties.html').write_text(html)
print(f"Wrote {OUT / 'nyc_kid_outflow_treemap_counties.svg'}")
print(f"Wrote {OUT / 'nyc_kid_outflow_treemap_counties.html'}")
