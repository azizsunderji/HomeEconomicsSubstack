#!/usr/bin/env python3
"""Immigration vs Happiness — core analysis.

Spec 1: Cross-sectional (change in immigration rate vs change in happiness)
Spec 2: Horizon sweep (varying time windows)
Spec 3: Panel regression (first-differenced, country-year)
Spec 4: Lag structure (does immigration predict future happiness?)
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
import json, base64, os

DATA = Path(__file__).parent.parent / "data"
OUT = Path(__file__).parent.parent / "outputs"

BLACK = "#3D3733"
BG = "#F6F7F3"
BLUE = "#0BB4FF"
RED = "#F4743B"
GREEN = "#67A275"
SUBTITLE_COLOR = "#7F7570"
GRID_COLOR = "#e1e2e3"

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
LOGO_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png"

ANGLOPHONE = ["USA", "CAN", "GBR", "AUS", "NZL", "IRL"]


def load_data():
    imm = pd.read_csv(DATA / "oecd_immigration_net.csv")
    hap = pd.read_csv(DATA / "happiness_combined.csv")
    return imm, hap


def get_brand_assets():
    logo_b64 = ""
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()
    font_faces = ""
    for wname, wnum in [("Thin", 200), ("Light", 300), ("Regular", 400), ("Medium", 500), ("Bold", 700)]:
        otf = f"{FONT_DIR}/ABCOracle-{wname}.otf"
        if os.path.exists(otf):
            with open(otf, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            font_faces += f"@font-face {{ font-family:'ABC Oracle Edu'; src:url('data:font/otf;base64,{b64}'); font-weight:{wnum}; }}\n"
    return logo_b64, font_faces


def spec1_cross_sectional(imm, hap):
    """Change in immigration rate vs change in happiness, full period."""
    print("\n" + "=" * 60)
    print("SPEC 1: Cross-sectional (avg 2006-10 → avg 2020-24)")
    print("=" * 60)

    # Immigration: avg rate 2006-2010 vs 2020-2024
    imm_early = imm[imm["year"].between(2006, 2010)].groupby("iso3")["rate_per1000"].mean()
    imm_late = imm[imm["year"].between(2020, 2024)].groupby("iso3")["rate_per1000"].mean()
    imm_change = (imm_late - imm_early).dropna()

    # Happiness: avg 2006-2010 vs 2020-2024
    hap_early = hap[hap["year"].between(2006, 2010)].groupby("iso3")["cantril"].mean()
    hap_late = hap[hap["year"].between(2020, 2024)].groupby("iso3")["cantril"].mean()
    hap_change = (hap_late - hap_early).dropna()

    # Merge
    both = pd.DataFrame({"imm_change": imm_change, "hap_change": hap_change}).dropna()
    print(f"Countries: {len(both)}")

    # Regression
    slope, intercept, r, p, se = stats.linregress(both["imm_change"], both["hap_change"])
    r_sq = r ** 2
    print(f"R² = {r_sq:.3f}, p = {p:.4f}, slope = {slope:+.4f}, n = {len(both)}")

    # Print country data
    names = imm.drop_duplicates("iso3").set_index("iso3")["country"].to_dict()
    both["country"] = both.index.map(names)
    both = both.sort_values("imm_change")
    print(f"\n{'Country':<25} {'ΔImmig':>8} {'ΔHappy':>8}")
    print("-" * 45)
    for iso3, row in both.iterrows():
        a = "*" if iso3 in ANGLOPHONE else " "
        print(f"{a}{row['country']:<24} {row['imm_change']:>+8.1f} {row['hap_change']:>+8.3f}")

    # Build scatter chart
    build_scatter(both, slope, intercept, r_sq, p,
                  "Immigration surge and happiness",
                  "Change in net migration rate vs change in life satisfaction, 2006\u201310 \u2192 2020\u201324",
                  "Change in net migration rate per 1,000 (avg 2006\u201310 \u2192 avg 2020\u201324)",
                  "scatter_immigration_vs_happiness")

    return r_sq, p, slope


def spec2_horizon_sweep(imm, hap):
    """Vary the time window and see how R² changes."""
    print("\n" + "=" * 60)
    print("SPEC 2: Horizon sweep")
    print("=" * 60)

    results = []

    # Test various early/late period pairs
    windows = [
        ("2006-10 → 2020-24", (2006, 2010), (2020, 2024)),
        ("2006-10 → 2018-22", (2006, 2010), (2018, 2022)),
        ("2006-10 → 2015-19", (2006, 2010), (2015, 2019)),
        ("2008-12 → 2020-24", (2008, 2012), (2020, 2024)),
        ("2010-14 → 2020-24", (2010, 2014), (2020, 2024)),
        ("2012-16 → 2020-24", (2012, 2016), (2020, 2024)),
        ("2014-18 → 2020-24", (2014, 2018), (2020, 2024)),
        # Short windows (surge-focused)
        ("2015-19 → 2020-24", (2015, 2019), (2020, 2024)),
        ("2017-19 → 2022-24", (2017, 2019), (2022, 2024)),
    ]

    print(f"\n{'Window':<25} {'R²':>8} {'p':>8} {'slope':>8} {'n':>5}")
    print("-" * 58)

    for label, (e1, e2), (l1, l2) in windows:
        imm_early = imm[imm["year"].between(e1, e2)].groupby("iso3")["rate_per1000"].mean()
        imm_late = imm[imm["year"].between(l1, l2)].groupby("iso3")["rate_per1000"].mean()
        imm_change = (imm_late - imm_early).dropna()

        hap_early = hap[hap["year"].between(e1, e2)].groupby("iso3")["cantril"].mean()
        hap_late = hap[hap["year"].between(l1, l2)].groupby("iso3")["cantril"].mean()
        hap_change = (hap_late - hap_early).dropna()

        both = pd.DataFrame({"imm": imm_change, "hap": hap_change}).dropna()
        if len(both) < 10:
            continue

        slope, intercept, r, p, se = stats.linregress(both["imm"], both["hap"])
        r_sq = r ** 2
        sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""
        print(f"{label:<25} {r_sq:>8.3f} {p:>8.3f} {slope:>+8.4f} {len(both):>5} {sig}")

        mid_year = (l1 + l2) / 2 - (e1 + e2) / 2
        results.append({
            "label": label,
            "r_sq": round(r_sq, 4),
            "p": round(p, 4),
            "slope": round(slope, 4),
            "n": len(both),
            "horizon": round(mid_year, 1),
        })

    return results


def spec3_panel(imm, hap):
    """Panel regression: ΔHappiness ~ ΔImmigration + country FE + year FE."""
    print("\n" + "=" * 60)
    print("SPEC 3: Panel (first-differenced, country-year)")
    print("=" * 60)

    from statsmodels.api import OLS, add_constant

    # Merge on iso3 + year
    panel = imm[["iso3", "year", "rate_per1000"]].merge(
        hap[["iso3", "year", "cantril"]], on=["iso3", "year"], how="inner"
    )
    panel = panel.sort_values(["iso3", "year"])

    # First differences within country
    panel["d_imm"] = panel.groupby("iso3")["rate_per1000"].diff()
    panel["d_hap"] = panel.groupby("iso3")["cantril"].diff()
    panel = panel.dropna(subset=["d_imm", "d_hap"])

    # Year dummies
    year_dummies = pd.get_dummies(panel["year"], prefix="yr", drop_first=True, dtype=float)

    X = pd.concat([panel[["d_imm"]].reset_index(drop=True), year_dummies.reset_index(drop=True)], axis=1)
    X = add_constant(X)
    y = panel["d_hap"].reset_index(drop=True)

    model = OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": panel["iso3"].values})

    print(f"n = {len(panel)}, countries = {panel['iso3'].nunique()}")
    print(f"Coefficient on ΔImmigration: {model.params['d_imm']:.4f}")
    print(f"  t-stat: {model.tvalues['d_imm']:.3f}")
    print(f"  p-value: {model.pvalues['d_imm']:.4f}")
    print(f"  95% CI: [{model.conf_int().loc['d_imm', 0]:.4f}, {model.conf_int().loc['d_imm', 1]:.4f}]")
    print(f"R² = {model.rsquared:.3f}")

    # Also run without year FE for comparison
    X_simple = add_constant(panel[["d_imm"]])
    model_simple = OLS(panel["d_hap"], X_simple).fit(
        cov_type="cluster", cov_kwds={"groups": panel["iso3"].values}
    )
    print(f"\nWithout year FE:")
    print(f"  Coefficient: {model_simple.params['d_imm']:.4f}, p = {model_simple.pvalues['d_imm']:.4f}")

    return model


def spec4_lags(imm, hap):
    """Does immigration in year t predict happiness in t+1, t+2, t+3?"""
    print("\n" + "=" * 60)
    print("SPEC 4: Lag structure")
    print("=" * 60)

    panel = imm[["iso3", "year", "rate_per1000"]].merge(
        hap[["iso3", "year", "cantril"]], on=["iso3", "year"], how="inner"
    )
    panel = panel.sort_values(["iso3", "year"])

    print(f"\n{'Lag':>5} {'Coeff':>10} {'p-value':>10} {'n':>6}")
    print("-" * 35)

    for lag in range(0, 6):
        # Immigration rate in year t, happiness change from t to t+lag
        rows = []
        for iso3, grp in panel.groupby("iso3"):
            grp = grp.sort_values("year")
            for i in range(len(grp) - lag):
                rows.append({
                    "iso3": iso3,
                    "imm_rate": grp.iloc[i]["rate_per1000"],
                    "hap_change": grp.iloc[i + lag]["cantril"] - grp.iloc[i]["cantril"],
                })
        df = pd.DataFrame(rows)
        if len(df) < 20:
            continue
        slope, intercept, r, p, se = stats.linregress(df["imm_rate"], df["hap_change"])
        print(f"  t+{lag}  {slope:>+10.4f} {p:>10.4f} {len(df):>6}")


def build_scatter(data, slope, intercept, r_sq, p, title, subtitle, x_label, filename):
    """Build D3 scatter chart."""
    logo_b64, font_faces = get_brand_assets()

    # Get population for bubble sizing
    pop_df = pd.read_csv(
        Path("/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness/data/wb_population_all.csv")
    )
    pop_latest = pop_df.sort_values("year").groupby("iso3").last()["population"]

    records = []
    for iso3, row in data.iterrows():
        pop_m = pop_latest.get(iso3, 10e6) / 1e6
        records.append({
            "iso3": iso3,
            "country": row["country"],
            "x": round(float(row["imm_change"]), 2),
            "y": round(float(row["hap_change"]), 3),
            "pop": round(float(pop_m), 1),
            "anglo": iso3 in ANGLOPHONE,
        })

    data_json = json.dumps(records)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
{font_faces}
body {{ margin:0; background:#FFFFFF; }}
svg {{ display:block; margin:0 auto; }}
</style>
<script src="d3.v7.min.js"></script>
</head><body>
<script>
const W = 960, H = 987;
const margin = {{top: 40, right: 40, bottom: 40, left: 40}};
const titleY = 72, subtitleY = 106;
const chartTop = subtitleY + 75;
const chartLeft = margin.left + 50;
const chartRight = W - margin.right;
const sourceY = H - 55;
const chartBottom = sourceY - 85;

const data = {data_json};
const slope = {slope}, intercept = {intercept};
const r2 = {r_sq:.4f}, pval = {p:.4f}, n = {len(records)};

const svg = d3.select("body").append("svg")
  .attr("width", W).attr("height", H).attr("viewBox", `0 0 ${{W}} ${{H}}`);

svg.append("rect").attr("width", W).attr("height", H).attr("fill", "{BG}");

svg.append("text").attr("x", margin.left).attr("y", titleY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 32).attr("font-weight", 500)
  .attr("fill", "{BLACK}").text("{title}");

// Subtitle wrapping
const subWords = "{subtitle}".split(' ');
let line1 = '', line2 = '';
for (const w of subWords) {{
  if (line1.length + w.length < 58) line1 += (line1 ? ' ' : '') + w;
  else line2 += (line2 ? ' ' : '') + w;
}}
svg.append("text").attr("x", margin.left).attr("y", subtitleY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 23).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").text(line1);
if (line2) svg.append("text").attr("x", margin.left).attr("y", subtitleY + 28)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 23).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").text(line2);

const xExt = d3.extent(data, d => d.x);
const yExt = d3.extent(data, d => d.y);
const xPad = (xExt[1] - xExt[0]) * 0.08;
const yPad = (yExt[1] - yExt[0]) * 0.08;

const x = d3.scaleLinear()
  .domain([Math.min(xExt[0] - xPad, -3), xExt[1] + xPad])
  .range([chartLeft, chartRight]);
const y = d3.scaleLinear()
  .domain([yExt[0] - yPad, yExt[1] + yPad])
  .range([chartBottom, chartTop]);

// Grid
const yTicks = y.ticks(8);
yTicks.forEach((t, i) => {{
  svg.append("line").attr("x1", margin.left).attr("x2", chartRight)
    .attr("y1", y(t)).attr("y2", y(t))
    .attr("stroke", "{GRID_COLOR}").attr("stroke-width", 1);
  let label = t.toFixed(1);
  if (i === yTicks.length - 1) label += " pts";
  svg.append("text").attr("x", margin.left).attr("y", y(t) - 6)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
    .attr("fill", "#333").attr("text-anchor", "start").text(label);
}});

// Zero lines
if (y.domain()[0] < 0 && y.domain()[1] > 0)
  svg.append("line").attr("x1", margin.left).attr("x2", chartRight)
    .attr("y1", y(0)).attr("y2", y(0))
    .attr("stroke", "{BLACK}").attr("stroke-width", 1.5).attr("opacity", 0.3);

// X-axis
const xTicks = x.ticks(8);
xTicks.forEach(t => {{
  svg.append("line").attr("x1", x(t)).attr("x2", x(t))
    .attr("y1", chartBottom).attr("y2", chartBottom + 12)
    .attr("stroke", "{BLACK}").attr("stroke-width", 0.5);
  svg.append("text").attr("x", x(t)).attr("y", chartBottom + 37)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 22).attr("font-weight", 300)
    .attr("fill", "#333").attr("text-anchor", "middle")
    .text((t >= 0 ? "+" : "") + t.toFixed(0));
}});

svg.append("text").attr("x", (chartLeft + chartRight) / 2).attr("y", chartBottom + 65)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 18).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "middle")
  .text("{x_label}");

// Regression line
const xMin = x.domain()[0], xMax = x.domain()[1];
svg.append("line")
  .attr("x1", x(xMin)).attr("x2", x(xMax))
  .attr("y1", y(slope * xMin + intercept)).attr("y2", y(slope * xMax + intercept))
  .attr("stroke", "{BLUE}").attr("stroke-width", 2).attr("stroke-dasharray", "8,6").attr("opacity", 0.6);

// Bubbles
const popExt = d3.extent(data, d => d.pop);
const rScale = d3.scaleSqrt().domain([0, popExt[1]]).range([4, 40]);

const sorted = [...data].sort((a, b) => a.anglo - b.anglo);
sorted.forEach(d => {{
  const r = Math.max(rScale(d.pop), 4);
  const color = d.anglo ? "{RED}" : (d.y > 0 ? "{GREEN}" : "#999");
  const opacity = d.anglo ? 0.75 : 0.35;

  svg.append("circle")
    .attr("cx", x(d.x)).attr("cy", y(d.y)).attr("r", r)
    .attr("fill", color).attr("opacity", opacity)
    .attr("stroke", d.anglo ? "{BLACK}" : "none").attr("stroke-width", d.anglo ? 1.5 : 0);
}});

// Labels
sorted.forEach(d => {{
  const r = Math.max(rScale(d.pop), 4);
  const show = d.anglo || Math.abs(d.y) > 0.6 || Math.abs(d.x) > 8;
  if (!show) return;
  const ly = y(d.y) - r - 6;
  svg.append("text").attr("x", x(d.x)).attr("y", ly)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", d.anglo ? 15 : 12)
    .attr("font-weight", d.anglo ? 500 : 300)
    .attr("fill", "{BG}").attr("stroke", "{BG}").attr("stroke-width", 4)
    .attr("stroke-linejoin", "round").attr("paint-order", "stroke")
    .attr("text-anchor", "middle").text(d.anglo ? d.country : d.iso3);
  svg.append("text").attr("x", x(d.x)).attr("y", ly)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", d.anglo ? 15 : 12)
    .attr("font-weight", d.anglo ? 500 : 300)
    .attr("fill", d.anglo ? "{BLACK}" : "#666")
    .attr("text-anchor", "middle").text(d.anglo ? d.country : d.iso3);
}});

// Stats
svg.append("text").attr("x", chartRight).attr("y", chartTop + 20)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 16).attr("font-weight", 400)
  .attr("fill", "{BLACK}").attr("text-anchor", "end")
  .text(`R² = ${{r2.toFixed(3)}}  (p = ${{pval.toFixed(3)}}, n = ${{n}})`);

// Source
svg.append("text").attr("x", margin.left).attr("y", sourceY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 15).attr("font-weight", 200)
  .attr("fill", "{BLACK}")
  .text("Sources: CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat CNMIGRAT; Gallup World Poll via WHR 2019/2026");
svg.append("text").attr("x", margin.left).attr("y", sourceY + 18)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 15).attr("font-weight", 200)
  .attr("fill", "{BLACK}")
  .text("Note: Bubble size = population. Anglophone countries highlighted in orange.");

svg.append("image")
  .attr("xlink:href", "data:image/png;base64,{logo_b64}")
  .attr("width", 130).attr("opacity", 0.6)
  .attr("x", chartRight - 130).attr("y", sourceY - 5);

</script></body></html>"""

    with open(OUT / f"{filename}.html", "w") as f:
        f.write(html)
    print(f"\nSaved {filename}.html")


def main():
    imm, hap = load_data()
    print(f"Immigration: {imm['iso3'].nunique()} countries, {imm['year'].min()}-{imm['year'].max()}")
    print(f"Happiness: {hap['iso3'].nunique()} countries, {hap['year'].min()}-{hap['year'].max()}")

    # Spec 1
    r2, p, slope = spec1_cross_sectional(imm, hap)

    # Spec 2
    sweep = spec2_horizon_sweep(imm, hap)

    # Spec 3
    model = spec3_panel(imm, hap)

    # Spec 4
    spec4_lags(imm, hap)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Spec 1 (cross-sectional): R² = {r2:.3f}, p = {p:.4f}, slope = {slope:+.4f}")
    print(f"Spec 3 (panel FD + year FE): coeff = {model.params['d_imm']:.4f}, p = {model.pvalues['d_imm']:.4f}")


if __name__ == "__main__":
    main()
