"""
Interactive NYC MSA map + decomposition chart — variant with a SELECTABLE
START YEAR (slider 1980-2023). End year fixed at 2024.

- Map left: each county colored by % change in under-18 between selected
  start year and 2024. Color scale auto-rescales to current data range.
- Chart right: hover a county (or default to MSA aggregate). Level trajectory
  is the 45-year line. For start years 2010+, cumulative decomposition bands
  (natural change / domestic mig / intl mig) re-anchor at the chosen year.
  For start years <2010 (where component data doesn't exist), bands are
  hidden — only the level line plus the start-year baseline are shown.

Output: outputs/nyc_decomposition_map_pct_interactive.html
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

g = json.loads((GEO / "metro10_counties.geojson").read_text())
nyc_features = [f for f in g["features"] if f["properties"].get("cbsa_code") == 35620]
geo_data = {"type": "FeatureCollection", "features": nyc_features}

decomp = pd.read_csv(DATA / "nyc_county_under18_decomposition.csv", dtype={"county_fips": str})
level = pd.read_csv(DATA / "nyc_county_under18_pep_seamless.csv", dtype={"county_fips": str})

counties = {}
for fips in NYC_FIPS:
    lvl = level[level["county_fips"] == fips].sort_values("year")
    dec = decomp[decomp["county_fips"] == fips].sort_values("interval_start")

    # Annual level points 1980-2024 — year + value, plus dict for quick lookup
    level_pts = [{"y": int(r.year), "v": int(r.under18)} for r in lvl.itertuples()]
    level_by_year = {p["y"]: p["v"] for p in level_pts}

    # Annual component deltas for each interval (2010..2023 → 2011..2024).
    # Store per-year increments so JS can re-anchor cumulative sums.
    annual = []
    for _, r in dec.iterrows():
        annual.append({
            "y_to": int(r["interval_start"]) + 1,  # year-end
            "nat": float(r["natural_change"]),
            "dom": float(r["net_mig_u18_dom"]),
            "intl": float(r["net_mig_u18_intl"]),
        })

    counties[fips] = {
        "name": NAMES[fips],
        "is_borough": fips in BOROUGHS,
        "level": level_pts,
        "level_by_year": level_by_year,
        "annual": annual,
    }

# MSA aggregate
import collections
msa_level_by_year = collections.defaultdict(int)
for c in counties.values():
    for p in c["level"]:
        msa_level_by_year[p["y"]] += p["v"]
msa_level_pts = [{"y": y, "v": v} for y, v in sorted(msa_level_by_year.items())]

msa_annual_by_year = collections.defaultdict(lambda: {"nat": 0.0, "dom": 0.0, "intl": 0.0})
for c in counties.values():
    for a in c["annual"]:
        msa_annual_by_year[a["y_to"]]["nat"] += a["nat"]
        msa_annual_by_year[a["y_to"]]["dom"] += a["dom"]
        msa_annual_by_year[a["y_to"]]["intl"] += a["intl"]
msa_annual = [{"y_to": y, **v} for y, v in sorted(msa_annual_by_year.items())]

counties["_MSA"] = {
    "name": "NYC MSA (all 22 counties)",
    "is_borough": False,
    "level": msa_level_pts,
    "level_by_year": dict(msa_level_by_year),
    "annual": msa_annual,
}

P = {"geo": geo_data, "counties": counties,
     "decomp_start": 2010, "year_end": 2024,
     "slider_min": 1980, "slider_max": 2023}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC MSA under-18: decomposition by county (interactive baseline)</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:28px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:14px; max-width:1500px; line-height:1.5; }
.controls { display:flex; align-items:center; gap:16px; margin-bottom:16px; max-width:1500px; }
.controls label { font-size:13px; color:#7F7570; }
#baselineYearLabel { font-size:18px; font-weight:500; color:#3D3733; min-width:54px; display:inline-block; }
input[type=range] { -webkit-appearance:none; appearance:none; height:4px; background:#DADFCE; border-radius:2px; flex:1; max-width:520px; cursor:pointer; }
input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; appearance:none; width:18px; height:18px; border-radius:50%; background:#0BB4FF; cursor:pointer; border:2px solid #F6F7F3; box-shadow:0 0 0 1px #0BB4FF; }
input[type=range]::-moz-range-thumb { width:18px; height:18px; border-radius:50%; background:#0BB4FF; cursor:pointer; border:2px solid #F6F7F3; box-shadow:0 0 0 1px #0BB4FF; }
.note { font-size:12.5px; color:#7F7570; }
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
.chart-totals .muted { color:#9D958F; font-style:italic; }
.county-label { font-size:9.5px; fill:#3D3733; font-weight:500; pointer-events:none; }
.county-label.light { fill:#fff; }
.source { color:#7F7570; font-size:12px; max-width:1500px; margin-top:24px; line-height:1.5; }
.chart-bands-legend { display:flex; gap:14px; font-size:11.5px; color:#3D3733; margin-top:12px; flex-wrap:wrap; }
.chart-bands-legend.dim { opacity:0.35; }
</style></head>
<body>
<h1>NYC MSA under-18: change since selected baseline year (interactive)</h1>
<div class="sub">Map shaded by <strong>percent change</strong> in under-18 between a chosen baseline year and 2024 (drag the slider). End year fixed at 2024. Hover any county to see the full 1980-2024 trajectory and the cumulative decomposition into natural change, domestic migration, and international migration (when the chosen baseline is 2010 or later — component data doesn't exist pre-2010). Default view is the MSA aggregate.</div>

<div class="controls">
  <label for="baselineSlider">Baseline year:</label>
  <span id="baselineYearLabel">2010</span>
  <input type="range" id="baselineSlider" min="__SLIDER_MIN__" max="__SLIDER_MAX__" step="1" value="2010">
  <span class="note">→ 2024</span>
</div>

<div class="layout">
  <div class="map-wrap">
    <svg id="map" viewBox="0 0 600 540" width="100%" height="auto"></svg>
    <div class="legend">
      <span id="legend-min">−__INIT_LEGEND__%</span>
      <span class="legend-bar"></span>
      <span id="legend-max">+__INIT_LEGEND__%</span>
      <span style="margin-left:20px;font-size:11px">% change in under-18, baseline → 2024</span>
    </div>
  </div>
  <div class="chart-wrap">
    <div class="chart-hdr">
      <div class="chart-name" id="chart-name"></div>
      <div class="chart-summary" id="chart-summary"></div>
    </div>
    <div class="chart-totals" id="chart-totals"></div>
    <svg id="chart" viewBox="0 0 740 440" width="100%" height="auto"></svg>
    <div class="chart-bands-legend" id="bands-legend">
      <span><span class="swatch" style="background:#C6DCCB"></span>Cumulative natural change</span>
      <span><span class="swatch" style="background:#FBCAB5"></span>Cumulative domestic net migration</span>
      <span><span class="swatch" style="background:#BCE8FF"></span>Cumulative international net migration</span>
      <span><span style="display:inline-block;width:14px;height:0;border-top:2px solid #3D3733;vertical-align:middle;margin-right:5px;"></span>Under-18 level</span>
      <span><span style="display:inline-block;width:14px;height:0;border-top:1px dashed #9D958F;vertical-align:middle;margin-right:5px;"></span>Baseline-year level</span>
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
const DECOMP_START = P.decomp_start;
const YEAR_END = P.year_end;

let currentFips = '_MSA';
let currentBaseline = 2010;

// --- MAP ---
const mapSvg = d3.select('#map');
const mapW = 600, mapH = 540;
const proj = d3.geoMercator().fitExtent([[10,10],[mapW-10,mapH-10]], P.geo);
const path = d3.geoPath(proj);

const colorScale = d3.scaleLinear()
  .range(['#F4743B', '#FBCAB5', '#f5f1ed', '#BCE8FF', '#0BB4FF'])
  .clamp(true);

function pctChange(fips, baseline) {
  const c = counties[fips];
  if (!c || !c.level_by_year[baseline] || !c.level_by_year[YEAR_END]) return 0;
  return (c.level_by_year[YEAR_END] - c.level_by_year[baseline]) / c.level_by_year[baseline];
}

function recomputeColorScale(baseline) {
  let maxAbs = 0;
  P.geo.features.forEach(f => {
    const fips = f.properties.county_fips;
    if (!counties[fips]) return;
    const pc = pctChange(fips, baseline);
    if (Math.abs(pc) > maxAbs) maxAbs = Math.abs(pc);
  });
  if (maxAbs < 0.01) maxAbs = 0.01;
  colorScale.domain([-maxAbs, -maxAbs/3, 0, maxAbs/3, maxAbs]);
  return maxAbs;
}

const fmtK = n => {
  if (Math.round(n) === 0) return '0';
  const abs = Math.abs(n);
  if (abs >= 1000) return (n >= 0 ? '+' : '') + (n/1000).toFixed(0) + 'K';
  return (n >= 0 ? '+' : '') + Math.round(n).toString();
};
const fmtKplain = n => Math.abs(n) >= 1000 ? (n/1000).toFixed(0) + 'K' : Math.round(n).toString();

let paths;
function drawMap() {
  if (!paths) {
    paths = mapSvg.append('g').selectAll('path').data(P.geo.features).join('path')
      .attr('d', path)
      .attr('stroke', '#fff').attr('stroke-width', 1)
      .style('cursor', 'pointer')
      .on('mouseenter', function(_, d) {
        const fips = d.properties.county_fips;
        if (!counties[fips]) return;
        currentFips = fips;
        d3.selectAll('.county-label').style('font-weight', dd => dd.properties.county_fips === fips ? '700' : '500');
        paths.attr('stroke-width', dd => dd.properties.county_fips === fips ? 2.5 : 1)
             .attr('stroke', dd => dd.properties.county_fips === fips ? '#3D3733' : '#fff');
        renderChart();
      });

    mapSvg.append('g').selectAll('text').data(P.geo.features).join('text')
      .attr('class', d => 'county-label')
      .attr('transform', d => `translate(${path.centroid(d)})`)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.32em')
      .text(d => {
        const fips = d.properties.county_fips;
        return counties[fips] ? counties[fips].name : '';
      });
  }
  paths.attr('fill', d => {
    const fips = d.properties.county_fips;
    if (!counties[fips]) return '#eee';
    return colorScale(pctChange(fips, currentBaseline));
  });
  // Recolor labels: if county color intensity is high, switch label to white
  const maxAbs = Math.max(...colorScale.domain().map(Math.abs));
  mapSvg.selectAll('g').selectAll('text.county-label').attr('class', d => {
    const fips = d.properties.county_fips;
    if (!counties[fips]) return 'county-label';
    const intensity = Math.abs(pctChange(fips, currentBaseline)) / (maxAbs || 1);
    return 'county-label' + (intensity > 0.55 ? ' light' : '');
  });
}

// --- CHART ---
const chartSvg = d3.select('#chart');
const chartW = 740, chartH = 440, cM = {t: 18, r: 20, b: 28, l: 50};

function cumulativeFrom(c, baseline) {
  // Sum annual components from year > baseline through 2024.
  let cumNat = 0, cumDom = 0, cumIntl = 0;
  const pts = [{y: baseline, nat: 0, dom: 0, intl: 0}];
  c.annual.forEach(a => {
    if (a.y_to > baseline) {
      cumNat += a.nat; cumDom += a.dom; cumIntl += a.intl;
      pts.push({y: a.y_to, nat: cumNat, dom: cumDom, intl: cumIntl});
    }
  });
  return pts;
}

function renderChart() {
  const c = counties[currentFips] || counties['_MSA'];
  const baseline = currentBaseline;
  const baselineLevel = c.level_by_year[baseline];
  chartSvg.selectAll('*').remove();

  // Header
  d3.select('#chart-name')
    .text(c.name)
    .attr('class', 'chart-name' + (c.is_borough ? ' borough' : ''));
  const level1980 = c.level_by_year[1980];
  const levelEnd = c.level_by_year[YEAR_END];
  d3.select('#chart-summary').text(`${fmtKplain(level1980)} (1980) → ${fmtKplain(baselineLevel)} (${baseline}) → ${fmtKplain(levelEnd)} (2024)`);

  const netChange = levelEnd - baselineLevel;
  const pct = (netChange / baselineLevel) * 100;
  const showBands = baseline >= DECOMP_START;

  if (showBands) {
    const compPts = cumulativeFrom(c, baseline);
    const finalNat = compPts[compPts.length - 1].nat;
    const finalDom = compPts[compPts.length - 1].dom;
    const finalIntl = compPts[compPts.length - 1].intl;
    d3.select('#chart-totals').html(
      `Change ${baseline}→${YEAR_END}: <span class="net">${fmtK(netChange)} (${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%)</span>  =  ` +
      `<span class="nat">natural ${fmtK(finalNat)}</span>  ` +
      `<span class="dom">domestic mig ${fmtK(finalDom)}</span>  ` +
      `<span class="intl">intl mig ${fmtK(finalIntl)}</span>`
    );
    d3.select('#bands-legend').classed('dim', false);
  } else {
    d3.select('#chart-totals').html(
      `Change ${baseline}→${YEAR_END}: <span class="net">${fmtK(netChange)} (${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%)</span>  ` +
      `<span class="muted">(decomposition not available before ${DECOMP_START})</span>`
    );
    d3.select('#bands-legend').classed('dim', true);
  }

  // Y range: include line + (if shown) stacked band extents
  let ymin = Infinity, ymax = -Infinity;
  c.level.forEach(p => { ymin = Math.min(ymin, p.v); ymax = Math.max(ymax, p.v); });
  if (showBands) {
    const compPts = cumulativeFrom(c, baseline);
    compPts.forEach(p => {
      const pos = baselineLevel + Math.max(0, p.nat) + Math.max(0, p.dom) + Math.max(0, p.intl);
      const neg = baselineLevel + Math.min(0, p.nat) + Math.min(0, p.dom) + Math.min(0, p.intl);
      ymin = Math.min(ymin, neg);
      ymax = Math.max(ymax, pos);
    });
  }
  const yPad = (ymax - ymin) * 0.08;

  const x = d3.scaleLinear().domain([1980, YEAR_END]).range([cM.l, chartW - cM.r]);
  const y = d3.scaleLinear().domain([ymin - yPad, ymax + yPad]).range([chartH - cM.b, cM.t]);

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

  const tickYears = [1980, 1990, 2000, 2010, 2020, 2024];
  tickYears.forEach(yr => {
    chartSvg.append('text')
      .attr('x', x(yr)).attr('y', chartH - 8)
      .attr('text-anchor', yr === 1980 ? 'start' : (yr === 2024 ? 'end' : 'middle'))
      .style('font-size', '11px').style('fill', '#9D958F')
      .text("'" + String(yr).slice(2));
  });

  // Baseline-year horizontal dashed (from baseline forward)
  chartSvg.append('line')
    .attr('x1', x(baseline)).attr('x2', x(YEAR_END))
    .attr('y1', y(baselineLevel)).attr('y2', y(baselineLevel))
    .attr('stroke', '#9D958F').attr('stroke-width', 0.6)
    .attr('stroke-dasharray', '3,3');

  // Baseline-year vertical separator
  chartSvg.append('line')
    .attr('x1', x(baseline)).attr('x2', x(baseline))
    .attr('y1', cM.t).attr('y2', chartH - cM.b)
    .attr('stroke', '#F4743B').attr('stroke-width', 1)
    .attr('stroke-dasharray', '3,3');
  chartSvg.append('text')
    .attr('x', x(baseline)).attr('y', cM.t - 4)
    .attr('text-anchor', baseline >= 2018 ? 'end' : (baseline <= 1986 ? 'start' : 'middle'))
    .style('font-size', '10.5px').style('fill', '#F4743B').style('font-weight', '500')
    .text(`baseline ${baseline}`);

  // Stacked component bands (only if baseline >= 2010)
  if (showBands) {
    const compPts = cumulativeFrom(c, baseline);
    const COMPS = [
      {key: 'nat', color: '#C6DCCB'},
      {key: 'dom', color: '#FBCAB5'},
      {key: 'intl', color: '#BCE8FF'},
    ];
    COMPS.forEach((comp, idx) => {
      const bandPoints = compPts.map(p => {
        const v = p[comp.key];
        let base = 0;
        for (let i = 0; i < idx; i++) {
          const prevV = p[COMPS[i].key];
          if ((v >= 0 && prevV > 0) || (v < 0 && prevV < 0)) base += prevV;
        }
        return {y: p.y, low: baselineLevel + base, high: baselineLevel + base + v};
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
  }

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

function updateAll() {
  const maxAbs = recomputeColorScale(currentBaseline);
  const lbl = (maxAbs * 100).toFixed(0);
  d3.select('#legend-min').text(`−${lbl}%`);
  d3.select('#legend-max').text(`+${lbl}%`);
  drawMap();
  renderChart();
}

document.getElementById('baselineSlider').addEventListener('input', e => {
  currentBaseline = +e.target.value;
  document.getElementById('baselineYearLabel').textContent = currentBaseline;
  updateAll();
});

updateAll();
</script>
</body></html>
"""

html = (template.replace("__DATA__", json.dumps(P))
                .replace("__SLIDER_MIN__", str(P["slider_min"]))
                .replace("__SLIDER_MAX__", str(P["slider_max"]))
                .replace("__INIT_LEGEND__", "21"))
out_path = OUT / "nyc_decomposition_map_pct_interactive.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.2f} MB)")
