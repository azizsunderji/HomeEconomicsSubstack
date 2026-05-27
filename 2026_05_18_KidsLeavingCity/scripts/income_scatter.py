"""
Second national scatter: % change in REAL median household income (2011→2023)
vs % change in under-18 population (2011→2024).

Income from ACS 5-year PUMS (median HHINCOME by county, weighted by HHWT).
Real-dollar adjustment: CPI-U 2011 = 224.94, 2023 = 304.70 (BLS annual).
"""
from __future__ import annotations
from pathlib import Path
import json
import duckdb
import numpy as np
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"
PUMS = "/Users/azizsunderji/Dropbox/Home Economics/Data/Reference/Microdata/ACS/acs_5year_all_windows.parquet"

CPI_2011 = 224.94
CPI_2023 = 304.70


def median_hhincome(year: int) -> pd.DataFrame:
    """Median household income by county (PERNUM=1, HHWT-weighted)."""
    # Use DuckDB's PERCENTILE_CONT for weighted median approximation
    sql = f"""
    WITH hh AS (
        SELECT STATEFIP, COUNTYFIP, HHWT, HHINCOME
        FROM '{PUMS}'
        WHERE YEAR = {year}
          AND PERNUM = 1
          AND HHWT > 0
          AND COUNTYFIP > 0
          AND HHINCOME > 0
          AND HHINCOME < 9999998
    )
    SELECT
        STATEFIP, COUNTYFIP,
        approx_quantile(HHINCOME, 0.5) AS median_hhincome,
        SUM(HHWT) AS hh_count
    FROM hh
    GROUP BY 1, 2
    """
    df = duckdb.query(sql).df()
    df["fips_5"] = df["STATEFIP"].astype(int).astype(str).str.zfill(2) \
                 + df["COUNTYFIP"].astype(int).astype(str).str.zfill(3)
    df["year"] = year
    return df[["fips_5", "year", "median_hhincome", "hh_count"]]


def main():
    print("Computing median HHINCOME by county for 2011 and 2023...")
    inc11 = median_hhincome(2011).rename(columns={"median_hhincome": "inc_2011", "hh_count": "hh_count_11"})
    inc23 = median_hhincome(2023).rename(columns={"median_hhincome": "inc_2023", "hh_count": "hh_count_23"})
    print(f"  2011: {len(inc11)} counties; 2023: {len(inc23)} counties")

    # Deflate 2011 income to 2023 dollars
    inc11["inc_2011_real_2023"] = inc11["inc_2011"] * (CPI_2023 / CPI_2011)

    # PEP under-18
    p11 = pd.read_csv(DATA / "pep_2011_national.csv", dtype={"fips_5": str})
    p24 = pd.read_csv(DATA / "pep_2024_national.csv", dtype={"fips_5": str})
    p11["fips_5"] = p11["fips_5"].str.zfill(5)
    p24["fips_5"] = p24["fips_5"].str.zfill(5)

    # Merge everything
    df = inc11[["fips_5", "inc_2011", "inc_2011_real_2023"]].merge(
        inc23[["fips_5", "inc_2023"]], on="fips_5", how="inner"
    ).merge(
        p11[["fips_5", "pop_under18"]], on="fips_5"
    ).merge(
        p24[["fips_5", "pop_under18_2024"]], on="fips_5"
    )
    df["real_inc_pct_change"] = (df["inc_2023"] - df["inc_2011_real_2023"]) / df["inc_2011_real_2023"] * 100
    df["delta_kids_pct"] = (df["pop_under18_2024"] - df["pop_under18"]) / df["pop_under18"] * 100
    df = df.dropna(subset=["real_inc_pct_change", "delta_kids_pct", "pop_under18"])
    df = df[df["pop_under18"] > 0]

    # County names (best-effort from cenpop file)
    cenpop = pd.read_csv(DATA / "cenpop2020.txt", dtype={"STATEFP": str, "COUNTYFP": str})
    cenpop["fips_5"] = cenpop["STATEFP"].str.zfill(2) + cenpop["COUNTYFP"].str.zfill(3)
    name_map = dict(zip(cenpop["fips_5"], cenpop["COUNAME"] + ", " + cenpop["STNAME"]))
    df["name"] = df["fips_5"].map(name_map).fillna("FIPS " + df["fips_5"])

    print(f"\nCounties in chart: {len(df)}")
    print(f"\nReal HHIncome change distribution:")
    print(df["real_inc_pct_change"].describe().to_string())

    # R-squared
    def r2(x, y, w=None):
        x = np.array(x); y = np.array(y)
        if w is None: w = np.ones_like(x)
        w = np.array(w, dtype=float)
        xm = np.average(x, weights=w); ym = np.average(y, weights=w)
        cov = np.average((x-xm)*(y-ym), weights=w)
        vx = np.average((x-xm)**2, weights=w); vy = np.average((y-ym)**2, weights=w)
        r = cov / np.sqrt(vx*vy) if vx>0 and vy>0 else 0
        return r, r**2
    r, r2v = r2(df["real_inc_pct_change"], df["delta_kids_pct"])
    print(f"\nΔ kids vs Δ real HHincome (unweighted)   r={r:+.3f}  R²={r2v:.3f}")
    r, r2v = r2(df["real_inc_pct_change"], df["delta_kids_pct"], w=df["pop_under18"])
    print(f"Δ kids vs Δ real HHincome (pop-weighted) r={r:+.3f}  R²={r2v:.3f}")

    points = [
        {
            "fips": r["fips_5"],
            "name": r["name"],
            "real_inc_pct_change": float(r["real_inc_pct_change"]),
            "inc_2023": float(r["inc_2023"]),
            "delta_kids_pct": float(r["delta_kids_pct"]),
            "pop_2011": int(r["pop_under18"]),
        }
        for _, r in df.iterrows()
    ]
    payload = json.dumps(points)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>National: real income change vs kid population</title>
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
  .text('Real median household income change vs kid population change');
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 28)
  .attr('font-family','ABC Oracle Edu').attr('font-size',17).attr('font-weight',400).attr('fill',TEXT)
  .text('X: % real change (inflation-adjusted) in median HH income, 2011→2023. Y: % change in under-18 population, 2011→2024. Color: 2023 income level.');

const chartLeft = 90, chartRight = W - PAD - 60;
const chartTop = PAD + 90, chartBottom = H - PAD - 110;

const xS = d3.scaleLinear().domain(d3.extent(D, d => d.real_inc_pct_change)).nice().range([chartLeft, chartRight]);
const yS = d3.scaleLinear().domain(d3.extent(D, d => d.delta_kids_pct)).nice().range([chartBottom, chartTop]);
const rS = d3.scaleSqrt().domain(d3.extent(D, d => d.pop_2011)).range([1.5, 22]);

// Color: sequential blue by 2023 income level
const incExtent = d3.extent(D, d => d.inc_2023);
const colorScale = d3.scaleSequential(d3.interpolate('#BCE8FF', '#003D66')).domain(incExtent);

yS.ticks(8).forEach(t => {{
  svg.append('line').attr('x1', chartLeft).attr('x2', chartRight).attr('y1', yS(t)).attr('y2', yS(t))
    .attr('stroke', t === 0 ? TEXT : GRID).attr('stroke-width', t === 0 ? 1 : 0.5);
  svg.append('text').attr('x', chartLeft - 8).attr('y', yS(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
    .text((t > 0 ? '+' : '') + t.toFixed(0) + '%');
}});
xS.ticks(10).forEach(t => {{
  if (t !== 0) svg.append('line').attr('x1', xS(t)).attr('x2', xS(t)).attr('y1', chartTop).attr('y2', chartBottom)
    .attr('stroke', GRID).attr('stroke-width', 0.5);
  svg.append('line').attr('x1', xS(t)).attr('x2', xS(t)).attr('y1', chartBottom).attr('y2', chartBottom + 5)
    .attr('stroke', TEXT).attr('stroke-width', 0.5);
  svg.append('text').attr('x', xS(t)).attr('y', chartBottom + 20).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
    .text((t > 0 ? '+' : '') + t.toFixed(0) + '%');
}});

svg.append('text').attr('x', (chartLeft + chartRight)/2).attr('y', chartBottom + 50)
  .attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
  .text('Real change in median household income, 2011 → 2023');

svg.append('text').attr('transform', `translate(${{30}}, ${{(chartTop+chartBottom)/2}}) rotate(-90)`)
  .attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
  .text('Change in under-18 population, 2011 → 2024');

svg.append('line').attr('x1', xS(0)).attr('x2', xS(0)).attr('y1', chartTop).attr('y2', chartBottom)
  .attr('stroke', TEXT).attr('stroke-width', 1);

const tip = d3.select('.tooltip');
D.forEach(p => {{
  svg.append('circle')
    .attr('cx', xS(p.real_inc_pct_change)).attr('cy', yS(p.delta_kids_pct))
    .attr('r', rS(p.pop_2011))
    .attr('fill', colorScale(p.inc_2023))
    .attr('fill-opacity', 0.7)
    .style('cursor','pointer')
    .on('mousemove', e => {{
      tip.style('display','block').style('left', (e.pageX + 12) + 'px').style('top', (e.pageY + 12) + 'px')
        .html(
          `<b>${{p.name}}</b><br>` +
          `Δ under-18: ${{p.delta_kids_pct > 0 ? '+' : ''}}${{p.delta_kids_pct.toFixed(1)}}%<br>` +
          `Median HH income 2023: $${{p.inc_2023.toLocaleString(undefined,{{maximumFractionDigits:0}})}}<br>` +
          `Δ real income 2011→23: ${{p.real_inc_pct_change > 0 ? '+' : ''}}${{p.real_inc_pct_change.toFixed(1)}}%<br>` +
          `2011 under-18 pop: ${{p.pop_2011.toLocaleString()}}`
        );
    }})
    .on('mouseout', () => tip.style('display','none'));
}});

const lgX = W - 280, lgY = chartTop + 10, lgW = 200, lgH = 12;
const stops = 30;
for (let i = 0; i < stops; i++) {{
  const t = i / (stops - 1);
  const v = incExtent[0] + t * (incExtent[1] - incExtent[0]);
  svg.append('rect').attr('x', lgX + t * lgW).attr('y', lgY)
    .attr('width', lgW/stops + 1).attr('height', lgH).attr('fill', colorScale(v));
}}
svg.append('text').attr('x', lgX + lgW/2).attr('y', lgY - 4).attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',500).attr('fill',TEXT)
  .text('2023 median HH income ($)');
svg.append('text').attr('x', lgX).attr('y', lgY + lgH + 14)
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill',TEXT)
  .text('$' + Math.round(incExtent[0]/1000) + 'k');
svg.append('text').attr('x', lgX + lgW).attr('y', lgY + lgH + 14).attr('text-anchor','end')
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill',TEXT)
  .text('$' + Math.round(incExtent[1]/1000) + 'k');

svg.append('text').attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',TEXT)
  .text(`n = ${{D.length}} counties. Income deflated using CPI-U (2011 = 224.94, 2023 = 304.70).`);
svg.append('text').attr('x', PAD).attr('y', H - PAD - 0)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',SUBTEXT)
  .text('Source: ACS 5-year PUMS (median HHINCOME by county, HHWT-weighted); Census PEP for under-18 stocks.');
</script>
</body></html>"""
    (OUTPUTS / "burden_scatter_income.html").write_text(html)
    print(f"\nWrote {OUTPUTS / 'burden_scatter_income.html'}")


if __name__ == "__main__":
    main()
