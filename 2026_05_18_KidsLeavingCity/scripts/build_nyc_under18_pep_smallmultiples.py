"""
Small-multiples chart: under-18 by NYC MSA county, annual 2010-2024.

Data source: PEP intercensal 2010-2020 + PEP V2024 2020-2024 (per-county scaled
to anchor at intercensal April 2020). Produces a continuous annual series with
no decennial-rebasing artifact.

Input:  data/nyc_county_under18_pep_seamless.csv
Output: outputs/nyc_under18_counties_pep.html
"""
import json
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

df = pd.read_csv(DATA / "nyc_county_under18_pep_seamless.csv",
                 dtype={"county_fips": str})

BOROUGHS = {"36005", "36047", "36061", "36081", "36085"}

# Order: boroughs by size (largest first), then suburban counties by 2024 size
last_year = int(df["year"].max())
order = (df[df["year"] == last_year]
         .sort_values("under18", ascending=False)["county_fips"].tolist())

panels = []
for fips in order:
    sub = df[df["county_fips"] == fips].sort_values("year")
    series = [{"year": int(r.year), "v": int(r.under18),
               "src": "ic" if r.source.startswith("intercensal") else "v24"}
              for r in sub.itertuples()]
    name = sub["county_name"].iloc[0]
    first, last = series[0]["v"], series[-1]["v"]
    pct = (last / first - 1) * 100
    ymin = min(p["v"] for p in series)
    ymax = max(p["v"] for p in series)
    panels.append({
        "fips": fips, "name": name,
        "is_borough": fips in BOROUGHS,
        "series": series,
        "first": first, "last": last, "pct_chg": pct,
        "ymin": ymin, "ymax": ymax,
    })

all_years = sorted({p["year"] for panel in panels for p in panel["series"]})
P = {
    "panels": panels,
    "x_min": min(all_years),
    "x_max": max(all_years),
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC MSA: under-18 by county, annual PEP 2010–2024 (seamless)</title>
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
.pct { font-size:11.5px; font-variant-numeric:tabular-nums; }
.pct.up { color:#67A275; }
.pct.down { color:#F4743B; }
.rng { font-size:10.5px; color:#9D958F; font-variant-numeric:tabular-nums; margin-bottom:2px; }
.source { color:#7F7570; font-size:12px; max-width:1500px; margin-top:24px; line-height:1.5; }
</style></head>
<body>
<h1>Where the kids are: NYC MSA under-18 by county, 1980–2024 (annual)</h1>
<div class="sub">45 years of annual July-1 estimates for the 22 New York–Newark–Jersey City MSA counties, stitched from five PEP releases: 1980s intercensal (5-year groups, under-15 scaled per county to 1990 anchor), 1990s postcensal cany files (exact under-18, scaled per county to 2000 Census anchor), 2000-2010 intercensal (5-year groups, under-15 scaled per county to 2010 anchor), 2010-2020 intercensal (exact under-18), and Vintage 2024 PEP 2020-2024 (single-year-of-age, scaled per county to intercensal April-2020). Joins align at decennial census anchors (1990, 2000, 2010, 2020). Each panel has its own y-axis. NYC boroughs in blue, all other counties in grey. Right-side number: % change 1980→2024.</div>

<div class="grid" id="grid"></div>

<div class="source">
Source: U.S. Census Bureau Population Estimates Program. 1980-1989: intercensal pe-02-19YY (5-year groups, under-15 × per-county factor to land on 1990 anchor). 1990-1999: postcensal cany9Y/canj9Y (direct under-18 = Ages 0-4 + Ages 5-17; per-county factor to land on 2000 Decennial). 2000-2009: intercensal co-est00int (5-year groups, under-15 × per-county factor to land on 2010 anchor). 2010-2019: intercensal cc-est2020int (exact under-18). 2020-2024: V2024 PEP (single-year-of-age 0-17, per-county factor to land on intercensal April-2020). All joins anchored to Decennial Census counts (1990, 2000, 2010, 2020). NYC county FIPS codes stable across all 45 years.
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const grid = d3.select('#grid');

const W = 260, H = 110, M = {t:6, r:8, b:18, l:6};
const iw = W - M.l - M.r;

const x = d3.scaleLinear().domain([P.x_min, P.x_max]).range([M.l, M.l + iw]);
const fmt = n => n >= 1000 ? (n/1000).toFixed(0) + 'K' : n.toString();

P.panels.forEach(panel => {
  const cell = grid.append('div').attr('class','panel');
  const hdr = cell.append('div').attr('class','panel-hdr');
  hdr.append('div').attr('class','cname' + (panel.is_borough ? ' borough':''))
     .text(panel.name);
  const pctCls = panel.pct_chg >= 0 ? 'up' : 'down';
  const pctTxt = (panel.pct_chg >= 0 ? '+' : '') + panel.pct_chg.toFixed(0) + '%';
  hdr.append('div').attr('class','pct ' + pctCls).text(pctTxt);

  cell.append('div').attr('class','rng')
      .text(`${fmt(panel.ymin)}–${fmt(panel.ymax)} kids`);

  const svg = cell.append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width','100%').attr('height',H);

  const y = d3.scaleLinear()
    .domain([panel.ymin * 0.97, panel.ymax * 1.03])
    .range([H - M.b, M.t]);

  const tickYears = [P.x_min, 1990, 2000, 2010, 2020, P.x_max];
  svg.append('g').selectAll('text').data(tickYears).join('text')
    .attr('x', d => x(d))
    .attr('y', H - 4)
    .attr('text-anchor', d => d === P.x_min ? 'start' : (d === P.x_max ? 'end' : 'middle'))
    .style('font-size', '9.5px')
    .style('fill', '#9D958F')
    .text(d => String(d).slice(2));

  const colr = panel.is_borough ? '#0BB4FF' : '#3D3733';
  const line = d3.line()
    .x(d => x(d.year))
    .y(d => y(d.v))
    .curve(d3.curveMonotoneX);

  svg.append('path').datum(panel.series)
    .attr('fill', 'none')
    .attr('stroke', colr)
    .attr('stroke-width', 1.6)
    .attr('d', line);

  // Data-source transition markers (subtle vertical guides at decade boundaries)
  [1990, 2000, 2010, 2020].forEach(yr => {
    svg.append('line').attr('x1', x(yr)).attr('x2', x(yr))
      .attr('y1', M.t).attr('y2', H - M.b)
      .attr('stroke', '#DADFCE').attr('stroke-width', 0.7).attr('stroke-dasharray', '2,2');
  });

  svg.append('circle').attr('cx', x(panel.series[0].year)).attr('cy', y(panel.series[0].v))
    .attr('r', 2.2).attr('fill', colr);
  svg.append('circle').attr('cx', x(panel.series[panel.series.length-1].year))
    .attr('cy', y(panel.series[panel.series.length-1].v))
    .attr('r', 2.4).attr('fill', colr);
});
</script>
</body>
</html>
"""

html = template.replace("__DATA__", json.dumps(P))
out_path = OUT / "nyc_under18_counties_pep.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.2f} MB)")
