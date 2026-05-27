"""
5-class chart: U.S. under-18 by fixed-geography ring, splitting "city core county"
into actual central city vs. balance-of-county from 1980 onward.

Series (after 1980 split):
  1. Central city only (place-level, top-60 1950 SMA central cities)         — 1980-2020
  2. Balance of city-core county (county minus central city = "inner suburb") — 1980-2020
  3. Original 1950-SMA outlying suburb counties                                — 1950-2020
  4. Added to MSA after 1950 (county reclassification)                        — 1950-2020
  5. Persistent non-metro counties                                            — 1950-2020

Plus: dotted gray "City core (1950 SMA central county) — county-level only" for 1950-1970
so the eye can follow the continuity before the city/balance split.
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

# County-level fixed-geography decomposition (1950-2020)
geo = pd.read_csv(DATA / "under18_fixed_geo_decomposition.csv")

# Central city under-18 by decade (place-level, 1980-2020)
cc = pd.read_csv(DATA / "under18_central_cities.csv")
city_totals = (
    cc.dropna(subset=["under18"])
    .groupby("year", as_index=False)["under18"]
    .sum()
    .rename(columns={"under18": "central_city_total"})
)
print("Central city totals (top 60 cities):")
print(city_totals)

# Merge
df = geo.merge(city_totals, on="year", how="left")
df["balance_of_city_core_county"] = df["A_city_core"] - df["central_city_total"]
df.to_csv(DATA / "under18_5class_decomposition.csv", index=False)

print("\n5-class decomposition (millions):")
disp = df.copy()
for c in disp.columns:
    if c != "year":
        disp[c] = disp[c] / 1e6
print(disp.round(2).to_string(index=False))

years = df["year"].astype(int).tolist()

# Series for the chart
# For 1950-1970, "central city" and "balance" are NaN; "city core county" is shown
# For 1980-2020, "central city" + "balance" replace "city core county"
def s(col, years=years):
    return [None if pd.isna(v) else v / 1e6 for v in df[col].tolist()]

series = [
    {
        "id": "central_city",
        "name": "Central city only (top 60)",
        "color": "#F4743B",          # red/orange — the actual urban-decline story
        "values": s("central_city_total"),
    },
    {
        "id": "balance",
        "name": "Inner suburb (rest of city-core county)",
        "color": "#FBCAB5",          # light red — paired with central city
        "values": s("balance_of_city_core_county"),
    },
    {
        "id": "city_core_legacy",
        "name": "City core (county-level, 1950–1970)",
        "color": "#3D3733",          # near-black, dotted, for pre-1980 only
        "values": [df["A_city_core"][i] / 1e6 if y <= 1970 else None for i, y in enumerate(years)],
        "dotted": True,
    },
    {
        "id": "original_suburb",
        "name": "Original suburb (1950 SMA outlying county)",
        "color": "#0BB4FF",          # blue
        "values": s("B_original_suburb"),
    },
    {
        "id": "added_msa",
        "name": "Added to MSA after 1950",
        "color": "#FEC439",          # yellow — the reclassification story
        "values": s("C_newly_added_msa"),
    },
    {
        "id": "non_metro",
        "name": "Never in an MSA",
        "color": "#67A275",          # green
        "values": s("D_persistent_nonmetro"),
    },
]

P = {
    "years": years,
    "series": series,
    "title": "U.S. under-18 population: actual central cities vs. their suburban surroundings, 1950–2020",
    "subtitle": "Top 60 1950 central cities lost ~1M kids since 1980 (red); their balance-of-county “inner-suburb” ring gained ~3M (pink). The rest of “suburbia” is dominated by counties that joined an MSA only after 1950 (yellow) — reclassification more than migration.",
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
<svg id="chart" viewBox="0 0 1200 987" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const BG='#F6F7F3', TEXT='#3D3733', SUBTEXT='#7F7570', GRID='#e1e2e3';
const W=1200, H=987, PAD=40;
const svg = d3.select('#chart');
svg.append('rect').attr('width',W).attr('height',H).attr('fill',BG);

svg.append('text').attr('x',PAD).attr('y',PAD+32)
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
const subT = svg.append('text').attr('x',PAD).attr('y',PAD+32+34)
  .attr('font-family','ABC Oracle Edu').attr('font-size',18).attr('font-weight',400).attr('fill',SUBTEXT);
subLines.forEach((l,i) => subT.append('tspan').attr('x',PAD).attr('dy', i===0 ? 0 : 22).text(l));

const chartTop = PAD + 32 + 34 + 22*subLines.length + 60;
const chartBottom = H - PAD - 180;
const chartLeft = PAD + 70;
const chartRight = W - PAD - 380;

const xs = P.years;
const x = d3.scaleLinear().domain(d3.extent(xs)).range([chartLeft, chartRight]);
const flat = P.series.flatMap(s => s.values.filter(v => v !== null && v !== undefined));
const ymax = d3.max(flat) * 1.08;
const y = d3.scaleLinear().domain([0, ymax]).range([chartBottom, chartTop]);

const yTicks = y.ticks(7);
const gridG = svg.append('g').attr('id','grid');
yTicks.forEach(t => {
  gridG.append('line').attr('x1',chartLeft).attr('x2',chartRight)
    .attr('y1',y(t)).attr('y2',y(t)).attr('stroke',GRID).attr('stroke-width',0.5);
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
const xLabG  = svg.append('g').attr('id','x-labels');
xs.forEach(yr => {
  xTickG.append('line').attr('x1',x(yr)).attr('x2',x(yr))
    .attr('y1',chartBottom).attr('y2',chartBottom+10).attr('stroke',TEXT).attr('stroke-width',0.5);
  let lbl = String(yr);
  if (yr !== 1950 && yr !== 2000 && yr !== 2020) lbl = String(yr).slice(2);
  xLabG.append('text').attr('x',x(yr)).attr('y',chartBottom+30).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

const lineFn = d3.line().defined(v => v !== null && v !== undefined).x((_,i)=>x(xs[i])).y(v=>y(v));
const linesG = svg.append('g').attr('id','lines');
P.series.forEach(s => {
  const path = linesG.append('path').attr('d',lineFn(s.values))
    .attr('fill','none').attr('stroke',s.color).attr('stroke-width', s.dotted ? 1.8 : 2.5)
    .attr('style','mix-blend-mode: multiply');
  if (s.dotted) path.attr('stroke-dasharray','3,4');
  xs.forEach((yr, i) => {
    if (s.values[i] !== null && s.values[i] !== undefined && !s.dotted)
      linesG.append('circle').attr('cx', x(yr)).attr('cy', y(s.values[i]))
        .attr('r', 3.5).attr('fill', s.color);
  });
});

// Right-side labels — multi-line, collision-avoided
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

// Find the last non-null value for each series
const labels = P.series.map(s => {
  let lv = null;
  for (let i = xs.length - 1; i >= 0; i--) {
    if (s.values[i] !== null && s.values[i] !== undefined) { lv = s.values[i]; break; }
  }
  if (lv === null) return null;
  return { color: s.color, y: y(lv), v: lv, lines: wrapLabel(s.name, 28), dotted: s.dotted };
}).filter(Boolean);

labels.sort((a,b) => a.y - b.y);
for (let i = 1; i < labels.length; i++) {
  const minGap = labels[i-1].lines.length * 17 + 8;
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}
const labG = svg.append('g').attr('id','labels');
labels.forEach(d => {
  d.lines.forEach((line, i) => {
    labG.append('text').attr('x',chartRight+14).attr('y', d.y + i*17).attr('dy','0.32em')
      .attr('font-family','ABC Oracle Edu').attr('font-size',14)
      .attr('font-weight', d.dotted ? 400 : 500).attr('fill', d.color)
      .text(line);
  });
});

// Source note
const srcLines = [
  'Sources: County under-18 1950–2020 from NHGIS decennial census tabulations (Manson et al.). City-level under-18 1980–2020 from NHGIS place-level',
  'sex-by-age tables (extract #124) for the named central cities of the top 60 entries in the 1950 SMA list (covers the 50 largest 1950 SMAs). 1950 SMA',
  'county membership and central-county designation from Census Bureau report P-23-23 (1967) and Census file 50mfips.txt. Modern MSA membership from',
  'OMB Bulletin 23-01 (2023 CBSA delineation). Each county is classified ONCE by its 1950 SMA and 2023 MSA status, then held fixed across decades. Pre-1980',
  'place-level data is not available at the national scale in NHGIS, so the central-city vs. balance-of-county split begins in 1980 (dotted line marks the',
  'unsplit county-level "city core" for 1950–1970). Central-city geographies follow contemporary place boundaries at each census (annexations not normalized).',
];
const srcG = svg.append('g').attr('id','source');
const srcStart = H - PAD - 15 - (srcLines.length - 1) * 16;
const srcT = srcG.append('text').attr('font-family','ABC Oracle Edu').attr('font-size',13)
  .attr('font-weight',200).attr('fill',TEXT);
srcLines.forEach((l,i) => srcT.append('tspan').attr('x',PAD).attr('y', srcStart + i*16).text(l));
</script>
</body></html>
"""

path = OUT / "under18_5_class.html"
html = template.replace("__TITLE__", P["title"]).replace("__DATA__", json.dumps(P))
path.write_text(html)
print(f"\nWrote {path}")
