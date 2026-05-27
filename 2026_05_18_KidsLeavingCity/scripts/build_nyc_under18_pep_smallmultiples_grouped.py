"""
Small-multiples chart, grouped: NYC proper (5 boroughs) vs Suburbs (17 counties).

Same underlying data as build_nyc_under18_pep_smallmultiples.py, but the 22
panels are split into two sections — boroughs first, suburbs second — each with
its own header, totals, and grid. Within each group, panels are sorted by 2024
size, largest first.

Input:  data/nyc_county_under18_pep_seamless.csv
Output: outputs/nyc_under18_counties_pep_grouped.html
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


def panel_for(fips: str) -> dict:
    sub = df[df["county_fips"] == fips].sort_values("year")
    series = [{"year": int(r.year), "v": int(r.under18)} for r in sub.itertuples()]
    name = sub["county_name"].iloc[0]
    first, last = series[0]["v"], series[-1]["v"]
    pct = (last / first - 1) * 100
    ymin = min(p["v"] for p in series)
    ymax = max(p["v"] for p in series)
    return {
        "fips": fips, "name": name,
        "is_borough": fips in BOROUGHS,
        "series": series,
        "first": first, "last": last, "pct_chg": pct,
        "ymin": ymin, "ymax": ymax,
    }


last_year = int(df["year"].max())
fips_by_size = (df[df["year"] == last_year]
                .sort_values("under18", ascending=False)["county_fips"].tolist())

borough_panels = [panel_for(f) for f in fips_by_size if f in BOROUGHS]
suburb_panels = [panel_for(f) for f in fips_by_size if f not in BOROUGHS]


def group_totals(panels: list[dict]) -> dict:
    first_total = sum(p["series"][0]["v"] for p in panels)
    last_total = sum(p["series"][-1]["v"] for p in panels)
    pct = (last_total / first_total - 1) * 100
    return {
        "first_total": first_total,
        "last_total": last_total,
        "pct": pct,
        "n": len(panels),
    }


all_years = sorted({p["year"] for panel in (borough_panels + suburb_panels) for p in panel["series"]})

P = {
    "groups": [
        {
            "label": "NYC proper — 5 boroughs",
            "subtitle": "Bronx · Brooklyn · Manhattan · Queens · Staten Island",
            "panels": borough_panels,
            "totals": group_totals(borough_panels),
            "color": "#0BB4FF",
        },
        {
            "label": "Suburbs — 17 counties of the NYC MSA",
            "subtitle": "Long Island + Westchester/Hudson Valley + 12 northern NJ counties",
            "panels": suburb_panels,
            "totals": group_totals(suburb_panels),
            "color": "#3D3733",
        },
    ],
    "x_min": min(all_years),
    "x_max": max(all_years),
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC MSA under-18 by county, 1980-2024 — grouped (boroughs vs suburbs)</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:28px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:24px; max-width:1500px; line-height:1.5; }
.group { max-width:1500px; margin-bottom:32px; }
.group-hdr { display:flex; align-items:baseline; gap:18px; padding-bottom:8px; margin-bottom:14px; border-bottom:1px solid #DADFCE; }
.group-hdr .gname { font-size:20px; font-weight:500; }
.group-hdr .gname.borough { color:#0BB4FF; }
.group-hdr .gsub { font-size:13px; color:#7F7570; flex:1; }
.group-hdr .gtot { font-size:13px; color:#3D3733; font-variant-numeric:tabular-nums; }
.group-hdr .gtot .pct.up { color:#67A275; font-weight:500; }
.group-hdr .gtot .pct.down { color:#F4743B; font-weight:500; }
.grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:14px 18px; }
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
<h1>NYC MSA under-18 by county, 1980–2024 — grouped</h1>
<div class="sub">Same 45 years of annual PEP-stitched data as the un-grouped chart, but now the 22 counties are split into the 5 NYC boroughs (top) and the 17 suburban counties of the MSA (bottom). Each panel has its own y-axis; sort within each group is by 2024 under-18 population. Right-side number on each panel is % change 1980→2024. Group headers carry the group's aggregate change.</div>

<div id="root"></div>

<div class="source">
Source: U.S. Census Bureau Population Estimates Program. 1980-1989: intercensal pe-02-19YY (5-year groups, under-15 × per-county factor to land on 1990 anchor). 1990-1999: postcensal cany9Y/canj9Y (direct under-18). 2000-2009: intercensal co-est00int (5-year groups, under-15 × per-county factor to 2010 anchor). 2010-2019: intercensal cc-est2020int (exact under-18). 2020-2024: V2024 PEP (single-year-of-age 0-17, per-county factor to intercensal April-2020). All joins anchored to Decennial Census counts (1990, 2000, 2010, 2020).
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const root = d3.select('#root');

const W = 260, H = 110, M = {t:6, r:8, b:18, l:6};
const iw = W - M.l - M.r;
const x = d3.scaleLinear().domain([P.x_min, P.x_max]).range([M.l, M.l + iw]);
const fmt = n => n >= 1000 ? (n/1000).toFixed(0) + 'K' : n.toString();
const fmtSign = n => (n >= 0 ? '+' : '') + (n/1000).toFixed(0) + 'K';

P.groups.forEach((group, gi) => {
  const wrap = root.append('div').attr('class', 'group');
  const hdr = wrap.append('div').attr('class', 'group-hdr');
  hdr.append('div').attr('class', 'gname' + (gi === 0 ? ' borough' : ''))
     .text(group.label);
  hdr.append('div').attr('class', 'gsub').text(group.subtitle);
  const t = group.totals;
  const pctCls = t.pct >= 0 ? 'up' : 'down';
  const pctTxt = (t.pct >= 0 ? '+' : '') + t.pct.toFixed(1) + '%';
  hdr.append('div').attr('class', 'gtot')
     .html(`${t.n} counties · ${fmt(t.first_total)} (1980) → ${fmt(t.last_total)} (2024)  ·  net ${fmtSign(t.last_total - t.first_total)}  <span class="pct ${pctCls}">${pctTxt}</span>`);

  const grid = wrap.append('div').attr('class', 'grid');

  group.panels.forEach(panel => {
    const cell = grid.append('div').attr('class', 'panel');
    const ph = cell.append('div').attr('class', 'panel-hdr');
    ph.append('div').attr('class', 'cname' + (panel.is_borough ? ' borough' : ''))
      .text(panel.name);
    const pctCls = panel.pct_chg >= 0 ? 'up' : 'down';
    const pctTxt = (panel.pct_chg >= 0 ? '+' : '') + panel.pct_chg.toFixed(0) + '%';
    ph.append('div').attr('class', 'pct ' + pctCls).text(pctTxt);

    cell.append('div').attr('class', 'rng').text(`${fmt(panel.ymin)}–${fmt(panel.ymax)} kids`);

    const svg = cell.append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width', '100%').attr('height', H);
    const y = d3.scaleLinear()
      .domain([panel.ymin * 0.97, panel.ymax * 1.03])
      .range([H - M.b, M.t]);

    const tickYears = [P.x_min, 1990, 2000, 2010, 2020, P.x_max];
    svg.append('g').selectAll('text').data(tickYears).join('text')
      .attr('x', d => x(d)).attr('y', H - 4)
      .attr('text-anchor', d => d === P.x_min ? 'start' : (d === P.x_max ? 'end' : 'middle'))
      .style('font-size', '9.5px').style('fill', '#9D958F')
      .text(d => String(d).slice(2));

    const colr = panel.is_borough ? '#0BB4FF' : '#3D3733';
    const line = d3.line().x(d => x(d.year)).y(d => y(d.v)).curve(d3.curveMonotoneX);
    svg.append('path').datum(panel.series)
      .attr('fill', 'none').attr('stroke', colr).attr('stroke-width', 1.6)
      .attr('d', line);

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
});
</script>
</body></html>
"""

html = template.replace("__DATA__", json.dumps(P))
out_path = OUT / "nyc_under18_counties_pep_grouped.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.2f} MB)")
print(f"  Boroughs: {P['groups'][0]['totals']}")
print(f"  Suburbs:  {P['groups'][1]['totals']}")
