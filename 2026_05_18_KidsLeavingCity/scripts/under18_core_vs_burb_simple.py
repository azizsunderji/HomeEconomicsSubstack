"""
Simple two-group comparison: kids in CITY CORE vs kids in SUBURBS, 1950-2020.

Suburb tier is split into:
  - Original 1970 suburbs (fixed-geography component)
  - Post-1970 annexed suburbs (the "MSA-got-larger" component)

Output:
  outputs/under18_core_vs_burb.html (+ .png)
  Levels view (millions of kids) AND indexed-to-1950 view
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

decomp = pd.read_csv(DATA / "under18_city_suburb_1970_decomp.csv")
# Columns: year, A_city_core_1950, B_original_suburb_1970, C_new_city_core_post1970, D_annexed_suburb_post1970, Z_never_msa

# Compute group totals
decomp["city_core_total"]   = decomp["A_city_core_1950"]
decomp["suburb_original"]   = decomp["B_original_suburb_1970"]
decomp["suburb_annexed"]    = decomp["D_annexed_suburb_post1970"]
decomp["suburb_total"]      = decomp["suburb_original"] + decomp["suburb_annexed"]
# (Treat post-1970 new city cores as a small separate annotation if asked, not in main view)

years = decomp["year"].astype(int).tolist()

# Convert to millions
to_m = lambda c: (decomp[c] / 1e6).round(3).tolist()


def chart(mode: str):
    if mode == "level":
        title = "U.S. children: city cores vs. suburbs, 1950–2020"
        subtitle = (
            "Kids in city-core counties (orange) have been roughly flat since 1970. "
            "Suburbs grew — but a substantial share of the growth is counties that got annexed into MSAs after 1970 (yellow band), not real growth in pre-1970 suburbs (blue band)."
        )
        cc_vals = to_m("city_core_total")
        orig_vals = to_m("suburb_original")
        annex_vals = to_m("suburb_annexed")
    else:  # indexed
        title = "U.S. children: city core vs. suburb growth — indexed to 1970 = 100"
        subtitle = (
            "Both lines start at 100 in 1970. Suburbs (with annexation) grew to 152 by 2020 (+52%). "
            "Original 1970 suburbs (fixed-geography) grew to 133 (+33%). City cores fell to 91 (−9%)."
        )
        idx = years.index(1970)
        def index_to_1970(col):
            base = decomp[col].iloc[idx]
            return [round(100 * v / base, 1) for v in decomp[col].tolist()]
        cc_vals = index_to_1970("city_core_total")
        orig_vals = index_to_1970("suburb_original")
        annex_vals_total = index_to_1970("suburb_total")  # suburb total incl annex
        annex_vals = annex_vals_total  # use total for indexed view

    if mode == "level":
        series = [
            {"id": "core",   "name": "City core (1950 central counties)",       "color": "#F4743B", "values": cc_vals,    "kind": "line"},
            {"id": "orig",   "name": "Original suburbs (1970 counties)",        "color": "#0BB4FF", "values": orig_vals,  "kind": "line"},
            {"id": "annex",  "name": "Suburbs annexed post-1970",               "color": "#FEC439", "values": annex_vals, "kind": "line"},
        ]
    else:
        series = [
            {"id": "core",       "name": "City core",                            "color": "#F4743B", "values": cc_vals,       "kind": "line"},
            {"id": "orig",       "name": "Suburbs — original 1970 (fixed geo)", "color": "#0BB4FF", "values": orig_vals,     "kind": "line"},
            {"id": "total_burb", "name": "Suburbs — with post-1970 annexation",  "color": "#67A275", "values": annex_vals,    "kind": "line"},
        ]

    P = {
        "years": [int(y) for y in years],
        "series": series,
        "mode": mode,
        "title": title,
        "subtitle": subtitle,
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
<svg id="chart" viewBox="0 0 1200 920" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const BG='#F6F7F3', TEXT='#3D3733', SUBTEXT='#7F7570', GRID='#e1e2e3';
const W=1200, H=920, PAD=40;
const svg = d3.select('#chart');
svg.append('rect').attr('width',W).attr('height',H).attr('fill',BG);

svg.append('text').attr('x',PAD).attr('y',PAD+30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',26).attr('font-weight',500).attr('fill',TEXT)
  .text(P.title);

const subLines = [];
{
  const words = P.subtitle.split(/\s+/);
  let line = '';
  const maxChars = 120;
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
const chartBottom = H - PAD - 120;
const chartLeft = PAD + 80;
const chartRight = W - PAD - 320;

const xs = P.years;
const x = d3.scaleLinear().domain(d3.extent(xs)).range([chartLeft, chartRight]);
const flat = P.series.flatMap(s => s.values);
const ymax = d3.max(flat) * 1.08;
const y = d3.scaleLinear().domain([0, ymax]).range([chartBottom, chartTop]);

function fmtY(v) {
  if (P.mode === 'indexed') return Math.round(v);
  return Math.round(v);
}

const yTicks = y.ticks(7);
const gridG = svg.append('g').attr('id','grid');
yTicks.forEach(t => {
  gridG.append('line').attr('x1',chartLeft).attr('x2',chartRight).attr('y1',y(t)).attr('y2',y(t))
    .attr('stroke',GRID).attr('stroke-width',0.5);
});
const yLabG = svg.append('g').attr('id','y-labels');
yTicks.forEach((t,i) => {
  const isTop = (i === yTicks.length - 1);
  let lbl = String(fmtY(t));
  if (isTop && P.mode !== 'indexed') lbl = lbl + 'M';
  yLabG.append('text').attr('x',chartLeft-8).attr('y',y(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

// 1970 = 100 reference line (indexed mode only)
if (P.mode === 'indexed') {
  svg.append('line').attr('x1',chartLeft).attr('x2',chartRight)
    .attr('y1',y(100)).attr('y2',y(100))
    .attr('stroke','#3D3733').attr('stroke-width',0.8).attr('stroke-dasharray','3,4').attr('opacity',0.5);
  svg.append('line').attr('x1',x(1970)).attr('x2',x(1970)).attr('y1',chartTop).attr('y2',chartBottom)
    .attr('stroke','#3D3733').attr('stroke-width',0.8).attr('stroke-dasharray','3,4').attr('opacity',0.5);
}

const xTickG = svg.append('g').attr('id','x-ticks');
const xLabG = svg.append('g').attr('id','x-labels');
xs.forEach(yr => {
  xTickG.append('line').attr('x1',x(yr)).attr('x2',x(yr)).attr('y1',chartBottom).attr('y2',chartBottom+10)
    .attr('stroke',TEXT).attr('stroke-width',0.5);
  let lbl = String(yr);
  if (yr !== 1950 && yr !== 1970 && yr !== 2000 && yr !== 2020) lbl = String(yr).slice(2);
  xLabG.append('text').attr('x',x(yr)).attr('y',chartBottom+30).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

// Lines
const lineFn = d3.line().x((_,i)=>x(xs[i])).y(v=>y(v));
const linesG = svg.append('g').attr('id','lines');
P.series.forEach(s => {
  linesG.append('path').attr('d',lineFn(s.values))
    .attr('fill','none').attr('stroke',s.color).attr('stroke-width',2.8)
    .attr('style','mix-blend-mode: multiply');
  xs.forEach((yr,i) => {
    if (s.values[i] !== null && s.values[i] !== undefined && (P.mode !== 'indexed' || s.values[i] > 0))
      linesG.append('circle').attr('cx', x(yr)).attr('cy', y(s.values[i]))
        .attr('r', 4).attr('fill', s.color);
  });
});

// Right-side labels
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
const labels = P.series.map(s => ({
  name: s.name, color: s.color, y: y(s.values[lastIdx]),
  lines: wrapLabel(s.name, 26),
}));
labels.sort((a,b) => a.y - b.y);
for (let i = 1; i < labels.length; i++) {
  const minGap = labels[i-1].lines.length * 17 + 12;
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}
const labG = svg.append('g').attr('id','labels');
labels.forEach(d => {
  d.lines.forEach((line, i) => {
    labG.append('text').attr('x',chartRight+14).attr('y', d.y + i*17).attr('dy','0.32em')
      .attr('font-family','ABC Oracle Edu').attr('font-size',15).attr('font-weight',500).attr('fill',d.color)
      .text(line);
  });
});

// Source
const srcLines = [
  'Source: U.S. under-18 by county and decennial from NHGIS (Manson et al.). MSA membership at each decennial from OMB delineations 1950–2023. City core =',
  '1950 SMA central counties (held fixed across decades). Original 1970 suburbs = counties that were in any MSA in 1970 and were not 1950 central counties.',
  'Annexed suburbs = outlying counties that joined an MSA after 1970. "City core" remains a COUNTY-level tier — within those counties the actual central city',
  'lost ~1M kids 1980-2020 while the rest of the central county absorbed the difference.',
];
const srcG = svg.append('g').attr('id','source');
const srcStart = H - PAD - 15 - (srcLines.length - 1) * 16;
const srcT = srcG.append('text').attr('font-family','ABC Oracle Edu').attr('font-size',13)
  .attr('font-weight',200).attr('fill',TEXT);
srcLines.forEach((l,i) => srcT.append('tspan').attr('x',PAD).attr('y', srcStart + i*16).text(l));
</script>
</body></html>
"""
    suffix = "_indexed" if mode == "indexed" else "_level"
    path = OUT / f"under18_core_vs_burb{suffix}.html"
    html = template.replace("__TITLE__", P["title"]).replace("__DATA__", json.dumps(P))
    path.write_text(html)
    print(f"Wrote {path}")


chart("level")
chart("indexed")
