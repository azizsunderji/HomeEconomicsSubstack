"""
Decadal decomposition chart for NYC 5-borough under-18 population, 1940-2020.

Stacked bars per decade: natural change (births - aging-out) in green, net
migration in blue. Black marker for net Δ. Same visual language as the
annual chart, just at decadal resolution.
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
</style></head><body>
<svg id="chart" viewBox="0 0 1400 920" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const data = __DATA__;
const BG = '#F6F7F3', TEXT = '#3D3733', SUBTEXT = '#7F7570', GRID = '#e1e2e3';
const GREEN = '#67A275', BLUE = '#0BB4FF', BLACK = '#3D3733', LIGHT_GREEN = '#C6DCCB', LIGHT_RED = '#FBCAB5';

const W = 1400, H = 920, PAD = 60;
const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

svg.append('text').attr('x', PAD).attr('y', PAD + 12)
  .attr('font-family','ABC Oracle Edu').attr('font-size',32).attr('font-weight',500).attr('fill',TEXT)
  .text('NYC: natural change vs net migration, decade by decade');
svg.append('text').attr('x', PAD).attr('y', PAD + 44)
  .attr('font-family','ABC Oracle Edu').attr('font-size',18).attr('font-weight',400).attr('fill',SUBTEXT)
  .text('Change in under-18 population, 5 boroughs combined. Births minus aging-out = natural change.');
svg.append('text').attr('x', PAD).attr('y', PAD + 70)
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',300).attr('fill',SUBTEXT)
  .text('Children (signed contributions per decade)');

const chartLeft = 110, chartRight = W - PAD - 30;
const chartTop = PAD + 100, chartBottom = H - PAD - 80;
const x = d3.scaleBand().domain(data.map(d => d.label)).range([chartLeft, chartRight]).padding(0.2);
const allVals = data.flatMap(d => [d.natural_change, d.net_migration, d.delta_pop, 0]);
const ymin = d3.min(allVals);
const ymax = d3.max(allVals);
const pad = Math.max(Math.abs(ymin), Math.abs(ymax)) * 0.05;
const y = d3.scaleLinear().domain([ymin - pad, ymax + pad]).range([chartBottom, chartTop]).nice();

y.ticks(8).forEach(t => {
  svg.append('line').attr('x1', chartLeft).attr('x2', chartRight)
    .attr('y1', y(t)).attr('y2', y(t)).attr('stroke', t === 0 ? TEXT : GRID).attr('stroke-width', t === 0 ? 1 : 0.5);
  const lbl = (t === 0 ? '0' : (t > 0 ? '+' : '') + (Math.abs(t) >= 1000 ? (Math.round(t/1000)) + 'k' : t));
  svg.append('text').attr('x', chartLeft - 8).attr('y', y(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',TEXT)
    .text(lbl);
});

data.forEach(d => {
  const cx = x(d.label);
  const bw = x.bandwidth();

  // Stack positive/negative components separately so positives stack up and
  // negatives stack down from zero. Natural change first, then net migration.
  let posBase = 0, negBase = 0;
  const components = [
    { value: d.natural_change, color: GREEN },
    { value: d.net_migration, color: BLUE },
  ];
  components.forEach(c => {
    const v = c.value;
    if (v >= 0) {
      const top = posBase + v;
      svg.append('rect')
        .attr('x', cx).attr('y', y(top))
        .attr('width', bw).attr('height', y(posBase) - y(top))
        .attr('fill', c.color);
      posBase = top;
    } else {
      const bottom = negBase + v;
      svg.append('rect')
        .attr('x', cx).attr('y', y(negBase))
        .attr('width', bw).attr('height', y(bottom) - y(negBase))
        .attr('fill', c.color);
      negBase = bottom;
    }
  });

  // Net Δ marker (always at posBase + negBase = natural + migration = delta_pop)
  svg.append('line').attr('x1', cx - 2).attr('x2', cx + bw + 2)
    .attr('y1', y(d.delta_pop)).attr('y2', y(d.delta_pop))
    .attr('stroke', BLACK).attr('stroke-width', 3);

  // Per-decade Δ label — placed at the outer edge of the stack
  const topY    = y(Math.max(0, posBase));
  const bottomY = y(Math.min(0, negBase));
  const dlblY = d.delta_pop >= 0 ? topY - 6 : bottomY + 18;
  svg.append('text').attr('x', cx + bw/2).attr('y', dlblY).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',500).attr('fill', TEXT)
    .text((d.delta_pop >= 0 ? '+' : '') + Math.round(d.delta_pop/1000) + 'k');

  // X-axis decade label
  svg.append('text').attr('x', cx + bw/2).attr('y', chartBottom + 22).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',400).attr('fill',TEXT)
    .text(d.label);
});

// Legend
const legY = chartBottom + 65;
const legItems = [
  { color: GREEN, label: 'Natural change (births − aging-out)' },
  { color: BLUE,  label: 'Net migration' },
  { color: BLACK, label: 'Net Δ', isLine: true },
];
let lx = chartLeft;
legItems.forEach(it => {
  if (it.isLine) {
    svg.append('line').attr('x1', lx).attr('x2', lx + 22).attr('y1', legY).attr('y2', legY)
      .attr('stroke', it.color).attr('stroke-width', 3);
  } else {
    svg.append('rect').attr('x', lx).attr('y', legY - 8).attr('width', 22).attr('height', 14).attr('fill', it.color);
  }
  svg.append('text').attr('x', lx + 28).attr('y', legY + 5)
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',400).attr('fill',TEXT)
    .text(it.label);
  lx += 28 + (it.label.length * 7.2) + 40;
});

// Source line
svg.append('text').attr('x', PAD).attr('y', H - PAD + 4)
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill', SUBTEXT)
  .text('Source: NHGIS decennial census age tables (population by single-year/5-year age, all-persons universe, individual datasets per decade); NYC DOH Summary of Vital Statistics (births by mother\\'s borough of residence, pre-1995 figures from the 5-yr-average historical series).');
svg.append('text').attr('x', PAD).attr('y', H - PAD + 22)
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill', SUBTEXT)
  .text('Methodology: aging-out ≈ persons aged 8-17 at decade start (turn 18 within the next 10 years); net migration = ΔPop − natural change. Deaths included implicitly in aging-out term.');
</script>
</body></html>"""

html = template.replace("__DATA__", json.dumps(records))
(OUTPUTS / "nyc_decadal_decomposition.html").write_text(html)
print(f"Wrote outputs/nyc_decadal_decomposition.html ({len(records)} decades)")
