"""
Build NYC-only small-multiples map: 1 metro × 5 periods.

Filters to the New York-Newark-Jersey City CBSA (35620, 22 counties) and
rescales the diverging color scale to NYC's own range (max abs change ~44K,
vs ~290K nationally), so within-MSA variation is actually visible.

Inputs:
  data/county_under18_metro10_periods.csv  — per-county per-period changes
  data/geo/metro10_counties.geojson        — county polygons (cbsa_code is int)
  data/geo/top10_cities.geojson            — city polygons (NYC is GEOID 3651000)

Output:
  outputs/nyc_period_maps.html
"""
import json
import math
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
GEO = DATA / "geo"
OUT = PROJECT / "outputs"

NYC_CBSA = 35620
CITY_NAME = "New York"
CITY_STATE_FIPS = "36"

PERIODS = [
    ("chg_00_05", "2000–2005"),
    ("chg_05_10", "2005–2010"),
    ("chg_10_15", "2010–2015"),
    ("chg_15_20", "2015–2020"),
    ("chg_19_24", "2019–2024"),
]

periods_df = pd.read_csv(
    DATA / "county_under18_metro10_periods.csv",
    dtype={"county_fips": str, "cbsa_code": str},
)
periods_df["county_fips"] = periods_df["county_fips"].str.zfill(5)
nyc_df = periods_df[periods_df["cbsa_code"] == str(NYC_CBSA)].copy()
print(f"NYC counties in panel data: {len(nyc_df)}")

county_changes = {}
all_changes = []
for _, row in nyc_df.iterrows():
    d = {p_col: int(row[p_col]) if pd.notna(row[p_col]) else 0 for p_col, _ in PERIODS}
    county_changes[row["county_fips"]] = d
    all_changes.extend(d.values())

max_abs = max(abs(v) for v in all_changes)
# Pick a "nice" round scale just above NYC's actual max
scale_max = math.ceil(max_abs / 5000) * 5000
print(f"NYC max abs change: {max_abs:,}  → color scale ±{scale_max:,}")

counties_geo = json.loads((GEO / "metro10_counties.geojson").read_text())
nyc_counties = [
    f for f in counties_geo["features"] if f["properties"].get("cbsa_code") == NYC_CBSA
]
print(f"NYC counties in geojson: {len(nyc_counties)}")

cities_geo = json.loads((GEO / "top10_cities.geojson").read_text())
nyc_city = [
    f
    for f in cities_geo["features"]
    if f["properties"].get("NAME") == CITY_NAME
    and f["properties"].get("state_fips") == CITY_STATE_FIPS
]
print(f"NYC city polygons: {len(nyc_city)}")

P = {
    "periods": PERIODS,
    "counties": {"type": "FeatureCollection", "features": nyc_counties},
    "city": {"type": "FeatureCollection", "features": nyc_city},
    "county_changes": county_changes,
    "scale_max": scale_max,
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC metro: under-18 change by period, 2000–2024</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:28px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:24px; max-width:1300px; }
.grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:10px; max-width:1800px; }
.col-hdr { font-size:15px; font-weight:500; text-align:center; padding:0 0 6px; color:#3D3733; }
.panel-wrap { display:flex; flex-direction:column; }
.panel { background:#fff; aspect-ratio:1; border:0.5px solid #e1e2e3; }
.legend { display:flex; align-items:center; gap:14px; margin-top:22px; font-size:13px; color:#7F7570; }
.legend-bar { display:inline-block; width:320px; height:14px; background:linear-gradient(to right, #A32515, #F4743B, #f5e6df, #BCE8FF, #0BB4FF, #003D66); }
.ticks { display:flex; justify-content:space-between; width:320px; margin-top:2px; font-size:11px; color:#7F7570; }
.source { color:#7F7570; font-size:12px; max-width:1300px; margin-top:22px; line-height:1.5; }
</style></head>
<body>
<h1>New York metro: under-18 change by period, 2000–2024</h1>
<div class="sub">22 counties of the New York–Newark–Jersey City MSA. Each panel covers a 5-year period; counties are shaded by absolute change in under-18 (people, not %). The five NYC boroughs are outlined in dark red. Color scale is rescaled to NYC's own range (±__SCALE_LABEL__), about 7× tighter than the 10-metro scale, so within-MSA variation is visible.</div>

<div class="grid" id="grid"></div>

<div style="display:flex; flex-direction:column; align-items:flex-start; margin-top:6px;">
  <div class="legend">
    <span>−__SCALE_LABEL__ kids</span>
    <span class="legend-bar"></span>
    <span>+__SCALE_LABEL__ kids</span>
  </div>
  <div class="ticks">
    <span>−__SCALE_LABEL__</span>
    <span>−__HALF_LABEL__</span>
    <span>0</span>
    <span>+__HALF_LABEL__</span>
    <span>+__SCALE_LABEL__</span>
  </div>
</div>

<div class="source">
Source: tract-level under-18 from U.S. Census Bureau Decennial 2000/2010/2020 and ACS 5-year endpoints (2009, 2014, 2023 vintages), aggregated to county level. MSA = New York–Newark–Jersey City, NY-NJ-PA (CBSA 35620) per OMB 2023. NYC city polygon = the five boroughs.
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const grid = d3.select('#grid');

const colorScale = d3.scaleLinear()
  .domain([-P.scale_max, -P.scale_max/2, 0, P.scale_max/2, P.scale_max])
  .range(['#A32515', '#F4743B', '#f5e6df', '#0BB4FF', '#003D66'])
  .clamp(true);

// Single shared projection across panels so boroughs sit in the same spot
const w = 360, h = 360;
const sharedProj = d3.geoMercator().fitExtent([[10,10],[w-10,h-10]], P.counties);
const path = d3.geoPath(sharedProj);

P.periods.forEach(([periodKey, periodLbl]) => {
  const wrap = grid.append('div').attr('class','panel-wrap');
  wrap.append('div').attr('class','col-hdr').text(periodLbl);
  const cell = wrap.append('div').attr('class','panel');
  const svg = cell.append('svg').attr('viewBox', `0 0 ${w} ${h}`).attr('width','100%').attr('height','100%');

  svg.append('g').selectAll('path').data(P.counties.features).join('path')
    .attr('d', path)
    .attr('fill', d => {
      const ch = (P.county_changes[d.properties.county_fips] || {})[periodKey] || 0;
      return colorScale(ch);
    })
    .attr('stroke', '#666').attr('stroke-width', 0.4);

  P.city.features.forEach(cf => {
    svg.append('path').datum(cf).attr('d', path)
      .attr('fill','none').attr('stroke','#A32515').attr('stroke-width',1.4);
  });
});

const fmt = n => (n/1000).toFixed(0) + 'K';
document.body.innerHTML = document.body.innerHTML
  .replace(/__SCALE_LABEL__/g, fmt(P.scale_max))
  .replace(/__HALF_LABEL__/g, fmt(P.scale_max/2));
</script>
</body>
</html>
"""

html = template.replace("__DATA__", json.dumps(P))
out_path = OUT / "nyc_period_maps.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.1f} MB)")
