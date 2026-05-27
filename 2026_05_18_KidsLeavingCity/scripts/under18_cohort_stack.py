"""
Cohort-stack chart of U.S. under-18 by MSA-vintage.

Each cohort = counties that first joined an MSA in a given decade.
The chart is a stacked area with 8 layers (1950 baseline + 7 reclassification cohorts)
plus a separate non-stacked "never in MSA" line for reference.

Each cohort's layer:
  - appears starting at its first_msa_decade
  - tracks the under-18 in those counties from that decade onward
  - the stack height at decade Y = total under-18 in counties that were in an MSA by Y

Inputs:
  data/msa_membership_by_decade.csv   — county × decade MSA membership + first_msa_decade
  data/under18_by_county_decade.csv   — county × decade under-18

Outputs:
  data/under18_cohort_decomposition.csv
  outputs/under18_cohort_stack.html
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

panel = pd.read_csv(DATA / "under18_by_county_decade.csv", dtype={"county_fips": str})
panel["county_fips"] = panel["county_fips"].str.zfill(5)

mem = pd.read_csv(DATA / "msa_membership_by_decade.csv", dtype={"county_fips": str})
mem["county_fips"] = mem["county_fips"].str.zfill(5)

# Join cohort onto panel
panel = panel.merge(mem[["county_fips", "first_msa_decade"]], on="county_fips", how="left")
panel["first_msa_decade"] = panel["first_msa_decade"].fillna(0).astype(int)

# Aggregate under-18 by cohort × year, BUT ONLY from each cohort's first_msa_decade onward
# (a cohort that joined in 1980 should show 0 for 1950-1970)
def cohort_value(row, year):
    if row["first_msa_decade"] == 0:
        return None  # never in MSA — handle separately
    if year < row["first_msa_decade"]:
        return 0
    return row["under18"]


# Per-cohort × year aggregation
years = sorted(panel["year"].unique())
cohorts = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020]
agg_rows = []
for year in years:
    for cohort in cohorts:
        # Counties in this cohort, valued in this year, but only if year >= cohort
        if year < cohort:
            v = 0
        else:
            sub = panel[(panel["year"] == year) & (panel["first_msa_decade"] == cohort)]
            v = sub["under18"].sum()
        agg_rows.append({"year": year, "cohort": cohort, "under18": v})
    # Never-in-MSA
    sub = panel[(panel["year"] == year) & (panel["first_msa_decade"] == 0)]
    agg_rows.append({"year": year, "cohort": 0, "under18": sub["under18"].sum()})

agg = pd.DataFrame(agg_rows)
agg.to_csv(DATA / "under18_cohort_decomposition.csv", index=False)

# Print summary table
print("Under-18 by cohort × year (millions):")
piv = agg.pivot(index="year", columns="cohort", values="under18") / 1e6
piv.columns = [f"Joined {c}" if c != 0 else "Never MSA" for c in piv.columns]
# Reorder columns: 1950 (baseline) first, then 1960, 1970, ..., 2020, then never
ordered = [c for c in ["Joined 1950", "Joined 1960", "Joined 1970", "Joined 1980", "Joined 1990", "Joined 2000", "Joined 2010", "Joined 2020", "Never MSA"] if c in piv.columns]
piv = piv[ordered]
piv["MSA total"] = piv[[c for c in piv.columns if c != "Never MSA"]].sum(axis=1)
piv["U.S. total"] = piv["MSA total"] + piv["Never MSA"]
print(piv.round(2).to_string())

# Build chart data
COHORT_LABELS = {
    1950: "1950 SMA baseline",
    1960: "Joined in 1950s",
    1970: "Joined in 1960s",
    1980: "Joined in 1970s",
    1990: "Joined in 1980s",
    2000: "Joined in 1990s",
    2010: "Joined in 2000s",
    2020: "Joined in 2010s",
}
# Color gradient: dark blue baseline → progressively lighter shades for newer cohorts
COHORT_COLORS = {
    1950: "#003D66",
    1960: "#005C99",
    1970: "#0077CC",
    1980: "#0BB4FF",
    1990: "#5BC8FF",
    2000: "#8FD9FF",
    2010: "#BCE8FF",
    2020: "#E0F3FF",
}

stack_series = []
for c in cohorts:
    sub = agg[agg["cohort"] == c].sort_values("year")
    stack_series.append({
        "id": f"c{c}",
        "name": COHORT_LABELS[c],
        "color": COHORT_COLORS[c],
        "values": [round(v / 1e6, 3) for v in sub["under18"].tolist()],
    })

# Non-stacked "never MSA" line for context
never_sub = agg[agg["cohort"] == 0].sort_values("year")
never_line = {
    "name": "Never in an MSA (line, not stacked)",
    "color": "#67A275",
    "values": [round(v / 1e6, 3) for v in never_sub["under18"].tolist()],
}

P = {
    "years": [int(y) for y in years],
    "stack": stack_series,
    "never": never_line,
    "title": "U.S. under-18 in current-MSA counties, by decade-of-reclassification, 1950–2020",
    "subtitle": "Each tier = counties that first joined an MSA in that decade. The stack accumulates as more counties are reclassified. Most of the headline “suburban growth” after 1950 came from county reclassification — non-metro counties absorbed into MSAs, not Americans moving to existing suburbs.",
}

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
<svg id="chart" viewBox="0 0 1200 987" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const BG='#F6F7F3', TEXT='#3D3733', SUBTEXT='#7F7570', GRID='#e1e2e3';
const W=1200, H=987, PAD=40;
const svg = d3.select('#chart');
svg.append('rect').attr('width',W).attr('height',H).attr('fill',BG);

svg.append('text').attr('x',PAD).attr('y',PAD+32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',24).attr('font-weight',500).attr('fill',TEXT)
  .text(P.title);

const subLines = [];
{
  const words = P.subtitle.split(/\s+/);
  let line = '';
  const maxChars = 130;
  for (const w of words) {
    if ((line + ' ' + w).length > maxChars) { subLines.push(line.trim()); line = w; }
    else { line += ' ' + w; }
  }
  if (line.trim()) subLines.push(line.trim());
}
const subT = svg.append('text').attr('x',PAD).attr('y',PAD+32+30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',17).attr('font-weight',400).attr('fill',SUBTEXT);
subLines.forEach((l,i) => subT.append('tspan').attr('x',PAD).attr('dy', i===0 ? 0 : 22).text(l));

const chartTop = PAD + 32 + 30 + 22*subLines.length + 60;
const chartBottom = H - PAD - 165;
const chartLeft = PAD + 80;
const chartRight = W - PAD - 280;

const xs = P.years;
const x = d3.scaleLinear().domain(d3.extent(xs)).range([chartLeft, chartRight]);

// Compute stack
const stackData = xs.map((yr, i) => {
  const o = {year: yr};
  P.stack.forEach(s => { o[s.id] = s.values[i]; });
  return o;
});
const keys = P.stack.map(s => s.id);
const stack = d3.stack().keys(keys)(stackData);
const ymaxStack = d3.max(stack, s => d3.max(s, p => p[1]));
const ymaxNever = d3.max(P.never.values);
const ymax = Math.max(ymaxStack, ymaxNever) * 1.06;
const y = d3.scaleLinear().domain([0, ymax]).range([chartBottom, chartTop]);

// Grid + y labels
const yTicks = y.ticks(7);
const gridG = svg.append('g').attr('id','grid');
yTicks.forEach(t => {
  gridG.append('line').attr('x1',chartLeft).attr('x2',chartRight)
    .attr('y1',y(t)).attr('y2',y(t)).attr('stroke',GRID).attr('stroke-width',0.5);
});
const yLabG = svg.append('g').attr('id','y-labels');
yTicks.forEach((t,i) => {
  const isTop = (i === yTicks.length - 1);
  let lbl = String(Math.round(t));
  if (isTop) lbl = lbl + 'M';
  yLabG.append('text').attr('x',chartLeft-8).attr('y',y(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

// X axis
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

// Stack areas
const area = d3.area().x((_,i)=>x(xs[i])).y0(d=>y(d[0])).y1(d=>y(d[1]));
const stacksG = svg.append('g').attr('id','stacks');
stack.forEach((layer, i) => {
  const sInfo = P.stack[i];
  stacksG.append('path').attr('d', area(layer)).attr('fill', sInfo.color).attr('stroke', BG).attr('stroke-width', 0.5);
});

// Never-MSA line (overlay)
const lineFn = d3.line().x((_,i)=>x(xs[i])).y(v=>y(v));
svg.append('path').attr('d', lineFn(P.never.values))
  .attr('fill','none').attr('stroke', P.never.color).attr('stroke-width', 2.5)
  .attr('stroke-dasharray','5,4').attr('style','mix-blend-mode: multiply');

// Right-side labels for each cohort (place at midpoint of the last stack segment)
const lastIdx = xs.length - 1;
const labels = P.stack.map((s, i) => {
  const lv = stack[i][lastIdx];
  return { name: s.name, color: s.color, y: y((lv[0]+lv[1])/2) };
});
// Add the never-MSA line label
labels.push({ name: P.never.name, color: P.never.color, y: y(P.never.values[lastIdx]) });

// Sort + collision avoidance
labels.sort((a,b) => a.y - b.y);
const minGap = 18;
for (let i = 1; i < labels.length; i++) {
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}
const labG = svg.append('g').attr('id','labels');
labels.forEach(d => {
  labG.append('text').attr('x',chartRight+10).attr('y', d.y).attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',d.color)
    .text(d.name);
});

// Source note
const srcLines = [
  'Sources: County under-18 1950–2020 from NHGIS decennial census tabulations (Manson et al.). MSA membership per decade from the OMB delineation file in',
  'force at each census: 1950 SMA (Oct 1950), 1960 SMSA (Nov 1960), 1970 SMSA (Apr 1973), 1980 MSA (Jun 1983), 1990 MSA (Jun 1993), 2000 MSA',
  '(Jun 1999), 2010 CBSA (Feb 2013, MSAs only — excludes Micropolitan), 2020 CBSA (Jul 2023, MSAs only). Each county is assigned to a cohort by the',
  'EARLIEST decade it appears in any MSA. The "1950 SMA baseline" cohort is 292 counties; cohorts 1960–2020 total 1,068 additional counties. 161',
  'counties drop out of MSA in at least one decade — preserved with earliest-True assignment. CT 2022 planning-region transition handled by overlap rule.',
  'Caveats: a few county FIPS recodes (Miami-Dade, Oglala Lakota SD, Kusilvak AK) appear under different IDs in different decades.',
];
const srcG = svg.append('g').attr('id','source');
const srcStart = H - PAD - 15 - (srcLines.length - 1) * 16;
const srcT = srcG.append('text').attr('font-family','ABC Oracle Edu').attr('font-size',13)
  .attr('font-weight',200).attr('fill',TEXT);
srcLines.forEach((l,i) => srcT.append('tspan').attr('x',PAD).attr('y', srcStart + i*16).text(l));
</script>
</body></html>
"""

path = OUT / "under18_cohort_stack.html"
html = template.replace("__TITLE__", P["title"]).replace("__DATA__", json.dumps(P))
path.write_text(html)
print(f"\nWrote {path}")
