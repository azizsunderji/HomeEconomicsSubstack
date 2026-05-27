"""
The headline chart: rate of growth of kids in cities vs. suburbs.

Two lines, indexed to 1970 = 100.
  - City core = 1950 SMA central counties (held fixed across decades)
  - Suburbs  = original 1970 suburbs (counties in any MSA in 1970, not 1950 central; held fixed)

This is a fixed-geography "constant boundary" comparison — neither line is inflated
by post-1970 county annexation into MSAs.
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

decomp = pd.read_csv(DATA / "under18_city_suburb_1970_decomp_to2024.csv")
decomp = decomp[decomp["year"] >= 1970].copy()
years = decomp["year"].astype(int).tolist()

# Place-level central-city totals (all 196 cities of all 172 1950 SMAs)
# NHGIS 1980-2020, ACS 2024
city_panel = pd.read_csv(DATA / "under18_central_cities_all172.csv")
city_panel = city_panel.dropna(subset=["under18"])
city_year = city_panel.groupby("year", as_index=False)["under18"].sum()
city_year_map = dict(zip(city_year["year"].astype(int), city_year["under18"]))
# Append 2024 (from ACS pull)
cc2024_path = DATA / "under18_central_cities_2024_all172.csv"
if not cc2024_path.exists():
    cc2024_path = DATA / "under18_central_cities_2024.csv"  # fall back to 60-city
cc2024 = pd.read_csv(cc2024_path)
city_year_map[2024] = cc2024["under18_2024"].sum()

def vals_m(col):
    return [round(v / 1e6, 2) for v in decomp[col].tolist()]

city_core_county = vals_m("A_city_core_1950")
new_city_cores   = vals_m("C_new_city_core_post1970")
suburbs_orig     = vals_m("B_original_suburb_1970")
suburbs_annx     = vals_m("D_annexed_suburb_post1970")

# Cities (place-level, top 60) — null before 1980
cities       = [round(city_year_map[y] / 1e6, 2) if y in city_year_map else None for y in years]
# Inner suburb = city-core county − actual top-60 city (1980+); null before 1980
inner_suburb = [round(city_core_county[i] - cities[i], 2) if cities[i] is not None else None for i in range(len(years))]

# Compute 1980-2020 changes for subtitle
def pct(values):
    return 100 * (values[-1] / values[0] - 1)

# Filter to 1980+ for the city/inner suburb pct calcs
y1980_idx = years.index(1980)
cities_1980plus = [cities[i] for i in range(y1980_idx, len(years))]
inner_1980plus  = [inner_suburb[i] for i in range(y1980_idx, len(years))]
outer_1980plus  = [suburbs_orig[i] for i in range(y1980_idx, len(years))]
annx_1980plus   = [suburbs_annx[i] for i in range(y1980_idx, len(years))]

P = {
    "years": [int(y) for y in years],
    "city_core_county": city_core_county,
    "cities":           cities,
    "inner_suburb":     inner_suburb,
    "new_city_cores":   new_city_cores,
    "suburbs_orig":     suburbs_orig,
    "suburbs_annx":     suburbs_annx,
    "title":    "U.S. under-18: cities, inner suburbs, outer suburbs (1970–2024)",
    "subtitle": (
        f"1980–2024: 196 central cities of the 172 1950 SMAs (place-level) {cities_1980plus[0]:.1f}M → {cities_1980plus[-1]:.1f}M ({pct(cities_1980plus):+.0f}%); "
        f"inner suburbs (rest of 1950 central counties) {inner_1980plus[0]:.1f}M → {inner_1980plus[-1]:.1f}M ({pct(inner_1980plus):+.0f}%); "
        f"outer (1970-fixed) suburbs {outer_1980plus[0]:.1f}M → {outer_1980plus[-1]:.1f}M ({pct(outer_1980plus):+.0f}%); "
        f"annexed suburbs {annx_1980plus[0]:.1f}M → {annx_1980plus[-1]:.1f}M."
    ),
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>__TITLE__</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Thin.otf') format('opentype'); font-weight:200; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }
svg { display:block; margin:20px auto; }
</style></head><body>
<svg id="chart" viewBox="0 0 960 720" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const BG='#F6F7F3', TEXT='#3D3733', SUBTEXT='#7F7570', GRID='#e1e2e3';
const W=960, H=720, PAD=40;
const svg = d3.select('#chart');
svg.append('rect').attr('width',W).attr('height',H).attr('fill',BG);

svg.append('text').attr('x',PAD).attr('y',PAD+30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',24).attr('font-weight',500).attr('fill',TEXT)
  .text(P.title);

const subLines = [];
{
  const words = P.subtitle.split(/\s+/);
  let line = '';
  const maxChars = 100;
  for (const w of words) {
    if ((line + ' ' + w).length > maxChars) { subLines.push(line.trim()); line = w; }
    else { line += ' ' + w; }
  }
  if (line.trim()) subLines.push(line.trim());
}
const subT = svg.append('text').attr('x',PAD).attr('y',PAD+30+30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',17).attr('font-weight',400).attr('fill',SUBTEXT);
subLines.forEach((l,i) => subT.append('tspan').attr('x',PAD).attr('dy', i===0 ? 0 : 22).text(l));

const chartTop = PAD + 30 + 30 + 22*subLines.length + 60;
const chartBottom = H - PAD - 110;
const chartLeft = PAD + 60;
const chartRight = W - PAD - 200;

const xs = P.years;
const x = d3.scaleLinear().domain(d3.extent(xs)).range([chartLeft, chartRight]);
const allVals = [...P.city_core_county, ...P.suburbs_orig].filter(v => v !== null);
P.cities.forEach(v => v !== null && allVals.push(v));
P.inner_suburb.forEach(v => v !== null && allVals.push(v));
P.suburbs_annx.forEach(v => v !== null && allVals.push(v));
P.new_city_cores.forEach(v => v !== null && allVals.push(v));
const ymax = Math.max(...allVals) * 1.08;
const y = d3.scaleLinear().domain([0, ymax]).range([chartBottom, chartTop]);

const yTicks = y.ticks(7);
const gridG = svg.append('g').attr('id','grid');
yTicks.forEach(t => {
  gridG.append('line').attr('x1',chartLeft).attr('x2',chartRight).attr('y1',y(t)).attr('y2',y(t))
    .attr('stroke', GRID).attr('stroke-width', 0.5);
});
const yLabG = svg.append('g').attr('id','y-labels');
yTicks.forEach((t,i) => {
  const isTop = (i === yTicks.length - 1);
  let lbl = String(Math.round(t));
  if (isTop) lbl = lbl + 'M';
  yLabG.append('text').attr('x',chartLeft-8).attr('y',y(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

const xTickG = svg.append('g').attr('id','x-ticks');
const xLabG = svg.append('g').attr('id','x-labels');
xs.forEach(yr => {
  xTickG.append('line').attr('x1',x(yr)).attr('x2',x(yr)).attr('y1',chartBottom).attr('y2',chartBottom+10)
    .attr('stroke',TEXT).attr('stroke-width',0.5);
  let lbl = String(yr);
  if (yr !== 1970 && yr !== 2000 && yr !== 2020) lbl = String(yr).slice(2);
  xLabG.append('text').attr('x',x(yr)).attr('y',chartBottom+30).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

const lineFn = d3.line().defined(v => v !== null && v !== undefined).x((_,i)=>x(xs[i])).y(v=>y(v));
const series = [
  {name: 'City (196 central cities, place-level)',  color: '#A32515', values: P.cities,           style: 'solid'},
  {name: 'Inner suburb (rest of 1950 central county)', color: '#F4743B', values: P.inner_suburb,    style: 'solid'},
  {name: 'New city cores (post-1970 metros)',        color: '#67A275', values: P.new_city_cores.map(v => v > 0 ? v : null), style: 'solid'},
  {name: 'Outer suburb (1970-fixed outlying)',       color: '#0BB4FF', values: P.suburbs_orig,    style: 'solid'},
  {name: 'Annexed suburb (post-1970)',               color: '#FEC439', values: P.suburbs_annx,    style: 'solid'},
  // pre-1980 city core (county-level) — dotted, since we can't split city from inner suburb
  {name: 'City core (county-level, pre-1980)',       color: '#7F7570', values: P.city_core_county.map((v,i)=>xs[i] < 1980 ? v : null), style: 'dotted'},
];
const linesG = svg.append('g').attr('id','lines');
series.forEach(s => {
  const p = linesG.append('path').attr('d', lineFn(s.values)).attr('fill','none')
    .attr('stroke', s.color).attr('stroke-width', s.style === 'dotted' ? 1.8 : 2.8)
    .attr('style','mix-blend-mode: multiply');
  if (s.style === 'dotted') p.attr('stroke-dasharray', '3,4');
  xs.forEach((yr, i) => {
    if (s.values[i] !== null && s.values[i] !== undefined && s.style !== 'dotted') {
      linesG.append('circle').attr('cx', x(yr)).attr('cy', y(s.values[i]))
        .attr('r', 3.5).attr('fill', s.color);
    }
  });
});

// Right-side labels: include 2020 indexed value
function wrapLabel(name, maxChars) {
  const words = name.split(' ');
  const lines = [];
  let cur = '';
  for (const w of words) {
    if ((cur + ' ' + w).length > maxChars) { lines.push(cur.trim()); cur = w; }
    else { cur += ' ' + w; }
  }
  if (cur.trim()) lines.push(cur.trim());
  return lines;
}
const lastIdx = xs.length - 1;
const labels = series
  .filter(s => s.values[lastIdx] !== null && s.values[lastIdx] !== undefined && s.style !== 'dotted')
  .map(s => ({
    name: s.name, value: s.values[lastIdx].toFixed(1) + 'M', color: s.color, y: y(s.values[lastIdx]),
    lines: wrapLabel(s.name, 22),
  }));
labels.sort((a,b) => a.y - b.y);
for (let i = 1; i < labels.length; i++) {
  const minGap = labels[i-1].lines.length * 17 + 20;
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}
const labG = svg.append('g').attr('id','labels');
labels.forEach(d => {
  labG.append('text').attr('x', chartRight+14).attr('y', d.y).attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',20).attr('font-weight',500).attr('fill',d.color)
    .text(d.value);
  d.lines.forEach((line, i) => {
    labG.append('text').attr('x', chartRight+14).attr('y', d.y + 18 + i*15).attr('dy','0.32em')
      .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',400).attr('fill',d.color)
      .text(line);
  });
});

// Source
const srcLines = [
  'Source: U.S. under-18 by county and decennial 1950–2020 from NHGIS (Manson et al.); 2024 county under-18 from Census PEP V2024. City under-18 (place-level)',
  'from NHGIS Sex×Age tables 1980–2020 + ACS 1-year/5-year 2024 for the 196 named central cities of all 172 1950 SMAs. Inner suburb = total under-18 in 1950 SMA',
  'central counties minus the central cities sitting in them. Outer suburb = the 480 counties in any MSA in 1970 that were not 1950 central counties, held fixed.',
  'Annexed suburb = outlying counties added to MSAs after 1970. New city cores = central counties of MSAs formed after 1970 (Las Vegas, Phoenix outer, etc.).',
  'Place boundaries follow contemporary annexations at each census (cities have annexed land over time). Pre-1980 city-level data not available at national scale.',
];
const srcG = svg.append('g').attr('id','source');
const srcStart = H - PAD - 15 - (srcLines.length - 1) * 16;
const srcT = srcG.append('text').attr('font-family','ABC Oracle Edu').attr('font-size',12)
  .attr('font-weight',200).attr('fill',TEXT);
srcLines.forEach((l,i) => srcT.append('tspan').attr('x',PAD).attr('y', srcStart + i*16).text(l));
</script>
</body></html>
"""

path = OUT / "under18_core_vs_burb_indexed.html"
html = template.replace("__TITLE__", P["title"]).replace("__DATA__", json.dumps(P))
path.write_text(html)
print(f"Wrote {path}")
print(f"Cities (M):       {dict(zip(years, cities))}")
print(f"Inner suburb (M): {dict(zip(years, inner_suburb))}")
print(f"New city cores:   {dict(zip(years, new_city_cores))}")
print(f"Outer suburb (M): {dict(zip(years, suburbs_orig))}")
print(f"Annexed (M):      {dict(zip(years, suburbs_annx))}")
