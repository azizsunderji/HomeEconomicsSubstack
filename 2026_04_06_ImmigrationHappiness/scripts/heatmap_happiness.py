#!/usr/bin/env python3
"""Heatmap: happiness by country (ranked by GDP), 2005-2025.

Generates 4 versions:
1. Level (raw Cantril score)
2. 1-year change
3. 3-year change
4. 5-year change

Each has diagonal hashing for cells where immigration rate exceeds
the country's 2005-2015 average by >50%.
"""

import pandas as pd
import numpy as np
import json, base64, os
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
OUT = Path(__file__).parent.parent / "outputs"

BLACK = "#3D3733"; BG = "#F6F7F3"; BLUE = "#0BB4FF"; RED = "#F4743B"
GREEN = "#67A275"; SUBTITLE_COLOR = "#7F7570"; GRID_COLOR = "#e1e2e3"
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


def build_heatmap(hap, imm, gdp, mode, title, subtitle, filename):
    """Build one heatmap variant.

    mode: 'level', '1y_change', '3y_change', '5y_change'
    """
    ANGLO = ["USA", "CAN", "GBR", "AUS", "NZL", "IRL"]
    years = list(range(2006, 2026))
    names = hap.drop_duplicates("iso3").set_index("iso3")["country"].to_dict()

    # Interpolate missing happiness years (only when data exists on both sides)
    hap_interp = []
    for iso3, grp in hap.groupby("iso3"):
        grp = grp.sort_values("year").set_index("year")["cantril"]
        # Reindex to full year range and interpolate (limit_direction='both' only fills interior gaps)
        full_range = range(int(grp.index.min()), int(grp.index.max()) + 1)
        filled = grp.reindex(full_range).interpolate(method="linear", limit_area="inside")
        for yr, val in filled.items():
            if pd.notna(val):
                source = "interpolated" if yr not in grp.index else "observed"
                hap_interp.append({"iso3": iso3, "year": yr, "cantril": val,
                                   "country": names.get(iso3, iso3), "source": source})
    hap = pd.DataFrame(hap_interp)

    # Rank countries by GDP (richest first)
    gdp_rank = gdp.sort_values("gdp_percapita", ascending=False)
    country_order = [iso3 for iso3 in gdp_rank["iso3"] if iso3 in hap["iso3"].unique()]

    # Compute immigration surge threshold per country: >100% above 2005-2015 median
    # Floor of 10/1000 for countries with low/negative baselines
    imm_thresholds = {}
    for iso3, grp in imm.groupby("iso3"):
        baseline_vals = grp[grp["year"].between(2005, 2015)]["rate_per1000"].dropna()
        baseline = baseline_vals.median() if len(baseline_vals) > 0 else 0
        if pd.notna(baseline) and baseline > 0:
            imm_thresholds[iso3] = max(baseline * 2.0, 10)
        else:
            imm_thresholds[iso3] = 10

    # Build cell data
    cells = []
    for iso3 in country_order:
        h_sub = hap[hap["iso3"] == iso3].set_index("year")["cantril"]
        i_sub = imm[imm["iso3"] == iso3].set_index("year")["rate_per1000"]

        for yr in years:
            val = None
            if mode == "level":
                val = h_sub.get(yr)
            elif mode == "1y_change":
                cur = h_sub.get(yr)
                prev = h_sub.get(yr - 1)
                if cur is not None and prev is not None:
                    val = cur - prev
            elif mode == "3y_change":
                cur = h_sub.get(yr)
                prev = h_sub.get(yr - 3)
                if cur is not None and prev is not None:
                    val = cur - prev
            elif mode == "5y_change":
                cur = h_sub.get(yr)
                prev = h_sub.get(yr - 5)
                if cur is not None and prev is not None:
                    val = cur - prev

            # Distance from peak for +/- markers
            cur_h = h_sub.get(yr)
            # Compute rolling peak up to this year
            past_vals = [h_sub.get(y) for y in range(int(h_sub.index.min()), yr + 1)
                         if h_sub.get(y) is not None and pd.notna(h_sub.get(y))]
            peak_so_far = max(past_vals) if past_vals else None
            dist_from_peak = None
            if cur_h is not None and peak_so_far is not None and pd.notna(cur_h):
                dist_from_peak = round(float(cur_h - peak_so_far), 3)

            # Immigration surge check
            imm_rate = i_sub.get(yr)
            threshold = imm_thresholds.get(iso3, 999)
            surge = bool(pd.notna(imm_rate) and imm_rate > threshold)

            cells.append({
                "iso3": iso3,
                "year": yr,
                "val": round(float(val), 3) if pd.notna(val) else None,
                "surge": surge,
                "dfp": dist_from_peak,
            })

    # Country metadata with long-term happiness change
    countries_meta = []
    for iso3 in country_order:
        h_sub = hap[hap["iso3"] == iso3].sort_values("year")
        if len(h_sub) >= 4:
            first_val = h_sub.head(2)["cantril"].mean()
            last_val = h_sub.tail(2)["cantril"].mean()
            lt_change = round(float(last_val - first_val), 2)
            first_yr = int(h_sub["year"].iloc[0])
            last_yr = int(h_sub["year"].iloc[-1])
        else:
            lt_change = None
            first_yr = None
            last_yr = None

        countries_meta.append({
            "iso3": iso3,
            "name": names.get(iso3, iso3),
            "anglo": iso3 in ANGLO,
            "gdp": round(float(gdp[gdp["iso3"] == iso3]["gdp_percapita"].iloc[0]) / 1000, 1)
            if iso3 in gdp["iso3"].values else None,
            "ltChange": lt_change,
            "ltYears": f"{first_yr}\u2013{last_yr}" if first_yr else None,
        })

    data_json = json.dumps({"cells": cells, "countries": countries_meta, "years": years})
    logo_b64, font_faces = get_brand_assets()

    n_countries = len(country_order)
    cellW = 34
    cellH = 22
    labelW = 145
    gdpW = 45
    changeColW = 55  # width for the long-term change column on the right
    chartLeft = 40 + labelW + gdpW
    chartTop = 170
    chartWidth = len(years) * cellW
    H = chartTop + n_countries * cellH + 100

    # Custom color interpolator (teal → warm neutral → burnt orange)
    # #0d6e6e (happy) → #6db8a5 → #f5f0e1 (mid) → #e4a94d → #c4561a (unhappy)
    color_interpolator = """function(t) {
      const colors = [
        [13,110,110],   // #0d6e6e — deep teal (happiest)
        [109,184,165],  // #6db8a5 — soft teal
        [245,240,225],  // #f5f0e1 — warm neutral
        [228,169,77],   // #e4a94d — amber
        [196,86,26]     // #c4561a — burnt orange (least happy)
      ];
      t = Math.max(0, Math.min(1, t));
      const idx = t * (colors.length - 1);
      const i = Math.floor(idx);
      const f = idx - i;
      const c0 = colors[Math.min(i, colors.length - 1)];
      const c1 = colors[Math.min(i + 1, colors.length - 1)];
      const r = Math.round(c0[0] + f * (c1[0] - c0[0]));
      const g = Math.round(c0[1] + f * (c1[1] - c0[1]));
      const b = Math.round(c0[2] + f * (c1[2] - c0[2]));
      return `rgb(${r},${g},${b})`;
    }"""

    # Color scale config
    if mode == "level":
        # Map 5.0→1 (unhappy, orange) and 8.0→0 (happy, teal)
        color_config = f"(v) => ({color_interpolator})((8.0 - v) / 3.0)"
        legend_domain = [5.0, 8.0]
        legend_labels = ["5.0", "6.0", "7.0", "8.0"]
        legend_title = "Life satisfaction (Cantril ladder)"
    else:
        # Map -1→1 (decline, orange) and +1→0 (improvement, teal)
        color_config = f"(v) => ({color_interpolator})((1.0 - v) / 2.0)"
        legend_domain = [-1.0, 1.0]
        legend_labels = ["-1.0", "-0.5", "0", "+0.5", "+1.0"]
        legend_title = "Change in life satisfaction"

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
const labelW = {labelW}, gdpW = {gdpW};

const d = {data_json};
const years = d.years;
const countries = d.countries;

const svg = d3.select("body").append("svg")
  .attr("width", W).attr("height", H).attr("viewBox", `0 0 ${{W}} ${{H}}`);

svg.append("rect").attr("width", W).attr("height", H).attr("fill", "{BG}");

// Color scale (defined early so legend can use it)
const color = {color_config};

// Hashing pattern
const defs = svg.append("defs");
const pattern = defs.append("pattern")
  .attr("id", "diag-hatch")
  .attr("patternUnits", "userSpaceOnUse")
  .attr("width", 4).attr("height", 4)
  .attr("patternTransform", "rotate(45)");
pattern.append("line")
  .attr("x1", 0).attr("x2", 0).attr("y1", 0).attr("y2", 4)
  .attr("stroke", "{BLACK}").attr("stroke-width", 2).attr("opacity", 0.55);

// Title
svg.append("text").attr("x", 40).attr("y", 72)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 32).attr("font-weight", 500)
  .attr("fill", "{BLACK}").text("{title}");

svg.append("text").attr("x", 40).attr("y", 106)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 21).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").text("{subtitle}");

// Legend — hashing explanation
const legY = 128;
svg.append("rect").attr("x", 40).attr("y", legY - 12).attr("width", 16).attr("height", 16)
  .attr("fill", "#aab866").attr("rx", 2);
svg.append("rect").attr("x", 41.5).attr("y", legY - 10.5).attr("width", 13).attr("height", 13)
  .attr("fill", "none").attr("stroke", "{BLACK}").attr("stroke-width", 2).attr("rx", 1);
svg.append("text").attr("x", 62).attr("y", legY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 13).attr("font-weight", 400)
  .attr("fill", "{BLACK}").text("Black border = immigration rate double 2005\u201315 avg");

// Change column header
const changeHeaderX = chartLeft + years.length * cellW + 8;
svg.append("text").attr("x", changeHeaderX + {changeColW} / 2).attr("y", chartTop - 30)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 500)
  .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "middle").text("Change");
svg.append("text").attr("x", changeHeaderX + {changeColW} / 2).attr("y", chartTop - 18)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 9).attr("font-weight", 300)
  .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "middle").text("(full period)");

// Color scale legend
const legBarX = chartLeft + 14 * cellW;
const legBarW = 150, legBarH = 12;
const legGrad = svg.append("defs").append("linearGradient")
  .attr("id", "color-legend").attr("x1", "0%").attr("x2", "100%");
for (let i = 0; i <= 10; i++) {{
  const t = i / 10;
  const v = {legend_domain[0]} + t * ({legend_domain[1]} - {legend_domain[0]});
  legGrad.append("stop").attr("offset", (t * 100) + "%").attr("stop-color", color(v));
}}
svg.append("rect").attr("x", legBarX).attr("y", legY - 12).attr("width", legBarW).attr("height", legBarH)
  .attr("fill", "url(#color-legend)").attr("rx", 2);
// Legend labels
const legLabels = {json.dumps(legend_labels)};
legLabels.forEach((lab, i) => {{
  const lx = legBarX + (i / (legLabels.length - 1)) * legBarW;
  svg.append("text").attr("x", lx).attr("y", legY + 10)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 300)
    .attr("fill", "#666").attr("text-anchor", "middle").text(lab);
}});
svg.append("text").attr("x", legBarX + legBarW / 2).attr("y", legY - 17)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "middle").text("{legend_title}");

// Facebook / iPhone markers
const fbYear = 2006, iphoneYear = 2007;
const fbX = chartLeft + (fbYear - years[0]) * cellW + cellW / 2;
const ipX = chartLeft + (iphoneYear - years[0]) * cellW + cellW / 2;

svg.append("text").attr("x", fbX).attr("y", chartTop - 18)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "middle").text("Facebook");
svg.append("line").attr("x1", fbX).attr("x2", fbX)
  .attr("y1", chartTop - 12).attr("y2", chartTop + countries.length * cellH)
  .attr("stroke", "{BLACK}").attr("stroke-width", 1).attr("stroke-dasharray", "4,3").attr("opacity", 0.3);

svg.append("text").attr("x", ipX).attr("y", chartTop - 6)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 10).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}").attr("text-anchor", "middle").text("iPhone");
svg.append("line").attr("x1", ipX).attr("x2", ipX)
  .attr("y1", chartTop).attr("y2", chartTop + countries.length * cellH)
  .attr("stroke", "{BLACK}").attr("stroke-width", 1).attr("stroke-dasharray", "4,3").attr("opacity", 0.2);

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

// Rows
countries.forEach((c, ci) => {{
  const rowY = chartTop + ci * cellH;

  // Country label
  svg.append("text")
    .attr("x", 40 + labelW - 5).attr("y", rowY + cellH / 2 + 4)
    .attr("font-family", "ABC Oracle Edu")
    .attr("font-size", c.anglo ? 13 : 12)
    .attr("font-weight", c.anglo ? 700 : 300)
    .attr("fill", c.anglo ? "{RED}" : "{BLACK}")
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
    if (!cell || cell.val === null) return;

    const cx = chartLeft + yi * cellW;

    // Color cell
    svg.append("rect")
      .attr("x", cx).attr("y", rowY)
      .attr("width", cellW - 1).attr("height", cellH - 1)
      .attr("fill", color(cell.val))
      .attr("rx", 1);

    // Immigration surge — inset black border
    if (cell.surge) {{
      svg.append("rect")
        .attr("x", cx + 1.5).attr("y", rowY + 1.5)
        .attr("width", cellW - 4).attr("height", cellH - 4)
        .attr("fill", "none")
        .attr("stroke", "{BLACK}").attr("stroke-width", 2)
        .attr("rx", 1);
    }}

  }});

  // Long-term change indicator on the right
  const changeX = chartLeft + years.length * cellW + 8;
  if (c.ltChange !== null && c.ltChange !== undefined) {{
    const isPos = c.ltChange >= 0;
    const symbol = isPos ? "+" : "\u2212";
    const absChange = Math.abs(c.ltChange);
    // Opacity proportional to magnitude (0.2 = faint, 0.8+ = bold)
    const maxChange = 1.5;
    const opacity = Math.min(0.25 + (absChange / maxChange) * 0.65, 0.9);
    const changeColor = isPos ? "rgb(13,110,110)" : "rgb(196,86,26)";

    svg.append("text")
      .attr("x", changeX + {changeColW} / 2).attr("y", rowY + cellH / 2 + 6)
      .attr("font-family", "ABC Oracle Edu").attr("font-size", 15).attr("font-weight", 700)
      .attr("fill", changeColor).attr("opacity", opacity).attr("text-anchor", "middle")
      .text(symbol + absChange.toFixed(1));
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

    with open(OUT / f"{filename}.html", "w") as f:
        f.write(html)
    print(f"Saved {filename}.html")


def main():
    hap = pd.read_csv(DATA / "happiness_combined.csv")
    imm = pd.read_csv(DATA / "oecd_immigration_net.csv")
    gdp = pd.read_csv("/Users/azizsunderji/Dropbox/Home Economics/2026_03_31_HousingHappiness/data/wb_gdp_percapita.csv")

    configs = [
        ("level", "Rich, unhappy", "Life satisfaction by country (ranked by GDP per capita), 2006\u20132025", "heatmap_happiness_level"),
        ("1y_change", "Rich, unhappy", "1-year change in life satisfaction, ranked by GDP per capita", "heatmap_happiness_1y"),
        ("3y_change", "Rich, unhappy", "3-year change in life satisfaction, ranked by GDP per capita", "heatmap_happiness_3y"),
        ("5y_change", "Rich, unhappy", "5-year change in life satisfaction, ranked by GDP per capita", "heatmap_happiness_5y"),
    ]

    for mode, title, subtitle, filename in configs:
        build_heatmap(hap, imm, gdp, mode, title, subtitle, filename)


if __name__ == "__main__":
    main()
