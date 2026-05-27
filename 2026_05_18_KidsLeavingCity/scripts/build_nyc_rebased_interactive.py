"""
Build interactive rebased-to-100 line chart for 22 NYC MSA counties.
- 5 boroughs in blue, 17 other counties in gray.
- Slider lets user pick the rebase year (1980-2024).
- Hover reveals county name + index value + raw under-18 count.
- Y-axis auto-scales to current data range.

Input:  data/nyc_county_under18_pep_seamless.csv
Output: outputs/nyc_under18_rebased_interactive.html
"""

from pathlib import Path
import json
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
CSV = PROJECT / "data" / "nyc_county_under18_pep_seamless.csv"
OUT = PROJECT / "outputs" / "nyc_under18_rebased_interactive.html"

BOROUGH_FIPS = {"36005": "Bronx", "36047": "Brooklyn", "36061": "Manhattan",
                "36081": "Queens", "36085": "Staten Island"}


def build_payload() -> dict:
    df = pd.read_csv(CSV, dtype={"county_fips": str})
    df = df.sort_values(["county_fips", "year"])
    counties = []
    for fips, sub in df.groupby("county_fips"):
        sub = sub.sort_values("year")
        counties.append({
            "fips": fips,
            "name": sub["county_name"].iloc[0],
            "is_borough": fips in BOROUGH_FIPS,
            "years": sub["year"].astype(int).tolist(),
            "values": sub["under18"].astype(float).tolist(),
        })
    # Boroughs drawn last (on top): sort suburbs first, boroughs after.
    counties.sort(key=lambda c: (c["is_borough"], c["name"]))
    return {
        "counties": counties,
        "year_min": int(df["year"].min()),
        "year_max": int(df["year"].max()),
    }


HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC MSA under-18 by county — rebased to 100 (interactive)</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }}
body {{ margin:0; padding:28px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }}
h1 {{ font-size:28px; font-weight:500; margin:0 0 6px; }}
.sub {{ color:#7F7570; font-size:15px; margin-bottom:16px; max-width:1100px; line-height:1.5; }}
.controls {{ display:flex; align-items:center; gap:18px; margin-bottom:10px; max-width:1100px; }}
.controls label {{ font-size:13px; color:#7F7570; }}
#rebaseYearLabel {{ font-size:18px; font-weight:500; color:#3D3733; min-width:54px; display:inline-block; }}
input[type=range] {{ -webkit-appearance:none; appearance:none; height:4px; background:#DADFCE; border-radius:2px; flex:1; max-width:520px; cursor:pointer; }}
input[type=range]::-webkit-slider-thumb {{ -webkit-appearance:none; appearance:none; width:18px; height:18px; border-radius:50%; background:#0BB4FF; cursor:pointer; border:2px solid #F6F7F3; box-shadow:0 0 0 1px #0BB4FF; }}
input[type=range]::-moz-range-thumb {{ width:18px; height:18px; border-radius:50%; background:#0BB4FF; cursor:pointer; border:2px solid #F6F7F3; box-shadow:0 0 0 1px #0BB4FF; }}
.legend {{ font-size:12.5px; color:#7F7570; display:flex; gap:18px; align-items:center; }}
.legend .sw {{ display:inline-block; width:18px; height:2px; vertical-align:middle; margin-right:6px; }}
.chartwrap {{ background:#fff; border:0.5px solid #e1e2e3; padding:18px 22px 14px; max-width:1100px; }}
.tooltip {{ position:absolute; pointer-events:none; background:#3D3733; color:#F6F7F3; font-size:12px; padding:6px 9px; border-radius:3px; line-height:1.4; opacity:0; transition:opacity 80ms; white-space:nowrap; }}
.tooltip .name {{ font-weight:500; color:#FEC439; }}
.source {{ color:#7F7570; font-size:12px; max-width:1100px; margin-top:16px; line-height:1.5; }}
</style></head>
<body>
<h1>NYC MSA under-18 by county, rebased to 100</h1>
<div class="sub">All 22 NYC metro counties indexed to 100 at a chosen rebase year. Five NYC boroughs in <span style="color:#0BB4FF;font-weight:500">blue</span>; the seventeen suburban counties in <span style="color:#9D958F;font-weight:500">gray</span>. Drag the slider to re-anchor the index. Hover any line for the county's name, index value, and raw under-18 count.</div>

<div class="controls">
  <label for="rebaseSlider">Rebase year:</label>
  <span id="rebaseYearLabel">2010</span>
  <input type="range" id="rebaseSlider" min="{year_min}" max="{year_max}" step="1" value="2010">
  <div class="legend">
    <span><span class="sw" style="background:#0BB4FF"></span>Borough</span>
    <span><span class="sw" style="background:#9D958F"></span>Suburb</span>
  </div>
</div>

<div class="chartwrap">
  <svg id="chart" viewBox="0 0 1040 560" width="100%" preserveAspectRatio="xMidYMid meet"></svg>
</div>
<div id="tooltip" class="tooltip"></div>

<div class="source">
Source: Stitched PEP — pe-02 intercensal 1980-1989 + cany9Y / canj9Y postcensal 1990-1999 (drift-corrected) + co-est00int 2000-2010 + cc-est2020int 2010-2020 + V2024 2020-2024 (scaled). Per-county correction factors linearly interpolated within each decade so the series passes exactly through NHGIS Decennial Census anchors at 1980, 1990, 2000, 2010. NYC MSA = OMB 2023 CBSA 35620 (22 counties).
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const DATA = {data_json};

const svg = d3.select('#chart');
const tooltip = d3.select('#tooltip');
const slider = document.getElementById('rebaseSlider');
const yearLbl = document.getElementById('rebaseYearLabel');

const W = 1040, H = 560;
const M = {{ t: 14, r: 90, b: 36, l: 50 }};
const iw = W - M.l - M.r;
const ih = H - M.t - M.b;

const x = d3.scaleLinear().domain([DATA.year_min, DATA.year_max]).range([M.l, M.l + iw]);
const y = d3.scaleLinear().range([M.t + ih, M.t]);

const COLOR_BOROUGH = '#0BB4FF';
const COLOR_SUBURB = '#BAB3AC';
const COLOR_AXIS = '#3D3733';
const COLOR_GRID = '#EEEEE6';
const COLOR_TICK = '#9D958F';
const COLOR_HIGHLIGHT = '#F4743B';

const line = d3.line()
  .x(d => x(d.year))
  .y(d => y(d.idx));

const gAxis = svg.append('g').attr('class','axis');
const gLines = svg.append('g').attr('class','lines');
const gOverlay = svg.append('g').attr('class','overlay');

function rebase(yearStart) {{
  const out = [];
  DATA.counties.forEach(c => {{
    const i0 = c.years.indexOf(yearStart);
    if (i0 < 0) return;
    const base = c.values[i0];
    if (!base) return;
    const pts = c.years.map((yr, i) => ({{ year: yr, idx: 100 * c.values[i] / base, raw: c.values[i] }}));
    out.push({{ fips: c.fips, name: c.name, is_borough: c.is_borough, pts: pts }});
  }});
  return out;
}}

function yDomain(series) {{
  let lo = Infinity, hi = -Infinity;
  series.forEach(s => s.pts.forEach(p => {{ if (p.idx < lo) lo = p.idx; if (p.idx > hi) hi = p.idx; }}));
  const pad = Math.max(2, (hi - lo) * 0.06);
  return [Math.max(0, lo - pad), hi + pad];
}}

function niceTicks(lo, hi) {{
  const span = hi - lo;
  let step;
  if (span > 200) step = 50;
  else if (span > 100) step = 25;
  else if (span > 50) step = 20;
  else if (span > 25) step = 10;
  else if (span > 10) step = 5;
  else step = 2;
  const ticks = [];
  const start = Math.ceil(lo / step) * step;
  for (let v = start; v <= hi; v += step) ticks.push(v);
  if (!ticks.includes(100) && lo <= 100 && hi >= 100) ticks.push(100);
  return ticks.sort((a,b)=>a-b);
}}

function draw(yearStart) {{
  const series = rebase(yearStart);
  const [lo, hi] = yDomain(series);
  y.domain([lo, hi]);

  // Axes
  gAxis.selectAll('*').remove();

  // Y gridlines + labels
  const yTicks = niceTicks(lo, hi);
  gAxis.selectAll('line.ygrid').data(yTicks).join('line')
    .attr('class','ygrid')
    .attr('x1', M.l).attr('x2', M.l + iw)
    .attr('y1', d => y(d)).attr('y2', d => y(d))
    .attr('stroke', d => d === 100 ? '#3D3733' : COLOR_GRID)
    .attr('stroke-width', d => d === 100 ? 1 : 0.5)
    .attr('stroke-dasharray', d => d === 100 ? '2,3' : null);
  gAxis.selectAll('text.ylab').data(yTicks).join('text')
    .attr('class','ylab')
    .attr('x', M.l - 6).attr('y', d => y(d) + 3)
    .attr('text-anchor','end')
    .style('font-size','10.5px').style('fill', d => d === 100 ? '#3D3733' : COLOR_TICK)
    .style('font-weight', d => d === 100 ? '500' : '400')
    .text(d => d);

  // X ticks
  const xTicks = [1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024];
  gAxis.selectAll('text.xlab').data(xTicks).join('text')
    .attr('class','xlab')
    .attr('x', d => x(d)).attr('y', M.t + ih + 16)
    .attr('text-anchor', d => d === DATA.year_min ? 'start' : (d === DATA.year_max ? 'end' : 'middle'))
    .style('font-size','11px').style('fill', COLOR_TICK)
    .text(d => "'" + String(d).slice(2));

  // Vertical marker at rebase year
  gAxis.append('line').attr('class','rebase-marker')
    .attr('x1', x(yearStart)).attr('x2', x(yearStart))
    .attr('y1', M.t).attr('y2', M.t + ih)
    .attr('stroke', COLOR_HIGHLIGHT).attr('stroke-width', 1).attr('stroke-dasharray','3,3');
  gAxis.append('text').attr('class','rebase-marker-lbl')
    .attr('x', x(yearStart)).attr('y', M.t - 3)
    .attr('text-anchor','middle')
    .style('font-size','10.5px').style('fill', COLOR_HIGHLIGHT).style('font-weight','500')
    .text('= 100');

  // Lines: draw suburbs first, then boroughs on top
  const sortedSeries = series.slice().sort((a,b) => (a.is_borough?1:0) - (b.is_borough?1:0));

  const paths = gLines.selectAll('path').data(sortedSeries, d => d.fips);
  paths.join(
    enter => enter.append('path')
      .attr('fill','none')
      .attr('stroke', d => d.is_borough ? COLOR_BOROUGH : COLOR_SUBURB)
      .attr('stroke-width', d => d.is_borough ? 1.8 : 1.0)
      .attr('stroke-opacity', d => d.is_borough ? 0.95 : 0.7)
      .attr('d', d => line(d.pts)),
    update => update
      .attr('stroke', d => d.is_borough ? COLOR_BOROUGH : COLOR_SUBURB)
      .attr('stroke-width', d => d.is_borough ? 1.8 : 1.0)
      .attr('stroke-opacity', d => d.is_borough ? 0.95 : 0.7)
      .transition().duration(250).attr('d', d => line(d.pts))
  );

  // Reorder so boroughs paint last (top)
  gLines.selectAll('path').sort((a,b) => (a.is_borough?1:0) - (b.is_borough?1:0));

  // Overlay for hover detection
  gOverlay.selectAll('*').remove();
  gOverlay.append('rect')
    .attr('x', M.l).attr('y', M.t).attr('width', iw).attr('height', ih)
    .attr('fill','transparent')
    .on('mousemove', (event) => onHover(event, series))
    .on('mouseleave', () => {{
      tooltip.style('opacity', 0);
      gLines.selectAll('path')
        .attr('stroke-width', d => d.is_borough ? 1.8 : 1.0)
        .attr('stroke-opacity', d => d.is_borough ? 0.95 : 0.7)
        .attr('stroke', d => d.is_borough ? COLOR_BOROUGH : COLOR_SUBURB);
      gOverlay.selectAll('circle.hover-dot').remove();
    }});
}}

function onHover(event, series) {{
  const [mx, my] = d3.pointer(event, svg.node());
  const yr = Math.round(x.invert(mx));
  if (yr < DATA.year_min || yr > DATA.year_max) return;
  // Find closest series by y at this year
  let best = null, bestDist = Infinity;
  series.forEach(s => {{
    const p = s.pts.find(pt => pt.year === yr);
    if (!p) return;
    const dy = Math.abs(y(p.idx) - my);
    if (dy < bestDist) {{ bestDist = dy; best = {{ s, p }}; }}
  }});
  if (!best || bestDist > 30) {{
    tooltip.style('opacity', 0);
    gLines.selectAll('path')
      .attr('stroke-width', d => d.is_borough ? 1.8 : 1.0)
      .attr('stroke-opacity', d => d.is_borough ? 0.95 : 0.7)
      .attr('stroke', d => d.is_borough ? COLOR_BOROUGH : COLOR_SUBURB);
    gOverlay.selectAll('circle.hover-dot').remove();
    return;
  }}
  const {{ s, p }} = best;
  gLines.selectAll('path')
    .attr('stroke-width', d => d.fips === s.fips ? 2.6 : (d.is_borough ? 1.6 : 0.8))
    .attr('stroke-opacity', d => d.fips === s.fips ? 1 : (d.is_borough ? 0.6 : 0.35))
    .attr('stroke', d => d.fips === s.fips ? (d.is_borough ? COLOR_BOROUGH : COLOR_HIGHLIGHT) : (d.is_borough ? COLOR_BOROUGH : COLOR_SUBURB));

  gOverlay.selectAll('circle.hover-dot').remove();
  gOverlay.append('circle').attr('class','hover-dot')
    .attr('cx', x(p.year)).attr('cy', y(p.idx))
    .attr('r', 4).attr('fill', s.is_borough ? COLOR_BOROUGH : COLOR_HIGHLIGHT)
    .attr('stroke','#F6F7F3').attr('stroke-width', 1.5);

  const fmt = n => n >= 1000 ? (n/1000).toFixed(0) + 'K' : Math.round(n).toString();
  const sign = p.idx >= 100 ? '+' : '';
  tooltip.html(
    `<span class="name">${{s.name}}</span>` +
    `<br/>${{p.year}}: index = ${{p.idx.toFixed(1)}} (${{sign}}${{(p.idx-100).toFixed(1)}})` +
    `<br/>Under-18: ${{fmt(p.raw)}}`
  );
  const rect = svg.node().getBoundingClientRect();
  const scaleX = rect.width / W;
  const scaleY = rect.height / H;
  const px = rect.left + x(p.year) * scaleX + window.scrollX;
  const py = rect.top + y(p.idx) * scaleY + window.scrollY;
  tooltip
    .style('left', (px + 12) + 'px')
    .style('top', (py - 18) + 'px')
    .style('opacity', 1);
}}

slider.addEventListener('input', e => {{
  const yr = +e.target.value;
  yearLbl.textContent = yr;
  draw(yr);
}});

draw(+slider.value);
</script>
</body></html>
"""


def main():
    payload = build_payload()
    html = HTML.format(
        year_min=payload["year_min"],
        year_max=payload["year_max"],
        data_json=json.dumps(payload),
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"  {len(payload['counties'])} counties, years {payload['year_min']}-{payload['year_max']}")


if __name__ == "__main__":
    main()
