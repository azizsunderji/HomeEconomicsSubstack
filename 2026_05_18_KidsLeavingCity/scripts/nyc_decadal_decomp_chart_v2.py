"""
Interactive decadal decomposition chart for NYC 5-borough under-18, 1940-2020.

Three stacked components per decade:
  • Births       (positive, green)
  • Aging-out    (negative, red — drawn going down from zero)
  • Net migration (signed, blue)

Hover legend items or bar segments to highlight a series. Each segment shows
its value when hovered. Net Δ marker (black) is the sum.
"""
import json
import pandas as pd
from pathlib import Path

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"

df = pd.read_csv(DATA / "nyc_decadal_decomposition.csv").sort_values("decade_start").reset_index(drop=True)
df["label"] = df["decade_start"].astype(str) + "–" + df["decade_end"].astype(str).str[-2:]
records = df.to_dict(orient="records")

template = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC under-18 decadal decomposition, 1940-2020</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }
body { margin:0; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; }
svg { display:block; margin:20px auto; background:#F6F7F3; }
.bar-rect { transition: opacity 120ms; cursor: pointer; }
.bar-rect.dim { opacity: 0.12; }
.legend-item { cursor: pointer; }
.value-label { font-family: 'ABC Oracle Edu'; font-size: 11px; font-weight: 500; fill: #3D3733; pointer-events: none; }
</style></head><body>
<svg id="chart" viewBox="0 0 1400 920" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const data = __DATA__;
const BG = '#F6F7F3', TEXT = '#3D3733', SUBTEXT = '#7F7570', GRID = '#e1e2e3';
const BIRTHS = '#67A275', AGING = '#F4743B', MIGRATION = '#0BB4FF', BLACK = '#3D3733';

const SERIES = [
  { key: 'births',      label: 'Births',      color: BIRTHS,    sign: +1 },
  { key: 'aging_out',   label: 'Aging-out',   color: AGING,     sign: -1 },
  { key: 'net_migration', label: 'Net migration', color: MIGRATION, sign:  0 }, // sign comes from value itself
];

const W = 1400, H = 920, PAD = 60;
const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

svg.append('text').attr('x', PAD).attr('y', PAD + 12)
  .attr('font-family','ABC Oracle Edu').attr('font-size',32).attr('font-weight',500).attr('fill',TEXT)
  .text('NYC under-18: births, aging-out, and net migration, by decade');
svg.append('text').attr('x', PAD).attr('y', PAD + 44)
  .attr('font-family','ABC Oracle Edu').attr('font-size',18).attr('font-weight',400).attr('fill',SUBTEXT)
  .text('Signed contributions to under-18 population change, 5 boroughs combined.');
svg.append('text').attr('x', PAD).attr('y', PAD + 70)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill',SUBTEXT)
  .text('Hover a colored segment or legend item to isolate that series. Net Δ shown as black bar.');

const chartLeft = 110, chartRight = W - PAD - 30;
const chartTop = PAD + 110, chartBottom = H - PAD - 100;
const x = d3.scaleBand().domain(data.map(d => d.label)).range([chartLeft, chartRight]).padding(0.22);

// Compute signed contributions: births = +births, aging_out = -aging_out, net_mig = as-is
function signed(d, key) {
  if (key === 'births') return d.births;
  if (key === 'aging_out') return -d.aging_out;
  if (key === 'net_migration') return d.net_migration;
}

const allVals = [];
data.forEach(d => SERIES.forEach(s => allVals.push(signed(d, s.key))));
allVals.push(0);
const ymin = d3.min(allVals);
const ymax = d3.max(allVals);
const pad = Math.max(Math.abs(ymin), Math.abs(ymax)) * 0.06;
const y = d3.scaleLinear().domain([ymin - pad, ymax + pad]).range([chartBottom, chartTop]).nice();

// Gridlines + y-axis labels
y.ticks(8).forEach(t => {
  svg.append('line').attr('x1', chartLeft).attr('x2', chartRight)
    .attr('y1', y(t)).attr('y2', y(t)).attr('stroke', t === 0 ? TEXT : GRID).attr('stroke-width', t === 0 ? 1 : 0.5);
  const lbl = (t === 0 ? '0' : (t > 0 ? '+' : '') + (Math.abs(t) >= 1000 ? (Math.round(t/1000)) + 'k' : t));
  svg.append('text').attr('x', chartLeft - 8).attr('y', y(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',TEXT)
    .text(lbl);
});

// Bars and per-segment metadata
const barGroup = svg.append('g').attr('id', 'bars');
const labelGroup = svg.append('g').attr('id', 'value-labels').style('opacity', 0);

data.forEach((d, i) => {
  const cx = x(d.label);
  const bw = x.bandwidth();

  let posBase = 0, negBase = 0;
  SERIES.forEach(s => {
    const v = signed(d, s.key);
    if (v === 0) return;
    let top, height;
    if (v > 0) {
      top = posBase + v;
      const rect = barGroup.append('rect')
        .attr('class', 'bar-rect series-' + s.key)
        .attr('data-series', s.key)
        .attr('data-decade', d.label)
        .attr('x', cx).attr('y', y(top))
        .attr('width', bw).attr('height', y(posBase) - y(top))
        .attr('fill', s.color);
      labelGroup.append('text')
        .attr('class', 'value-label vlabel-' + s.key + ' vlabel-decade-' + d.decade_start)
        .attr('x', cx + bw/2).attr('y', y(posBase + v/2)).attr('text-anchor','middle').attr('dy','0.32em')
        .text(formatVal(v));
      posBase = top;
    } else {
      const bottom = negBase + v;
      const rect = barGroup.append('rect')
        .attr('class', 'bar-rect series-' + s.key)
        .attr('data-series', s.key)
        .attr('data-decade', d.label)
        .attr('x', cx).attr('y', y(negBase))
        .attr('width', bw).attr('height', y(bottom) - y(negBase))
        .attr('fill', s.color);
      labelGroup.append('text')
        .attr('class', 'value-label vlabel-' + s.key + ' vlabel-decade-' + d.decade_start)
        .attr('x', cx + bw/2).attr('y', y(negBase + v/2)).attr('text-anchor','middle').attr('dy','0.32em')
        .text(formatVal(v));
      negBase = bottom;
    }
  });

  // Net Δ marker
  svg.append('line').attr('x1', cx - 3).attr('x2', cx + bw + 3)
    .attr('y1', y(d.delta_pop)).attr('y2', y(d.delta_pop))
    .attr('stroke', BLACK).attr('stroke-width', 3);

  // Per-decade Δ label
  const topY    = y(Math.max(0, posBase));
  const bottomY = y(Math.min(0, negBase));
  const lblY = d.delta_pop >= 0 ? topY - 8 : bottomY + 18;
  svg.append('text').attr('x', cx + bw/2).attr('y', lblY).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',500).attr('fill', TEXT)
    .text((d.delta_pop >= 0 ? '+' : '') + Math.round(d.delta_pop/1000) + 'k');

  // X-axis decade label
  svg.append('text').attr('x', cx + bw/2).attr('y', chartBottom + 22).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',400).attr('fill',TEXT)
    .text(d.label);
});

function formatVal(v) {
  const av = Math.abs(v);
  const sign = v > 0 ? '+' : (v < 0 ? '−' : '');
  if (av >= 1e6) return sign + (av/1e6).toFixed(2) + 'M';
  if (av >= 1000) return sign + Math.round(av/1000) + 'k';
  return sign + Math.round(av);
}

// Legend with hover-to-isolate
const legY = chartBottom + 65;
let lx = chartLeft;
SERIES.forEach(s => {
  const g = svg.append('g').attr('class', 'legend-item').attr('data-series', s.key);
  g.append('rect').attr('x', lx).attr('y', legY - 8).attr('width', 22).attr('height', 14).attr('fill', s.color);
  g.append('text').attr('x', lx + 28).attr('y', legY + 5)
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
    .text(s.label);
  lx += 28 + (s.label.length * 8.2) + 36;
});
// Net Δ legend entry
const g_net = svg.append('g');
g_net.append('line').attr('x1', lx).attr('x2', lx + 22).attr('y1', legY).attr('y2', legY)
  .attr('stroke', BLACK).attr('stroke-width', 3);
g_net.append('text').attr('x', lx + 28).attr('y', legY + 5)
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',400).attr('fill',TEXT)
  .text('Net Δ');

// Source line
svg.append('text').attr('x', PAD).attr('y', H - PAD + 4)
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill', SUBTEXT)
  .text('Source: NHGIS decennial census age tables (population by age, all-persons universe, individual datasets per decade); NYC DOH Summary of Vital Statistics (births by mother\\'s borough of residence; pre-1995 figures are 5-year averages).');
svg.append('text').attr('x', PAD).attr('y', H - PAD + 22)
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill', SUBTEXT)
  .text('Methodology: aging-out ≈ persons aged 8-17 at decade start (turn 18 within the decade); net migration = ΔPop − births + aging-out. Deaths implicit in aging-out.');

// Interactivity
function isolateSeries(key) {
  d3.selectAll('.bar-rect').classed('dim', function() {
    return key !== null && d3.select(this).attr('data-series') !== key;
  });
  d3.selectAll('.value-label').style('opacity', 0);
  if (key !== null) {
    d3.selectAll('.vlabel-' + key).style('opacity', 1);
  }
}

d3.selectAll('.bar-rect')
  .on('mouseenter', function() { isolateSeries(d3.select(this).attr('data-series')); })
  .on('mouseleave', function() { isolateSeries(null); });

d3.selectAll('.legend-item')
  .on('mouseenter', function() { isolateSeries(d3.select(this).attr('data-series')); })
  .on('mouseleave', function() { isolateSeries(null); });
</script>
</body></html>"""

html = template.replace("__DATA__", json.dumps(records))
(OUTPUTS / "nyc_decadal_decomposition.html").write_text(html)
print(f"Wrote outputs/nyc_decadal_decomposition.html (interactive, {len(records)} decades)")
