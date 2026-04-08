#!/usr/bin/env python3
"""Bivariate heatmap: happiness level × change direction.

Each cell colored by TWO dimensions:
- Level: how happy (Cantril score)
- Change: 3-year trailing change (improving/stable/declining)

3×3 color grid with immigration surge borders.
"""

import pandas as pd
import numpy as np
import json, base64, os
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
OUT = Path(__file__).parent.parent / "outputs"

BLACK = "#3D3733"; BG = "#F6F7F3"; SUBTITLE_COLOR = "#7F7570"; GRID_COLOR = "#e1e2e3"
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
LOGO_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png"


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


def main():
    hap = pd.read_csv(DATA / "happiness_combined.csv")
    imm = pd.read_csv(DATA / "oecd_immigration_net.csv")
    gdp = pd.read_csv("/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness/data/wb_gdp_percapita.csv")
    names = hap.drop_duplicates("iso3").set_index("iso3")["country"].to_dict()

    ANGLO = ["USA", "CAN", "GBR", "AUS", "NZL", "IRL"]
    years = list(range(2006, 2026))

    # Interpolate gaps
    hap_interp = []
    for iso3, grp in hap.groupby("iso3"):
        grp = grp.sort_values("year").set_index("year")["cantril"]
        full_range = range(int(grp.index.min()), int(grp.index.max()) + 1)
        filled = grp.reindex(full_range).interpolate(method="linear", limit_area="inside")
        for yr, val in filled.items():
            if pd.notna(val):
                hap_interp.append({"iso3": iso3, "year": yr, "cantril": val,
                                   "country": names.get(iso3, iso3)})
    hap = pd.DataFrame(hap_interp)

    # Rank by GDP, exclude countries with incomplete data
    EXCLUDE = {"LUX", "ISL", "MLT", "HRV", "BGR"}
    gdp_rank = gdp.sort_values("gdp_percapita", ascending=False)
    country_order = [iso3 for iso3 in gdp_rank["iso3"]
                     if iso3 in hap["iso3"].unique() and iso3 not in EXCLUDE]

    # Immigration threshold: top quartile of all per-capita rates in the dataset
    EXCLUDE_COUNTRIES = {"LUX", "ISL", "MLT", "HRV", "BGR"}
    all_rates = imm[(imm["year"].between(2006, 2025)) & (~imm["iso3"].isin(EXCLUDE_COUNTRIES))]["rate_per1000"].dropna()
    imm_top_quartile = all_rates.quantile(0.80)
    print(f"Immigration border threshold (75th pct): {imm_top_quartile:.1f}/1000")

    # Level threshold (median across all data)
    all_vals = hap[hap["year"].isin(years)]["cantril"].dropna()
    level_mid = all_vals.median()

    # Build cell data
    cells = []
    for iso3 in country_order:
        h_sub = hap[hap["iso3"] == iso3].set_index("year")["cantril"]
        i_sub = imm[imm["iso3"] == iso3].set_index("year")["rate_per1000"]

        for yr in years:
            level = h_sub.get(yr)
            if level is None or pd.isna(level):
                cells.append({"iso3": iso3, "year": yr, "biv": None, "surge": False})
                continue

            # 1-year change
            prev = h_sub.get(yr - 1)
            if prev is not None and pd.notna(prev):
                change = level - prev
            else:
                change = 0  # no prior year, assume stable

            # Classify into 2×2 grid
            # Level: 0=below median, 1=above median
            lev = 1 if level >= level_mid else 0

            # Change: 0=declining (negative), 1=improving (zero or positive)
            chg = 1 if change >= 0 else 0

            biv = lev * 2 + chg  # 0-3 index into 2x2 grid

            # Immigration: two tiers — high (10-14) and extreme (15+)
            imm_rate = i_sub.get(yr)
            surge = 0  # 0 = none, 1 = high, 2 = extreme
            if pd.notna(imm_rate):
                rounded = round(float(imm_rate))
                if rounded >= 15:
                    surge = 2
                elif rounded >= 10:
                    surge = 1

            cells.append({
                "iso3": iso3, "year": yr,
                "biv": biv, "surge": surge,
                "level": round(float(level), 2),
                "change": round(float(change), 2),
            })

    # Country metadata with long-term change
    countries_meta = []
    for iso3 in country_order:
        h_sub = hap[hap["iso3"] == iso3].sort_values("year")
        if len(h_sub) >= 4:
            first_val = h_sub.head(2)["cantril"].mean()
            last_val = h_sub.tail(2)["cantril"].mean()
            lt_change = round(float(last_val - first_val), 2)
        else:
            lt_change = None
        # Find peak happiness year
        peak_yr = None
        if len(h_sub) > 0:
            peak_row = h_sub.loc[h_sub["cantril"].idxmax()]
            peak_yr = int(peak_row["year"])

        countries_meta.append({
            "iso3": iso3,
            "name": names.get(iso3, iso3),
            "anglo": iso3 in ANGLO,
            "gdp": round(float(gdp[gdp["iso3"] == iso3]["gdp_percapita"].iloc[0]) / 1000, 1)
            if iso3 in gdp["iso3"].values else None,
            "ltChange": lt_change,
            "peakYr": peak_yr,
        })

    data_json = json.dumps({"cells": cells, "countries": countries_meta, "years": years,
                            "levelMid": round(level_mid, 2)})
    logo_b64, font_faces = get_brand_assets()

    n_countries = len(country_order)
    cellW = 34
    cellH = 32
    labelW = 145
    gdpW = 45
    changeColW = 55
    chartLeft = 40 + labelW + gdpW
    chartTop = 185
    H = chartTop + n_countries * cellH + 100

    # 3×3 bivariate color grid
    # Rows = change (declining, stable, improving)
    # Cols = level (low, medium, high)
    #
    #                  Low happiness    Mid happiness    High happiness
    # Declining        #c4561a          #8c7e8a          #5a8a8a
    #                  (dark orange)    (muted mauve)    (steel teal)
    # Stable           #e4a94d          #c8c0a8          #6db8a5
    #                  (amber)          (warm grey)      (soft teal)
    # Improving        #dcc66e          #8ec48e          #0d6e6e
    #                  (gold)           (sage green)     (deep teal)

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
const W = 960, H = {H};
const cellW = {cellW}, cellH = {cellH};
const chartLeft = {chartLeft}, chartTop = {chartTop};
const labelW = {labelW}, gdpW = {gdpW}, changeColW = {changeColW};

const d = {data_json};
const years = d.years;
const countries = d.countries;

const svg = d3.select("body").append("svg")
  .attr("width", W).attr("height", H).attr("viewBox", `0 0 ${{W}} ${{H}}`);

svg.append("rect").attr("width", W).attr("height", H).attr("fill", "{BG}");

// Hashing pattern
const defs = svg.append("defs");
const pattern = defs.append("pattern")
  .attr("id", "diag-hatch")
  .attr("patternUnits", "userSpaceOnUse")
  .attr("width", 4).attr("height", 4)
  .attr("patternTransform", "rotate(45)");
pattern.append("line")
  .attr("x1", 0).attr("x2", 0).attr("y1", 0).attr("y2", 4)
  .attr("stroke", "{BLACK}").attr("stroke-width", 2).attr("opacity", 0.35);

// 2×2 bivariate colors [level * 2 + change]
// Index: level(0=below median, 1=above median) * 2 + change(0=declining, 1=improving)
const bivColors = [
  "#de9070",  // 0: below median + declining
  "#ebc06e",  // 1: below median + improving
  "#c2e0d9",  // 2: above median + declining (lighter teal)
  "#5bb8a6",  // 3: above median + improving (lighter teal)
];

// Title
svg.append("text").attr("x", 40).attr("y", 72)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 32).attr("font-weight", 500)
  .attr("fill", "{BLACK}").text("Rich, unhappy");

svg.append("text").attr("x", 40).attr("y", 106)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 21).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}")
  .text("Happiness level \u00d7 1-year change, ranked by GDP per capita, 2006\u20132025");

// Bivariate legend (2×2 grid)
const legX = 40, legY = 120;
const legCellW = 22, legCellH = 18;

// Grid cells: rows = change (declining bottom, improving top), cols = level (low left, high right)
for (let lev = 0; lev < 2; lev++) {{
  for (let chg = 0; chg < 2; chg++) {{
    const idx = lev * 2 + chg;
    svg.append("rect")
      .attr("x", legX + 70 + lev * legCellW)
      .attr("y", legY + (1 - chg) * legCellH)
      .attr("width", legCellW - 1).attr("height", legCellH - 1)
      .attr("fill", bivColors[idx]);
  }}
}}

// Corner labels
svg.append("text").attr("x", legX + 70 + 2 * legCellW + 5).attr("y", legY + 10)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 400)
  .attr("fill", "#5bb8a6").text("Happy + improving");
svg.append("text").attr("x", legX + 70 - 5).attr("y", legY + 2 * legCellH - 3)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 400)
  .attr("fill", "#de9070").attr("text-anchor", "end").text("Unhappy + declining");

// Immigration legend — two tiers
const legImmX = legX + 200;
const tiers = [
  {{sw: 1.2, label: "High"}},
  {{sw: 2.5, label: "Extreme"}},
];
svg.append("text").attr("x", legImmX).attr("y", legY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 12).attr("font-weight", 400)
  .attr("fill", "{BLACK}").text("Black border = net migration rate:");
tiers.forEach((t, i) => {{
  const tx = legImmX + i * 70;
  svg.append("rect").attr("x", tx).attr("y", legY + 6).attr("width", 16).attr("height", 16)
    .attr("fill", "#c2e0d9");
  const inset = 1.25;
  const r = svg.append("rect").attr("x", tx + inset).attr("y", legY + 6 + inset)
    .attr("width", 16 - inset * 2).attr("height", 16 - inset * 2)
    .attr("fill", "none").attr("stroke", "{BLACK}").attr("stroke-width", 1.5);
  if (i === 0) r.attr("stroke-dasharray", "2,2");
  svg.append("text").attr("x", tx + 20).attr("y", legY + 18)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 300)
    .attr("fill", "{BLACK}").text(t.label);
}});

// Year labels
years.forEach((yr, i) => {{
  svg.append("text")
    .attr("x", chartLeft + i * cellW + cellW / 2)
    .attr("y", chartTop - 30)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 11).attr("font-weight", 300)
    .attr("fill", "#999").attr("text-anchor", "middle")
    .text(yr % 5 === 0 ? yr : "'" + String(yr).slice(2));
}});

// GDP header
svg.append("text").attr("x", 40 + labelW + gdpW / 2).attr("y", chartTop - 30)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "middle").text("GDP/cap");

// Change column header
const changeHeaderX = chartLeft + years.length * cellW + 8;
svg.append("text").attr("x", changeHeaderX + changeColW / 2).attr("y", chartTop - 30)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 500)
  .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "middle").text("Change");
svg.append("text").attr("x", changeHeaderX + changeColW / 2).attr("y", chartTop - 18)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 9).attr("font-weight", 300)
  .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "middle").text("(full period)");

// Rows
countries.forEach((c, ci) => {{
  const rowY = chartTop + ci * cellH;

  // Country label
  svg.append("text")
    .attr("x", 40 + labelW - 5).attr("y", rowY + cellH / 2 + 4)
    .attr("font-family", "ABC Oracle Edu")
    .attr("font-size", 12)
    .attr("font-weight", 300)
    .attr("fill", "{BLACK}")
    .attr("text-anchor", "end")
    .text(c.name);

  // GDP label
  if (c.gdp) {{
    svg.append("text")
      .attr("x", 40 + labelW + gdpW - 5).attr("y", rowY + cellH / 2 + 4)
      .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 300)
      .attr("fill", "#999").attr("text-anchor", "end")
      .text("$" + c.gdp.toFixed(0) + "k");
  }}

  // Cells
  years.forEach((yr, yi) => {{
    const cell = d.cells.find(cl => cl.iso3 === c.iso3 && cl.year === yr);
    if (!cell || cell.biv === null) return;

    const cx = chartLeft + yi * cellW;

    svg.append("rect")
      .attr("x", cx).attr("y", rowY)
      .attr("width", cellW - 2).attr("height", cellH - 2)
      .attr("fill", bivColors[cell.biv]);

  }});

  // Immigration borders — merge contiguous runs of same tier
  const countryCells = years.map((yr, yi) => {{
    const cell = d.cells.find(cl => cl.iso3 === c.iso3 && cl.year === yr);
    return {{ yi, surge: (cell && cell.surge) || 0 }};
  }});

  let runStart = null;
  let runTier = 0;
  const drawRun = (start, end, tier) => {{
    if (tier === 0) return;
    const sw = 1.5;
    const inset = sw / 2 + 0.5;
    const x1 = chartLeft + start * cellW + inset;
    const w = (end - start + 1) * cellW - 2 - inset * 2;
    const rect = svg.append("rect")
      .attr("x", x1).attr("y", rowY + inset)
      .attr("width", w).attr("height", cellH - 2 - inset * 2)
      .attr("fill", "none").attr("stroke", "{BLACK}").attr("stroke-width", sw);
    if (tier === 1) {{
      rect.attr("stroke-dasharray", "1.5,2");
    }}
  }};

  countryCells.forEach((cc, i) => {{
    if (cc.surge > 0 && cc.surge === runTier) {{
      // continue run
    }} else {{
      if (runTier > 0) drawRun(runStart, i - 1, runTier);
      runStart = i;
      runTier = cc.surge;
    }}
  }});
  if (runTier > 0) drawRun(runStart, countryCells.length - 1, runTier);

  // Peak happiness year — subtle dot
  if (c.peakYr && c.peakYr >= years[0] && c.peakYr <= years[years.length - 1]) {{
    const peakCx = chartLeft + (c.peakYr - years[0]) * cellW + (cellW - 1) / 2;
    svg.append("circle")
      .attr("cx", peakCx).attr("cy", rowY + cellH / 2)
      .attr("r", 2.5)
      .attr("fill", "{BLACK}").attr("opacity", 0.3);
  }}

  // Long-term change indicator — circle + label
  if (c.ltChange !== null && c.ltChange !== undefined) {{
    const isPos = c.ltChange >= 0;
    const absChange = Math.abs(c.ltChange);
    const maxChange = 1.8;
    const radius = 3 + (absChange / maxChange) * 10;
    const changeColor = isPos ? "#5bb8a6" : "#de9070";
    const circleX = changeHeaderX + 12;

    svg.append("circle")
      .attr("cx", circleX).attr("cy", rowY + cellH / 2)
      .attr("r", radius)
      .attr("fill", changeColor).attr("opacity", 0.8);

    const label = (isPos ? "+" : "\u2212") + absChange.toFixed(1);
    svg.append("text")
      .attr("x", circleX + radius + 4).attr("y", rowY + cellH / 2 + 4)
      .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 300)
      .attr("fill", "{BLACK}")
      .text(label);
  }}
}});

// Source
const sourceY = H - 45;
svg.append("text").attr("x", 40).attr("y", sourceY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 14).attr("font-weight", 200)
  .attr("fill", "{BLACK}")
  .text("Sources: Gallup World Poll via WHR 2019/2026; CBO, Statistics Canada, ONS, ABS, Stats NZ, Eurostat; World Bank GDP");

svg.append("image")
  .attr("xlink:href", "data:image/png;base64,{logo_b64}")
  .attr("width", 120).attr("opacity", 0.6)
  .attr("x", W - 40 - 120).attr("y", sourceY - 10);

</script></body></html>"""

    with open(OUT / "heatmap_bivariate.html", "w") as f:
        f.write(html)
    print(f"Saved heatmap_bivariate.html")
    print(f"Level threshold (median): {level_mid:.2f}")
    print(f"Change: negative = declining, zero/positive = improving")


if __name__ == "__main__":
    main()
