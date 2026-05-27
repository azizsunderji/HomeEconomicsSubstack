"""
NYC MSA under-18 by county, 1980-2024 — trajectory only, shared absolute y-axis.

22 small multiples, all panels share 0-650K so absolute magnitudes are directly
comparable (Brooklyn fills, Putnam tiny — that's the point).

Input:  data/nyc_county_under18_pep_seamless.csv
Output: outputs/nyc_under18_levels_shared.html
"""
import json
import math
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

NAMES = {
    "34003": "Bergen", "34013": "Essex", "34017": "Hudson",
    "34019": "Hunterdon", "34023": "Middlesex", "34025": "Monmouth",
    "34027": "Morris", "34029": "Ocean", "34031": "Passaic",
    "34035": "Somerset", "34037": "Sussex", "34039": "Union",
    "36005": "Bronx", "36047": "Brooklyn", "36059": "Nassau",
    "36061": "Manhattan", "36079": "Putnam", "36081": "Queens",
    "36085": "Staten Island", "36087": "Rockland",
    "36103": "Suffolk", "36119": "Westchester",
}
BOROUGHS = {"36005", "36047", "36061", "36081", "36085"}

df = pd.read_csv(DATA / "nyc_county_under18_pep_seamless.csv",
                 dtype={"county_fips": str})

# Order by 2024 size (largest first)
order = (df[df["year"] == 2024]
         .sort_values("under18", ascending=False)["county_fips"].tolist())

panels = []
for fips in order:
    sub = df[df["county_fips"] == fips].sort_values("year")
    series = [{"y": int(r.year), "v": int(r.under18)} for r in sub.itertuples()]
    panels.append({
        "fips": fips, "name": NAMES[fips],
        "is_borough": fips in BOROUGHS,
        "series": series,
        "first": series[0]["v"], "last": series[-1]["v"],
        "min": min(p["v"] for p in series),
        "max": max(p["v"] for p in series),
    })

# Shared y-axis: 0 to next-50K-above the global max
global_max = max(p["max"] for p in panels)
ymax_padded = math.ceil(global_max / 50000) * 50000  # round up to 50K
print(f"Global max: {global_max:,}; padded ymax: {ymax_padded:,}")

all_years = sorted({s["y"] for p in panels for s in p["series"]})
P = {
    "panels": panels,
    "x_min": min(all_years), "x_max": max(all_years),
    "ymin": 0, "ymax": ymax_padded,
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC MSA under-18 by county, 1980-2024 — shared scale</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:28px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:20px; max-width:1500px; line-height:1.5; }
.grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:14px 18px; max-width:1500px; }
.panel { background:#fff; border:0.5px solid #e1e2e3; padding:10px 12px 12px; }
.panel-hdr { display:flex; align-items:baseline; justify-content:space-between; gap:6px; margin-bottom:2px; }
.cname { font-size:13.5px; font-weight:500; }
.cname.borough { color:#0BB4FF; }
.endpoints { font-size:11px; color:#7F7570; font-variant-numeric:tabular-nums; }
.source { color:#7F7570; font-size:12px; max-width:1500px; margin-top:24px; line-height:1.5; }
</style></head>
<body>
<h1>NYC MSA under-18 by county, 1980–2024 (shared scale)</h1>
<div class="sub">All 22 panels share the same absolute y-axis (0 to __YMAX__) so absolute magnitudes are directly comparable. Brooklyn (~595K) dwarfs Putnam (~20K) by 30×. Boroughs in blue. Sorted by 2024 size, largest first. Y-axis gridlines at every 100K. Annual July-1 estimates stitched from PEP intercensal 1980-2020 + V2024 2020-2024 with per-county anchoring to NHGIS Decennial Census counts at 1980, 1990, 2000, 2010, and intercensal April-2020.</div>

<div class="grid" id="grid"></div>

<div class="source">
Source: Stitched PEP — pe-02 intercensal 1980-1989 + cany9Y postcensal 1990-1999 (drift-corrected) + co-est00int 2000-2010 + cc-est2020int 2010-2020 + V2024 2020-2024 (scaled). Per-county correction factors linearly interpolated within each decade so the series passes exactly through NHGIS Decennial Census anchors. NYC MSA = OMB 2023 CBSA 35620 (22 counties: 5 NYC boroughs + Long Island + Westchester/Hudson Valley + 12 NJ counties).
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const grid = d3.select('#grid');

const W = 280, H = 160, M = {t:8, r:8, b:18, l:6};
const iw = W - M.l - M.r;

const x = d3.scaleLinear().domain([P.x_min, P.x_max]).range([M.l, M.l + iw]);
const y = d3.scaleLinear().domain([P.ymin, P.ymax]).range([H - M.b, M.t]);

const fmtK = n => n >= 1000 ? (n/1000).toFixed(0) + 'K' : n.toString();

P.panels.forEach(panel => {
  const cell = grid.append('div').attr('class','panel');
  const hdr = cell.append('div').attr('class','panel-hdr');
  hdr.append('div').attr('class','cname' + (panel.is_borough ? ' borough':''))
     .text(panel.name);
  hdr.append('div').attr('class','endpoints')
     .text(`${fmtK(panel.first)} → ${fmtK(panel.last)}`);

  const svg = cell.append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width','100%').attr('height',H);

  // Horizontal gridlines + y-axis labels every 100K
  for (let v = 0; v <= P.ymax; v += 100000) {
    svg.append('line')
      .attr('x1', M.l).attr('x2', M.l + iw)
      .attr('y1', y(v)).attr('y2', y(v))
      .attr('stroke', '#EEEEE6').attr('stroke-width', 0.5);
    if (v > 0) {
      svg.append('text')
        .attr('x', M.l + 2).attr('y', y(v) - 2)
        .style('font-size', '8.5px').style('fill', '#BAB3AC')
        .text((v/1000) + 'K');
    }
  }

  // X-axis ticks
  const tickYears = [P.x_min, 1990, 2000, 2010, 2020, P.x_max];
  svg.append('g').selectAll('text').data(tickYears).join('text')
    .attr('x', d => x(d))
    .attr('y', H - 4)
    .attr('text-anchor', d => d === P.x_min ? 'start' : (d === P.x_max ? 'end' : 'middle'))
    .style('font-size', '9.5px').style('fill', '#9D958F')
    .text(d => "'" + String(d).slice(2));

  // Trajectory line
  const colr = panel.is_borough ? '#0BB4FF' : '#3D3733';
  const line = d3.line()
    .x(d => x(d.y))
    .y(d => y(d.v))
    .curve(d3.curveMonotoneX);
  svg.append('path').datum(panel.series)
    .attr('fill', 'none').attr('stroke', colr)
    .attr('stroke-width', 1.7).attr('d', line);

  // Endpoint dots
  svg.append('circle').attr('cx', x(panel.series[0].y)).attr('cy', y(panel.series[0].v))
    .attr('r', 2).attr('fill', colr);
  const endL = panel.series[panel.series.length - 1];
  svg.append('circle').attr('cx', x(endL.y)).attr('cy', y(endL.v))
    .attr('r', 2.4).attr('fill', colr);
});
</script>
</body></html>
"""

html = (template.replace("__DATA__", json.dumps(P))
                .replace("__YMAX__", f"{ymax_padded//1000}K"))
out_path = OUT / "nyc_under18_levels_shared.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.2f} MB)")
