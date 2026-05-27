"""
Cumulative small-multiples decomposition chart, 2010-2024.

Each panel shows the cumulative running total of the three components from 2010:
  Green area = cumulative natural change (births − aging out − deaths)
  Light red area = cumulative domestic net migration
  Light blue area = cumulative international net migration
  Black line = cumulative ΔU18 (sum of all three)

Positive components stack upward from 0; negative components stack downward.
At any year, distance from 0 to the colored band shows how much that component
has contributed to net under-18 change since 2010.

Input:  data/nyc_county_under18_decomposition.csv
Output: outputs/nyc_under18_decomposition.html
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

df = pd.read_csv(DATA / "nyc_county_under18_decomposition.csv",
                 dtype={"county_fips": str})

order = (df.groupby("county_fips")["u18_start"].mean()
         .sort_values(ascending=False).index.tolist())

panels = []
for fips in order:
    sub = df[df["county_fips"] == fips].sort_values("interval_start").reset_index(drop=True)
    cum_nat = 0
    cum_dom = 0
    cum_intl = 0
    series = [{"y": int(sub["interval_start"].iloc[0]),
               "nat": 0, "dom": 0, "intl": 0, "delta": 0}]
    for _, r in sub.iterrows():
        cum_nat += int(r["natural_change"])
        cum_dom += int(r["net_mig_u18_dom"])
        cum_intl += int(r["net_mig_u18_intl"])
        # The interval (interval_start = y) covers y → y+1; cumulative point is at y+1
        series.append({
            "y": int(r["interval_start"]) + 1,
            "nat": cum_nat, "dom": cum_dom, "intl": cum_intl,
            "delta": cum_nat + cum_dom + cum_intl,
        })
    # Compute y-axis range
    pos = [max(0, s["nat"]) + max(0, s["dom"]) + max(0, s["intl"]) for s in series]
    neg = [min(0, s["nat"]) + min(0, s["dom"]) + min(0, s["intl"]) for s in series]
    panels.append({
        "fips": fips, "name": NAMES[fips],
        "is_borough": fips in BOROUGHS,
        "series": series,
        "ymax": max(pos + [s["delta"] for s in series]),
        "ymin": min(neg + [s["delta"] for s in series]),
        "final_delta": series[-1]["delta"],
        "final_nat": series[-1]["nat"],
        "final_dom": series[-1]["dom"],
        "final_intl": series[-1]["intl"],
    })

all_years = sorted({s["y"] for panel in panels for s in panel["series"]})
P = {
    "panels": panels,
    "x_min": min(all_years), "x_max": max(all_years),
}

template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC MSA: cumulative under-18 decomposition, 2010–2024</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; padding:28px; background:#F6F7F3; font-family:'ABC Oracle Edu',sans-serif; color:#3D3733; }
h1 { font-size:28px; font-weight:500; margin:0 0 6px; }
.sub { color:#7F7570; font-size:15px; margin-bottom:18px; max-width:1500px; line-height:1.5; }
.legend { display:flex; gap:22px; align-items:center; font-size:12.5px; color:#3D3733; margin-bottom:18px; }
.swatch { display:inline-block; width:16px; height:12px; vertical-align:middle; margin-right:6px; border:0.5px solid rgba(0,0,0,.15); }
.grid { display:grid; grid-template-columns:repeat(5, 1fr); gap:14px 18px; max-width:1500px; }
.panel { background:#fff; border:0.5px solid #e1e2e3; padding:10px 12px 12px; }
.panel-hdr { display:flex; align-items:baseline; justify-content:space-between; gap:6px; margin-bottom:2px; }
.cname { font-size:13.5px; font-weight:500; }
.cname.borough { color:#0BB4FF; }
.totals { font-size:10.5px; color:#9D958F; margin-bottom:2px; font-variant-numeric:tabular-nums; }
.totals .nat { color:#67A275; }
.totals .dom { color:#F4743B; }
.totals .intl { color:#0BB4FF; }
.totals .net { color:#3D3733; font-weight:500; }
.source { color:#7F7570; font-size:12px; max-width:1500px; margin-top:24px; line-height:1.5; }
</style></head>
<body>
<h1>NYC MSA: cumulative components of under-18 change since 2010</h1>
<div class="sub">Each panel: cumulative running totals of the three components contributing to under-18 change since July 2010. Positive components stack upward from zero, negative stack downward. Black line = cumulative net ΔU18 (sum of all three). At year Y, the gap between the colored band and zero shows how much that component has added/subtracted to under-18 since 2010. Right-side numbers: net total + each component's cumulative contribution by 2024 (in thousands).</div>

<div class="legend">
  <span><span class="swatch" style="background:#C6DCCB"></span>Cumulative natural change (births − aging out)</span>
  <span><span class="swatch" style="background:#FBCAB5"></span>Cumulative domestic net migration</span>
  <span><span class="swatch" style="background:#BCE8FF"></span>Cumulative international net migration</span>
  <span><span style="display:inline-block;width:16px;height:0;border-top:2px solid #3D3733;vertical-align:middle;margin-right:6px;"></span>Cumulative net ΔU18</span>
</div>

<div class="grid" id="grid"></div>

<div class="source">
Source: PEP intercensal 2010-2020 + V2024 (stock); NCHS WONDER Natality 2007-2024 (county births); PEP county-totals co-est2020-alldata / co-est2024-alldata (migration components). Aging-out ≈ AGE1417 stock × 0.25. Deaths ≈ 40/100K × under-18 stock. International U18 share = 0.20 (national ACS share of intl migrants who are under-18); domestic = total net mig − intl. Putnam County births imputed (suppressed in WONDER pull). Cumulative from July 2010 baseline; values at year Y represent total net change since July 2010.
</div>

<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const grid = d3.select('#grid');

const W = 260, H = 160, M = {t:8, r:8, b:18, l:6};
const iw = W - M.l - M.r;

const x = d3.scaleLinear().domain([P.x_min, P.x_max]).range([M.l, M.l + iw]);
const fmtK = n => {
  if (n === 0) return '0';
  const abs = Math.abs(n);
  if (abs >= 1000) return (n >= 0 ? '+' : '') + (n/1000).toFixed(0) + 'K';
  return (n >= 0 ? '+' : '') + n.toString();
};
const fmtKnone = n => {
  if (n === 0) return '0';
  const abs = Math.abs(n);
  if (abs >= 1000) return (n/1000).toFixed(0) + 'K';
  return n.toString();
};

P.panels.forEach(panel => {
  const cell = grid.append('div').attr('class','panel');
  const hdr = cell.append('div').attr('class','panel-hdr');
  hdr.append('div').attr('class','cname' + (panel.is_borough ? ' borough':''))
     .text(panel.name);
  hdr.append('div').attr('class','totals')
     .html(`<span class="net">${fmtK(panel.final_delta)}</span>`);

  cell.append('div').attr('class','totals')
      .html(`<span class="nat">nat ${fmtK(panel.final_nat)}</span>  ` +
            `<span class="dom">dom ${fmtK(panel.final_dom)}</span>  ` +
            `<span class="intl">intl ${fmtK(panel.final_intl)}</span>`);

  // y-axis: pad so both extremes visible
  const yPad = Math.max(Math.abs(panel.ymin), Math.abs(panel.ymax)) * 1.10;
  const yPadFinal = Math.max(yPad, 2000);
  const y = d3.scaleLinear().domain([-yPadFinal, yPadFinal]).range([H - M.b, M.t]);

  const svg = cell.append('svg').attr('viewBox', `0 0 ${W} ${H}`).attr('width','100%').attr('height',H);

  // Zero line
  svg.append('line').attr('x1', M.l).attr('x2', M.l + iw)
    .attr('y1', y(0)).attr('y2', y(0))
    .attr('stroke', '#9D958F').attr('stroke-width', 0.6);

  // X-axis ticks
  const tickYears = [P.x_min, 2015, 2020, P.x_max];
  svg.append('g').selectAll('text').data(tickYears).join('text')
    .attr('x', d => x(d))
    .attr('y', H - 4)
    .attr('text-anchor', d => d === P.x_min ? 'start' : (d === P.x_max ? 'end' : 'middle'))
    .style('font-size', '9.5px').style('fill', '#9D958F')
    .text(d => "'" + String(d).slice(2));

  // Build stacked areas per year, separating positive and negative stacks.
  // At each point, positive components stack up from 0; negative components stack down.
  // Component order: nat, dom, intl (consistent across panels).
  const COMPS = [
    {key: 'nat', color: '#C6DCCB'},
    {key: 'dom', color: '#FBCAB5'},
    {key: 'intl', color: '#BCE8FF'},
  ];

  // Build per-component stacked bands: [y0, y1] over time
  COMPS.forEach((comp, idx) => {
    // Bottom of this band at year Y = sum of same-sign components ABOVE (for neg) or BELOW (for pos)
    // Simpler approach: for each point in series, compute its band [base, base + v]
    // where base is the running stack of preceding components matching the sign.
    const bandPoints = panel.series.map(s => {
      const v = s[comp.key];
      // Compute base = sum of preceding components with the same sign as v
      let base = 0;
      for (let i = 0; i < idx; i++) {
        const prevV = s[COMPS[i].key];
        if ((v >= 0 && prevV > 0) || (v < 0 && prevV < 0)) {
          base += prevV;
        }
      }
      return {y: s.y, base, top: base + v};
    });

    const area = d3.area()
      .x(d => x(d.y))
      .y0(d => y(d.base))
      .y1(d => y(d.top))
      .curve(d3.curveMonotoneX);

    svg.append('path').datum(bandPoints)
      .attr('fill', comp.color)
      .attr('fill-opacity', 0.88)
      .attr('d', area);
  });

  // Net ΔU18 line
  const line = d3.line()
    .x(d => x(d.y))
    .y(d => y(d.delta))
    .curve(d3.curveMonotoneX);
  svg.append('path').datum(panel.series)
    .attr('fill', 'none').attr('stroke', '#3D3733')
    .attr('stroke-width', 1.4).attr('d', line);
  // End dot
  const endPt = panel.series[panel.series.length - 1];
  svg.append('circle').attr('cx', x(endPt.y)).attr('cy', y(endPt.delta))
    .attr('r', 2.4).attr('fill', '#3D3733');
});
</script>
</body></html>
"""

html = template.replace("__DATA__", json.dumps(P))
out_path = OUT / "nyc_under18_decomposition.html"
out_path.write_text(html)
print(f"Wrote {out_path} ({out_path.stat().st_size/1e6:.2f} MB)")

# Print summary
print("\nCounty | net | nat | dom | intl (thousands, cumulative 2010-2024)")
for p in panels:
    print(f"  {p['name']:20s} {p['final_delta']/1000:>+6.1f}K | "
          f"{p['final_nat']/1000:>+6.1f}K | {p['final_dom']/1000:>+6.1f}K | "
          f"{p['final_intl']/1000:>+6.1f}K")
