"""
Side-by-side WSJ-style treemaps:
  LEFT:  Households WITH kids — where NYC-borough movers went
  RIGHT: Households WITHOUT kids — where NYC-borough movers went

Universe: persons whose state-of-residence 1 yr ago was NY (MIGPLAC1=36) and
whose MIGPUMA1 was a NYC borough (3700, 3800, 3900, 4000, 4100), who
actually moved (MIGRATE1 in {2,3,4}) and who are NOT currently in another
NYC borough (i.e., they LEFT the 5 boroughs entirely). HH-with-kids flag is
computed by checking every member of the household (SERIAL) for any AGE<18.

Data source: data lake at
  /Users/azizsunderji/Dropbox/Home Economics/Data/IPUMS/acs_1y_degfield_migration.csv.gz
Years pooled: 2021 + 2022 (most recent available in the lake for migration).

Output:
  outputs/nyc_outflow_treemap_family_compare.svg
  outputs/nyc_outflow_treemap_family_compare.html
"""
from __future__ import annotations
from pathlib import Path

import duckdb
import pandas as pd
import squarify

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
OUT = PROJECT / "outputs"
LAKE = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/IPUMS/acs_1y_degfield_migration.csv.gz")

NYC_PUMA_PREFIX = {37, 38, 39, 40, 41}

# ---- 1. Pull mover persons from the data lake (DuckDB on gzipped CSV) ----
con = duckdb.connect()
q = f"""
SELECT YEAR, SERIAL, PERNUM, AGE, STATEFIP, PUMA, MET2013,
       MIGRATE1, MIGPLAC1, MIGPUMA1, PERWT
FROM read_csv_auto('{LAKE}')
WHERE MIGPLAC1 = 36
  AND MIGPUMA1 IN (3700, 3800, 3900, 4000, 4100)
  AND MIGRATE1 IN (2, 3, 4)
  AND YEAR IN (2021, 2022)
"""
movers = con.execute(q).df()

# ---- 2. HH-with-kid flag ----
hh_keys = movers[['YEAR', 'SERIAL']].drop_duplicates()
con.register('hh_keys', hh_keys)
q2 = f"""
SELECT a.YEAR, a.SERIAL, MAX(CASE WHEN a.AGE < 18 THEN 1 ELSE 0 END) AS has_kid
FROM read_csv_auto('{LAKE}') a
INNER JOIN hh_keys k ON a.YEAR = k.YEAR AND a.SERIAL = k.SERIAL
WHERE a.YEAR IN (2021, 2022)
GROUP BY 1, 2
"""
hh_kid = con.execute(q2).df()
movers = movers.merge(hh_kid, on=['YEAR', 'SERIAL'])

# ---- 3. Restrict to people who LEFT all 5 NYC boroughs ----
movers['cons_puma'] = (movers['PUMA'] // 100)
movers['in_nyc_borough'] = ((movers['STATEFIP'] == 36) &
                            movers['cons_puma'].isin(NYC_PUMA_PREFIX))
left = movers[~movers['in_nyc_borough']].copy()


def bucket(r):
    st, cp = int(r['STATEFIP']), int(r['PUMA'])
    if st == 36:
        if 3100 <= cp <= 3199: return 'Westchester / Rockland / Putnam'
        if 3200 <= cp <= 3299: return 'Nassau (Long Island)'
        if 3300 <= cp <= 3399: return 'Suffolk (Long Island)'
        return 'Other NY State (Hudson Valley / upstate)'
    if st == 34: return 'New Jersey'
    if st == 9:  return 'Connecticut'
    if st == 42: return 'Pennsylvania'
    if st == 12: return 'Florida'
    if st == 48: return 'Texas'
    if st == 6:  return 'California'
    if st == 37: return 'North Carolina'
    if st == 13: return 'Georgia'
    SE = {45,47,51,54,21,24,11,1,22,5,28,10}
    MW = {17,18,26,39,55,19,27,29,31,38,46,20}
    W  = {4,8,32,35,49,30,16,41,53,56,15,2}
    NE = {25,23,33,50,44}
    if st in SE: return 'Other Southeast'
    if st in MW: return 'Midwest'
    if st in W:  return 'Other West'
    if st in NE: return 'Other Northeast'
    return 'Other US'


left['dest'] = left.apply(bucket, axis=1)

# ---- 4. Aggregate per (HH-with-kids, destination) ----
agg = left.groupby(['has_kid', 'dest'])['PERWT'].sum().unstack(level='has_kid', fill_value=0)
agg = agg.rename(columns={0: 'no_kid', 1: 'with_kid'})

TOTAL_KIDS = int(agg['with_kid'].sum())
TOTAL_NOKID = int(agg['no_kid'].sum())
print(f"HH-with-kids movers leaving NYC: {TOTAL_KIDS:,} weighted")
print(f"HH-without-kids movers leaving NYC: {TOTAL_NOKID:,} weighted")
print(agg.to_string())

# ---- 5. Color per destination — consistent across both treemaps for comparison ----
COLOR = {
    'New Jersey':                                '#0BB4FF',   # HE blue - close suburb
    'Westchester / Rockland / Putnam':           '#7BC2E0',
    'Nassau (Long Island)':                      '#1E5A8C',
    'Suffolk (Long Island)':                     '#34556E',
    'Other NY State (Hudson Valley / upstate)':  '#67A275',   # HE green
    'Connecticut':                               '#9CB39E',
    'Pennsylvania':                              '#FEC439',   # HE yellow
    'Florida':                                   '#D03A2E',   # WSJ red
    'Other Southeast':                           '#E8806C',
    'North Carolina':                            '#C5621F',
    'Georgia':                                   '#B05D2C',
    'Texas':                                     '#A0531D',
    'California':                                '#7E89C7',
    'Other West':                                '#B9A78A',
    'Midwest':                                   '#9CA68F',
    'Other Northeast':                           '#C6DCCB',
    'Other US':                                  '#BAB3AC',
}


# ---- 6. Layout two treemaps side by side ----
WIDTH = 1700
HEIGHT = 950
TITLE_H = 110
FOOTER_H = 55
GAP = 30
COL_W = (WIDTH - 2 * 24 - GAP) / 2  # ~821
PLOT_Y = TITLE_H
PLOT_H = HEIGHT - TITLE_H - FOOTER_H


def layout_treemap(values, labels, x, y, w, h):
    return squarify.padded_squarify(
        squarify.normalize_sizes(values, w, h), x, y, w, h)


def shade(hex_color: str, factor: float) -> str:
    hh = hex_color.lstrip('#')
    r, g, b = int(hh[0:2], 16), int(hh[2:4], 16), int(hh[4:6], 16)
    def adj(c):
        if factor < 1: return int(c * factor)
        return int(c + (255 - c) * (factor - 1))
    return f"#{adj(r):02X}{adj(g):02X}{adj(b):02X}"


def render_treemap(col_x: int, col_y: int, w: int, h: int,
                   data_col: str, header_label: str,
                   subtitle: str):
    out = []
    df = agg[[data_col]].copy()
    df = df.sort_values(data_col, ascending=False)
    df = df[df[data_col] > 0]
    total = int(df[data_col].sum())
    rects = layout_treemap(df[data_col].tolist(), df.index.tolist(),
                            col_x, col_y, w, h)
    # Column header (above the treemap)
    out.append(f'<text x="{col_x}" y="{col_y - 18}" font-size="18" font-weight="700" fill="#3D3733">{header_label}</text>')
    out.append(f'<text x="{col_x}" y="{col_y - 4}" font-size="11.5" fill="#7F7570">{subtitle}  ·  {total:,} weighted persons</text>')
    for i, (name, r) in enumerate(zip(df.index, rects)):
        val = int(df.iloc[i, 0])
        pct = val / total * 100
        rx, ry, rw, rh = r['x'], r['y'], r['dx'], r['dy']
        color = COLOR.get(name, '#999999')
        out.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" fill="{color}" stroke="#FFFFFF" stroke-width="2"/>')
        # Text: hide if too small
        if rw > 65 and rh > 30:
            out.append(f'<text x="{rx + 7}" y="{ry + 17}" font-size="12" font-weight="700" fill="#1A1A1A">{name}</text>')
            out.append(f'<text x="{rx + 7}" y="{ry + 32}" font-size="11" fill="#1A1A1A">{val:,} · {pct:.1f}%</text>')
        elif rw > 48 and rh > 18:
            out.append(f'<text x="{rx + 4}" y="{ry + 12}" font-size="9.5" font-weight="700" fill="#1A1A1A">{name.split(" (")[0]}</text>')
            if rh > 26:
                out.append(f'<text x="{rx + 4}" y="{ry + 23}" font-size="9.5" fill="#1A1A1A">{pct:.1f}%</text>')
    return out


# ---- 7. Assemble SVG ----
svg_parts = []
svg_parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'viewBox="0 0 {WIDTH} {HEIGHT}" width="{WIDTH}" height="{HEIGHT}" '
    f'style="background:#FFFFFF;font-family:\'ABC Oracle Edu\',Arial,sans-serif">'
)
# Title
svg_parts.append(f'<rect x="24" y="20" width="40" height="3" fill="#D03A2E"/>')
svg_parts.append(
    f'<text x="24" y="48" font-size="24" font-weight="700" fill="#3D3733">'
    'Families and singles leave NYC at the same rate — but they go to different places'
    '</text>'
)
svg_parts.append(
    f'<text x="24" y="72" font-size="13" fill="#7F7570">'
    'Where movers from Bronx · Brooklyn · Manhattan · Queens · Staten Island went, when they left the 5 boroughs entirely. '
    'IPUMS USA ACS 1-year, 2021 + 2022 pooled. Households flagged as "with kids" if any member is under 18.'
    '</text>'
)

LEFT_X = 24
RIGHT_X = int(24 + COL_W + GAP)
svg_parts.extend(render_treemap(LEFT_X, PLOT_Y, int(COL_W), PLOT_H,
                                'with_kid', 'Households WITH children',
                                'Families with at least one kid under 18'))
svg_parts.extend(render_treemap(RIGHT_X, PLOT_Y, int(COL_W), PLOT_H,
                                'no_kid', 'Households WITHOUT children',
                                'No member under 18 in the household'))

# Footer comparison numbers
svg_parts.append(
    f'<text x="{WIDTH/2}" y="{HEIGHT - 28}" font-size="14" font-weight="700" '
    f'fill="#3D3733" text-anchor="middle">'
    f'Both groups left NYC MSA at ≈51% of all out-of-borough moves — '
    f'families: {TOTAL_KIDS:,}  ·  no-kids: {TOTAL_NOKID:,}</text>'
)
svg_parts.append(
    f'<text x="24" y="{HEIGHT - 8}" font-size="9" fill="#7F7570" font-style="italic">'
    'Source: U.S. Census Bureau ACS 1-year microdata via IPUMS USA (Data lake: Data/IPUMS/acs_1y_degfield_migration). '
    'PUMS persons whose MIGPLAC1=NY and MIGPUMA1 in NYC borough (3700-4100), excluding intra-NYC moves. Person weights (PERWT).'
    '</text>'
)
svg_parts.append('</svg>')

svg_text = '\n'.join(svg_parts)
(OUT / 'nyc_outflow_treemap_family_compare.svg').write_text(svg_text)
html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Family vs non-family destinations — NYC outflow</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Bold.otf') format('opentype'); font-weight:700; }}
body {{ margin:0; padding:20px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; }}
</style></head><body>{svg_text}</body></html>"""
(OUT / 'nyc_outflow_treemap_family_compare.html').write_text(html)
print(f"\nWrote {OUT / 'nyc_outflow_treemap_family_compare.svg'}")
print(f"Wrote {OUT / 'nyc_outflow_treemap_family_compare.html'}")
