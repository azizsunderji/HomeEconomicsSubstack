"""
Build small-multiples map: 10 metros × 5 periods.

Each panel shows MSA counties shaded by absolute change in under-18 during the
period. Diverging color scale red-blue centered at 0. City polygon outlined.

Inputs:
  data/county_under18_metro10_periods.csv  — per-county per-period changes
  data/geo/metro10_counties.geojson        — county polygons (126 counties)
  data/geo/top10_cities.geojson            — city polygons (12 cities)

Output:
  outputs/metro_period_maps.html
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
GEO = DATA / "geo"
OUT = PROJECT / "outputs"

# 10 CBSAs in display order
METROS = [
    ("35620", "New York", "New York", "36"),
    ("31080", "Los Angeles", "Los Angeles", "06"),
    ("16980", "Chicago", "Chicago", "17"),
    ("19100", "Dallas", "Dallas", "48"),
    ("26420", "Houston", "Houston", "48"),
    ("47900", "Washington DC", None, "11"),   # DC has no place polygon — county = city
    ("12060", "Atlanta", "Atlanta", "13"),
    ("33100", "Miami", "Miami", "12"),
    ("37980", "Philadelphia", "Philadelphia", "42"),
    ("38060", "Phoenix", "Phoenix", "04"),
]

PERIODS = [
    ("chg_00_05", "2000–2005"),
    ("chg_05_10", "2005–2010"),
    ("chg_10_15", "2010–2015"),
    ("chg_15_20", "2015–2020"),
    ("chg_19_24", "2019–2024"),
]

# Load data
periods_df = pd.read_csv(DATA / "county_under18_metro10_periods.csv", dtype={"county_fips": str, "cbsa_code": str})
periods_df["county_fips"] = periods_df["county_fips"].str.zfill(5)

counties_geo = json.loads((GEO / "metro10_counties.geojson").read_text())
cities_geo   = json.loads((GEO / "top10_cities.geojson").read_text())

# Build per-metro panel data
metros_data = []
all_changes = []
for cbsa, label, city_name, state_fips in METROS:
    metro_counties = periods_df[periods_df["cbsa_code"] == cbsa].copy()
    county_periods = {}
    for _, row in metro_counties.iterrows():
        county_periods[row["county_fips"]] = {p_col: int(row[p_col]) if pd.notna(row[p_col]) else 0 for p_col, _ in PERIODS}
    # Collect for color scale
    for cdict in county_periods.values():
        all_changes.extend(cdict.values())
    metros_data.append({
        "cbsa": cbsa,
        "label": label,
        "city_name": city_name,
        "state_fips": state_fips,
        "county_changes": county_periods,
    })

# Color scale parameters
import math
max_abs = max(abs(v) for v in all_changes)
# Round to a "nice" number for the scale
scale_max = math.ceil(max_abs / 50000) * 50000
print(f"Color scale: ±{scale_max:,}")

P = {
    "metros": metros_data,
    "periods": PERIODS,
    "counties_geo": counties_geo,
    "cities_geo": cities_geo,
    "scale_max": scale_max,
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>U.S. metros: under-18 change by period, 2000–2024</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:24px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:24px; max-width:1100px; }
.grid { display:grid; grid-template-columns:140px repeat(5, 1fr); gap:6px; align-items:start; max-width:1300px; }
.col-hdr { font-size:14px; font-weight:500; text-align:center; padding-bottom:4px; color:#3D3733; }
.row-label { font-size:15px; font-weight:500; padding:50px 4px 0; }
.panel { background:#fff; aspect-ratio:1.05; border:0.5px solid #e1e2e3; }
.legend { display:flex; align-items:center; gap:14px; margin-top:18px; font-size:13px; color:#7F7570; }
.legend-bar { display:inline-block; width:280px; height:14px; background:linear-gradient(to right, #A32515, #F4743B, #f5e6df, #BCE8FF, #0BB4FF, #003D66); }
.source { color:#7F7570; font-size:12px; max-width:1100px; margin-top:20px; line-height:1.5; }
</style></head>
<body>
<h1>Where the kids are: under-18 change by metro and period, 2000–2024</h1>
<div class="sub">Each panel is one metropolitan area (rows) and one 5-year period (columns). Counties shaded by absolute change in under-18 population (people, not %). City polygon outlined in dark red where applicable.</div>

<div class="grid" id="grid"></div>

<div class="legend">
  <span>−__SCALE_LABEL__ kids</span>
  <span class="legend-bar"></span>
  <span>+__SCALE_LABEL__ kids</span>
</div>

<div class="source">
Source: tract-level under-18 from U.S. Census Bureau Decennial 2000/2010/2020 and ACS 5-year endpoints (2009, 2014, 2023 vintages), aggregated to county level. MSA counties per OMB 2023 CBSA delineation. Each panel shows the simple change in under-18 within each county over the labeled 5-year period.
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const grid = d3.select('#grid');

// Color scale
const colorScale = d3.scaleLinear()
  .domain([-P.scale_max, 0, P.scale_max])
  .range(['#A32515', '#f5e6df', '#003D66'])
  .clamp(true);

// Header row
grid.append('div'); // empty corner cell
P.periods.forEach(([k, lbl]) => {
  grid.append('div').attr('class','col-hdr').text(lbl);
});

// One row per metro
P.metros.forEach(metro => {
  // Row label
  grid.append('div').attr('class','row-label').text(metro.label);

  // Filter counties for this CBSA
  const metroCounties = P.counties_geo.features.filter(f => f.properties.cbsa_code == metro.cbsa);
  // Filter city polygons for this metro
  const metroCities = P.cities_geo.features.filter(f => {
    if (!metro.city_name) return false;
    if (f.properties.NAME !== metro.city_name) return false;
    if (f.properties.state_fips !== metro.state_fips) return false;
    return true;
  });

  // Fit a single projection across all panels for this metro
  const fc = { type: 'FeatureCollection', features: metroCounties };
  P.periods.forEach(([periodKey, periodLbl]) => {
    const cell = grid.append('div').attr('class','panel');
    const w = 240, h = 230;
    const svg = cell.append('svg').attr('viewBox', `0 0 ${w} ${h}`).attr('width','100%').attr('height','100%');
    const proj = d3.geoMercator().fitExtent([[6,6],[w-6,h-6]], fc);
    const path = d3.geoPath(proj);

    // Counties (shaded)
    svg.append('g').selectAll('path').data(metroCounties).join('path')
      .attr('d', path)
      .attr('fill', d => {
        const ch = (metro.county_changes[d.properties.county_fips] || {})[periodKey] || 0;
        return colorScale(ch);
      })
      .attr('stroke', '#666').attr('stroke-width', 0.4);

    // City polygons outline
    metroCities.forEach(cf => {
      svg.append('path').datum(cf).attr('d', path)
        .attr('fill','none').attr('stroke','#A32515').attr('stroke-width',1.2);
    });
  });
});

// Replace legend labels
const fmt = n => (n/1000).toFixed(0) + 'K';
document.body.innerHTML = document.body.innerHTML.replace(/__SCALE_LABEL__/g, fmt(P.scale_max));
</script>
</body>
</html>
"""

path = OUT / "metro_period_maps.html"
html = template.replace("__DATA__", json.dumps(P))
path.write_text(html)
print(f"Wrote {path} ({path.stat().st_size/1e6:.1f} MB)")
