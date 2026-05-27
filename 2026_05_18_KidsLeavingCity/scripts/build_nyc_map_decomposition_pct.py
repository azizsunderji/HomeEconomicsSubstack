"""
Interactive NYC MSA map + decomposition chart — PERCENT-CHANGE COLORING variant.

Same chart on the right as the absolute version, but the map on the left is
colored by % change in under-18 since 2010 (net_change / level_2010), not by
absolute count. This lets small outer-ring counties (Sussex −22%, Putnam −19%)
read just as strongly as boroughs (Brooklyn −10%) even though Brooklyn's
absolute loss is 10× larger.

Output: outputs/nyc_decomposition_map_pct.html
"""
import json
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
GEO = DATA / "geo"
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
NYC_FIPS = set(NAMES.keys())

# Load geo
g = json.loads((GEO / "metro10_counties.geojson").read_text())
nyc_features = [f for f in g["features"] if f["properties"].get("cbsa_code") == 35620]
geo_data = {"type": "FeatureCollection", "features": nyc_features}

# Load decomposition + level data
decomp = pd.read_csv(DATA / "nyc_county_under18_decomposition.csv", dtype={"county_fips": str})
level = pd.read_csv(DATA / "nyc_county_under18_pep_seamless.csv", dtype={"county_fips": str})

# Build per-county data: level trajectory + annual components + cumulative components
counties = {}
all_net_change = []
for fips in NYC_FIPS:
    lvl = level[level["county_fips"] == fips].sort_values("year")
    dec = decomp[decomp["county_fips"] == fips].sort_values("interval_start")
    baseline_2010 = int(lvl[lvl["year"] == 2010]["under18"].iloc[0])

    level_pts = [{"y": int(r.year), "v": int(r.under18)} for r in lvl.itertuples()]

    cum_nat, cum_dom, cum_intl = 0, 0, 0
    comp_pts = [{"y": 2010, "nat": 0, "dom": 0, "intl": 0}]
    for _, r in dec.iterrows():
        cum_nat += int(r["natural_change"])
        cum_dom += int(r["net_mig_u18_dom"])
        cum_intl += int(r["net_mig_u18_intl"])
        comp_pts.append({"y": int(r["interval_start"]) + 1,
                          "nat": cum_nat, "dom": cum_dom, "intl": cum_intl})

    counties[fips] = {
        "name": NAMES[fips],
        "is_borough": fips in BOROUGHS,
        "level": level_pts,
        "baseline_2010": baseline_2010,
        "comp": comp_pts,
        "level_1980": level_pts[0]["v"],
        "level_2010": baseline_2010,
        "level_2024": level_pts[-1]["v"],
        "final_nat": comp_pts[-1]["nat"],
        "final_dom": comp_pts[-1]["dom"],
        "final_intl": comp_pts[-1]["intl"],
        "net_change": comp_pts[-1]["nat"] + comp_pts[-1]["dom"] + comp_pts[-1]["intl"],
    }
    counties[fips]["pct_change"] = counties[fips]["net_change"] / baseline_2010
    all_net_change.append(counties[fips]["pct_change"])

# Color scale: diverging on % change 2010-2024
max_abs_change = max(abs(v) for v in all_net_change)

# MSA aggregate (sum across all counties)
import collections
msa_level = collections.defaultdict(int)
for c in counties.values():
    for p in c["level"]:
        msa_level[p["y"]] += p["v"]
msa_level_pts = sorted([{"y": y, "v": v} for y, v in msa_level.items()], key=lambda d: d["y"])
msa_baseline_2010 = msa_level[2010]

msa_comp_by_year = collections.defaultdict(lambda: {"nat": 0, "dom": 0, "intl": 0})
for fips, c in counties.items():
    for p in c["comp"]:
        msa_comp_by_year[p["y"]]["nat"] += p["nat"]
        msa_comp_by_year[p["y"]]["dom"] += p["dom"]
        msa_comp_by_year[p["y"]]["intl"] += p["intl"]
msa_comp_pts = sorted([{"y": y, **v} for y, v in msa_comp_by_year.items()], key=lambda d: d["y"])

counties["_MSA"] = {
    "name": "NYC MSA (all 22 counties)",
    "is_borough": False,
    "level": msa_level_pts,
    "baseline_2010": msa_baseline_2010,
    "comp": msa_comp_pts,
    "level_1980": msa_level_pts[0]["v"],
    "level_2010": msa_baseline_2010,
    "level_2024": msa_level_pts[-1]["v"],
    "final_nat": msa_comp_pts[-1]["nat"],
    "final_dom": msa_comp_pts[-1]["dom"],
    "final_intl": msa_comp_pts[-1]["intl"],
    "net_change": msa_comp_pts[-1]["nat"] + msa_comp_pts[-1]["dom"] + msa_comp_pts[-1]["intl"],
    "pct_change": (msa_comp_pts[-1]["nat"] + msa_comp_pts[-1]["dom"] + msa_comp_pts[-1]["intl"]) / msa_baseline_2010,
}

P = {
    "geo": geo_data,
    "counties": counties,
    "max_abs_change": max_abs_change,
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC MSA: under-18 decomposition by county</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:28px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:18px; max-width:1500px; line-height:1.5; }
.layout { display:grid; grid-template-columns:600px 1fr; gap:28px; max-width:1500px; align-items:start; }
.map-wrap { background:#fff; border:0.5px solid #e1e2e3; padding:14px; }
.chart-wrap { background:#fff; border:0.5px solid #e1e2e3; padding:18px 22px; min-height:580px; }
.legend { display:flex; gap:18px; align-items:center; margin-top:10px; font-size:12px; color:#7F7570; }
.swatch { display:inline-block; width:14px; height:11px; border:0.5px solid rgba(0,0,0,.15); vertical-align:middle; margin-right:5px; }
.legend-bar { display:inline-block; width:200px; height:12px; background:linear-gradient(to right, #F4743B, #FBCAB5, #f5f1ed, #BCE8FF, #0BB4FF); }
.chart-hdr { display:flex; justify-content:space-between; align-items:baseline; gap:10px; margin-bottom:4px; }
.chart-name { font-size:22px; font-weight:500; }
.chart-name.borough { color:#0BB4FF; }
.chart-summary { font-size:13px; color:#7F7570; font-variant-numeric:tabular-nums; }
.chart-totals { font-size:13px; margin-bottom:18px; font-variant-numeric:tabular-nums; }
.chart-totals .nat { color:#67A275; }
.chart-totals .dom { color:#F4743B; }
.chart-totals .intl { color:#0BB4FF; }
.chart-totals .net { color:#3D3733; font-weight:500; }
.county-label { font-size:9.5px; fill:#3D3733; font-weight:500; pointer-events:none; }
.county-label.light { fill:#fff; }
.source { color:#7F7570; font-size:12px; max-width:1500px; margin-top:24px; line-height:1.5; }
.chart-bands-legend { display:flex; gap:14px; font-size:11.5px; color:#3D3733; margin-top:12px; flex-wrap:wrap; }
</style></head>
<body>
<h1>NYC MSA under-18: hover a county to decompose the change (% change coloring)</h1>
<div class="sub">Map shaded by <strong>percent change</strong> in under-18 since 2010 (net change / 2010 baseline). Blue = grew; red = shrank. Outer-ring counties stand out here even though their absolute losses are small. Hover any county to see the trajectory 1980-2024 and the cumulative decomposition since 2010 (natural change, domestic migration, international migration). Default view shows the MSA-aggregate decomposition.</div>

<div class="layout">
  <div class="map-wrap">
    <svg id="map" viewBox="0 0 600 540" width="100%" height="auto"></svg>
    <div class="legend">
      <span>−__MAX_PCT__%</span>
      <span class="legend-bar"></span>
      <span>+__MAX_PCT__%</span>
      <span style="margin-left:20px;font-size:11px">(% change in under-18 since 2010)</span>
    </div>
  </div>
  <div class="chart-wrap">
    <div class="chart-hdr">
      <div class="chart-name" id="chart-name"></div>
      <div class="chart-summary" id="chart-summary"></div>
    </div>
    <div class="chart-totals" id="chart-totals"></div>
    <svg id="chart" viewBox="0 0 740 440" width="100%" height="auto"></svg>
    <div class="chart-bands-legend">
      <span><span class="swatch" style="background:#C6DCCB"></span>Cumulative natural change</span>
      <span><span class="swatch" style="background:#FBCAB5"></span>Cumulative domestic net migration</span>
      <span><span class="swatch" style="background:#BCE8FF"></span>Cumulative international net migration</span>
      <span><span style="display:inline-block;width:14px;height:0;border-top:2px solid #3D3733;vertical-align:middle;margin-right:5px;"></span>Under-18 level</span>
      <span><span style="display:inline-block;width:14px;height:0;border-top:1px dashed #9D958F;vertical-align:middle;margin-right:5px;"></span>2010 baseline</span>
    </div>
  </div>
</div>

<div class="source">
Source: Stitched PEP 1980-2024 (pe-02 intercensal 1980-1989 + cany 1990-1999 + co-est00int 2000-2010 + cc-est2020int 2010-2020 + V2024 2020-2024) anchored to NHGIS Decennial counts. Components 2010-2024: NCHS WONDER Natality births; aging-out ≈ AGE1417 × 0.25; deaths ≈ 40/100K × U18; net mig as residual. International U18 share = 0.20 (national ACS); domestic = residual.
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const counties = P.counties;
const maxAbs = P.max_abs_change;

// --- MAP ---
const mapSvg = d3.select('#map');
const mapW = 600, mapH = 540;
const proj = d3.geoMercator().fitExtent([[10,10],[mapW-10,mapH-10]], P.geo);
const path = d3.geoPath(proj);

const colorScale = d3.scaleLinear()
  .domain([-maxAbs, -maxAbs/3, 0, maxAbs/3, maxAbs])
  .range(['#F4743B', '#FBCAB5', '#f5f1ed', '#BCE8FF', '#0BB4FF'])
  .clamp(true);

const fmtK = n => {
  if (n === 0) return '0';
  const abs = Math.abs(n);
  if (abs >= 1000) return (n >= 0 ? '+' : '') + (n/1000).toFixed(0) + 'K';
  return (n >= 0 ? '+' : '') + n.toString();
};
const fmtKplain = n => Math.abs(n) >= 1000 ? (n/1000).toFixed(0) + 'K' : n.toString();

const paths = mapSvg.append('g').selectAll('path').data(P.geo.features).join('path')
  .attr('d', path)
  .attr('fill', d => {
    const c = counties[d.properties.county_fips];
    return c ? colorScale(c.pct_change) : '#eee';
  })
  .attr('stroke', '#fff').attr('stroke-width', 1)
  .style('cursor', 'pointer')
  .on('mouseenter', function(_, d) {
    const fips = d.properties.county_fips;
    d3.selectAll('.county-label').style('font-weight', dd => dd.properties.county_fips === fips ? '700' : '500');
    paths.attr('stroke-width', dd => dd.properties.county_fips === fips ? 2.5 : 1)
         .attr('stroke', dd => dd.properties.county_fips === fips ? '#3D3733' : '#fff');
    renderChart(fips);
  });

// County labels (centered, small)
mapSvg.append('g').selectAll('text').data(P.geo.features).join('text')
  .attr('class', d => {
    const c = counties[d.properties.county_fips];
    const intensity = c ? Math.abs(c.pct_change) / maxAbs : 0;
    return 'county-label' + (intensity > 0.55 ? ' light' : '');
  })
  .attr('transform', d => `translate(${path.centroid(d)})`)
  .attr('text-anchor', 'middle')
  .attr('dy', '0.32em')
  .text(d => {
    const fips = d.properties.county_fips;
    return counties[fips] ? counties[fips].name : '';
  });

// --- CHART ---
const chartSvg = d3.select('#chart');
const chartW = 740, chartH = 440, cM = {t: 18, r: 20, b: 28, l: 50};

function renderChart(fips) {
  const c = counties[fips] || counties['_MSA'];
  chartSvg.selectAll('*').remove();

  // Header
  d3.select('#chart-name')
    .text(c.name)
    .attr('class', 'chart-name' + (c.is_borough ? ' borough' : ''));
  d3.select('#chart-summary').text(`${fmtKplain(c.level_1980)} (1980) → ${fmtKplain(c.level_2010)} (2010) → ${fmtKplain(c.level_2024)} (2024)`);
  d3.select('#chart-totals').html(
    `Net change since 2010: <span class="net">${fmtK(c.net_change)}</span>  =  ` +
    `<span class="nat">natural ${fmtK(c.final_nat)}</span>  ` +
    `<span class="dom">domestic mig ${fmtK(c.final_dom)}</span>  ` +
    `<span class="intl">intl mig ${fmtK(c.final_intl)}</span>`
  );

  // Y range: include line + stacked band extents
  let ymin = Infinity, ymax = -Infinity;
  c.level.forEach(p => { ymin = Math.min(ymin, p.v); ymax = Math.max(ymax, p.v); });
  c.comp.forEach(p => {
    const pos = c.baseline_2010 + Math.max(0, p.nat) + Math.max(0, p.dom) + Math.max(0, p.intl);
    const neg = c.baseline_2010 + Math.min(0, p.nat) + Math.min(0, p.dom) + Math.min(0, p.intl);
    ymin = Math.min(ymin, neg);
    ymax = Math.max(ymax, pos);
  });
  const yPad = (ymax - ymin) * 0.08;

  const x = d3.scaleLinear().domain([1980, 2024]).range([cM.l, chartW - cM.r]);
  const y = d3.scaleLinear().domain([ymin - yPad, ymax + yPad]).range([chartH - cM.b, cM.t]);

  // Y-axis gridlines/labels (every 50K or appropriate increment)
  const yRange = ymax - ymin;
  const step = yRange > 400000 ? 100000 : yRange > 100000 ? 50000 : yRange > 30000 ? 10000 : 5000;
  const yTicks = [];
  const tickMin = Math.floor((ymin - yPad) / step) * step;
  const tickMax = Math.ceil((ymax + yPad) / step) * step;
  for (let v = tickMin; v <= tickMax; v += step) yTicks.push(v);
  yTicks.forEach(v => {
    chartSvg.append('line')
      .attr('x1', cM.l).attr('x2', chartW - cM.r)
      .attr('y1', y(v)).attr('y2', y(v))
      .attr('stroke', '#EEEEE6').attr('stroke-width', 0.5);
    chartSvg.append('text')
      .attr('x', cM.l - 8).attr('y', y(v))
      .attr('text-anchor', 'end').attr('dominant-baseline', 'middle')
      .style('font-size', '11px').style('fill', '#9D958F')
      .text(v >= 1000 ? (v/1000) + 'K' : v);
  });

  // X-axis ticks
  const tickYears = [1980, 1990, 2000, 2010, 2020, 2024];
  tickYears.forEach(yr => {
    chartSvg.append('text')
      .attr('x', x(yr)).attr('y', chartH - 8)
      .attr('text-anchor', yr === 1980 ? 'start' : (yr === 2024 ? 'end' : 'middle'))
      .style('font-size', '11px').style('fill', '#9D958F')
      .text("'" + String(yr).slice(2));
  });

  // 2010 baseline dashed horizontal
  chartSvg.append('line')
    .attr('x1', x(2010)).attr('x2', x(2024))
    .attr('y1', y(c.baseline_2010)).attr('y2', y(c.baseline_2010))
    .attr('stroke', '#9D958F').attr('stroke-width', 0.6)
    .attr('stroke-dasharray', '3,3');

  // 2010 vertical separator
  chartSvg.append('line')
    .attr('x1', x(2010)).attr('x2', x(2010))
    .attr('y1', cM.t).attr('y2', chartH - cM.b)
    .attr('stroke', '#9D958F').attr('stroke-width', 0.5)
    .attr('stroke-dasharray', '1,2');

  // Stacked component bands (pos above baseline, neg below)
  const COMPS = [
    {key: 'nat', color: '#C6DCCB'},
    {key: 'dom', color: '#FBCAB5'},
    {key: 'intl', color: '#BCE8FF'},
  ];
  COMPS.forEach((comp, idx) => {
    const bandPoints = c.comp.map(p => {
      const v = p[comp.key];
      let base = 0;
      for (let i = 0; i < idx; i++) {
        const prevV = p[COMPS[i].key];
        if ((v >= 0 && prevV > 0) || (v < 0 && prevV < 0)) base += prevV;
      }
      return {y: p.y, low: c.baseline_2010 + base, high: c.baseline_2010 + base + v};
    });
    const area = d3.area()
      .x(d => x(d.y))
      .y0(d => y(d.low))
      .y1(d => y(d.high))
      .curve(d3.curveMonotoneX);
    chartSvg.append('path').datum(bandPoints)
      .attr('fill', comp.color).attr('fill-opacity', 0.85)
      .attr('d', area);
  });

  // Level line (white halo + dark)
  const lineGen = d3.line().x(d => x(d.y)).y(d => y(d.v)).curve(d3.curveMonotoneX);
  chartSvg.append('path').datum(c.level)
    .attr('fill', 'none').attr('stroke', '#F6F7F3')
    .attr('stroke-width', 4.5).attr('d', lineGen);
  const colr = c.is_borough ? '#0BB4FF' : '#3D3733';
  chartSvg.append('path').datum(c.level)
    .attr('fill', 'none').attr('stroke', colr)
    .attr('stroke-width', 2).attr('d', lineGen);

  // Endpoint dots
  chartSvg.append('circle').attr('cx', x(c.level[0].y)).attr('cy', y(c.level[0].v))
    .attr('r', 3).attr('fill', colr);
  const endL = c.level[c.level.length - 1];
  chartSvg.append('circle').attr('cx', x(endL.y)).attr('cy', y(endL.v))
    .attr('r', 3.5).attr('fill', colr);
}

// Initial render: MSA aggregate
renderChart('_MSA');
</script>
</body></html>
"""

html = (template.replace("__DATA__", json.dumps(P))
                .replace("__MAX_PCT__", f"{int(round(max_abs_change*100))}"))
out_path = OUT / "nyc_decomposition_map_pct.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.2f} MB)")
print(f"Max abs % change: {max_abs_change*100:.1f}%")
# Print sorted % changes for inspection
print("\nPer-county % change 2010→2024:")
for fips, c in sorted(counties.items(), key=lambda kv: kv[1].get('pct_change', 0)):
    if fips == '_MSA': continue
    print(f"  {c['name']:24s} {c['pct_change']*100:+6.1f}%   (net {c['net_change']:+,})")

