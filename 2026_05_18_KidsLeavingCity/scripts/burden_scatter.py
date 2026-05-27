"""
Two scatter plots for housing-burden vs kid-population change.

Left: Δ% under-18 (2011→2024) vs LEVEL of housing burden in 2023
Right: Δ% under-18 vs CHANGE in housing burden (2011→2023), colored by 2023 level

Each point = one county. Bubble size ∝ 2011 under-18 population. Hover for tooltip.
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"


def main():
    d = pd.read_csv(DATA / "housing_burden.csv", dtype={"fips_5": str})
    d["fips_5"] = d["fips_5"].str.zfill(5)
    d = d[d["msa_name_short"].notna()]              # only our 12 MSAs
    d = d.dropna(subset=["pct_burdened_2023", "delta_under18_pct", "pop_under18"])
    print(f"Counties with complete data: {len(d)}")

    points = []
    for _, r in d.iterrows():
        points.append({
            "fips": r["fips_5"],
            "name": str(r["County/County Equivalent"]),
            "msa": r["msa_name_short"].split(",")[0].split("-")[0].strip(),
            "burden_2011": float(r["pct_burdened_2011"]) if pd.notna(r["pct_burdened_2011"]) else None,
            "burden_2023": float(r["pct_burdened_2023"]),
            "burden_delta": float(r["pct_burdened_delta"]) if pd.notna(r["pct_burdened_delta"]) else None,
            "delta_kids_pct": float(r["delta_under18_pct"]),
            "pop_2011": int(r["pop_under18"]),
        })

    payload = json.dumps(points)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Housing burden vs kid population change</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Bold.otf') format('opentype'); font-weight:700; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }}
body {{ margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }}
svg {{ display:block; margin:20px auto; }}
.tooltip {{ position:absolute; pointer-events:none; background:rgba(61,55,51,0.95); color:#F6F7F3; padding:8px 12px; font-size:13px; border-radius:4px; font-family:'ABC Oracle Edu',sans-serif; max-width: 280px; }}
</style></head><body>
<svg id="chart" viewBox="0 0 1920 987" xmlns="http://www.w3.org/2000/svg"></svg>
<div class="tooltip" style="display:none"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const D = {payload};
const BG = '#F6F7F3', TEXT = '#3D3733', SUBTEXT='#7F7570', GRID = '#e1e2e3';
const W = 1920, H = 987, PAD = 40;
const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

// Title row
svg.append('text').attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',30).attr('font-weight',700).attr('fill',TEXT)
  .text('Housing burden and the urban child population');
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 28)
  .attr('font-family','ABC Oracle Edu').attr('font-size',17).attr('font-weight',400).attr('fill',TEXT)
  .text('Each bubble = one county across our 12 MSAs. Burden = share of households (owners + renters) paying ≥30% of income on housing.');

// Color scale (for chart 2, by burden level 2023)
const burdenExtent = d3.extent(D, d => d.burden_2023);
const colorScale = d3.scaleSequential(d3.interpolate('#BCE8FF', '#003D66')).domain(burdenExtent);

// Common bubble-size scale
const popExtent = d3.extent(D, d => d.pop_2011);
const rScale = d3.scaleSqrt().domain(popExtent).range([3, 28]);

function drawPanel(x0, y0, pw, ph, xVal, xLabel, xExtent, colorFn, panelTitle, panelSubtitle, yRange) {{
  // Local panel scales
  const chartLeft = x0 + 80, chartRight = x0 + pw - 30;
  const chartTop = y0 + 80, chartBottom = y0 + ph - 60;

  const xS = d3.scaleLinear().domain(xExtent).nice().range([chartLeft, chartRight]);
  const yS = d3.scaleLinear().domain(yRange).nice().range([chartBottom, chartTop]);

  // Panel title
  svg.append('text').attr('x', x0 + 30).attr('y', y0 + 30)
    .attr('font-family','ABC Oracle Edu').attr('font-size',20).attr('font-weight',700).attr('fill',TEXT)
    .text(panelTitle);
  svg.append('text').attr('x', x0 + 30).attr('y', y0 + 52)
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',400).attr('fill',SUBTEXT)
    .text(panelSubtitle);

  // Gridlines
  yS.ticks(6).forEach(t => {{
    svg.append('line').attr('x1', chartLeft).attr('x2', chartRight).attr('y1', yS(t)).attr('y2', yS(t))
      .attr('stroke', t === 0 ? TEXT : GRID).attr('stroke-width', t === 0 ? 1 : 0.5);
    svg.append('text').attr('x', chartLeft - 8).attr('y', yS(t)).attr('text-anchor','end').attr('dy','0.32em')
      .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
      .text(t > 0 ? '+' + t + '%' : t + '%');
  }});
  xS.ticks(6).forEach(t => {{
    svg.append('line').attr('x1', xS(t)).attr('x2', xS(t)).attr('y1', chartBottom).attr('y2', chartBottom + 5)
      .attr('stroke', TEXT).attr('stroke-width', 0.5);
    svg.append('text').attr('x', xS(t)).attr('y', chartBottom + 20).attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
      .text(t.toFixed(t === 0 ? 0 : 0) + (xLabel.includes('change') ? 'pp' : '%'));
  }});

  // X axis title
  svg.append('text').attr('x', (chartLeft + chartRight)/2).attr('y', chartBottom + 50)
    .attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
    .text(xLabel);

  // Y axis title (left)
  svg.append('text').attr('transform', `translate(${{x0 + 22}}, ${{(chartTop + chartBottom)/2}}) rotate(-90)`)
    .attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
    .text('Change in under-18 population (2011 → 2024)');

  // Reference line at 0
  if (xExtent[0] < 0 && xExtent[1] > 0) {{
    svg.append('line').attr('x1', xS(0)).attr('x2', xS(0)).attr('y1', chartTop).attr('y2', chartBottom)
      .attr('stroke', TEXT).attr('stroke-width', 1);
  }}

  // Bubbles
  const tip = d3.select('.tooltip');
  D.forEach(p => {{
    const x = xVal(p);
    if (x === null || x === undefined || isNaN(x)) return;
    svg.append('circle')
      .attr('cx', xS(x)).attr('cy', yS(p.delta_kids_pct))
      .attr('r', rScale(p.pop_2011))
      .attr('fill', colorFn(p))
      .attr('fill-opacity', 0.7)
      .attr('stroke', TEXT).attr('stroke-width', 0.5)
      .style('cursor', 'pointer')
      .on('mousemove', e => {{
        tip.style('display','block').style('left', (e.pageX + 12) + 'px').style('top', (e.pageY + 12) + 'px')
          .html(
            `<b>${{p.name}}</b><br>` +
            `<span style="opacity:0.7">${{p.msa}}</span><br>` +
            `Δ under-18: ${{p.delta_kids_pct > 0 ? '+' : ''}}${{p.delta_kids_pct.toFixed(1)}}%<br>` +
            `Burden 2023: ${{p.burden_2023.toFixed(1)}}%<br>` +
            (p.burden_delta !== null ? `Δ burden 2011→23: ${{p.burden_delta > 0 ? '+' : ''}}${{p.burden_delta.toFixed(1)}}pp<br>` : '') +
            `2011 under-18 pop: ${{p.pop_2011.toLocaleString()}}`
          );
      }})
      .on('mouseout', () => tip.style('display','none'));
  }});
}}

// Panel 1: Δ kids vs burden LEVEL in 2023
drawPanel(
  0, 100, W/2, H - 160,
  d => d.burden_2023,
  'Burden level in 2023 (% households paying ≥30% of income)',
  d3.extent(D, d => d.burden_2023),
  d => '#0BB4FF',
  'Burden LEVEL vs kid population change',
  'Are high-burden counties losing more kids?',
  d3.extent(D, d => d.delta_kids_pct),
);

// Panel 2: Δ kids vs change in burden, colored by 2023 level
drawPanel(
  W/2, 100, W/2, H - 160,
  d => d.burden_delta,
  'Change in burden 2011 → 2023 (percentage points)',
  d3.extent(D.filter(d => d.burden_delta !== null), d => d.burden_delta),
  d => colorScale(d.burden_2023),
  'Burden CHANGE vs kid population change',
  'Color: 2023 burden level (light = low, dark = high)',
  d3.extent(D, d => d.delta_kids_pct),
);

// Color legend for panel 2
const lgX = W/2 + 80, lgY = H - 50;
const lgW = 200, lgH = 12;
const stops = 30;
for (let i = 0; i < stops; i++) {{
  const t = i / (stops - 1);
  const v = burdenExtent[0] + t * (burdenExtent[1] - burdenExtent[0]);
  svg.append('rect').attr('x', lgX + t * lgW).attr('y', lgY)
    .attr('width', lgW / stops + 1).attr('height', lgH).attr('fill', colorScale(v));
}}
svg.append('text').attr('x', lgX).attr('y', lgY + lgH + 14)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',TEXT)
  .text(burdenExtent[0].toFixed(0) + '%');
svg.append('text').attr('x', lgX + lgW).attr('y', lgY + lgH + 14)
  .attr('text-anchor','end')
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',TEXT)
  .text(burdenExtent[1].toFixed(0) + '%');
svg.append('text').attr('x', lgX + lgW/2).attr('y', lgY - 4)
  .attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',500).attr('fill',TEXT)
  .text('2023 burden level');

// Bubble-size legend
const blX = 100, blY = H - 50;
[3, 14, 28].forEach((r, i) => {{
  const xb = blX + i * 60;
  svg.append('circle').attr('cx', xb).attr('cy', blY).attr('r', r)
    .attr('fill','none').attr('stroke', TEXT).attr('stroke-width', 0.5);
  const pop = rScale.invert(r);
  svg.append('text').attr('x', xb).attr('y', blY + 35).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill',TEXT)
    .text(pop > 1e6 ? (pop/1e6).toFixed(1)+'M' : Math.round(pop/1000) + 'k');
}});
svg.append('text').attr('x', blX - 60).attr('y', blY + 4)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',500).attr('fill',TEXT)
  .text('2011 under-18 pop:');

// Source
svg.append('text').attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',TEXT)
  .text('Source: ACS 5-year PUMS (housing burden, 2007-2011 and 2019-2023 windows); Census PEP for under-18 population (2011, 2024).');
svg.append('text').attr('x', PAD).attr('y', H - PAD)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',SUBTEXT)
  .text('Burden = % of households (owners + renters combined) paying ≥30% of income on housing. Counties shown: ' + D.length + ' (counties where PUMS COUNTYFIP populated).');
</script>
</body></html>"""
    (OUTPUTS / "burden_scatter.html").write_text(html)
    print(f"Wrote {OUTPUTS / 'burden_scatter.html'}")


if __name__ == "__main__":
    main()
