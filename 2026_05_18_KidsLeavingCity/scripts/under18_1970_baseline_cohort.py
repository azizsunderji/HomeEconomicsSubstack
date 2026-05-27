"""
1970-baseline cohort stack chart for U.S. under-18.

Mirrors Johnson & Lichter (2020) decomposition framing: bottom layer is "MSA
counties as of 1970" (pre-1970 cohort, fixed geography), subsequent layers are
post-1970 reclassification waves.

Adds a "Never in any MSA" tier on top so the full U.S. under-18 sums to 100%.
Annotations call out J&L's headline number ("metro share would have FALLEN from
67% to 64% without reclassification — instead it rose to 86%") and our under-18
analog.

Outputs:
  outputs/under18_1970_baseline_cohort.html
  outputs/under18_1970_baseline_cohort.png
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

cohort = pd.read_csv(DATA / "under18_cohort_decomposition.csv")

# Pivot to year × cohort
pivot = cohort.pivot(index="year", columns="cohort", values="under18").fillna(0).reset_index()
# Columns: 0 (never), 1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020

# Collapse pre-1970 cohorts into a single "MSA as of 1970" tier
pre_1970 = [1950, 1960, 1970]
pivot["pre_1970_msa"] = pivot[pre_1970].sum(axis=1)
post_1970 = [1980, 1990, 2000, 2010, 2020]
never = 0

years = pivot["year"].astype(int).tolist()

# Compute key shares
def share_at(yr, num_col, denom_total):
    row = pivot[pivot["year"] == yr].iloc[0]
    return 100 * row[num_col] / denom_total

# Total US under-18 each year
pivot["total"] = pivot[pre_1970 + post_1970 + [0]].sum(axis=1)

# MSA-share at 1970 (= pre_1970_msa / total)
share_1970 = 100 * pivot[pivot["year"]==1970]["pre_1970_msa"].iloc[0] / pivot[pivot["year"]==1970]["total"].iloc[0]
# MSA-share at 2020 (actual = all cohorts / total)
share_2020 = 100 * (pivot[pivot["year"]==2020][pre_1970 + post_1970].sum(axis=1).iloc[0]) / pivot[pivot["year"]==2020]["total"].iloc[0]
# MSA-share at 2020 if no reclassification (= pre_1970_msa / 2020 total)
share_2020_constant = 100 * pivot[pivot["year"]==2020]["pre_1970_msa"].iloc[0] / pivot[pivot["year"]==2020]["total"].iloc[0]

print(f"Under-18 MSA share 1970: {share_1970:.1f}%")
print(f"Under-18 MSA share 2020 (with reclassification): {share_2020:.1f}%")
print(f"Under-18 MSA share 2020 (counterfactual — 1970 geography held fixed): {share_2020_constant:.1f}%")

# Build series for stack
LAYER_META = [
    ("pre_1970_msa", "MSA counties as of 1970",       "#003D66"),   # darkest
    (1980,           "Reclassified in 1970s",         "#0077CC"),
    (1990,           "Reclassified in 1980s",         "#0BB4FF"),
    (2000,           "Reclassified in 1990s",         "#5BC8FF"),
    (2010,           "Reclassified in 2000s",         "#8FD9FF"),
    (2020,           "Reclassified in 2010s",         "#BCE8FF"),
    (0,              "Never in any MSA",              "#67A275"),
]

stack_series = []
for col, name, color in LAYER_META:
    vals = (pivot[col] / 1e6).tolist()
    stack_series.append({"id": str(col), "name": name, "color": color, "values": [round(v, 3) for v in vals]})

P = {
    "years": [int(y) for y in years],
    "stack": stack_series,
    "share_1970": round(share_1970, 1),
    "share_2020": round(share_2020, 1),
    "share_2020_constant": round(share_2020_constant, 1),
    "title": "U.S. children, by metropolitan classification (1970 baseline), 1950–2020",
    "subtitle": (
        f"Under-18 share in MSAs rose from {share_1970:.1f}% (1970) to {share_2020:.1f}% (2020). "
        f"But if MSA boundaries had been held at their 1970 definition, the same metric would have FALLEN to {share_2020_constant:.1f}% — "
        f"all of the apparent metro-share gain is post-1970 county reclassification."
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
<svg id="chart" viewBox="0 0 1280 1000" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const BG='#F6F7F3', TEXT='#3D3733', SUBTEXT='#7F7570', GRID='#e1e2e3';
const W=1280, H=1000, PAD=40;
const svg = d3.select('#chart');
svg.append('rect').attr('width',W).attr('height',H).attr('fill',BG);

svg.append('text').attr('x',PAD).attr('y',PAD+30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',24).attr('font-weight',500).attr('fill',TEXT)
  .text(P.title);

const subLines = [];
{
  const words = P.subtitle.split(/\s+/);
  let line = '';
  const maxChars = 130;
  for (const w of words) {
    if ((line + ' ' + w).length > maxChars) { subLines.push(line.trim()); line = w; }
    else { line += ' ' + w; }
  }
  if (line.trim()) subLines.push(line.trim());
}
const subT = svg.append('text').attr('x',PAD).attr('y',PAD+30+30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',400).attr('fill',SUBTEXT);
subLines.forEach((l,i) => subT.append('tspan').attr('x',PAD).attr('dy', i===0 ? 0 : 22).text(l));

const chartTop = PAD + 30 + 30 + 22*subLines.length + 50;
const chartBottom = H - PAD - 200;
const chartLeft = PAD + 80;
const chartRight = W - PAD - 330;

const xs = P.years;
const x = d3.scaleLinear().domain(d3.extent(xs)).range([chartLeft, chartRight]);

const stackData = xs.map((yr, i) => {
  const o = {year: yr};
  P.stack.forEach(s => { o[s.id] = s.values[i]; });
  return o;
});
const keys = P.stack.map(s => s.id);
const stack = d3.stack().keys(keys)(stackData);
const ymax = d3.max(stack, s => d3.max(s, p => p[1])) * 1.05;
const y = d3.scaleLinear().domain([0, ymax]).range([chartBottom, chartTop]);

// Grid + y-axis
const yTicks = y.ticks(8);
const gridG = svg.append('g').attr('id','grid');
yTicks.forEach(t => {
  gridG.append('line').attr('x1',chartLeft).attr('x2',chartRight).attr('y1',y(t)).attr('y2',y(t))
    .attr('stroke',GRID).attr('stroke-width',0.5);
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

// X axis
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

// Stack
const area = d3.area().x((_,i)=>x(xs[i])).y0(d=>y(d[0])).y1(d=>y(d[1]));
const stacksG = svg.append('g').attr('id','stacks');
stack.forEach((layer, i) => {
  const sInfo = P.stack[i];
  stacksG.append('path').attr('d', area(layer))
    .attr('fill', sInfo.color).attr('stroke', BG).attr('stroke-width', 0.5);
});

// Vertical 1970 reference line
const refG = svg.append('g').attr('id','ref');
refG.append('line').attr('x1',x(1970)).attr('x2',x(1970)).attr('y1',chartTop).attr('y2',chartBottom)
  .attr('stroke','#3D3733').attr('stroke-width',1).attr('stroke-dasharray','3,4').attr('opacity',0.6);
refG.append('text').attr('x',x(1970)).attr('y',chartTop-8).attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill','#3D3733')
  .text('1970 baseline');

// Annotations: share callouts
const annG = svg.append('g').attr('id','annotations');
function annotation(yr, share, label, dy) {
  const xi = xs.indexOf(yr);
  const lastY = y(stack[stack.length-2][xi][1]);  // top of the MSA stack (everything except 'never')
  annG.append('text').attr('x',x(yr)).attr('y', lastY - 10 + (dy || 0)).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',500).attr('fill','#3D3733')
    .text(`${share}% in MSAs`);
  annG.append('text').attr('x',x(yr)).attr('y', lastY - 26 + (dy || 0)).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',400).attr('fill',SUBTEXT)
    .text(label);
}
annotation(1970, P.share_1970, '', -2);
annotation(2020, P.share_2020, 'actual', 0);

// Counterfactual annotation: where would the MSA-stack top be if no reclassification?
const lastIdx = xs.length - 1;
const pre1970_2020 = stack[0][lastIdx][1];  // top of bottom (pre_1970) layer in 2020 = its under-18 in 2020
// In 2020 with no reclassification, MSA total = pre_1970_msa value; place dotted line at that height
const yCounter = y(pre1970_2020);
svg.append('line').attr('x1',x(2010)).attr('x2',x(2020)).attr('y1', yCounter).attr('y2', yCounter)
  .attr('stroke','#A32515').attr('stroke-width',2).attr('stroke-dasharray','4,3');
svg.append('text').attr('x',x(2020)).attr('y', yCounter - 5).attr('text-anchor','end')
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',500).attr('fill','#A32515')
  .text(`${P.share_2020_constant}% — if 1970 boundaries held`);

// Right-side labels (midpoint of last stack segment)
const labels = P.stack.map((s, i) => {
  const lv = stack[i][lastIdx];
  return { name: s.name, color: s.color, y: y((lv[0]+lv[1])/2) };
});
labels.sort((a,b) => a.y - b.y);
const minGap = 22;
for (let i = 1; i < labels.length; i++) {
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}
const labG = svg.append('g').attr('id','labels');
labels.forEach(d => {
  labG.append('text').attr('x',chartRight+12).attr('y', d.y).attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',d.color)
    .text(d.name);
});

// Source note
const srcLines = [
  'Sources: U.S. under-18 by county and decennial from NHGIS (Manson et al.). MSA membership at each decennial from OMB delineations:',
  '1950 SMA · 1960/1970 SMSA · 1980/1990/2000 MSA · 2010/2020 CBSA (Metropolitan Statistical Areas only — Micropolitan excluded). Each county is',
  'assigned to a cohort by the earliest decade it appears in any MSA. The "MSA counties as of 1970" cohort = 1,033 counties (1950 SMA + 1950s adds',
  '+ 1960s adds). The five post-1970 cohorts add 693 counties. Replicates the framing of Johnson & Lichter (2020), "Metropolitan Reclassification and',
  'the Urbanization of Rural America," Demography 57:1929–1950, for the under-18 population specifically. J&L find for the TOTAL population that the metro',
  'share rose from 67% (1970) to 86% (2017) but would have FALLEN to 64% without reclassification — i.e. all of the gain was reclassification, not migration.',
];
const srcG = svg.append('g').attr('id','source');
const srcStart = H - PAD - 15 - (srcLines.length - 1) * 16;
const srcT = srcG.append('text').attr('font-family','ABC Oracle Edu').attr('font-size',13)
  .attr('font-weight',200).attr('fill',TEXT);
srcLines.forEach((l,i) => srcT.append('tspan').attr('x',PAD).attr('y', srcStart + i*16).text(l));
</script>
</body></html>
"""

path = OUT / "under18_1970_baseline_cohort.html"
html = template.replace("__TITLE__", P["title"]).replace("__DATA__", json.dumps(P))
path.write_text(html)
print(f"\nWrote {path}")
