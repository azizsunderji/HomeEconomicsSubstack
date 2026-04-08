#!/usr/bin/env python3
"""Small multiples: cumulative net migration per capita since 2000.

Each panel shows one country in blue with all others in light grey behind.
Y-axis = cumulative net migrants per 1,000 population since start year.
"""

import pandas as pd
import numpy as np
import json, base64, os
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
OUT = Path(__file__).parent.parent / "outputs"

BLACK = "#3D3733"
BG = "#F6F7F3"
BLUE = "#0BB4FF"
SUBTITLE_COLOR = "#7F7570"
GRID_COLOR = "#e1e2e3"

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
LOGO_PATH = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png"

ANGLOPHONE = ["USA", "CAN", "GBR", "AUS", "NZL", "IRL"]


def main():
    df = pd.read_csv(DATA / "oecd_immigration_net.csv")
    names = df.drop_duplicates("iso3").set_index("iso3")["country"].to_dict()

    # Compute cumulative rate per 1000 from each country's first year
    all_series = {}
    for iso3, grp in df.groupby("iso3"):
        grp = grp.sort_values("year")
        grp = grp[grp["rate_per1000"].notna()].copy()
        if len(grp) < 5:
            continue
        grp["cumulative"] = grp["rate_per1000"].cumsum()
        pts = [{"year": int(r["year"]), "cum": round(float(r["cumulative"]), 1)}
               for _, r in grp.iterrows()]
        all_series[iso3] = pts

    # Sort countries: Anglophone first, then by latest cumulative (descending)
    def sort_key(iso3):
        pts = all_series[iso3]
        latest_cum = pts[-1]["cum"] if pts else 0
        is_anglo = 0 if iso3 in ANGLOPHONE else 1
        return (is_anglo, -latest_cum)

    sorted_countries = sorted(all_series.keys(), key=sort_key)

    # Build chart data
    records = []
    for iso3 in sorted_countries:
        records.append({
            "iso3": iso3,
            "country": names.get(iso3, iso3),
            "anglo": iso3 in ANGLOPHONE,
            "points": all_series[iso3],
        })

    # All series for background
    all_bg = []
    for iso3, pts in all_series.items():
        all_bg.append({"iso3": iso3, "points": pts})

    data_json = json.dumps(records)
    bg_json = json.dumps(all_bg)

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

    n = len(records)
    cols = 5
    rows = int(np.ceil(n / cols))
    cellW = 178
    cellH = 150
    gapX = 8
    gapY = 8
    gridLeft = 40
    gridTop = 140
    H = gridTop + rows * (cellH + gapY) + 80

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
const cols = {cols}, rows = {rows};
const cellW = {cellW}, cellH = {cellH};
const cellPadL = 8, cellPadR = 5, cellPadT = 28, cellPadB = 18;
const gridLeft = {gridLeft}, gridTop = {gridTop};
const gapX = {gapX}, gapY = {gapY};

const data = {data_json};
const bgData = {bg_json};

const svg = d3.select("body").append("svg")
  .attr("width", W).attr("height", H).attr("viewBox", `0 0 ${{W}} ${{H}}`);

svg.append("rect").attr("width", W).attr("height", H).attr("fill", "{BG}");

// Title
svg.append("text").attr("x", 40).attr("y", 72)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 32).attr("font-weight", 500)
  .attr("fill", "{BLACK}").text("Cumulative immigration since 2000");

svg.append("text").attr("x", 40).attr("y", 106)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 23).attr("font-weight", 400)
  .attr("fill", "{SUBTITLE_COLOR}")
  .text("Cumulative net migrants per 1,000 population, rebased to zero");

// Global y domain across all countries
const allCums = bgData.flatMap(s => s.points.map(p => p.cum));
const globalYMin = Math.min(0, d3.min(allCums));
const globalYMax = d3.max(allCums);
const yPad = (globalYMax - globalYMin) * 0.05;

data.forEach((country, i) => {{
  const col = i % cols, row = Math.floor(i / cols);
  const cx = gridLeft + col * (cellW + gapX);
  const cy = gridTop + row * (cellH + gapY);

  const g = svg.append("g").attr("transform", `translate(${{cx}},${{cy}})`);

  // Cell background
  g.append("rect").attr("width", cellW).attr("height", cellH)
    .attr("fill", "#FFFFFF").attr("rx", 3).attr("opacity", 0.35);

  // Country name
  g.append("text").attr("x", cellPadL + 2).attr("y", 18)
    .attr("font-family", "ABC Oracle Edu")
    .attr("font-size", country.anglo ? 13 : 12)
    .attr("font-weight", country.anglo ? 700 : 500)
    .attr("fill", country.anglo ? "{BLUE}" : "{BLACK}")
    .text(country.country);

  // Scales — shared y domain
  const x = d3.scaleLinear()
    .domain([2000, 2025])
    .range([cellPadL, cellW - cellPadR]);
  const y = d3.scaleLinear()
    .domain([globalYMin - yPad, globalYMax + yPad])
    .range([cellH - cellPadB, cellPadT]);

  // Zero line
  g.append("line")
    .attr("x1", cellPadL).attr("x2", cellW - cellPadR)
    .attr("y1", y(0)).attr("y2", y(0))
    .attr("stroke", "{GRID_COLOR}").attr("stroke-width", 0.5);

  // Light gridlines
  const yTicks = y.ticks(3);
  yTicks.forEach(t => {{
    if (t === 0) return;
    g.append("line")
      .attr("x1", cellPadL).attr("x2", cellW - cellPadR)
      .attr("y1", y(t)).attr("y2", y(t))
      .attr("stroke", "{GRID_COLOR}").attr("stroke-width", 0.3);
  }});

  // Y-axis labels (only leftmost column)
  if (col === 0) {{
    yTicks.forEach(t => {{
      g.append("text").attr("x", cellPadL - 2).attr("y", y(t) + 3)
        .attr("font-family", "ABC Oracle Edu").attr("font-size", 8).attr("font-weight", 300)
        .attr("fill", "#aaa").attr("text-anchor", "end").text(t.toFixed(0));
    }});
  }}

  // X-axis labels (bottom row only)
  if (row === rows - 1 || i === data.length - 1) {{
    [2000, 2012, 2025].forEach(yr => {{
      g.append("text").attr("x", x(yr)).attr("y", cellH - 3)
        .attr("font-family", "ABC Oracle Edu").attr("font-size", 8).attr("font-weight", 300)
        .attr("fill", "#aaa").attr("text-anchor", "middle")
        .text(yr === 2000 ? "'00" : yr === 2012 ? "'12" : "'25");
    }});
  }}

  const line = d3.line().x(d => x(d.year)).y(d => y(d.cum));

  // Background: all other countries in light grey
  bgData.forEach(bg => {{
    if (bg.iso3 === country.iso3) return;
    if (bg.points.length < 2) return;
    g.append("path").datum(bg.points)
      .attr("d", line).attr("fill", "none")
      .attr("stroke", "#ddd").attr("stroke-width", 0.5);
  }});

  // Foreground: this country in blue
  g.append("path").datum(country.points)
    .attr("d", line).attr("fill", "none")
    .attr("stroke", "{BLUE}").attr("stroke-width", 2);

  // End value label
  const last = country.points[country.points.length - 1];
  g.append("text")
    .attr("x", cellW - cellPadR).attr("y", y(last.cum) - 4)
    .attr("font-family", "ABC Oracle Edu").attr("font-size", 9).attr("font-weight", 500)
    .attr("fill", "{BLUE}").attr("text-anchor", "end")
    .text(last.cum.toFixed(0));
}});

// Source
const sourceY = H - 45;
svg.append("text").attr("x", 40).attr("y", sourceY)
  .attr("font-family", "ABC Oracle Edu").attr("font-size", 14).attr("font-weight", 200)
  .attr("fill", "{BLACK}")
  .text("Sources: CBO (US), Statistics Canada, ONS (UK), ABS (AUS), Stats NZ, Eurostat CNMIGRAT, national stats offices");

svg.append("image")
  .attr("xlink:href", "data:image/png;base64,{logo_b64}")
  .attr("width", 120).attr("opacity", 0.6)
  .attr("x", W - 40 - 120).attr("y", sourceY - 10);

</script></body></html>"""

    with open(OUT / "small_multiples_cumulative_migration.html", "w") as f:
        f.write(html)
    print(f"Saved small_multiples_cumulative_migration.html ({n} countries, {cols}x{rows} grid)")


if __name__ == "__main__":
    main()
