"""
Combined per-county chart: 1980-2024 under-18 trajectory plus 2010-2024
decomposition into cumulative components.

Each panel:
  X-axis: 1980 to 2024
  Y-axis: absolute under-18 level
  1980-2009: just the black trajectory line (no decomposition — pre-WONDER births era)
  2010 horizontal dashed reference line at the 2010 level
  2010-2024:
    - Above the 2010 baseline: positive cumulative contributions stacked
    - Below the 2010 baseline: negative cumulative contributions stacked
    - Black line continues, showing the actual trajectory
    - Net change at any year = top of positive stack minus bottom of negative stack

Components shown for 2010-2024:
  Green (#C6DCCB) = cumulative natural change (births − aging-out − deaths)
  Red (#FBCAB5)   = cumulative domestic net migration
  Blue (#BCE8FF)  = cumulative international net migration

Inputs:
  data/nyc_county_under18_pep_seamless.csv         (1980-2024 levels)
  data/nyc_county_under18_decomposition.csv        (annual components 2010-2024)

Output: outputs/nyc_under18_combined.html
"""
import json
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

# Load level data 1980-2024
level = pd.read_csv(DATA / "nyc_county_under18_pep_seamless.csv",
                    dtype={"county_fips": str})

# Load decomposition 2010-2024 (annual)
decomp = pd.read_csv(DATA / "nyc_county_under18_decomposition.csv",
                     dtype={"county_fips": str})

# Order by 2024 stock (largest first) for nicer layout
order = (level[level["year"] == 2024]
         .sort_values("under18", ascending=False)["county_fips"].tolist())

panels = []
for fips in order:
    lvl = level[level["county_fips"] == fips].sort_values("year")
    dec = decomp[decomp["county_fips"] == fips].sort_values("interval_start")

    # Level series for 1980-2024
    level_pts = [{"y": int(r.year), "v": int(r.under18)} for r in lvl.itertuples()]
    baseline_2010 = next(p["v"] for p in level_pts if p["y"] == 2010)

    # Build cumulative components for 2010-2024 (starting from 0 at 2010)
    cum_nat, cum_dom, cum_intl = 0, 0, 0
    comp_pts = [{"y": 2010, "nat": 0, "dom": 0, "intl": 0}]
    for _, r in dec.iterrows():
        cum_nat += int(r["natural_change"])
        cum_dom += int(r["net_mig_u18_dom"])
        cum_intl += int(r["net_mig_u18_intl"])
        comp_pts.append({
            "y": int(r["interval_start"]) + 1,  # interval end year
            "nat": cum_nat, "dom": cum_dom, "intl": cum_intl,
        })

    # Y-axis range: must include line trajectory AND the full vertical extent of
    # stacked component bands (positive stack top, negative stack bottom).
    all_levels = [p["v"] for p in level_pts]
    for c in comp_pts:
        pos_top = baseline_2010 + sum(max(0, c[k]) for k in ("nat", "dom", "intl"))
        neg_bot = baseline_2010 + sum(min(0, c[k]) for k in ("nat", "dom", "intl"))
        all_levels.extend([pos_top, neg_bot])

    panels.append({
        "fips": fips, "name": NAMES[fips],
        "is_borough": fips in BOROUGHS,
        "level": level_pts,
        "baseline_2010": baseline_2010,
        "comp": comp_pts,
        "ymin": min(all_levels), "ymax": max(all_levels),
        "level_1980": level_pts[0]["v"],
        "level_2024": level_pts[-1]["v"],
        "level_2010": baseline_2010,
        "final_nat": comp_pts[-1]["nat"],
        "final_dom": comp_pts[-1]["dom"],
        "final_intl": comp_pts[-1]["intl"],
    })

all_years = sorted({p["y"] for panel in panels for p in panel["level"]})

# Shared y-axis: max across all panels (zero floor, round to nice number)
global_ymax = max(p["ymax"] for p in panels)
global_ymin = min(0, min(p["ymin"] for p in panels))
# Pad and round to nearest 100K
import math
global_ymax_padded = math.ceil(global_ymax / 100000) * 100000
global_ymin_padded = math.floor(global_ymin / 100000) * 100000 if global_ymin < 0 else 0

P = {
    "panels": panels,
    "x_min": min(all_years), "x_max": max(all_years),
    "global_ymin": global_ymin_padded,
    "global_ymax": global_ymax_padded,
}

print(f"\nGlobal y-axis range: {global_ymin_padded:,} to {global_ymax_padded:,}")

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC MSA: under-18 1980–2024 with decomposition since 2010</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:28px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:18px; max-width:1500px; line-height:1.5; }
.legend { display:flex; gap:22px; align-items:center; flex-wrap:wrap; font-size:12.5px; color:#3D3733; margin-bottom:18px; }
.swatch { display:inline-block; width:16px; height:12px; vertical-align:middle; margin-right:6px; border:0.5px solid rgba(0,0,0,.15); }
.grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:14px 18px; max-width:1500px; }
.panel { background:#fff; border:0.5px solid #e1e2e3; padding:10px 12px 12px; }
.panel-hdr { display:flex; align-items:baseline; justify-content:space-between; gap:6px; margin-bottom:2px; }
.cname { font-size:13.5px; font-weight:500; }
.cname.borough { color:#0BB4FF; }
.summary { font-size:10.5px; color:#9D958F; margin-bottom:1px; font-variant-numeric:tabular-nums; }
.summary .nat { color:#67A275; }
.summary .dom { color:#F4743B; }
.summary .intl { color:#0BB4FF; }
.source { color:#7F7570; font-size:12px; max-width:1500px; margin-top:24px; line-height:1.5; }
</style></head>
<body>
<h1>NYC MSA under-18 by county: 45-year trajectory + decomposition since 2010</h1>
<div class="sub">All panels share the same absolute y-axis (0 to __YMAX__ kids) so magnitudes are directly comparable: Brooklyn dwarfs Putnam by 30×. Black line shows under-18 absolute level 1980–2024. From the 2010 baseline (dashed horizontal), colored bands stack out to show how each component of change has contributed since: natural change (births − aging-out − deaths), domestic net migration, international net migration. Positive contributions stack above the baseline; negative contributions below. Pre-2010 data is just the level line (no component data before NCHS WONDER births era).</div>

<div class="legend">
  <span><span class="swatch" style="background:#C6DCCB"></span>Cumulative natural change (births − aging out)</span>
  <span><span class="swatch" style="background:#FBCAB5"></span>Cumulative domestic net migration</span>
  <span><span class="swatch" style="background:#BCE8FF"></span>Cumulative international net migration</span>
  <span><span style="display:inline-block;width:16px;height:0;border-top:2px solid #3D3733;vertical-align:middle;margin-right:6px;"></span>Under-18 level</span>
  <span><span style="display:inline-block;width:16px;height:0;border-top:1px dashed #9D958F;vertical-align:middle;margin-right:6px;"></span>2010 baseline</span>
</div>

<div class="grid" id="grid"></div>

<div class="source">
Sources: Stitched PEP (1980-2024 levels): pe-02 intercensal 1980-1989 + cany9Y postcensal 1990-1999 + co-est00int 2000-2010 + cc-est2020int 2010-2020 + V2024 2020-2024, with per-county anchoring to NHGIS Decennial counts at 1980/1990/2000/2010 and intercensal April-2020. Components 2010-2024: NCHS WONDER Natality births (county); aging-out ≈ AGE1417 × 0.25; deaths ≈ 40/100K × U18 stock; net migration as residual (ΔU18 − natural change); intl share = PEP intl × 0.20 (ACS national share under-18), domestic = residual.
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const grid = d3.select('#grid');

const W = 280, H = 160, M = {t:8, r:8, b:18, l:6};
const iw = W - M.l - M.r;

const x = d3.scaleLinear().domain([P.x_min, P.x_max]).range([M.l, M.l + iw]);
const fmtK = n => {
  if (n === 0) return '0';
  const abs = Math.abs(n);
  if (abs >= 1000) return (n >= 0 ? '+' : '') + (n/1000).toFixed(0) + 'K';
  return (n >= 0 ? '+' : '') + n.toString();
};
const fmtKplain = n => {
  const abs = Math.abs(n);
  if (abs >= 1000) return (n/1000).toFixed(0) + 'K';
  return n.toString();
};

P.panels.forEach(panel => {
  const cell = grid.append('div').attr('class','panel');
  const hdr = cell.append('div').attr('class','panel-hdr');
  hdr.append('div').attr('class','cname' + (panel.is_borough ? ' borough':''))
     .text(panel.name);
  hdr.append('div').attr('class','summary')
     .text(`${fmtKplain(panel.level_1980)} → ${fmtKplain(panel.level_2024)}`);

  cell.append('div').attr('class','summary')
      .html(`since '10: <span class="nat">nat ${fmtK(panel.final_nat)}</span>  ` +
            `<span class="dom">dom ${fmtK(panel.final_dom)}</span>  ` +
            `<span class="intl">intl ${fmtK(panel.final_intl)}</span>`);

  // SHARED y-axis across all panels — magnitudes directly comparable.
  const y = d3.scaleLinear()
    .domain([P.global_ymin, P.global_ymax])
    .range([H - M.b, M.t]);

  const svg = cell.append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width','100%').attr('height',H);

  // 2010 baseline horizontal dashed line
  svg.append('line')
    .attr('x1', x(2010)).attr('x2', x(P.x_max))
    .attr('y1', y(panel.baseline_2010)).attr('y2', y(panel.baseline_2010))
    .attr('stroke', '#9D958F').attr('stroke-width', 0.6)
    .attr('stroke-dasharray', '2,2');

  // X-axis ticks (just years)
  const tickYears = [P.x_min, 1990, 2000, 2010, 2020, P.x_max];
  svg.append('g').selectAll('text').data(tickYears).join('text')
    .attr('x', d => x(d))
    .attr('y', H - 4)
    .attr('text-anchor', d => d === P.x_min ? 'start' : (d === P.x_max ? 'end' : 'middle'))
    .style('font-size', '9.5px').style('fill', '#9D958F')
    .text(d => "'" + String(d).slice(2));

  // Y-axis tick reference lines + labels at every 200K on shared scale
  const yTicks = [];
  for (let v = 0; v <= P.global_ymax; v += 200000) yTicks.push(v);
  yTicks.forEach(v => {
    svg.append('line')
      .attr('x1', M.l).attr('x2', M.l + iw)
      .attr('y1', y(v)).attr('y2', y(v))
      .attr('stroke', '#EEEEE6').attr('stroke-width', 0.5);
    svg.append('text')
      .attr('x', M.l + 2).attr('y', y(v) - 2)
      .style('font-size', '8.5px').style('fill', '#BAB3AC')
      .text(v === 0 ? '0' : (v/1000) + 'K');
  });

  // Per-component band: each component gets a colored region showing its FULL
  // signed contribution stacked separately from same-sign sibling components.
  // Positive contributions stack upward from baseline, negative downward.
  // Line is NET (= baseline + sum of all components) — it falls inside the
  // dominant-sign stack when components partially offset.
  const COMPS = [
    {key: 'nat', color: '#C6DCCB'},
    {key: 'dom', color: '#FBCAB5'},
    {key: 'intl', color: '#BCE8FF'},
  ];

  COMPS.forEach((comp, idx) => {
    const bandPoints = panel.comp.map(c => {
      const v = c[comp.key];
      // Base = stack of preceding same-sign components
      let base = 0;
      for (let i = 0; i < idx; i++) {
        const prevV = c[COMPS[i].key];
        if ((v >= 0 && prevV > 0) || (v < 0 && prevV < 0)) {
          base += prevV;
        }
      }
      return {y: c.y,
              low: panel.baseline_2010 + base,
              high: panel.baseline_2010 + base + v};
    });

    const area = d3.area()
      .x(d => x(d.y))
      .y0(d => y(d.low))
      .y1(d => y(d.high))
      .curve(d3.curveMonotoneX);

    svg.append('path').datum(bandPoints)
      .attr('fill', comp.color)
      .attr('fill-opacity', 0.85)
      .attr('d', area);
  });

  // Under-18 level line 1980-2024 (full series) — draw white halo then dark line
  // on top so it reads clearly through the colored bands.
  const colr = panel.is_borough ? '#0BB4FF' : '#3D3733';
  const line = d3.line()
    .x(d => x(d.y))
    .y(d => y(d.v))
    .curve(d3.curveMonotoneX);
  svg.append('path').datum(panel.level)
    .attr('fill', 'none').attr('stroke', '#F6F7F3')
    .attr('stroke-width', 3.6).attr('d', line);
  svg.append('path').datum(panel.level)
    .attr('fill', 'none').attr('stroke', colr)
    .attr('stroke-width', 1.7).attr('d', line);

  // 2010 vertical reference (subtle)
  svg.append('line')
    .attr('x1', x(2010)).attr('x2', x(2010))
    .attr('y1', M.t).attr('y2', H - M.b)
    .attr('stroke', '#9D958F').attr('stroke-width', 0.5)
    .attr('stroke-dasharray', '1,2');

  // Endpoint dots
  svg.append('circle').attr('cx', x(panel.level[0].y)).attr('cy', y(panel.level[0].v))
    .attr('r', 1.8).attr('fill', colr);
  const endL = panel.level[panel.level.length - 1];
  svg.append('circle').attr('cx', x(endL.y)).attr('cy', y(endL.v))
    .attr('r', 2.2).attr('fill', colr);
});
</script>
</body></html>
"""

html = (template.replace("__DATA__", json.dumps(P))
                .replace("__YMAX__", f"{global_ymax_padded//1000}K"))
out_path = OUT / "nyc_under18_combined.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.2f} MB)")
