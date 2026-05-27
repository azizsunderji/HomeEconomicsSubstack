"""
Simple two-line chart: under-18 in NYC proper (5 boroughs summed) vs
suburbs (17 NYC MSA counties summed), annual 1980-2024.

Input:  data/nyc_county_under18_pep_seamless.csv
Output: outputs/nyc_under18_nyc_vs_suburbs.html
"""
import json
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"
BOROUGHS = {"36005", "36047", "36061", "36081", "36085"}

df = pd.read_csv(DATA / "nyc_county_under18_pep_seamless.csv",
                 dtype={"county_fips": str})

df["group"] = df["county_fips"].map(lambda f: "nyc" if f in BOROUGHS else "suburbs")
agg = (df.groupby(["group", "year"], as_index=False)["under18"]
         .sum()
         .sort_values(["group", "year"]))

def series(group_key: str) -> list[dict]:
    sub = agg[agg["group"] == group_key]
    return [{"y": int(r.year), "v": int(r.under18)} for r in sub.itertuples()]

nyc_series = series("nyc")
sub_series = series("suburbs")

P = {
    "nyc": nyc_series,
    "suburbs": sub_series,
    "year_min": int(df["year"].min()),
    "year_max": int(df["year"].max()),
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC vs suburbs: under-18 population, 1980-2024</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:32px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:20px; max-width:1000px; line-height:1.5; }
.chartwrap { background:#fff; border:0.5px solid #e1e2e3; padding:22px 26px; max-width:1000px; }
.source { color:#7F7570; font-size:12px; max-width:1000px; margin-top:16px; line-height:1.5; }
</style></head>
<body>
<h1>Under-18 population: NYC proper vs surrounding suburbs, 1980–2024</h1>
<div class="sub">Annual July-1 estimates summed across two groups within the NY-Newark-Jersey City MSA (CBSA 35620): <span style="color:#0BB4FF;font-weight:500">NYC proper</span> = 5 boroughs (Bronx, Brooklyn, Manhattan, Queens, Staten Island); <span style="color:#3D3733;font-weight:500">Suburbs</span> = the other 17 MSA counties (Long Island + Westchester/Hudson Valley + 12 northern NJ counties). Same stitched PEP+NHGIS series as the per-county chart.</div>

<div class="chartwrap">
  <svg id="chart" viewBox="0 0 940 540" width="100%" preserveAspectRatio="xMidYMid meet"></svg>
</div>

<div class="source">
Source: Stitched U.S. Census Bureau PEP — pe-02 intercensal 1980-1989 + cany/canj postcensal 1990-1999 (drift-corrected) + co-est00int 2000-2010 + cc-est2020int 2010-2020 + V2024 2020-2024 (scaled). Per-county correction factors linearly interpolated within each decade so each county series passes exactly through NHGIS Decennial Census anchors at 1980, 1990, 2000, 2010.
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const svg = d3.select('#chart');
const W = 940, H = 540, M = {t:24, r:160, b:38, l:60};
const iw = W - M.l - M.r;
const ih = H - M.t - M.b;

const x = d3.scaleLinear().domain([P.year_min, P.year_max]).range([M.l, M.l + iw]);

const all = P.nyc.concat(P.suburbs);
const ymin = d3.min(all, d => d.v);
const ymax = d3.max(all, d => d.v);
const pad = (ymax - ymin) * 0.08;
const y = d3.scaleLinear().domain([Math.max(0, ymin - pad), ymax + pad]).range([M.t + ih, M.t]);

// Y gridlines + labels (round step)
const span = (ymax + pad) - Math.max(0, ymin - pad);
const step = span > 2000000 ? 500000 : span > 1000000 ? 250000 : span > 500000 ? 200000 : 100000;
const yTicks = [];
for (let v = Math.ceil(y.domain()[0] / step) * step; v <= y.domain()[1]; v += step) yTicks.push(v);
svg.append('g').selectAll('line').data(yTicks).join('line')
  .attr('x1', M.l).attr('x2', M.l + iw)
  .attr('y1', d => y(d)).attr('y2', d => y(d))
  .attr('stroke', '#EEEEE6').attr('stroke-width', 0.5);
svg.append('g').selectAll('text').data(yTicks).join('text')
  .attr('x', M.l - 8).attr('y', d => y(d) + 4)
  .attr('text-anchor', 'end')
  .style('font-size', '11.5px').style('fill', '#9D958F')
  .text(d => (d / 1e6).toFixed(d < 1e6 ? 2 : 1) + 'M');

// X ticks
const xTicks = [1980, 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2024];
svg.append('g').selectAll('text').data(xTicks).join('text')
  .attr('x', d => x(d)).attr('y', M.t + ih + 18)
  .attr('text-anchor', d => d === P.year_min ? 'start' : (d === P.year_max ? 'end' : 'middle'))
  .style('font-size', '11.5px').style('fill', '#9D958F')
  .text(d => "'" + String(d).slice(2));

const line = d3.line().x(d => x(d.y)).y(d => y(d.v)).curve(d3.curveMonotoneX);

const SERIES = [
  {key: 'suburbs', label: 'Suburbs (17 counties)', color: '#3D3733', data: P.suburbs},
  {key: 'nyc',     label: 'NYC proper (5 boroughs)', color: '#0BB4FF', data: P.nyc},
];

SERIES.forEach(s => {
  svg.append('path').datum(s.data)
    .attr('fill', 'none').attr('stroke', s.color).attr('stroke-width', 2.2)
    .attr('d', line);

  // Endpoint dots
  const first = s.data[0], last = s.data[s.data.length - 1];
  svg.append('circle').attr('cx', x(first.y)).attr('cy', y(first.v)).attr('r', 3.2).attr('fill', s.color);
  svg.append('circle').attr('cx', x(last.y)).attr('cy', y(last.v)).attr('r', 3.6).attr('fill', s.color);

  // End-of-line label
  const pct = (last.v / first.v - 1) * 100;
  const sign = pct >= 0 ? '+' : '';
  svg.append('text')
    .attr('x', x(last.y) + 8).attr('y', y(last.v) - 6)
    .style('font-size', '13.5px').style('font-weight', '500').style('fill', s.color)
    .text(s.label);
  svg.append('text')
    .attr('x', x(last.y) + 8).attr('y', y(last.v) + 10)
    .style('font-size', '12px').style('fill', '#7F7570')
    .text(`${(last.v / 1e6).toFixed(2)}M  (${sign}${pct.toFixed(1)}% since 1980)`);
});

// Decade reference verticals
[1990, 2000, 2010, 2020].forEach(yr => {
  svg.append('line').attr('x1', x(yr)).attr('x2', x(yr))
    .attr('y1', M.t).attr('y2', M.t + ih)
    .attr('stroke', '#DADFCE').attr('stroke-width', 0.6).attr('stroke-dasharray', '2,3');
});
</script>
</body></html>
"""

html = template.replace("__DATA__", json.dumps(P))
out_path = OUT / "nyc_under18_nyc_vs_suburbs.html"
out_path.write_text(html)
print(f"Wrote {out_path}")
print(f"  NYC:     {nyc_series[0]['v']:,} (1980) → {nyc_series[-1]['v']:,} (2024)  "
      f"= {(nyc_series[-1]['v']/nyc_series[0]['v']-1)*100:+.1f}%")
print(f"  Suburbs: {sub_series[0]['v']:,} (1980) → {sub_series[-1]['v']:,} (2024)  "
      f"= {(sub_series[-1]['v']/sub_series[0]['v']-1)*100:+.1f}%")
