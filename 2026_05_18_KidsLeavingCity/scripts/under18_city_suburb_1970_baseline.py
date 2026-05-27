"""
City core vs. suburb chart with 1970 baseline.

Four tiers, all within U.S. counties that are CURRENTLY in some MSA (or were in 1950):
  1. City core (1950 SMA central counties) — fixed at 187 counties; the original urban cores
  2. Original suburbs (as of 1970) — counties in any MSA in 1970 that are not 1950 central counties
  3. New city cores (post-1970) — central counties of MSAs that didn't exist before 1970
  4. Annexed suburbs (post-1970) — outlying counties added to MSAs after 1970

Plus, as a separate non-stacked line: "Never in any MSA"

The point: cleanly separate "growth within original (1970-defined) suburbs" from
"counties annexed into MSAs after 1970", with new city cores broken out so they don't
get lumped into the suburb growth story.

Inputs:
  data/msa_membership_by_decade.csv      — first_msa_decade per county
  data/sma_1950_counties.csv             — 1950 SMA central designation
  data/modern_msa_counties.csv           — current central/outlying designation
  data/under18_by_county_decade.csv      — kids per county per decade

Outputs:
  data/under18_city_suburb_1970_decomp.csv
  outputs/under18_city_suburb_1970.html
"""
import json
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUT = PROJECT / "outputs"

# Inputs
panel = pd.read_csv(DATA / "under18_by_county_decade.csv", dtype={"county_fips": str})
panel["county_fips"] = panel["county_fips"].str.zfill(5)

mem = pd.read_csv(DATA / "msa_membership_by_decade.csv", dtype={"county_fips": str})
mem["county_fips"] = mem["county_fips"].str.zfill(5)

sma1950 = pd.read_csv(DATA / "sma_1950_counties.csv", dtype={"county_fips": str})
sma1950["county_fips"] = sma1950["county_fips"].str.zfill(5)
sma_central = sma1950.groupby("county_fips", as_index=False)["is_central_county"].max()
sma_central["was_1950_central"] = sma_central["is_central_county"] == 1
sma_central = sma_central[["county_fips", "was_1950_central"]]

modern = pd.read_csv(DATA / "modern_msa_counties.csv", dtype={"county_fips": str})
modern["county_fips"] = modern["county_fips"].str.zfill(5)
modern_central = modern.groupby("county_fips", as_index=False)["central_or_outlying"].max()
modern_central["is_modern_central"] = modern_central["central_or_outlying"] == "Central"
modern_central = modern_central[["county_fips", "is_modern_central"]]

# Build classification per county
counties = panel[["county_fips"]].drop_duplicates().copy()
counties = counties.merge(mem[["county_fips", "first_msa_decade"]], on="county_fips", how="left")
counties = counties.merge(sma_central, on="county_fips", how="left")
counties = counties.merge(modern_central, on="county_fips", how="left")
counties["first_msa_decade"] = counties["first_msa_decade"].fillna(0).astype(int)
counties["was_1950_central"] = counties["was_1950_central"].fillna(False)
counties["is_modern_central"] = counties["is_modern_central"].fillna(False)


def tier(row):
    fmd = row["first_msa_decade"]
    if fmd == 0:
        return "Z_never_msa"
    if fmd == 1950 and row["was_1950_central"]:
        return "A_city_core_1950"
    if fmd <= 1970:  # 1950 outlying (104), 1960 (79), 1970 (296)
        return "B_original_suburb_1970"
    # post-1970 (1980, 1990, 2000, 2010, 2020 first_msa_decade values)
    if row["is_modern_central"]:
        return "C_new_city_core_post1970"
    return "D_annexed_suburb_post1970"


counties["tier"] = counties.apply(tier, axis=1)

# Count counties per tier
print("County classification:")
print(counties["tier"].value_counts().sort_index())

# Aggregate under-18
panel = panel.merge(counties[["county_fips", "tier", "first_msa_decade"]], on="county_fips", how="left")
panel["tier"] = panel["tier"].fillna("Z_never_msa")

agg = panel.groupby(["year", "tier"], as_index=False)["under18"].sum()
pivot = agg.pivot(index="year", columns="tier", values="under18").fillna(0).reset_index()

# Zero out post-1970 tiers before their joining year
# (a county joining in 1980 should be in non-metro for all decades before 1980)
# To handle this we need to NOT use the simple groupby — instead, for each row in the panel,
# only count it if its first_msa_decade <= year. Otherwise, count it as "Z_never_msa" for that year.
panel2 = panel.copy()
panel2["effective_tier"] = panel2.apply(
    lambda r: r["tier"] if (r["first_msa_decade"] == 0 or r["year"] >= r["first_msa_decade"]) else "Z_never_msa",
    axis=1,
)
agg2 = panel2.groupby(["year", "effective_tier"], as_index=False)["under18"].sum()
pivot2 = agg2.pivot(index="year", columns="effective_tier", values="under18").fillna(0).reset_index()

# Reorder & save
stack_order = ["A_city_core_1950", "C_new_city_core_post1970",
               "B_original_suburb_1970", "D_annexed_suburb_post1970"]
stack_order = [c for c in stack_order if c in pivot2.columns]
other = [c for c in pivot2.columns if c not in stack_order and c != "year"]
pivot2 = pivot2[["year"] + stack_order + other]
pivot2.to_csv(DATA / "under18_city_suburb_1970_decomp.csv", index=False)

print("\nUnder-18 by tier × year (millions):")
disp = pivot2.copy()
for c in disp.columns:
    if c != "year":
        disp[c] = disp[c] / 1e6
print(disp.round(2).to_string(index=False))

# ====== Chart ======
TIER_META = {
    "A_city_core_1950":         ("City core (1950 SMA central counties)",     "#F4743B"),
    "C_new_city_core_post1970": ("New city cores (post-1970 MSAs)",            "#A32515"),
    "B_original_suburb_1970":   ("Original suburbs as of 1970",                "#0BB4FF"),
    "D_annexed_suburb_post1970":("Annexed suburbs (post-1970 reclassification)","#FEC439"),
}

years = pivot2["year"].astype(int).tolist()
stack_series = []
for col in stack_order:
    if col not in TIER_META:
        continue
    name, color = TIER_META[col]
    vals = (pivot2[col] / 1e6).tolist()
    stack_series.append({"id": col, "name": name, "color": color, "values": [round(v, 3) for v in vals]})

never_vals = []
if "Z_never_msa" in pivot2.columns:
    never_vals = (pivot2["Z_never_msa"] / 1e6).tolist()
    never_vals = [round(v, 3) for v in never_vals]

# Compute suburb-growth attribution 1970 → 2020
def get(col, yr):
    return pivot2[pivot2["year"] == yr][col].iloc[0]

orig_sub_1970 = get("B_original_suburb_1970", 1970)
orig_sub_2020 = get("B_original_suburb_1970", 2020)
annex_sub_2020 = get("D_annexed_suburb_post1970", 2020)
total_suburb_growth = (orig_sub_2020 - orig_sub_1970) + annex_sub_2020
within_orig = orig_sub_2020 - orig_sub_1970
print(f"\nSuburb growth attribution, 1970 → 2020:")
print(f"  Original 1970 suburbs grew internally: {within_orig/1e6:.2f}M (from {orig_sub_1970/1e6:.2f}M to {orig_sub_2020/1e6:.2f}M)")
print(f"  Annexed suburbs added: {annex_sub_2020/1e6:.2f}M (entered with 0 in 1970)")
print(f"  Total suburb growth: {total_suburb_growth/1e6:.2f}M")
print(f"  Share from annexation: {100*annex_sub_2020/total_suburb_growth:.1f}%")
print(f"  Share from intra-original growth: {100*within_orig/total_suburb_growth:.1f}%")

share_annex = 100*annex_sub_2020/total_suburb_growth
share_intra = 100*within_orig/total_suburb_growth

P = {
    "years": [int(y) for y in years],
    "stack": stack_series,
    "never_values": never_vals,
    "share_annex": round(share_annex, 0),
    "share_intra": round(share_intra, 0),
    "orig_1970": round(orig_sub_1970/1e6, 1),
    "orig_2020": round(orig_sub_2020/1e6, 1),
    "annex_2020": round(annex_sub_2020/1e6, 1),
    "title": "U.S. children: city core, original (1970) suburbs, and post-1970 annexation",
    "subtitle": (
        f"Of the {(within_orig+annex_sub_2020)/1e6:.0f}M-kid growth in suburban (= MSA outlying) under-18 from 1970 to 2020, "
        f"{share_annex:.0f}% came from counties annexed into MSAs after 1970, and only "
        f"{share_intra:.0f}% from intra-boundary growth in the original 1970 suburbs."
    ),
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
const subT = svg.append('text').attr('x',PAD).attr('y',PAD+30+30)
  .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',400).attr('fill',SUBTEXT);
subLines.forEach((l,i) => subT.append('tspan').attr('x',PAD).attr('dy', i===0 ? 0 : 22).text(l));

const chartTop = PAD + 30 + 30 + 22*subLines.length + 50;
const chartBottom = H - PAD - 180;
const chartLeft = PAD + 80;
const chartRight = W - PAD - 320;

const xs = P.years;
const x = d3.scaleLinear().domain(d3.extent(xs)).range([chartLeft, chartRight]);

// Find max across all lines (each tier separately) + never line
const allVals = P.stack.flatMap(s => s.values.filter(v => v !== null && v > 0));
if (P.never_values.length) allVals.push(...P.never_values);
const ymax = d3.max(allVals) * 1.08;
const y = d3.scaleLinear().domain([0, ymax]).range([chartBottom, chartTop]);

const yTicks = y.ticks(7);
const gridG = svg.append('g').attr('id','grid');
yTicks.forEach(t => {
  gridG.append('line').attr('x1',chartLeft).attr('x2',chartRight).attr('y1',y(t)).attr('y2',y(t))
    .attr('stroke',GRID).attr('stroke-width',0.5);
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

const xTickG = svg.append('g').attr('id','x-ticks');
const xLabG = svg.append('g').attr('id','x-labels');
xs.forEach(yr => {
  xTickG.append('line').attr('x1',x(yr)).attr('x2',x(yr)).attr('y1',chartBottom).attr('y2',chartBottom+10)
    .attr('stroke',TEXT).attr('stroke-width',0.5);
  let lbl = String(yr);
  if (yr !== 1950 && yr !== 1970 && yr !== 2000 && yr !== 2020) lbl = String(yr).slice(2);
  xLabG.append('text').attr('x',x(yr)).attr('y',chartBottom+30).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

// Lines (each tier as its own line — defined only when value > 0 for tiers that enter mid-series)
const lineFn = d3.line().defined(v => v !== null && v !== undefined && v > 0).x((_,i)=>x(xs[i])).y(v=>y(v));
const linesG = svg.append('g').attr('id','lines');
P.stack.forEach(s => {
  linesG.append('path').attr('d', lineFn(s.values))
    .attr('fill','none').attr('stroke', s.color).attr('stroke-width', 2.8)
    .attr('style','mix-blend-mode: multiply');
  // dots at each year where the value > 0
  xs.forEach((yr, i) => {
    if (s.values[i] !== null && s.values[i] !== undefined && s.values[i] > 0)
      linesG.append('circle').attr('cx', x(yr)).attr('cy', y(s.values[i]))
        .attr('r', 3.5).attr('fill', s.color);
  });
});

// Never-in-MSA line (dashed)
if (P.never_values.length) {
  const lineFn2 = d3.line().x((_,i)=>x(xs[i])).y(v=>y(v));
  svg.append('path').attr('d', lineFn2(P.never_values))
    .attr('fill','none').attr('stroke', '#67A275').attr('stroke-width', 2.5)
    .attr('stroke-dasharray', '5,4');
  xs.forEach((yr, i) => {
    svg.append('circle').attr('cx', x(yr)).attr('cy', y(P.never_values[i]))
      .attr('r', 3).attr('fill', '#67A275').attr('opacity', 0.7);
  });
}

// 1970 reference line
const refG = svg.append('g').attr('id','ref');
refG.append('line').attr('x1',x(1970)).attr('x2',x(1970)).attr('y1',chartTop).attr('y2',chartBottom)
  .attr('stroke','#3D3733').attr('stroke-width',1).attr('stroke-dasharray','3,4').attr('opacity',0.55);
refG.append('text').attr('x',x(1970)).attr('y',chartTop-8).attr('text-anchor','middle')
  .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill','#3D3733')
  .text('1970 baseline');

// Right-side labels (at last value of each line)
const lastIdx = xs.length - 1;
const labels = P.stack.map(s => {
  return { name: s.name, color: s.color, y: y(s.values[lastIdx]) };
});
if (P.never_values.length) {
  labels.push({ name: 'Never in an MSA', color: '#67A275', y: y(P.never_values[lastIdx]) });
}
labels.sort((a,b) => a.y - b.y);
const minGap = 20;
for (let i = 1; i < labels.length; i++) {
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}
const labG = svg.append('g').attr('id','labels');
labels.forEach(d => {
  labG.append('text').attr('x',chartRight+12).attr('y', d.y).attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',14).attr('font-weight',500).attr('fill',d.color)
    .text(d.name);
});

// Source note
const srcLines = [
  'Sources: U.S. under-18 by county and decennial from NHGIS (Manson et al.). MSA membership at each decennial from OMB delineations',
  '(1950 SMA → 2023 CBSA, Metropolitan Statistical Areas only). City-core designation: a county is "city core" if it is a central county of any 1950 SMA',
  '(per Census Bureau report P-23-23). "Original suburbs as of 1970" = all other counties that were in any MSA in 1970 (1950 SMA outlying + counties',
  'first joining 1950s/60s). "Annexed suburbs (post-1970)" = counties that first joined any MSA from 1980 onward and are classified as Outlying in the 2023 CBSA.',
  '"New city cores (post-1970)" = those that joined post-1970 and are Central in the 2023 CBSA (e.g., new metros like Las Vegas, McAllen). Note that "city core"',
  'remains a COUNTY-level tier — it includes both the actual central city and its closest-in suburbs, since the county is much larger than the city itself.',
];
const srcG = svg.append('g').attr('id','source');
const srcStart = H - PAD - 15 - (srcLines.length - 1) * 16;
const srcT = srcG.append('text').attr('font-family','ABC Oracle Edu').attr('font-size',13)
  .attr('font-weight',200).attr('fill',TEXT);
srcLines.forEach((l,i) => srcT.append('tspan').attr('x',PAD).attr('y', srcStart + i*16).text(l));
</script>
</body></html>
"""

path = OUT / "under18_city_suburb_1970.html"
html = template.replace("__TITLE__", P["title"]).replace("__DATA__", json.dumps(P))
path.write_text(html)
print(f"\nWrote {path}")
