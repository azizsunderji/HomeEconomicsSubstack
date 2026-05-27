"""
City vs. suburb chart with within-suburb cohort decomposition.

Tiers (bottom to top in stack):
  1. City core              — 187 1950-SMA central counties (= city + inner-suburb,
                                cannot split city from balance before 1980)
  2. Original suburb        — 104 outlying counties of 1950 SMAs
  3-9. Reclassified suburbs — counties whose first MSA membership was a later decade,
                                stacked in vintage order (1950s, 60s, ..., 2010s)

Plus, as separate non-stacked lines:
  - Central city only (top 60, place-level, 1980-2020) — to show what the actual
    cities did *within* the city-core tier
  - Never in MSA (persistent non-metro)

The point of the chart: most of "suburb growth" since 1950 is from county reclassification
into MSAs, not from migration into pre-existing suburbs.
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

# Load county-level under-18 panel
panel = pd.read_csv(DATA / "under18_by_county_decade.csv", dtype={"county_fips": str})
panel["county_fips"] = panel["county_fips"].str.zfill(5)

# MSA membership panel with first_msa_decade
mem = pd.read_csv(DATA / "msa_membership_by_decade.csv", dtype={"county_fips": str})
mem["county_fips"] = mem["county_fips"].str.zfill(5)

# 1950 SMA county list (to identify central vs outlying within the 1950 cohort)
sma1950 = pd.read_csv(DATA / "sma_1950_counties.csv", dtype={"county_fips": str})
sma1950["county_fips"] = sma1950["county_fips"].str.zfill(5)
sma_central = (
    sma1950.groupby("county_fips", as_index=False)["is_central_county"].max()
    .rename(columns={"is_central_county": "is_1950_central"})
)

# Build per-county tier label
counties = panel[["county_fips"]].drop_duplicates().copy()
counties = counties.merge(mem[["county_fips", "first_msa_decade"]], on="county_fips", how="left")
counties = counties.merge(sma_central, on="county_fips", how="left")
counties["first_msa_decade"] = counties["first_msa_decade"].fillna(0).astype(int)
counties["is_1950_central"] = counties["is_1950_central"].fillna(0).astype(int)


def tier(row):
    if row["first_msa_decade"] == 0:
        return "Z_never_msa"
    if row["first_msa_decade"] == 1950 and row["is_1950_central"] == 1:
        return "A_city_core_1950"          # 187 central counties of 1950 SMAs
    if row["first_msa_decade"] == 1950:
        return "B_original_suburb_1950"    # 104 outlying counties of 1950 SMAs
    return f"C_added_{row['first_msa_decade']}s"   # e.g. "C_added_1960s" for 1950-joiners' first decade=1960


counties["tier"] = counties.apply(tier, axis=1)
panel = panel.merge(counties[["county_fips", "tier", "first_msa_decade"]], on="county_fips", how="left")

# Aggregate
agg = panel.groupby(["year", "tier"], as_index=False)["under18"].sum()
pivot = agg.pivot(index="year", columns="tier", values="under18").fillna(0).reset_index()

# Apply "appears at joining decade only" for cohort tiers
# (a cohort that joins in decade D should show 0 for years before D)
def cohort_decade_label(t):
    # "C_added_1960s" -> 1960
    if not t.startswith("C_added_"):
        return None
    return int(t.replace("C_added_", "").rstrip("s"))


for col in pivot.columns:
    d = cohort_decade_label(col)
    if d is None:
        continue
    pivot.loc[pivot["year"] < d, col] = 0

# Reorder columns: stack-bottom to top
stack_order = ["A_city_core_1950", "B_original_suburb_1950",
               "C_added_1960s", "C_added_1970s", "C_added_1980s",
               "C_added_1990s", "C_added_2000s", "C_added_2010s", "C_added_2020s"]
# Filter to columns that exist
stack_order = [c for c in stack_order if c in pivot.columns]
other = [c for c in pivot.columns if c not in stack_order and c != "year"]
pivot = pivot[["year"] + stack_order + other]
pivot.to_csv(DATA / "under18_city_vs_suburb_cohort.csv", index=False)

print("\nUnder-18 by tier × year (millions):")
disp = pivot.copy()
for c in disp.columns:
    if c != "year":
        disp[c] = disp[c] / 1e6
print(disp.round(2).to_string(index=False))

# Central city overlay line (place-level top-60, 1980-2020)
cc = pd.read_csv(DATA / "under18_central_cities.csv")
cc_yr = cc.dropna(subset=["under18"]).groupby("year", as_index=False)["under18"].sum()

# Build the chart data structure
TIER_META = {
    "A_city_core_1950":      ("City core (1950 SMA central counties, 187)",       "#F4743B"),
    "B_original_suburb_1950":("Original suburb (1950 SMA outlying counties, 104)","#0BB4FF"),
    "C_added_1960s":         ("Added to MSA in 1950s (79 counties)",              "#5BC8FF"),
    "C_added_1970s":         ("Added to MSA in 1960s (296 counties)",             "#8FD9FF"),
    "C_added_1980s":         ("Added to MSA in 1970s (173 counties)",             "#A8E0FF"),
    "C_added_1990s":         ("Added to MSA in 1980s (108 counties)",             "#BCE8FF"),
    "C_added_2000s":         ("Added to MSA in 1990s (12 counties)",              "#D0EFFF"),
    "C_added_2010s":         ("Added to MSA in 2000s (336 counties)",             "#E0F3FF"),
    "C_added_2020s":         ("Added to MSA in 2010s (64 counties)",              "#EFF9FF"),
}

years = pivot["year"].astype(int).tolist()
stack_series = []
for col in stack_order:
    if col not in TIER_META:
        continue
    name, color = TIER_META[col]
    vals = (pivot[col] / 1e6).tolist()
    stack_series.append({"id": col, "name": name, "color": color, "values": [round(v, 3) for v in vals]})

# Lines on top
city_line_years = sorted(cc_yr["year"].tolist())
city_line_vals = []
for y in years:
    sub = cc_yr[cc_yr["year"] == y]
    city_line_vals.append(round(sub["under18"].iloc[0] / 1e6, 3) if len(sub) else None)

never_vals = []
for y in years:
    sub = pivot[pivot["year"] == y]
    never_vals.append(round(sub["Z_never_msa"].iloc[0] / 1e6, 3) if "Z_never_msa" in sub.columns else None)

P = {
    "years": [int(y) for y in years],
    "stack": stack_series,
    "city_line": {"name": "Central city only (top 60, place-level)", "color": "#A32515", "values": city_line_vals},
    "never_line": {"name": "Never in an MSA (persistent non-metro)", "color": "#67A275", "values": never_vals},
    "title": "Where U.S. children lived, 1950–2020: cities, original suburbs, and the suburb-by-reclassification growth",
    "subtitle": "Stack shows U.S. under-18 in current-MSA counties, with within-suburb breakdown by when each county was reclassified into an MSA. Top-60 central cities themselves (red line) lost ~1M kids since 1980; almost all MSA growth has been suburbs, and a large share of that has come from non-metro counties being absorbed into MSAs.",
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
<svg id="chart" viewBox="0 0 1280 1000" xmlns="http://www.w3.org/2000/svg"></svg>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const P = __DATA__;
const BG='#F6F7F3', TEXT='#3D3733', SUBTEXT='#7F7570', GRID='#e1e2e3';
const W=1280, H=1000, PAD=40;
const svg = d3.select('#chart');
svg.append('rect').attr('width',W).attr('height',H).attr('fill',BG);

svg.append('text').attr('x',PAD).attr('y',PAD+30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',22).attr('font-weight',500).attr('fill',TEXT)
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
const subT = svg.append('text').attr('x',PAD).attr('y',PAD+30+30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',400).attr('fill',SUBTEXT);
subLines.forEach((l,i) => subT.append('tspan').attr('x',PAD).attr('dy', i===0 ? 0 : 22).text(l));

const chartTop = PAD + 30 + 30 + 22*subLines.length + 50;
const chartBottom = H - PAD - 150;
const chartLeft = PAD + 80;
const chartRight = W - PAD - 330;

const xs = P.years;
const x = d3.scaleLinear().domain(d3.extent(xs)).range([chartLeft, chartRight]);

// Stack data
const stackData = xs.map((yr, i) => {
  const o = {year: yr};
  P.stack.forEach(s => { o[s.id] = s.values[i]; });
  return o;
});
const keys = P.stack.map(s => s.id);
const stack = d3.stack().keys(keys)(stackData);
const ymaxStack = d3.max(stack, s => d3.max(s, p => p[1]));
const ymaxLines = Math.max(
  d3.max(P.city_line.values.filter(v=>v!==null)),
  d3.max(P.never_line.values.filter(v=>v!==null))
);
const ymax = Math.max(ymaxStack, ymaxLines) * 1.05;
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

// Stack
const area = d3.area().x((_,i)=>x(xs[i])).y0(d=>y(d[0])).y1(d=>y(d[1]));
const stacksG = svg.append('g').attr('id','stacks');
stack.forEach((layer, i) => {
  const sInfo = P.stack[i];
  stacksG.append('path').attr('d', area(layer))
    .attr('fill', sInfo.color).attr('stroke', BG).attr('stroke-width', 0.5);
});

// City line (dashed red)
const lineFn = d3.line().defined(v => v !== null).x((_,i)=>x(xs[i])).y(v=>y(v));
svg.append('path').attr('d', lineFn(P.city_line.values))
  .attr('fill','none').attr('stroke', P.city_line.color).attr('stroke-width', 2.5)
  .attr('stroke-dasharray','6,4');
// Add dots
xs.forEach((yr, i) => {
  if (P.city_line.values[i] !== null)
    svg.append('circle').attr('cx', x(yr)).attr('cy', y(P.city_line.values[i]))
      .attr('r', 3.5).attr('fill', P.city_line.color);
});

// Never-in-MSA line (dashed green)
svg.append('path').attr('d', lineFn(P.never_line.values))
  .attr('fill','none').attr('stroke', P.never_line.color).attr('stroke-width', 2.5)
  .attr('stroke-dasharray','4,3');

// Right-side labels at midpoint of each stack layer
const lastIdx = xs.length - 1;
const labels = P.stack.map((s, i) => {
  const lv = stack[i][lastIdx];
  return { name: s.name, color: s.color, y: y((lv[0]+lv[1])/2), kind: 'stack' };
});
// City line label
const cityLastIdx = (() => { for (let i = xs.length-1; i>=0; i--) if (P.city_line.values[i]!==null) return i; return -1; })();
if (cityLastIdx >= 0)
  labels.push({ name: P.city_line.name, color: P.city_line.color, y: y(P.city_line.values[cityLastIdx]), kind: 'city' });
labels.push({ name: P.never_line.name, color: P.never_line.color, y: y(P.never_line.values[lastIdx]), kind: 'never' });

labels.sort((a,b) => a.y - b.y);
const minGap = 18;
for (let i = 1; i < labels.length; i++) {
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}
const labG = svg.append('g').attr('id','labels');
labels.forEach(d => {
  labG.append('text').attr('x',chartRight+12).attr('y', d.y).attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',500).attr('fill',d.color)
    .text(d.name);
});

// Source
const srcLines = [
  'Sources: County under-18 1950–2020 from NHGIS decennial tabulations. MSA membership per decade from OMB delineations: 1950 SMA, 1960/1970 SMSA,',
  '1980/1990/2000 MSA, 2010/2020 CBSA (MSAs only — Micropolitan excluded). 1950 SMA central-county designation from Census Bureau report P-23-23.',
  'Top-60 central-city totals from NHGIS place-level Sex×Age tables for the named central cities of the largest 50 1950 SMAs. Note: "City core (1950 SMA',
  'central counties, 187)" is a COUNTY-level tier — it includes the central city AND its closest-in suburbs. The "Central city only" dashed red line shows',
  'what those actual cities did (1980 onward only; place-level historical data is not available at national scale before 1980 in NHGIS).',
]
const srcG = svg.append('g').attr('id','source');
const srcStart = H - PAD - 15 - (srcLines.length - 1) * 16;
const srcT = srcG.append('text').attr('font-family','ABC Oracle Edu').attr('font-size',13)
  .attr('font-weight',200).attr('fill',TEXT);
srcLines.forEach((l,i) => srcT.append('tspan').attr('x',PAD).attr('y', srcStart + i*16).text(l));
</script>
</body></html>
"""

path = OUT / "under18_city_vs_suburb_cohort.html"
html = template.replace("__TITLE__", P["title"]).replace("__DATA__", json.dumps(P))
path.write_text(html)
print(f"\nWrote {path}")
