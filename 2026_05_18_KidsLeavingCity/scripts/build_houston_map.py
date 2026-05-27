"""
Build interactive Houston-MSA map showing decade-by-decade growth.

- TX county polygons (geo: data/geo/tx_counties.geojson)
- Houston city polygon (data/geo/houston_city.geojson) — for visual reference
- Houston MSA county membership by decade (data/houston_msa_counties_by_decade.csv)
- Under-18 per county per decade (data/under18_by_county_decade.csv)

Output: outputs/houston_map.html

UI:
  - Decade slider (1950, 1960, ..., 2020)
  - At each decade, color counties:
      * Outside Houston MSA: light grey
      * In MSA: shaded by 'when they joined' (cohort color)
      * Harris (city core): always distinct orange
  - Houston city polygon outlined in red
  - Hover tooltip: county name + under-18 in that decade
  - Legend showing cohort colors
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

# Load geo (raw GeoJSON)
tx_counties = json.loads((DATA / "geo/tx_counties.geojson").read_text())
houston_city = json.loads((DATA / "geo/houston_city.geojson").read_text())

# Load Houston MSA membership and under-18
houston_panel = pd.read_csv(DATA / "houston_msa_counties_by_decade.csv", dtype={"county_fips": str})
houston_panel["county_fips"] = houston_panel["county_fips"].str.zfill(5)

under18 = pd.read_csv(DATA / "under18_by_county_decade.csv", dtype={"county_fips": str})
under18["county_fips"] = under18["county_fips"].str.zfill(5)
# Filter to TX counties only (state 48)
under18_tx = under18[under18["county_fips"].str.startswith("48")].copy()

# Build per-decade county data: { decade: { county_fips: {under18: X, in_msa: bool, joined: year, name: ...} } }
DECADES = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020]
county_data = {}
for d in DECADES:
    county_data[d] = {}
    pop_d = under18_tx[under18_tx["year"] == d].set_index("county_fips")["under18"].to_dict()
    for _, row in houston_panel.iterrows():
        cf = row["county_fips"]
        county_data[d][cf] = {
            "in_msa": bool(row[f"in_{d}"]),
            "joined": int(row["first_in_houston_msa"]) if pd.notna(row["first_in_houston_msa"]) else None,
            "under18": int(pop_d.get(cf, 0)),
            "name": row["county_name"],
        }
    # Also add under-18 for non-MSA TX counties (to display in tooltip)
    for cf, v in pop_d.items():
        if cf not in county_data[d]:
            county_data[d][cf] = {"in_msa": False, "joined": None, "under18": int(v), "name": ""}

P = {
    "decades": DECADES,
    "county_data": county_data,
    "geo": tx_counties,
    "city": houston_city,
    "houston_counties": sorted(houston_panel["county_fips"].tolist()),
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Houston MSA growth, 1950-2020</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Thin.otf') format('opentype'); font-weight:200; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
.wrap { max-width:1100px; margin:0 auto; padding:30px; }
h1 { font-size:28px; font-weight:500; margin:0 0 10px; }
.subtitle { color:#7F7570; font-size:16px; margin-bottom:20px; }
#map { background:#fff; border:1px solid #e1e2e3; }
.controls { display:flex; align-items:center; gap:20px; margin:20px 0; }
.controls button { font-family:'ABC Oracle Edu',sans-serif; font-size:14px; padding:6px 14px; background:#fff; border:1px solid #3D3733; color:#3D3733; cursor:pointer; border-radius:3px; }
.controls button:hover { background:#3D3733; color:#fff; }
.controls button.playing { background:#F4743B; color:#fff; border-color:#F4743B; }
#decade-display { font-size:28px; font-weight:500; color:#F4743B; min-width:80px; }
.slider { flex:1; }
.slider input { width:100%; }
.tick-labels { display:flex; justify-content:space-between; font-size:13px; color:#7F7570; padding:0 4px; margin-top:-4px; }
.legend { display:flex; flex-wrap:wrap; gap:14px; margin-top:14px; align-items:center; font-size:13px; }
.legend-item { display:flex; align-items:center; gap:6px; }
.legend-swatch { width:18px; height:14px; border:0.5px solid #3D3733; }
.stat-bar { display:flex; gap:18px; margin-top:14px; padding:12px; background:#fff; border:1px solid #e1e2e3; font-size:14px; }
.stat-bar .item { flex:1; }
.stat-bar .item-label { color:#7F7570; font-size:12px; }
.stat-bar .item-value { font-size:18px; font-weight:500; }
.tooltip { position:absolute; background:#3D3733; color:#fff; padding:8px 12px; font-size:13px; pointer-events:none; opacity:0; transition:opacity 0.12s; border-radius:3px; white-space:nowrap; z-index:10; }
.tooltip strong { color:#FEC439; }
.source { font-size:11px; color:#7F7570; margin-top:14px; line-height:1.4; }
</style>
</head>
<body>
<div class="wrap">
<h1>The Houston MSA, 1950–2020</h1>
<div class="subtitle">Counties join the MSA as commuting belts grow. Each one already had children before being reclassified — drag the slider to see when each was absorbed and how many kids were already there.</div>

<div class="tooltip" id="tip"></div>

<svg id="map" viewBox="0 0 1000 720" preserveAspectRatio="xMidYMid meet" width="100%" height="720"></svg>

<div class="controls">
  <button id="play">▶ Play</button>
  <div id="decade-display">1950</div>
  <div class="slider">
    <input type="range" id="slider" min="0" max="7" value="0" step="1">
    <div class="tick-labels">
      <span>1950</span><span>1960</span><span>1970</span><span>1980</span><span>1990</span><span>2000</span><span>2010</span><span>2020</span>
    </div>
  </div>
</div>

<div class="legend">
  <div class="legend-item"><div class="legend-swatch" style="background:#F4743B"></div>City core (Harris County, in MSA since 1950)</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#0BB4FF"></div>Joined 1970</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#5BC8FF"></div>Joined 1980</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#8FD9FF"></div>Joined 1990</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#BCE8FF"></div>Joined 2010</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#E0F3FF"></div>Joined 2020</div>
  <div class="legend-item"><div class="legend-swatch" style="background:#DADFCE"></div>Not in MSA</div>
  <div class="legend-item"><span style="border:1.5px solid #A32515; padding:0 8px; height:14px; display:inline-block;"></span>City of Houston (modern boundary)</div>
</div>

<div class="stat-bar">
  <div class="item"><div class="item-label">Counties in MSA</div><div class="item-value" id="stat-counties">1</div></div>
  <div class="item"><div class="item-label">Under-18 in MSA</div><div class="item-value" id="stat-under18">— M</div></div>
  <div class="item"><div class="item-label">Newly joined this decade</div><div class="item-value" id="stat-new">0</div></div>
  <div class="item"><div class="item-label">Their under-18 contribution</div><div class="item-value" id="stat-new-pop">— K</div></div>
</div>

<div class="source">
Sources: TIGER 2020 county and place boundaries (cartographic 1:500k). Houston-MSA membership per decade from OMB delineation files (1950–2020). County under-18 populations from NHGIS decennial census tabulations 1950–2020 (Manson et al.).
Note: county boundaries are shown at 2020 boundaries (TX county boundaries are stable since 1950); the City of Houston polygon is the 2020 city limits (city annexed substantially since 1950).
</div>

</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const W = 1000, H = 720;

// Cohort colors
const COHORT_COLORS = {
  1950: '#F4743B',  // city core (Harris)
  1970: '#0BB4FF',
  1980: '#5BC8FF',
  1990: '#8FD9FF',
  2000: '#A8E0FF',
  2010: '#BCE8FF',
  2020: '#E0F3FF',
};
const NOT_IN_MSA = '#DADFCE';

const svg = d3.select('#map');

// Project to fit the Houston metro region
const houstonFeatures = P.geo.features.filter(f => P.houston_counties.includes(f.properties.county_fips));
const houstonFC = { type: 'FeatureCollection', features: houstonFeatures };

// Use Albers projection centered on the Houston area
const projection = d3.geoAlbers()
  .rotate([95, 0])
  .center([0, 30])
  .parallels([28, 32])
  .fitExtent([[40, 40], [W-40, H-40]], houstonFC);
const path = d3.geoPath(projection);

// Draw ALL TX counties (background)
const allG = svg.append('g').attr('id','all-counties');
P.geo.features.forEach(f => {
  const fips = f.properties.county_fips;
  const isHou = P.houston_counties.includes(fips);
  allG.append('path').attr('d', path(f))
    .attr('fill', isHou ? NOT_IN_MSA : '#F6F7F3')
    .attr('stroke', '#a0a0a0').attr('stroke-width', isHou ? 0.8 : 0.4)
    .attr('data-fips', fips)
    .attr('class', isHou ? 'houston-county' : 'other-county');
});

// Houston city outline (drawn on top)
const cityG = svg.append('g').attr('id','city');
P.city.features.forEach(f => {
  cityG.append('path').attr('d', path(f))
    .attr('fill', 'none').attr('stroke', '#A32515').attr('stroke-width', 1.8);
});

// County labels for Houston MSA counties
const labelG = svg.append('g').attr('id','labels');
P.houston_counties.forEach(fips => {
  const f = P.geo.features.find(g => g.properties.county_fips === fips);
  if (!f) return;
  const c = path.centroid(f);
  if (!isFinite(c[0])) return;
  const nm = (P.county_data[2020][fips] || {}).name || '';
  const short = nm.replace(' County', '');
  labelG.append('text').attr('x', c[0]).attr('y', c[1]).attr('text-anchor','middle').attr('dy','-2')
    .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',400)
    .attr('fill','#3D3733').attr('pointer-events','none')
    .text(short);
});

// Tooltip
const tip = d3.select('#tip');
const tipShow = (evt, txt) => {
  tip.html(txt).style('opacity', 1)
    .style('left', (evt.pageX + 12) + 'px').style('top', (evt.pageY + 12) + 'px');
};
const tipHide = () => tip.style('opacity', 0);

// Render a decade
function render(decade) {
  d3.select('#decade-display').text(decade);
  let countiesInMSA = 0;
  let totalUnder18 = 0;
  let newCounties = 0;
  let newUnder18 = 0;

  P.houston_counties.forEach(fips => {
    const c = P.county_data[decade][fips];
    if (!c) return;
    const cellInMSA = c.in_msa;
    const joined = c.joined;
    let fill = NOT_IN_MSA;
    if (cellInMSA) {
      fill = COHORT_COLORS[joined] || '#bbbbbb';
      countiesInMSA += 1;
      totalUnder18 += c.under18;
      if (joined === decade) {
        newCounties += 1;
        newUnder18 += c.under18;
      }
    }
    const el = svg.select(`path[data-fips="${fips}"]`);
    el.transition().duration(350).attr('fill', fill);
  });

  d3.select('#stat-counties').text(countiesInMSA);
  d3.select('#stat-under18').text((totalUnder18/1e6).toFixed(2) + ' M');
  d3.select('#stat-new').text(newCounties);
  d3.select('#stat-new-pop').text(newUnder18 >= 1e6 ? (newUnder18/1e6).toFixed(2) + ' M' : (newUnder18/1e3).toFixed(0) + ' K');
}

// Hover for all houston counties
P.houston_counties.forEach(fips => {
  const el = svg.select(`path[data-fips="${fips}"]`);
  el.on('mouseenter', (evt) => {
    const decade = P.decades[+d3.select('#slider').node().value];
    const c = P.county_data[decade][fips];
    if (!c) return;
    const status = c.in_msa
      ? `<strong>In Houston MSA</strong> (joined ${c.joined})`
      : `<strong>Not yet in Houston MSA</strong>`;
    tipShow(evt, `${c.name}<br>${status}<br>Under-18 in ${decade}: ${c.under18.toLocaleString()}`);
  });
  el.on('mousemove', (evt) => {
    tip.style('left', (evt.pageX + 12) + 'px').style('top', (evt.pageY + 12) + 'px');
  });
  el.on('mouseleave', tipHide);
});

// Slider
const slider = d3.select('#slider');
slider.on('input', () => render(P.decades[+slider.node().value]));

// Play/pause
let playing = false;
let playTimer = null;
d3.select('#play').on('click', function() {
  if (playing) {
    clearInterval(playTimer);
    playing = false;
    d3.select(this).text('▶ Play').classed('playing', false);
  } else {
    playing = true;
    d3.select(this).text('⏸ Pause').classed('playing', true);
    playTimer = setInterval(() => {
      const cur = +slider.node().value;
      const nxt = cur >= P.decades.length - 1 ? 0 : cur + 1;
      slider.node().value = nxt;
      render(P.decades[nxt]);
    }, 1100);
  }
});

// Initial render
render(P.decades[0]);
</script>
</body>
</html>
"""

path = OUT / "houston_map.html"
html = template.replace("__DATA__", json.dumps(P))
path.write_text(html)
print(f"Wrote {path}")
print(f"  size: {path.stat().st_size/1e6:.1f} MB")
