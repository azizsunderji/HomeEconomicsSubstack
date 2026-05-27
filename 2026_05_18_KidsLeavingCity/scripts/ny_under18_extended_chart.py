"""
Render extended NY under-18 chart (1970-2024) using NHGIS decennial + PEP annual.
Same hover-to-highlight + collision-avoided right labels as the prior version.
"""
import json
import pandas as pd
from pathlib import Path

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"

df = pd.read_csv(DATA / "ny_under18_extended.csv")
years = df["year"].astype(int).tolist()
fips_cols = [c for c in df.columns if c != "year"]

# Match the existing chart's naming and color logic
NAMES = {
    "09120": "Greater Bridgeport (CT)",
    "09190": "Western CT Planning Region",
    "34003": "Bergen NJ", "34013": "Essex NJ", "34017": "Hudson NJ",
    "34019": "Hunterdon NJ", "34021": "Mercer NJ", "34023": "Middlesex NJ",
    "34025": "Monmouth NJ", "34027": "Morris NJ", "34029": "Ocean NJ",
    "34031": "Passaic NJ", "34035": "Somerset NJ", "34037": "Sussex NJ",
    "34039": "Union NJ",
    "36005": "Bronx", "36027": "Dutchess", "36047": "Brooklyn",
    "36059": "Nassau", "36061": "Manhattan", "36071": "Orange (NY)",
    "36079": "Putnam", "36081": "Queens", "36085": "Staten Island",
    "36087": "Rockland", "36103": "Suffolk", "36105": "Sullivan (NY)",
    "36111": "Ulster", "36119": "Westchester",
    "42103": "Pike PA",
}

BOROUGH_COLORS = {
    "36005": "#FEC439",  # Bronx — Yellow
    "36047": "#0BB4FF",  # Brooklyn — Blue
    "36061": "#F4743B",  # Manhattan — Red/Orange
    "36081": "#67A275",  # Queens — Green
    "36085": "#A32515",  # Staten Island — Dark red
}

GREYS = ["#7E8F8C", "#909FA0", "#A1B2AF", "#7C8D8A", "#919FA2", "#8FA09E", "#A0B5B0"]


series = []
for i, fips in enumerate(fips_cols):
    values = []
    for v in df[fips]:
        if pd.isna(v):
            values.append(None)
        else:
            values.append(int(v))
    is_borough = fips in BOROUGH_COLORS
    color = BOROUGH_COLORS.get(fips, GREYS[i % len(GREYS)])
    series.append({
        "fips": fips,
        "name": NAMES.get(fips, fips),
        "values": values,
        "color": color,
        "is_borough": is_borough,
    })

P = {"years": years, "series": series}

template = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC area under-18 population, 1970–2024</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }
body { margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }
svg { display:block; margin:20px auto; }
</style></head><body>
<svg id="chart" viewBox="0 0 1600 920" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const BG = '#F6F7F3', TEXT = '#3D3733', SUBTEXT = '#7F7570', GRID = '#e1e2e3';
const W = 1600, H = 920, PAD = 40;
const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

svg.append('text').attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',30).attr('font-weight',500).attr('fill',TEXT)
  .text('Under-18 population, NYC CSA counties, 1970–2024');
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',18).attr('font-weight',400).attr('fill',SUBTEXT)
  .text('Raw count. Decennial census 1970-2010, then annual PEP 2010-2024. 5 NYC boroughs in color, surrounding counties grey. Hover to highlight.');

const chartLeft = 110, chartRight = W - PAD - 220;
const chartTop = PAD + 90, chartBottom = H - PAD - 70;

const x = d3.scaleLinear().domain(d3.extent(P.years)).range([chartLeft, chartRight]);
const ymax = d3.max(P.series.flatMap(s => s.values.filter(v => v !== null)));
const y = d3.scaleLinear().domain([0, ymax * 1.05]).range([chartBottom, chartTop]);

// Gridlines & y-axis labels
const yTicks = y.ticks(8);
yTicks.forEach(t => {
  svg.append('line').attr('x1', chartLeft).attr('x2', chartRight)
    .attr('y1', y(t)).attr('y2', y(t)).attr('stroke', GRID).attr('stroke-width', 0.5);
  svg.append('text').attr('x', chartLeft - 8).attr('y', y(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
    .text(t >= 1e6 ? (t/1e6).toFixed(1) + 'M' : Math.round(t/1000) + 'k');
});

// X-axis: label every decade plus the latest year
const xTickYears = [1970, 1980, 1990, 2000, 2010, 2020, 2024];
xTickYears.forEach(yr => {
  svg.append('line').attr('x1', x(yr)).attr('x2', x(yr))
    .attr('y1', chartBottom).attr('y2', chartBottom + 5)
    .attr('stroke', TEXT).attr('stroke-width', 0.5);
  svg.append('text').attr('x', x(yr)).attr('y', chartBottom + 20).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
    .text(yr);
});

const lineFn = d3.line().defined(v => v !== null)
  .x((_, i) => x(P.years[i]))
  .y(v => y(v));

const slug = s => s.replace(/[^a-z0-9]+/gi, '_');
const lineGroup = svg.append('g').attr('id','lines');

P.series.forEach(s => {
  const id = slug(s.fips);
  lineGroup.append('path').attr('d', lineFn(s.values))
    .attr('fill','none').attr('stroke', s.color)
    .attr('stroke-width', s.is_borough ? 2.5 : 1.6).attr('opacity', s.is_borough ? 1.0 : 0.55)
    .attr('class','series-line').attr('data-id', id)
    .attr('style','mix-blend-mode: multiply');
  lineGroup.append('path').attr('d', lineFn(s.values))
    .attr('fill','none').attr('stroke','transparent').attr('stroke-width', 16)
    .attr('class','series-hit').attr('data-id', id).style('cursor','pointer');
});

// Endpoint dots — use the last NON-NULL value
P.series.forEach(s => {
  let lastIdx = -1;
  for (let i = s.values.length - 1; i >= 0; i--) {
    if (s.values[i] !== null) { lastIdx = i; break; }
  }
  if (lastIdx < 0) return;
  const lv = s.values[lastIdx];
  lineGroup.append('circle').attr('cx', x(P.years[lastIdx])).attr('cy', y(lv))
    .attr('r', s.is_borough ? 4 : 2.5).attr('fill', s.color)
    .attr('class','series-dot').attr('data-id', slug(s.fips));
});

const labels = P.series.map(s => {
  let li = -1;
  for (let i = s.values.length - 1; i >= 0; i--) { if (s.values[i] !== null) { li = i; break; } }
  if (li < 0) return null;
  const lv = s.values[li];
  return { id: slug(s.fips), color: s.color, y: y(lv), v: lv, name: s.name, is_borough: s.is_borough };
}).filter(Boolean);
labels.sort((a, b) => a.y - b.y);
const minGap = 14;
for (let i = 1; i < labels.length; i++) {
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}

const labelGroup = svg.append('g').attr('id','labels');
labels.forEach(d => {
  labelGroup.append('line').attr('x1', chartRight + 4).attr('x2', chartRight + 14)
    .attr('y1', d.y).attr('y2', d.y)
    .attr('stroke', d.color).attr('stroke-width', d.is_borough ? 2 : 1.2)
    .attr('class','series-label-line').attr('data-id', d.id);
  labelGroup.append('text').attr('x', chartRight + 18).attr('y', d.y).attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size', d.is_borough ? 13 : 11)
    .attr('font-weight', d.is_borough ? 700 : 400)
    .attr('fill', d.color).attr('class','series-label-text').attr('data-id', d.id)
    .style('cursor','pointer')
    .text(`${d.name}  ${d.v >= 1e6 ? (d.v/1e6).toFixed(2) + 'M' : Math.round(d.v/1000) + 'k'}`);
});

function focus(targetId) {
  d3.selectAll('.series-line, .series-dot, .series-label-line, .series-label-text').each(function() {
    const el = d3.select(this);
    const myId = el.attr('data-id');
    const isT = myId === targetId;
    const isLine = el.classed('series-line');
    const isDot = el.classed('series-dot');
    const isLabLine = el.classed('series-label-line');
    const isLabText = el.classed('series-label-text');
    if (targetId === null) {
      const s = P.series.find(s => slug(s.fips) === myId);
      const isB = s && s.is_borough;
      if (isLine) el.attr('opacity', isB ? 1.0 : 0.55).attr('stroke-width', isB ? 2.5 : 1.6);
      if (isDot) el.attr('opacity', 1).attr('r', isB ? 4 : 2.5);
      if (isLabLine) el.attr('opacity', 1);
      if (isLabText) el.attr('opacity', 1).attr('font-weight', isB ? 700 : 400);
    } else {
      if (isLine) el.attr('opacity', isT ? 1 : 0.06).attr('stroke-width', isT ? 4 : 1.6);
      if (isDot) el.attr('opacity', isT ? 1 : 0.1).attr('r', isT ? 6 : 2.5);
      if (isLabLine) el.attr('opacity', isT ? 1 : 0.15);
      if (isLabText) el.attr('opacity', isT ? 1 : 0.25).attr('font-weight', isT ? 700 : 400);
    }
  });
}
d3.selectAll('.series-hit, .series-label-text, .series-dot')
  .on('mouseenter', function() { focus(d3.select(this).attr('data-id')); })
  .on('mouseleave', function() { focus(null); });

svg.append('text').attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',200).attr('fill',TEXT)
  .text('Source: NHGIS decennial census time-series table D08 (1970, 1980, 1990, 2000) and Census Bureau Population Estimates Program (2010-2024, July 1 estimates).');
svg.append('text').attr('x', PAD).attr('y', H - PAD + 0)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',200).attr('fill',SUBTEXT)
  .text('Counties: NYC CSA (5 boroughs + NY/NJ/CT/PA suburbs). Two CT planning regions begin in 2022.');
</script>
</body></html>"""

html = template.replace("__DATA__", json.dumps(P))
(OUTPUTS / "ny_under18_timeseries.html").write_text(html)
print(f"Wrote ny_under18_timeseries.html — {len(P['years'])} year points, {len(P['series'])} counties")
print(f"Years: {P['years']}")
