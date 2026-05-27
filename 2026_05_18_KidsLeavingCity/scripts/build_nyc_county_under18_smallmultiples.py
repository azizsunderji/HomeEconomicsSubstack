"""
Small-multiples chart: under-18 population by NYC MSA county, 2009-2023.
One panel per county, sorted by 2023 size (largest first).

Per-panel y-axis (independent) so small counties' trends are readable.
Each panel labels its own min/max range.

Uses every ACS 5-year endpoint we can pull (2009 through 2023, 15 vintages).

Input:  data/nyc_county_under18_acs5_ts.csv
Output: outputs/nyc_under18_counties_acs5.html
"""
import json
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

df = pd.read_csv(DATA / "nyc_county_under18_acs5_ts.csv",
                 dtype={"county_fips": str, "state_fips": str})

# 5 NYC boroughs (NY state) get colored as core; others = grey
BOROUGHS = {"36005", "36047", "36061", "36081", "36085"}

# Order counties by 2023 under-18 (largest first)
order = (df[df["year"] == 2023]
         .sort_values("under18", ascending=False)["county_fips"].tolist())

panels = []
for fips in order:
    sub = df[df["county_fips"] == fips].sort_values("year")
    series = [{"year": int(r.year), "v": int(r.under18)} for r in sub.itertuples()]
    name = sub["county_name"].iloc[0]
    first = series[0]["v"]
    last = series[-1]["v"]
    pct = (last / first - 1) * 100
    ymin = min(p["v"] for p in series)
    ymax = max(p["v"] for p in series)
    panels.append({
        "fips": fips,
        "name": name,
        "is_borough": fips in BOROUGHS,
        "series": series,
        "first": first, "last": last, "pct_chg": pct,
        "ymin": ymin, "ymax": ymax,
    })

# Min/max year across all panels for shared x-axis
all_years = sorted({p["year"] for panel in panels for p in panel["series"]})
P = {
    "panels": panels,
    "years": all_years,
    "x_min": min(all_years),
    "x_max": max(all_years),
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC MSA: under-18 population by county, 2009–2023 (ACS 5-year)</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:28px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:20px; max-width:1400px; line-height:1.5; }
.grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:14px 18px; max-width:1500px; }
.panel { background:#fff; border:0.5px solid #e1e2e3; padding:10px 12px 12px; }
.panel-hdr { display:flex; align-items:baseline; justify-content:space-between; gap:6px; margin-bottom:2px; }
.cname { font-size:13.5px; font-weight:500; }
.cname.borough { color:#0BB4FF; }
.pct { font-size:11.5px; color:#7F7570; font-variant-numeric:tabular-nums; }
.pct.up { color:#67A275; }
.pct.down { color:#F4743B; }
.rng { font-size:10.5px; color:#9D958F; font-variant-numeric:tabular-nums; margin-bottom:2px; }
.source { color:#7F7570; font-size:12px; max-width:1500px; margin-top:24px; line-height:1.5; }
</style></head>
<body>
<h1>Where the kids are: NYC MSA under-18 by county, 2009–2023</h1>
<div class="sub">Every available ACS 5-year endpoint (2005-09 through 2019-23) for the 22 New York–Newark–Jersey City MSA counties. Each panel has its own y-axis so smaller counties' trends are visible. Counties ordered by 2023 under-18 size (largest first). Boroughs of NYC in blue, all other counties in grey. Right-side number: % change endpoint-to-endpoint. ACS 5-year smooths out short-term noise; the "2009" point is really a 2005–2009 average.</div>

<div class="grid" id="grid"></div>

<div class="source">
Source: U.S. Census Bureau, American Community Survey 5-year estimates, Table B01001 (Sex by Age). Under-18 = sum of cells B01001_003E to _006E (male) and _027E to _030E (female). 15 endpoint years (2009-2023). MSA = New York–Newark–Jersey City, NY-NJ-PA (CBSA 35620) per OMB 2023.
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const grid = d3.select('#grid');

const W = 260, H = 110, M = {t:6, r:8, b:18, l:6};
const iw = W - M.l - M.r;
const ih = H - M.t - M.b;

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
    .domain([panel.ymin * 0.95, panel.ymax * 1.05])
    .range([H - M.b, M.t]);

  // Zero baseline reference (only if range crosses zero — these never do, but draw the lower bound)
  // X-axis ticks (years)
  const tickYears = [P.x_min, 2014, 2019, P.x_max];
  svg.append('g').selectAll('text').data(tickYears).join('text')
    .attr('x', d => x(d))
    .attr('y', H - 4)
    .attr('text-anchor', d => d === P.x_min ? 'start' : (d === P.x_max ? 'end' : 'middle'))
    .style('font-size', '9.5px')
    .style('fill', '#9D958F')
    .text(d => String(d).slice(2));

  // Line
  const line = d3.line()
    .x(d => x(d.year))
    .y(d => y(d.v))
    .curve(d3.curveMonotoneX);

  const colr = panel.is_borough ? '#0BB4FF' : '#3D3733';
  svg.append('path').datum(panel.series)
    .attr('fill', 'none')
    .attr('stroke', colr)
    .attr('stroke-width', 1.6)
    .attr('d', line);

  // Endpoint dots
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
out_path = OUT / "nyc_under18_counties_acs5.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.2f} MB)")
