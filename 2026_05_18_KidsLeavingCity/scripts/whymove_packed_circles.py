"""
Packed-circles chart: granular stated reasons for families with kids moving across
state lines OUT of major MSA central states — proxying inner-city → suburb flight.

Each panel shows one cross-state pair. CPS public-use only has state-level previous
residence, so we use cross-state migration as a proxy for the cross-state portion
of MSA suburban flight (the most natural for MSAs whose suburbs straddle states).

Pairs (MSA — origin → destinations):
  NY MSA   — NY → NJ + CT + PA          (strongest sample)
  Philly   — PA → NJ + DE + MD
  Chicago  — IL → IN + WI
  DC       — DC → VA + MD + WV          (marginal sample)
  Charlotte — NC → SC                    (marginal sample)

Data source: IPUMS CPS ASEC 1999-2025, MIGRATE1=5 (interstate), NCHILD>0.
"""
from __future__ import annotations
import json
from pathlib import Path
import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"
F = "/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec_full.parquet"

WHYMOVE_LABELS = {
    1: "Marital status change", 2: "Establish own household", 3: "Other family reason",
    4: "New job / job transfer", 5: "Lost job / looking for work",
    6: "Easier commute", 7: "Retired", 8: "Other job-related",
    9: "Own / stop owning", 10: "New / better housing",
    11: "Better neighborhood, less crime", 12: "Cheaper housing", 13: "Other housing",
    14: "College", 15: "Climate", 16: "Health", 17: "Natural disaster",
    18: "Foreclosure / eviction", 19: "Other", 20: "Other family",
}
CATEGORIES = {
    "employment": [4, 5, 8],
    "housing":    [6, 9, 10, 11, 12, 13],
    "family":     [1, 2, 3, 20],
    "retirement": [7],
    "education":  [14],
    "other":      [15, 16, 17, 18, 19],
}
CODE_TO_CAT = {c: cat for cat, codes in CATEGORIES.items() for c in codes}

COLORS = {
    "employment": "#0BB4FF", "housing": "#F4743B", "family": "#67A275",
    "retirement": "#FEC439", "education": "#C6DCCB", "other": "#DADFCE",
    "bg": "#F6F7F3", "text": "#3D3733", "subtext": "#7F7570",
}


def pull_pair(origin: int, dests: list[int]) -> pd.DataFrame:
    dests_sql = ",".join(map(str, dests))
    sql = f"""
    SELECT WHYMOVE, ASECWT
    FROM '{F}'
    WHERE MIGSTA1 = {origin}
      AND STATEFIP IN ({dests_sql})
      AND MIGRATE1 = 5
      AND NCHILD > 0
      AND WHYMOVE BETWEEN 1 AND 20
    """
    return duckdb.query(sql).df()


def panel(label: str, sub: str, df: pd.DataFrame):
    g = df.groupby("WHYMOVE")["ASECWT"].sum().reset_index()
    total = g["ASECWT"].sum()
    nodes = []
    for _, r in g.iterrows():
        c = int(r["WHYMOVE"])
        if c not in WHYMOVE_LABELS:
            continue
        cat = CODE_TO_CAT.get(c, "other")
        nodes.append({
            "code": c,
            "label": WHYMOVE_LABELS[c],
            "cat": cat,
            "color": COLORS[cat],
            "weight": int(r["ASECWT"]),
            "pct": float(r["ASECWT"] / total * 100),
        })
    nodes.sort(key=lambda x: -x["weight"])
    return {"label": label, "sub": sub, "n_records": len(df),
            "total_weight": int(total), "nodes": nodes}


def main():
    pairs = [
        ("NY → NJ/CT/PA",       "Strongest sample",     36, [34, 9, 42]),
        ("Philly (PA) → NJ/DE/MD", "Strong sample",      42, [34, 10, 24]),
        ("Chicago (IL) → IN/WI", "Workable",             17, [18, 55]),
        ("DC → VA/MD/WV",       "Marginal sample",       11, [51, 24, 54]),
        ("Charlotte (NC) → SC", "Marginal sample",       37, [45]),
    ]
    panels = []
    for label, sub, origin, dests in pairs:
        df = pull_pair(origin, dests)
        sub_text = f"{sub}  ·  n = {len(df):,} records, ~{int(df['ASECWT'].sum()/1000):,}k weighted"
        panels.append(panel(label, sub_text, df))
        print(f"  {label:<26}  n={len(df):>5}")

    payload = json.dumps(panels)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Why families with kids leave central states — cross-state proxies</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }}
body {{ margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }}
svg {{ display:block; margin:20px auto; }}
</style></head><body>
<svg id="chart" viewBox="0 0 1800 900" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const PANELS = {payload};
const C = {json.dumps(COLORS)};
const W = 1800, H = 900;
const PAD = 30;

const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', C.bg);

svg.append('text').attr('x', PAD).attr('y', PAD + 30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',28).attr('font-weight',500).attr('fill',C.text)
  .text('Why families with kids leave city-state cores (cross-state proxies for suburban flight)');
svg.append('text').attr('x', PAD).attr('y', PAD + 30 + 28)
  .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',400).attr('fill',C.subtext)
  .text('Stated reasons for moving (CPS ASEC 1999-2025) among householders with own children. Each panel = one cross-state migration corridor that proxies an MSAs inner-to-outer flight.');

const N = PANELS.length;
const panelW = (W - (N + 1) * PAD) / N;
const panelH = H - PAD - 200;
const startY = PAD + 90;

PANELS.forEach((p, i) => {{
  const x0 = PAD + i * (panelW + PAD);
  const y0 = startY;

  svg.append('text').attr('x', x0 + panelW/2).attr('y', y0 + 14)
    .attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',500).attr('fill',C.text)
    .text(p.label);
  svg.append('text').attr('x', x0 + panelW/2).attr('y', y0 + 32)
    .attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill',C.subtext)
    .text(p.sub);

  // Outer box (optional, faint)
  svg.append('rect').attr('x', x0).attr('y', y0 + 44).attr('width', panelW).attr('height', panelH - 50)
    .attr('fill','none').attr('stroke','#d0d0d0').attr('stroke-width',0.5);

  const hier = d3.hierarchy({{children: p.nodes}}).sum(d => d.weight);
  const pack = d3.pack().size([panelW - 8, panelH - 60]).padding(2);
  pack(hier);

  const g = svg.append('g').attr('transform', `translate(${{x0 + 4}}, ${{y0 + 50}})`);
  hier.leaves().forEach(n => {{
    g.append('circle')
      .attr('cx', n.x).attr('cy', n.y).attr('r', n.r)
      .attr('fill', n.data.color).attr('opacity', 0.9)
      .attr('stroke','#3D3733').attr('stroke-width',0.5);
    if (n.r > 22) {{
      const fs = Math.min(13, Math.max(9, n.r / 4.5));
      const lbl = n.data.label.length > 16 ? n.data.label.slice(0,16) + '…' : n.data.label;
      g.append('text').attr('x', n.x).attr('y', n.y - 2).attr('text-anchor','middle')
        .attr('font-family','ABC Oracle Edu').attr('font-size', fs).attr('font-weight',500).attr('fill','#3D3733')
        .text(lbl);
      g.append('text').attr('x', n.x).attr('y', n.y + fs).attr('text-anchor','middle')
        .attr('font-family','ABC Oracle Edu').attr('font-size', fs - 1).attr('font-weight',300).attr('fill','#3D3733')
        .text(`${{n.data.pct.toFixed(0)}}%`);
    }}
    g.append('title')
      .text(`${{n.data.label}}\\n${{n.data.pct.toFixed(1)}}% (${{n.data.weight.toLocaleString()}} weighted)`);
  }});
}});

// Legend
const legendY = H - PAD - 70;
const cats = ['employment','housing','family','retirement','education','other'];
const catLabels = {{
  employment: 'Employment', housing: 'Housing', family: 'Family',
  retirement: 'Retirement', education: 'Education', other: 'Other / catastrophic',
}};
let lx = PAD;
cats.forEach(c => {{
  svg.append('circle').attr('cx', lx + 8).attr('cy', legendY).attr('r', 8).attr('fill', C[c]);
  svg.append('text').attr('x', lx + 22).attr('y', legendY + 4)
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',400).attr('fill',C.text)
    .text(catLabels[c]);
  lx += 22 + (catLabels[c].length * 8) + 24;
}});

svg.append('text').attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',200).attr('fill',C.text)
  .text('Source: IPUMS CPS ASEC 1999-2025, WHYMOVE variable. Householders with own children in household. Interstate moves only.');
svg.append('text').attr('x', PAD).attr('y', H - PAD)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',200).attr('fill',C.subtext)
  .text('Intra-state moves (e.g., Manhattan -> Westchester) not captured. The 5 MSAs shown have suburbs that straddle state lines, so cross-state moves proxy inner-to-outer flight well.');
</script>
</body></html>"""

    out = OUTPUTS / "whymove_packed_circles.html"
    out.write_text(html)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
