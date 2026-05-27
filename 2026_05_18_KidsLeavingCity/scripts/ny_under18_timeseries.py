"""
Annual under-18 population for the New York CSA counties (5 boroughs + suburbs)
from PEP V2019 (2010-2019) + V2024 (2020-2024). Raw numbers, one line per county,
hover-to-highlight interaction.
"""
from __future__ import annotations
import json
from pathlib import Path
import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"
CACHE = DATA / "pep_cache"

# NY CSA counties
NY_STATES = ["09", "34", "36", "42"]

# County display name overrides
DISPLAY = {
    "36005": "Bronx",     "36047": "Brooklyn",       "36061": "Manhattan",
    "36081": "Queens",    "36085": "Staten Island",
    "36119": "Westchester", "36059": "Nassau", "36103": "Suffolk",
    "36087": "Rockland", "36079": "Putnam", "36071": "Orange (NY)",
    "36027": "Dutchess", "36111": "Ulster",
    "34003": "Bergen NJ", "34013": "Essex NJ", "34017": "Hudson NJ",
    "34019": "Hunterdon NJ", "34021": "Mercer NJ", "34023": "Middlesex NJ",
    "34025": "Monmouth NJ", "34027": "Morris NJ", "34029": "Ocean NJ",
    "34031": "Passaic NJ", "34035": "Somerset NJ", "34037": "Sussex NJ",
    "34039": "Union NJ", "34041": "Warren NJ",
    "09001": "Fairfield CT", "09005": "Litchfield CT", "09009": "New Haven CT",
    "42103": "Pike PA",
}

# Highlight colors for the 5 boroughs (brand palette) — others get muted greys
COLORS = {
    "36061": "#F4743B",  # Manhattan = red
    "36047": "#0BB4FF",  # Brooklyn = blue
    "36081": "#67A275",  # Queens = green
    "36005": "#FEC439",  # Bronx = yellow
    "36085": "#A32515",  # Staten Island = dark red
}
SUBURB_PALETTE = ["#8FA09E", "#A0B5B0", "#7E8F8C", "#909FA0", "#A1B2AF", "#7C8D8A", "#919FA2"]


def main():
    # Load NY CSA counties from CSA file (created earlier)
    csa = pd.read_csv(DATA / "csa_counties.csv", dtype={"fips_5": str})
    csa["fips_5"] = csa["fips_5"].str.zfill(5)
    ny_csa = csa[csa["csa_short"] == "New York"].copy()
    print(f"NY CSA counties: {len(ny_csa)}")

    # === V2019: years 2010-2019 (YEAR codes 3-12 = July 1, 2010 .. July 1, 2019) ===
    v2019_files = [str(CACHE / f"v2019-agesex-{s}.csv") for s in NY_STATES
                   if (CACHE / f"v2019-agesex-{s}.csv").exists()]
    print(f"V2019 files: {len(v2019_files)}")

    # V2019 file has age brackets, not single years. Use UNDER5_TOT + AGE513_TOT + AGE1417_TOT.
    frames = []
    for fp in v2019_files:
        sub = duckdb.query(f"""
            SELECT
                LPAD(CAST(STATE AS VARCHAR),2,'0') || LPAD(CAST(COUNTY AS VARCHAR),3,'0') AS fips_5,
                YEAR,
                (UNDER5_TOT + AGE513_TOT + AGE1417_TOT) AS pop_under18
            FROM read_csv_auto('{fp}', encoding='latin-1', header=True)
            WHERE SUMLEV = 50 AND YEAR BETWEEN 3 AND 12
        """).df()
        frames.append(sub)
    df19 = pd.concat(frames, ignore_index=True)
    # YEAR code → actual year: 3 = July 1, 2010 ... 12 = July 1, 2019
    df19["year"] = df19["YEAR"] + 2007
    df19 = df19[["fips_5", "year", "pop_under18"]]

    # === V2024: years 2020-2024 (YEAR codes 2-6 = July 1, 2020 .. July 1, 2024) ===
    v2024_files = [str(CACHE / f"v2024-syasex-{s}.csv") for s in NY_STATES
                   if (CACHE / f"v2024-syasex-{s}.csv").exists()]
    print(f"V2024 files: {len(v2024_files)}")

    frames2 = []
    for fp in v2024_files:
        sub = duckdb.query(f"""
            SELECT
                LPAD(CAST(STATE AS VARCHAR),2,'0') || LPAD(CAST(COUNTY AS VARCHAR),3,'0') AS fips_5,
                YEAR,
                SUM(CASE WHEN AGE BETWEEN 0 AND 17 THEN TOT_POP ELSE 0 END) AS pop_under18
            FROM read_csv_auto('{fp}', encoding='latin-1', header=True)
            WHERE YEAR BETWEEN 2 AND 6
            GROUP BY 1, 2
        """).df()
        frames2.append(sub)
    df24 = pd.concat(frames2, ignore_index=True)
    df24["year"] = df24["YEAR"] + 2018  # YEAR=2 → 2020, YEAR=6 → 2024
    df24 = df24[["fips_5", "year", "pop_under18"]]

    df_all = pd.concat([df19, df24], ignore_index=True)
    df_all = df_all[df_all["fips_5"].isin(ny_csa["fips_5"])]
    df_all = df_all.sort_values(["fips_5", "year"])
    print(f"\nMerged: {len(df_all)} rows ({df_all['fips_5'].nunique()} counties × {df_all['year'].nunique()} years)")

    # Pivot to wide
    piv = df_all.pivot_table(index="year", columns="fips_5", values="pop_under18").reset_index()
    piv.to_csv(DATA / "ny_under18_timeseries.csv", index=False)
    print(f"Wrote ny_under18_timeseries.csv")

    # Build payload for D3
    years = sorted(df_all["year"].unique().tolist())
    series = []
    suburb_color_idx = 0
    for fips in sorted(df_all["fips_5"].unique()):
        sub = df_all[df_all["fips_5"] == fips].set_index("year").reindex(years)
        vals = [int(v) if pd.notna(v) else None for v in sub["pop_under18"]]
        name = DISPLAY.get(fips, f"FIPS {fips}")
        is_borough = fips in COLORS
        if is_borough:
            color = COLORS[fips]
        else:
            color = SUBURB_PALETTE[suburb_color_idx % len(SUBURB_PALETTE)]
            suburb_color_idx += 1
        series.append({
            "fips": fips,
            "name": name,
            "values": vals,
            "color": color,
            "is_borough": is_borough,
        })

    payload = json.dumps({"years": years, "series": series})

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>NYC area under-18 population, 2010–2024</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }}
body {{ margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }}
svg {{ display:block; margin:20px auto; }}
</style></head><body>
<svg id="chart" viewBox="0 0 1600 920" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = {payload};
const BG = '#F6F7F3', TEXT = '#3D3733', SUBTEXT = '#7F7570', GRID = '#e1e2e3';
const W = 1600, H = 920, PAD = 40;
const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

svg.append('text').attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',30).attr('font-weight',500).attr('fill',TEXT)
  .text('Under-18 population, NYC CSA counties, 2010–2024');
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',18).attr('font-weight',400).attr('fill',SUBTEXT)
  .text('Raw count, July 1 estimates. The 5 NYC boroughs in color; surrounding NY/NJ/CT counties in grey. Hover to highlight.');

const chartLeft = 110, chartRight = W - PAD - 200;
const chartTop = PAD + 90, chartBottom = H - PAD - 70;

const x = d3.scaleLinear().domain(d3.extent(P.years)).range([chartLeft, chartRight]);
const ymax = d3.max(P.series.flatMap(s => s.values.filter(v => v !== null)));
const y = d3.scaleLinear().domain([0, ymax * 1.05]).range([chartBottom, chartTop]);

// Gridlines & y-axis labels
const yTicks = y.ticks(8);
yTicks.forEach(t => {{
  svg.append('line').attr('x1', chartLeft).attr('x2', chartRight)
    .attr('y1', y(t)).attr('y2', y(t)).attr('stroke', GRID).attr('stroke-width', 0.5);
  svg.append('text').attr('x', chartLeft - 8).attr('y', y(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
    .text(t >= 1e6 ? (t/1e6).toFixed(1) + 'M' : Math.round(t/1000) + 'k');
}});

P.years.forEach(yr => {{
  svg.append('line').attr('x1', x(yr)).attr('x2', x(yr))
    .attr('y1', chartBottom).attr('y2', chartBottom + 5)
    .attr('stroke', TEXT).attr('stroke-width', 0.5);
  svg.append('text').attr('x', x(yr)).attr('y', chartBottom + 20).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill','#333')
    .text(yr);
}});

// Line generator
const lineFn = d3.line().defined(v => v !== null)
  .x((_, i) => x(P.years[i]))
  .y(v => y(v));

const slug = s => s.replace(/[^a-z0-9]+/gi, '_');
const lineGroup = svg.append('g').attr('id','lines');

P.series.forEach(s => {{
  const id = slug(s.fips);
  lineGroup.append('path').attr('d', lineFn(s.values))
    .attr('fill','none').attr('stroke', s.color)
    .attr('stroke-width', s.is_borough ? 2.5 : 1.6).attr('opacity', s.is_borough ? 1.0 : 0.55)
    .attr('class','series-line').attr('data-id', id)
    .attr('style','mix-blend-mode: multiply');
  lineGroup.append('path').attr('d', lineFn(s.values))
    .attr('fill','none').attr('stroke','transparent').attr('stroke-width', 16)
    .attr('class','series-hit').attr('data-id', id).style('cursor','pointer');
}});

// Endpoint dots
const lastIdx = P.years.length - 1;
P.series.forEach(s => {{
  const lv = s.values[lastIdx];
  if (lv === null) return;
  lineGroup.append('circle').attr('cx', x(P.years[lastIdx])).attr('cy', y(lv))
    .attr('r', s.is_borough ? 4 : 2.5).attr('fill', s.color)
    .attr('class','series-dot').attr('data-id', slug(s.fips));
}});

// Right-side labels, collision-avoided
const labels = P.series.map(s => {{
  const lv = s.values[lastIdx];
  return lv !== null ? {{ id: slug(s.fips), color: s.color, y: y(lv), v: lv, name: s.name, is_borough: s.is_borough }} : null;
}}).filter(Boolean);
labels.sort((a, b) => a.y - b.y);
const minGap = 14;
for (let i = 1; i < labels.length; i++) {{
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}}

const labelGroup = svg.append('g').attr('id','labels');
labels.forEach(d => {{
  labelGroup.append('line').attr('x1', chartRight + 4).attr('x2', chartRight + 14)
    .attr('y1', d.y).attr('y2', d.y)
    .attr('stroke', d.color).attr('stroke-width', d.is_borough ? 2 : 1.2)
    .attr('class','series-label-line').attr('data-id', d.id);
  labelGroup.append('text').attr('x', chartRight + 18).attr('y', d.y).attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size', d.is_borough ? 13 : 11)
    .attr('font-weight', d.is_borough ? 700 : 400)
    .attr('fill', d.color).attr('class','series-label-text').attr('data-id', d.id)
    .style('cursor','pointer')
    .text(`${{d.name}}  ${{d.v >= 1e6 ? (d.v/1e6).toFixed(2) + 'M' : Math.round(d.v/1000) + 'k'}}`);
}});

function focus(targetId) {{
  d3.selectAll('.series-line, .series-dot, .series-label-line, .series-label-text').each(function() {{
    const el = d3.select(this);
    const myId = el.attr('data-id');
    const isT = myId === targetId;
    const isLine = el.classed('series-line');
    const isDot = el.classed('series-dot');
    const isLabLine = el.classed('series-label-line');
    const isLabText = el.classed('series-label-text');
    if (targetId === null) {{
      // restore defaults
      if (isLine) el.attr('opacity', el.attr('data-id') && P.series.find(s => slug(s.fips) === el.attr('data-id'))?.is_borough ? 1.0 : 0.55).attr('stroke-width', P.series.find(s => slug(s.fips) === el.attr('data-id'))?.is_borough ? 2.5 : 1.6);
      if (isDot) el.attr('opacity', 1);
      if (isLabLine) el.attr('opacity', 1);
      if (isLabText) el.attr('opacity', 1);
    }} else {{
      if (isLine) el.attr('opacity', isT ? 1 : 0.06).attr('stroke-width', isT ? 4 : 1.6);
      if (isDot) el.attr('opacity', isT ? 1 : 0.1).attr('r', isT ? 6 : 2.5);
      if (isLabLine) el.attr('opacity', isT ? 1 : 0.15);
      if (isLabText) el.attr('opacity', isT ? 1 : 0.25).attr('font-weight', isT ? 700 : 400);
    }}
  }});
}}
d3.selectAll('.series-hit, .series-label-text, .series-dot')
  .on('mouseenter', function() {{ focus(d3.select(this).attr('data-id')); }})
  .on('mouseleave', function() {{ focus(null); }});

svg.append('text').attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',200).attr('fill',TEXT)
  .text('Source: Census Bureau Population Estimates Program, Vintage 2019 (years 2010–2019) and Vintage 2024 (years 2020–2024). Annual July 1 estimates of under-18 residents.');
svg.append('text').attr('x', PAD).attr('y', H - PAD + 0)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',200).attr('fill',SUBTEXT)
  .text('Counties: NYC CSA (5 boroughs + NY/NJ/CT/PA suburbs).');
</script>
</body></html>"""
    (OUTPUTS / "ny_under18_timeseries.html").write_text(html)
    print(f"Wrote {OUTPUTS / 'ny_under18_timeseries.html'}")


if __name__ == "__main__":
    main()
