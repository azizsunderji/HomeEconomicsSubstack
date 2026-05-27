"""
National burden vs kid-change scatter — every US county with both data points.
Builds on housing_burden.csv (which already has burden 2011 + 2023 for all counties
where PUMS COUNTYFIP is populated) and joins to national PEP for ΔPop_under18.

Highlights our 12 in-scope MSAs in a distinct color; everything else in grey.
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"


def main():
    burden = pd.read_csv(DATA / "housing_burden.csv", dtype={"fips_5": str})
    burden["fips_5"] = burden["fips_5"].str.zfill(5)
    # housing_burden.csv was previously merged with our 12-MSA decomposition —
    # drop the population columns here so the national PEP join is clean.
    burden = burden.drop(columns=[c for c in burden.columns
                                   if c in ("pop_under18", "pop_under18_2024", "delta_under18", "delta_under18_pct")],
                          errors="ignore")

    pep11 = pd.read_csv(DATA / "pep_2011_national.csv", dtype={"fips_5": str})
    pep24 = pd.read_csv(DATA / "pep_2024_national.csv", dtype={"fips_5": str})
    pep11["fips_5"] = pep11["fips_5"].str.zfill(5)
    pep24["fips_5"] = pep24["fips_5"].str.zfill(5)

    # In-scope MSAs (for highlighting)
    in_scope = pd.read_csv(DATA / "counties_in_scope.csv", dtype={"fips_5": str})
    in_scope["fips_5"] = in_scope["fips_5"].str.zfill(5)
    scope_map = dict(zip(in_scope["fips_5"], in_scope["msa_name_short"]))

    df = burden.merge(pep11[["fips_5", "pop_under18"]], on="fips_5", how="inner") \
               .merge(pep24[["fips_5", "pop_under18_2024"]], on="fips_5", how="inner")
    df["delta_under18"] = df["pop_under18_2024"] - df["pop_under18"]
    df["delta_under18_pct"] = df["delta_under18"] / df["pop_under18"] * 100
    df = df.dropna(subset=["pct_burdened_2023", "delta_under18_pct", "pop_under18",
                            "pct_burdened_2011", "pct_burdened_delta"])
    df = df[df["pop_under18"] > 0]
    print(f"Counties in chart: {len(df)}")

    df["msa_short"] = df["fips_5"].map(scope_map).fillna("Other US")

    # NAME from existing in_scope file or just FIPS
    df["name"] = df["fips_5"].map(dict(zip(in_scope["fips_5"], in_scope["County/County Equivalent"])))
    df["name"] = df["name"].fillna("FIPS " + df["fips_5"])

    points = []
    for _, r in df.iterrows():
        points.append({
            "fips": r["fips_5"],
            "name": r["name"],
            "msa_short": r["msa_short"].split(",")[0].split("-")[0].strip() if r["msa_short"] != "Other US" else "Other US",
            "burden_2011": float(r["pct_burdened_2011"]),
            "burden_2023": float(r["pct_burdened_2023"]),
            "burden_delta": float(r["pct_burdened_delta"]),
            "delta_kids_pct": float(r["delta_under18_pct"]),
            "pop_2011": int(r["pop_under18"]),
            "in_scope": r["msa_short"] != "Other US",
        })
    print(f"  in-scope MSA counties: {sum(p['in_scope'] for p in points)}")
    print(f"  other US counties:      {sum(not p['in_scope'] for p in points)}")

    payload = json.dumps(points)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>National: housing burden vs kid population change</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Bold.otf') format('opentype'); font-weight:700; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }}
body {{ margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }}
svg {{ display:block; margin:20px auto; }}
.tooltip {{ position:absolute; pointer-events:none; background:rgba(61,55,51,0.95); color:#F6F7F3; padding:8px 12px; font-size:13px; border-radius:4px; font-family:'ABC Oracle Edu',sans-serif; max-width:280px; }}
</style></head><body>
<svg id="chart" viewBox="0 0 1400 920" xmlns="http://www.w3.org/2000/svg"></svg>
<div class="tooltip" style="display:none"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const D = {payload};
const BG = '#F6F7F3', TEXT = '#3D3733', SUBTEXT = '#7F7570', GRID = '#e1e2e3';
const W = 1400, H = 920, PAD = 40;
const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

svg.append('text').attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',30).attr('font-weight',700).attr('fill',TEXT)
  .text('Housing burden vs kid population, every US county where data is available');
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 28)
  .attr('font-family','ABC Oracle Edu').attr('font-size',17).attr('font-weight',400).attr('fill',TEXT)
  .text('X: change in housing burden 2011→2023 (percentage points). Y: % change in under-18 population 2011→2024. Bubble color: burden level in 2023.');

const chartLeft = 90, chartRight = W - PAD - 60;
const chartTop = PAD + 90, chartBottom = H - PAD - 110;

const xS = d3.scaleLinear().domain(d3.extent(D, d => d.burden_delta)).nice().range([chartLeft, chartRight]);
const yS = d3.scaleLinear().domain(d3.extent(D, d => d.delta_kids_pct)).nice().range([chartBottom, chartTop]);

// Bubble size scale (sqrt for area-proportional)
const rS = d3.scaleSqrt().domain(d3.extent(D, d => d.pop_2011)).range([1.5, 22]);

// Color: sequential blue by burden level 2023
const burdenExtent = d3.extent(D, d => d.burden_2023);
const colorScale = d3.scaleSequential(d3.interpolate('#BCE8FF', '#003D66')).domain(burdenExtent);

// Gridlines
yS.ticks(8).forEach(t => {{
  svg.append('line').attr('x1', chartLeft).attr('x2', chartRight).attr('y1', yS(t)).attr('y2', yS(t))
    .attr('stroke', t === 0 ? TEXT : GRID).attr('stroke-width', t === 0 ? 1 : 0.5);
  svg.append('text').attr('x', chartLeft - 8).attr('y', yS(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
    .text(t > 0 ? '+' + t + '%' : t + '%');
}});
xS.ticks(10).forEach(t => {{
  if (t !== 0) svg.append('line').attr('x1', xS(t)).attr('x2', xS(t)).attr('y1', chartTop).attr('y2', chartBottom)
    .attr('stroke', GRID).attr('stroke-width', 0.5);
  svg.append('line').attr('x1', xS(t)).attr('x2', xS(t)).attr('y1', chartBottom).attr('y2', chartBottom + 5)
    .attr('stroke', TEXT).attr('stroke-width', 0.5);
  svg.append('text').attr('x', xS(t)).attr('y', chartBottom + 20).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
    .text((t > 0 ? '+' : '') + t + 'pp');
}});

// X axis title
svg.append('text').attr('x', (chartLeft + chartRight)/2).attr('y', chartBottom + 50)
  .attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
  .text('Change in % households housing-burdened, 2011 → 2023 (percentage points)');

// Y axis title
svg.append('text').attr('transform', `translate(${{30}}, ${{(chartTop+chartBottom)/2}}) rotate(-90)`)
  .attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
  .text('Change in under-18 population, 2011 → 2024');

// Zero line
svg.append('line').attr('x1', xS(0)).attr('x2', xS(0)).attr('y1', chartTop).attr('y2', chartBottom)
  .attr('stroke', TEXT).attr('stroke-width', 1);

// Bubbles — all counties shown uniformly
const tip = d3.select('.tooltip');
D.forEach(p => {{
  svg.append('circle')
    .attr('cx', xS(p.burden_delta)).attr('cy', yS(p.delta_kids_pct))
    .attr('r', rS(p.pop_2011))
    .attr('fill', colorScale(p.burden_2023))
    .attr('fill-opacity', 0.7)
    .attr('stroke', 'none')
    .style('cursor','pointer')
    .on('mousemove', e => {{
      tip.style('display','block').style('left', (e.pageX + 12) + 'px').style('top', (e.pageY + 12) + 'px')
        .html(
          `<b>${{p.name}}</b><br>` +
          `<span style="opacity:0.7">${{p.msa_short}}</span><br>` +
          `Δ under-18: ${{p.delta_kids_pct > 0 ? '+' : ''}}${{p.delta_kids_pct.toFixed(1)}}%<br>` +
          `Burden 2023: ${{p.burden_2023.toFixed(1)}}%<br>` +
          `Δ burden 2011→23: ${{p.burden_delta > 0 ? '+' : ''}}${{p.burden_delta.toFixed(1)}}pp<br>` +
          `2011 under-18 pop: ${{p.pop_2011.toLocaleString()}}`
        );
    }})
    .on('mouseout', () => tip.style('display','none'));
}});

// Color legend (for burden level)
const lgX = W - 280, lgY = chartTop + 10, lgW = 200, lgH = 12;
const stops = 30;
for (let i = 0; i < stops; i++) {{
  const t = i / (stops - 1);
  const v = burdenExtent[0] + t * (burdenExtent[1] - burdenExtent[0]);
  svg.append('rect').attr('x', lgX + t * lgW).attr('y', lgY)
    .attr('width', lgW/stops + 1).attr('height', lgH).attr('fill', colorScale(v));
}}
svg.append('text').attr('x', lgX + lgW/2).attr('y', lgY - 4).attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',500).attr('fill',TEXT)
  .text('2023 burden level (% households)');
svg.append('text').attr('x', lgX).attr('y', lgY + lgH + 14)
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill',TEXT)
  .text(burdenExtent[0].toFixed(0) + '%');
svg.append('text').attr('x', lgX + lgW).attr('y', lgY + lgH + 14).attr('text-anchor','end')
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill',TEXT)
  .text(burdenExtent[1].toFixed(0) + '%');

// (No MSA distinction — all counties shown uniformly)

// Source
svg.append('text').attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',TEXT)
  .text(`n = ${{D.length}} counties (where ACS PUMS publishes county-level burden). Counties without identifiable COUNTYFIP (smaller, more rural) excluded.`);
svg.append('text').attr('x', PAD).attr('y', H - PAD - 0)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',SUBTEXT)
  .text('Source: ACS 5-year PUMS (housing burden); Census PEP (under-18 stocks). Burden = % of households (owners + renters) paying ≥30% of income on housing.');
</script>
</body></html>"""
    (OUTPUTS / "burden_scatter_national.html").write_text(html)
    print(f"\nWrote {OUTPUTS / 'burden_scatter_national.html'}")


if __name__ == "__main__":
    main()
