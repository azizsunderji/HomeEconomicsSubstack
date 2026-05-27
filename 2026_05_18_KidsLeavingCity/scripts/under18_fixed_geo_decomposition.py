"""
U.S. under-18 population by fixed-geography ring, 1950-2020.

Classifies every U.S. county into one of four classes based on its 1950 SMA status
and current MSA status. The classification is FIXED across time (a county doesn't
change classes between decades), which lets us decompose the "suburbs grew" story
into within-1950-MSA growth vs. growth from county reclassification.

4 classes:
  A. **City core**          = central county of a 1950 SMA
  B. **Original suburb**    = outlying county of a 1950 SMA
  C. **Newly-added MSA**    = not in any 1950 SMA, but in a modern (2023) MSA
  D. **Persistent non-metro** = never in an MSA (1950 or 2023)

Inputs:
  data/under18_by_county_decade.csv       — under-18 by county × decade 1950-2020
  data/sma_1950_counties.csv              — 1950 SMA county membership
  data/modern_msa_counties.csv            — 2023 OMB MSA county membership

Outputs:
  data/under18_fixed_geo_decomposition.csv — aggregated by class × year
  data/under18_county_classification.csv  — per-county class assignment
  outputs/under18_fixed_geo.html          — chart (levels)
  outputs/under18_fixed_geo_indexed.html  — chart (indexed to 1950)
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

# ---- Load inputs ----
panel = pd.read_csv(DATA / "under18_by_county_decade.csv", dtype={"county_fips": str})
panel["county_fips"] = panel["county_fips"].str.zfill(5)

sma1950 = pd.read_csv(DATA / "sma_1950_counties.csv", dtype={"county_fips": str})
sma1950["county_fips"] = sma1950["county_fips"].str.zfill(5)

modern = pd.read_csv(DATA / "modern_msa_counties.csv", dtype={"county_fips": str})
modern["county_fips"] = modern["county_fips"].str.zfill(5)

# ---- Build per-county classification ----
# A county can appear in multiple rows in sma1950 (rare — happens if same county is part of
# overlapping SMAs). Collapse: if it's central in ANY 1950 SMA, mark as central.
sma_county = (
    sma1950.groupby("county_fips", as_index=False)["is_central_county"]
    .max()
    .rename(columns={"is_central_county": "in_1950_sma_central"})
)
sma_county["in_1950_sma"] = True

modern_county = modern.groupby("county_fips", as_index=False).size()[["county_fips"]].assign(in_modern_msa=True)

# Union of all counties from the panel (so every county is classified)
counties = panel[["county_fips"]].drop_duplicates()
counties = counties.merge(sma_county, on="county_fips", how="left")
counties = counties.merge(modern_county, on="county_fips", how="left")
counties["in_1950_sma"] = counties["in_1950_sma"].fillna(False)
counties["in_1950_sma_central"] = counties["in_1950_sma_central"].fillna(0).astype(int)
counties["in_modern_msa"] = counties["in_modern_msa"].fillna(False)


def classify(row):
    if row["in_1950_sma"] and row["in_1950_sma_central"] == 1:
        return "A_city_core"
    if row["in_1950_sma"]:  # in 1950 SMA but not central
        return "B_original_suburb"
    if row["in_modern_msa"]:  # not in 1950 SMA, but in modern MSA
        return "C_newly_added_msa"
    return "D_persistent_nonmetro"


counties["class"] = counties.apply(classify, axis=1)
counties.to_csv(DATA / "under18_county_classification.csv", index=False)

print("County classification:")
print(counties["class"].value_counts().sort_index())
print()

# ---- Aggregate panel by class × year ----
panel = panel.merge(counties[["county_fips", "class"]], on="county_fips", how="left")
panel["class"] = panel["class"].fillna("D_persistent_nonmetro")  # safety net

agg = (
    panel.groupby(["year", "class"], as_index=False)["under18"]
    .sum()
    .pivot(index="year", columns="class", values="under18")
    .fillna(0)
    .reset_index()
)
agg["total"] = agg[[c for c in agg.columns if c != "year"]].sum(axis=1)
agg.to_csv(DATA / "under18_fixed_geo_decomposition.csv", index=False)
print("Aggregated (millions):")
disp = agg.copy()
for c in disp.columns:
    if c != "year":
        disp[c] = disp[c] / 1e6
print(disp.round(2).to_string(index=False))


# ---- Build chart ----
CLASS_LABELS = {
    "A_city_core":            "City core (1950 SMA central county)",
    "B_original_suburb":      "Original suburb (1950 SMA outlying county)",
    "C_newly_added_msa":      "Added to MSA after 1950",
    "D_persistent_nonmetro":  "Never in an MSA",
}
CLASS_COLORS = {
    "A_city_core":            "#F4743B",  # red/orange
    "B_original_suburb":      "#0BB4FF",  # blue
    "C_newly_added_msa":      "#FEC439",  # yellow
    "D_persistent_nonmetro":  "#67A275",  # green
}

years = agg["year"].astype(int).tolist()


def chart(mode: str):
    series = []
    for cls_id in ["A_city_core", "B_original_suburb", "C_newly_added_msa", "D_persistent_nonmetro"]:
        vals = (agg[cls_id] / 1e6).tolist()
        if mode == "indexed":
            base = vals[0]  # 1950 baseline
            if base <= 0:
                # for "Added to MSA after 1950" the 1950 value is mechanically zero
                # (these counties weren't in any MSA in 1950). Use 1960 as base.
                base = vals[1] if vals[1] > 0 else 1
                base_year = 1960
            else:
                base_year = 1950
            vals = [round(100 * v / base, 1) if base > 0 else None for v in vals]
        else:
            vals = [round(v, 2) for v in vals]
        series.append({
            "id": cls_id,
            "name": CLASS_LABELS[cls_id],
            "color": CLASS_COLORS[cls_id],
            "values": vals,
        })

    title = ("U.S. under-18 population by fixed-geography classification, 1950–2020"
             if mode == "level"
             else "U.S. under-18 population by fixed-geography class — indexed to 1950 = 100")
    subtitle = ("Every U.S. county is classified once by its 1950 SMA status and current MSA status, then held fixed across decades. "
                "This separates real population shifts from MSA-boundary expansions: the yellow line is entirely the latter."
                if mode == "level"
                else "Each ring's under-18 population as a % of its 1950 level. Counties added to MSAs after 1950 are indexed to 1960 (since they were non-metro in 1950).")

    P = {"years": years, "series": series, "mode": mode, "title": title, "subtitle": subtitle}

    template = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>__TITLE__</title>
<style>
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Thin.otf') format('opentype'); font-weight:200; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Light.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Regular.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracle-Medium.otf') format('opentype'); font-weight:500; }
body { margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }
svg { display:block; margin:20px auto; }
</style></head><body>
<svg id="chart" viewBox="0 0 960 987" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const BG='#F6F7F3', TEXT='#3D3733', SUBTEXT='#7F7570', GRID='#e1e2e3';
const W=960, H=987, PAD=40;
const svg = d3.select('#chart');
svg.append('rect').attr('width',W).attr('height',H).attr('fill',BG);

svg.append('text').attr('x',PAD).attr('y',PAD+32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',28).attr('font-weight',500).attr('fill',TEXT)
  .text(P.title);

const subLines = [];
{
  const words = P.subtitle.split(/\s+/);
  let line = '';
  const maxChars = 95;
  for (const w of words) {
    if ((line + ' ' + w).length > maxChars) { subLines.push(line.trim()); line = w; }
    else { line += ' ' + w; }
  }
  if (line.trim()) subLines.push(line.trim());
}
const subT = svg.append('text').attr('x',PAD).attr('y',PAD+32+34)
  .attr('font-family','ABC Oracle Edu').attr('font-size',19).attr('font-weight',400).attr('fill',SUBTEXT);
subLines.forEach((l,i) => subT.append('tspan').attr('x',PAD).attr('dy', i===0 ? 0 : 24).text(l));

const chartTop = PAD + 32 + 34 + 24*subLines.length + 60;
const chartBottom = H - PAD - 180;
const chartLeft = PAD + 80;
const chartRight = W - PAD - 245;

const xs = P.years;
const x = d3.scaleLinear().domain(d3.extent(xs)).range([chartLeft, chartRight]);
const flat = P.series.flatMap(s => s.values.filter(v => v !== null));
const ymax = d3.max(flat) * 1.08;
const y = d3.scaleLinear().domain([0, ymax]).range([chartBottom, chartTop]);

const yTicks = y.ticks(7);
const gridG = svg.append('g').attr('id','grid');
yTicks.forEach(t => {
  gridG.append('line').attr('x1',chartLeft).attr('x2',chartRight)
    .attr('y1',y(t)).attr('y2',y(t)).attr('stroke',GRID).attr('stroke-width',0.5);
});
const yLabG = svg.append('g').attr('id','y-labels');
yTicks.forEach((t,i) => {
  const isTop = (i === yTicks.length - 1);
  let lbl = (P.mode === 'indexed') ? String(Math.round(t)) : String(t.toFixed(0));
  if (isTop && P.mode !== 'indexed') lbl = lbl + 'M';
  yLabG.append('text').attr('x',chartLeft-8).attr('y',y(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

const xTickG = svg.append('g').attr('id','x-ticks');
const xLabG  = svg.append('g').attr('id','x-labels');
xs.forEach(yr => {
  xTickG.append('line').attr('x1',x(yr)).attr('x2',x(yr))
    .attr('y1',chartBottom).attr('y2',chartBottom+10).attr('stroke',TEXT).attr('stroke-width',0.5);
  let lbl = String(yr);
  if (yr !== 1950 && yr !== 2000 && yr !== 2020) lbl = String(yr).slice(2);
  xLabG.append('text').attr('x',x(yr)).attr('y',chartBottom+30).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

const lineFn = d3.line().defined(v => v !== null).x((_,i)=>x(xs[i])).y(v=>y(v));
const linesG = svg.append('g').attr('id','lines');
P.series.forEach(s => {
  linesG.append('path').attr('d',lineFn(s.values))
    .attr('fill','none').attr('stroke',s.color).attr('stroke-width',2.5)
    .attr('style','mix-blend-mode: multiply');
  // Endpoint dots
  xs.forEach((yr, i) => {
    if (s.values[i] !== null)
      linesG.append('circle').attr('cx', x(yr)).attr('cy', y(s.values[i]))
        .attr('r', 3.5).attr('fill', s.color);
  });
});

// Right-side labels — multi-line for long names, collision-avoided
function wrapLabel(name, maxChars) {
  const words = name.split(' ');
  const lines = [];
  let cur = '';
  for (const w of words) {
    if ((cur + ' ' + w).length > maxChars) { lines.push(cur.trim()); cur = w; }
    else { cur += ' ' + w; }
  }
  if (cur.trim()) lines.push(cur.trim());
  return lines;
}

const lastIdx = xs.length - 1;
const labels = P.series.map(s => {
  const lines = wrapLabel(s.name, 22);
  let lv = s.values[lastIdx];
  // if last value null, find last non-null
  if (lv === null) {
    for (let i = lastIdx; i >= 0; i--) { if (s.values[i] !== null) { lv = s.values[i]; break; } }
  }
  return { color: s.color, y: y(lv), v: lv, lines };
});
labels.sort((a,b) => a.y - b.y);
// Space lines: each label needs lines.length * 16 + 6 padding
for (let i = 1; i < labels.length; i++) {
  const minGap = (labels[i-1].lines.length * 16) + 10;
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}
const labG = svg.append('g').attr('id','labels');
labels.forEach(d => {
  d.lines.forEach((line, i) => {
    labG.append('text').attr('x',chartRight+12).attr('y', d.y + i*16).attr('dy','0.32em')
      .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',d.color)
      .text(line);
  });
});

// Source note
const srcLines = [
  'Sources: County under-18 from NHGIS decennial census tabulations 1950-2020 (Manson, Schroeder, Van Riper et al.).',
  '1950 SMA county membership and central-county designation from Census Bureau report P-23-23 (1967). Modern',
  'MSA membership from OMB Bulletin 23-01 (2023 CBSA delineation). Each county is classified ONCE by its 1950 SMA',
  'and current MSA status, then held fixed across decades. "Original suburb" = outlying county of a 1950 SMA;',
  '"Added to MSA after 1950" = county not in any 1950 SMA but in a 2023 MSA — the part of "suburban growth" that',
  'is reclassification rather than migration.',
];
const srcG = svg.append('g').attr('id','source');
const srcStart = H - PAD - 15 - (srcLines.length - 1) * 16;
const srcT = srcG.append('text').attr('font-family','ABC Oracle Edu').attr('font-size',13)
  .attr('font-weight',200).attr('fill',TEXT);
srcLines.forEach((l,i) => srcT.append('tspan').attr('x',PAD).attr('y', srcStart + i*16).text(l));
</script>
</body></html>
"""

    suffix = "_indexed" if mode == "indexed" else "_level"
    path = OUT / f"under18_fixed_geo{suffix}.html"
    html = template.replace("__TITLE__", title).replace("__DATA__", json.dumps(P))
    path.write_text(html)
    print(f"Wrote {path}")


chart("level")
chart("indexed")
