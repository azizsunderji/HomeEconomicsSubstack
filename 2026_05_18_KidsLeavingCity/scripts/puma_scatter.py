"""
PUMA-level scatters: kid-population change vs (a) burden change and (b) real
income change. Both rebuilt to use PUMA geography (2,351 PUMAs vs 316 counties).

Window: 2013 → 2021 (both in the 2010 PUMA vintage; no crosswalk needed).

Output:
  outputs/burden_scatter_puma.html
  outputs/income_scatter_puma.html
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

CPI_2013 = 232.96
CPI_2021 = 270.97


def per_puma_stats(year: int) -> pd.DataFrame:
    """Per-PUMA: under-18 pop, median HHincome, % housing-burdened."""
    sql = f"""
    WITH base AS (
        SELECT YEAR, SAMPLE, SERIAL, PERNUM, STATEFIP, PUMA,
               PERWT, HHWT, AGE, HHINCOME, OWNERSHP, OWNCOST, RENTGRS
        FROM '{PUMS}'
        WHERE YEAR = {year}
    ),
    kids AS (
        SELECT STATEFIP, PUMA, SUM(PERWT) AS pop_under18
        FROM base WHERE AGE < 18 AND PERWT > 0
        GROUP BY 1, 2
    ),
    hh AS (
        SELECT STATEFIP, PUMA, HHWT, HHINCOME, OWNERSHP, OWNCOST, RENTGRS
        FROM base
        WHERE PERNUM = 1 AND HHWT > 0
          AND HHINCOME > 0 AND HHINCOME < 9999998
          AND OWNERSHP IN (1, 2)
    ),
    hh_burden AS (
        SELECT STATEFIP, PUMA, HHWT,
               CASE WHEN OWNERSHP = 1 AND OWNCOST > 0 AND OWNCOST < 99999
                    THEN (OWNCOST * 12.0) / HHINCOME
                    WHEN OWNERSHP = 2 AND RENTGRS > 0 AND RENTGRS < 99999
                    THEN (RENTGRS * 12.0) / HHINCOME
                    ELSE NULL END AS burden,
               HHINCOME
        FROM hh
    ),
    burden_agg AS (
        SELECT STATEFIP, PUMA,
               SUM(HHWT) AS hh_weighted,
               SUM(CASE WHEN burden >= 0.30 THEN HHWT ELSE 0 END) AS hh_burdened,
               approx_quantile(HHINCOME, 0.5) AS median_hhincome
        FROM hh_burden
        GROUP BY 1, 2
    )
    SELECT
        b.STATEFIP, b.PUMA,
        k.pop_under18,
        b.hh_weighted,
        (b.hh_burdened / NULLIF(b.hh_weighted, 0)) * 100 AS pct_burdened,
        b.median_hhincome
    FROM burden_agg b
    LEFT JOIN kids k USING (STATEFIP, PUMA)
    """
    df = duckdb.query(sql).df()
    df["puma_key"] = df["STATEFIP"].astype(int).astype(str).str.zfill(2) + "-" \
                   + df["PUMA"].astype(int).astype(str).str.zfill(5)
    df["year"] = year
    return df


def make_chart(df, x_col, x_label, x_format, title, subtitle, color_col, color_label, color_format, outfile):
    points = []
    for _, r in df.iterrows():
        points.append({
            "puma": r["puma_key"],
            "x": float(r[x_col]),
            "y": float(r["delta_kids_pct"]),
            "size": int(r["pop_under18_start"]),
            "color_val": float(r[color_col]),
            "burden_2013": float(r["pct_burdened_2013"]) if pd.notna(r["pct_burdened_2013"]) else None,
            "burden_2021": float(r["pct_burdened_2021"]) if pd.notna(r["pct_burdened_2021"]) else None,
            "inc_2013_real": float(r["inc_2013_real"]) if pd.notna(r["inc_2013_real"]) else None,
            "inc_2021": float(r["inc_2021"]) if pd.notna(r["inc_2021"]) else None,
            "real_inc_pct": float(r["real_inc_pct_change"]) if pd.notna(r["real_inc_pct_change"]) else None,
            "burden_delta": float(r["burden_delta"]) if pd.notna(r["burden_delta"]) else None,
        })
    payload = json.dumps(points)

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{title}</title>
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
const X_FORMAT = {json.dumps(x_format)};
const COLOR_FORMAT = {json.dumps(color_format)};
const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);
svg.append('text').attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',30).attr('font-weight',700).attr('fill',TEXT)
  .text({json.dumps(title)});
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 28)
  .attr('font-family','ABC Oracle Edu').attr('font-size',17).attr('font-weight',400).attr('fill',TEXT)
  .text({json.dumps(subtitle)});

const chartLeft = 90, chartRight = W - PAD - 60;
const chartTop = PAD + 90, chartBottom = H - PAD - 110;

const xS = d3.scaleLinear().domain(d3.extent(D, d => d.x)).nice().range([chartLeft, chartRight]);
const yS = d3.scaleLinear().domain(d3.extent(D, d => d.y)).nice().range([chartBottom, chartTop]);
const rS = d3.scaleSqrt().domain(d3.extent(D, d => d.size)).range([1.2, 14]);
const colorExtent = d3.extent(D, d => d.color_val);
const colorScale = d3.scaleSequential(d3.interpolate('#BCE8FF', '#003D66')).domain(colorExtent);

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
    .text((t > 0 ? '+' : '') + t.toFixed(X_FORMAT === 'pp' ? 1 : 0) + (X_FORMAT === 'pp' ? 'pp' : '%'));
}});

svg.append('text').attr('x', (chartLeft + chartRight)/2).attr('y', chartBottom + 50)
  .attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
  .text({json.dumps(x_label)});

svg.append('text').attr('transform', `translate(${{30}}, ${{(chartTop+chartBottom)/2}}) rotate(-90)`)
  .attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',TEXT)
  .text('Change in under-18 population, 2013 → 2021');

svg.append('line').attr('x1', xS(0)).attr('x2', xS(0)).attr('y1', chartTop).attr('y2', chartBottom)
  .attr('stroke', TEXT).attr('stroke-width', 1);

const tip = d3.select('.tooltip');
D.forEach(p => {{
  svg.append('circle')
    .attr('cx', xS(p.x)).attr('cy', yS(p.y))
    .attr('r', rS(p.size))
    .attr('fill', colorScale(p.color_val))
    .attr('fill-opacity', 0.6)
    .style('cursor','pointer')
    .on('mousemove', e => {{
      tip.style('display','block').style('left', (e.pageX + 12) + 'px').style('top', (e.pageY + 12) + 'px')
        .html(
          `<b>PUMA ${{p.puma}}</b><br>` +
          `Δ under-18: ${{p.y > 0 ? '+' : ''}}${{p.y.toFixed(1)}}%<br>` +
          (p.burden_2021 !== null ? `Burden 2021: ${{p.burden_2021.toFixed(1)}}%<br>` : '') +
          (p.burden_delta !== null ? `Δ burden: ${{p.burden_delta > 0 ? '+' : ''}}${{p.burden_delta.toFixed(1)}}pp<br>` : '') +
          (p.inc_2021 !== null ? `Median HH inc 2021: $${{p.inc_2021.toLocaleString(undefined,{{maximumFractionDigits:0}})}}<br>` : '') +
          (p.real_inc_pct !== null ? `Δ real income: ${{p.real_inc_pct > 0 ? '+' : ''}}${{p.real_inc_pct.toFixed(1)}}%<br>` : '') +
          `2013 under-18 pop: ${{p.size.toLocaleString()}}`
        );
    }})
    .on('mouseout', () => tip.style('display','none'));
}});

const lgX = W - 280, lgY = chartTop + 10, lgW = 200, lgH = 12;
const stops = 30;
for (let i = 0; i < stops; i++) {{
  const t = i / (stops - 1);
  const v = colorExtent[0] + t * (colorExtent[1] - colorExtent[0]);
  svg.append('rect').attr('x', lgX + t * lgW).attr('y', lgY)
    .attr('width', lgW/stops + 1).attr('height', lgH).attr('fill', colorScale(v));
}}
svg.append('text').attr('x', lgX + lgW/2).attr('y', lgY - 4).attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',500).attr('fill',TEXT)
  .text({json.dumps(color_label)});
svg.append('text').attr('x', lgX).attr('y', lgY + lgH + 14)
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill',TEXT)
  .text(COLOR_FORMAT === 'dollar' ? '$' + Math.round(colorExtent[0]/1000) + 'k' : colorExtent[0].toFixed(0) + '%');
svg.append('text').attr('x', lgX + lgW).attr('y', lgY + lgH + 14).attr('text-anchor','end')
  .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill',TEXT)
  .text(COLOR_FORMAT === 'dollar' ? '$' + Math.round(colorExtent[1]/1000) + 'k' : colorExtent[1].toFixed(0) + '%');

svg.append('text').attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',TEXT)
  .text(`n = ${{D.length}} PUMAs. 2010-vintage PUMAs used throughout (window chosen to avoid PUMA boundary crosswalks).`);
svg.append('text').attr('x', PAD).attr('y', H - PAD - 0)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',300).attr('fill',SUBTEXT)
  .text('Source: ACS 5-year PUMS, YEAR=2013 (covering 2009-2013) and YEAR=2021 (2017-2021). Median HHINCOME deflated to 2021 dollars using CPI-U.');
</script>
</body></html>"""
    outfile.write_text(html)


def r2(x, y, w=None):
    x = np.array(x); y = np.array(y)
    if w is None: w = np.ones_like(x)
    w = np.array(w, dtype=float)
    xm = np.average(x, weights=w); ym = np.average(y, weights=w)
    cov = np.average((x-xm)*(y-ym), weights=w)
    vx = np.average((x-xm)**2, weights=w); vy = np.average((y-ym)**2, weights=w)
    r_v = cov / np.sqrt(vx*vy) if vx > 0 and vy > 0 else 0
    return r_v, r_v**2


def main():
    print("Computing 2013 PUMA stats...")
    s13 = per_puma_stats(2013).rename(columns={
        "pop_under18": "pop_under18_start",
        "pct_burdened": "pct_burdened_2013",
        "median_hhincome": "inc_2013",
    })
    print(f"  {len(s13)} PUMAs")
    print("Computing 2021 PUMA stats...")
    s21 = per_puma_stats(2021).rename(columns={
        "pop_under18": "pop_under18_end",
        "pct_burdened": "pct_burdened_2021",
        "median_hhincome": "inc_2021",
    })
    print(f"  {len(s21)} PUMAs")

    df = s13[["puma_key", "pop_under18_start", "pct_burdened_2013", "inc_2013"]].merge(
        s21[["puma_key", "pop_under18_end", "pct_burdened_2021", "inc_2021"]],
        on="puma_key", how="inner",
    )
    df["delta_kids_pct"] = (df["pop_under18_end"] - df["pop_under18_start"]) / df["pop_under18_start"] * 100
    df["burden_delta"] = df["pct_burdened_2021"] - df["pct_burdened_2013"]
    df["inc_2013_real"] = df["inc_2013"] * (CPI_2021 / CPI_2013)
    df["real_inc_pct_change"] = (df["inc_2021"] - df["inc_2013_real"]) / df["inc_2013_real"] * 100

    df = df.dropna(subset=["delta_kids_pct", "burden_delta", "real_inc_pct_change", "pop_under18_start"])
    df = df[df["pop_under18_start"] > 0]
    print(f"\nMerged: {len(df)} PUMAs in both years")

    # R-squareds
    print("\n=== Δ burden vs Δ kids % ===")
    r, r2v = r2(df["burden_delta"], df["delta_kids_pct"]); print(f"  unweighted   r={r:+.3f}  R²={r2v:.3f}")
    r, r2v = r2(df["burden_delta"], df["delta_kids_pct"], w=df["pop_under18_start"]); print(f"  pop-weighted r={r:+.3f}  R²={r2v:.3f}")

    print("\n=== Δ real income vs Δ kids % ===")
    r, r2v = r2(df["real_inc_pct_change"], df["delta_kids_pct"]); print(f"  unweighted   r={r:+.3f}  R²={r2v:.3f}")
    r, r2v = r2(df["real_inc_pct_change"], df["delta_kids_pct"], w=df["pop_under18_start"]); print(f"  pop-weighted r={r:+.3f}  R²={r2v:.3f}")

    # Chart 1: burden
    make_chart(
        df, x_col="burden_delta",
        x_label="Change in % households housing-burdened, 2013 → 2021 (percentage points)",
        x_format="pp",
        title="Burden change vs kid population, US PUMAs",
        subtitle=f"Each bubble = one of {len(df)} PUMAs nationally. Color = 2021 burden level.",
        color_col="pct_burdened_2021", color_label="2021 burden level", color_format="pct",
        outfile=OUTPUTS / "burden_scatter_puma.html",
    )
    make_chart(
        df, x_col="real_inc_pct_change",
        x_label="Real change in median household income, 2013 → 2021 (%)",
        x_format="pct",
        title="Real income change vs kid population, US PUMAs",
        subtitle=f"Each bubble = one of {len(df)} PUMAs nationally. Color = 2021 median HH income.",
        color_col="inc_2021", color_label="2021 median HH income ($)", color_format="dollar",
        outfile=OUTPUTS / "income_scatter_puma.html",
    )
    print(f"\nWrote both PUMA scatters")


if __name__ == "__main__":
    main()
