"""
Tabulate under-18 population by Census metro ring (central city / suburb / non-metro),
1950-2024, from IPUMS USA harmonized METRO variable.

Inputs:
  data/ipums_usa_kids_metro.parquet  (decennial 1950-2000 + ACS 1-year 2005-2024)

Outputs:
  data/under18_by_metro_ring.csv     — tabulation
  outputs/under18_by_metro_ring.html — D3 chart (levels)
  outputs/under18_by_metro_ring_indexed.html — D3 chart (% change from 1950)

METRO variable values (IPUMS USA, per DDI codebook):
  1 = Not in metropolitan area
  2 = Metropolitan status indeterminable (mixed)        — PUMA spans metro/non-metro
  3 = In metropolitan area, not in central/principal city  (= suburb)
  4 = In metropolitan area, central/principal city status indeterminable
  5 = In metropolitan area, in central/principal city  (= central city)

Known gaps in IPUMS METRO at the microdata level:
  - 1950: no METRO=5 records (central-city status not coded in the 1950 1% sample)
  - 1990: METRO entirely unset for the us1990a 5% sample
  - METRO=4 ("metro, central-city status unknown") is huge: ~40-45% of all metro under-18s
    from 2000+. IPUMS suppresses central-city status in smaller metros for confidentiality.
"""
import json
from pathlib import Path
import duckdb
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"

PARQUET = DATA / "ipums_usa_kids_metro.parquet"

METRO_LABEL = {
    1: "non_metro",
    2: "metro_indeterminate",     # mixed metro/non-metro PUMA
    3: "suburb",
    4: "metro_ring_unknown",      # in metro, central-city status suppressed
    5: "central_city",
}


def tabulate():
    con = duckdb.connect()
    q = f"""
    SELECT
      YEAR,
      METRO,
      SUM(PERWT) AS pop
    FROM '{PARQUET}'
    WHERE AGE < 18
    GROUP BY YEAR, METRO
    ORDER BY YEAR, METRO
    """
    df = con.execute(q).df()
    df["category"] = df["METRO"].map(METRO_LABEL)
    pivot = df.pivot_table(index="YEAR", columns="category", values="pop", aggfunc="sum").fillna(0)

    # Ensure all expected columns exist
    for c in METRO_LABEL.values():
        if c not in pivot.columns:
            pivot[c] = 0

    pivot["total_under18"] = pivot.sum(axis=1)
    pivot["pct_central_city"] = 100 * pivot["central_city"] / pivot["total_under18"]
    pivot["pct_suburb"] = 100 * pivot["suburb"] / pivot["total_under18"]
    pivot["pct_non_metro"] = 100 * pivot["non_metro"] / pivot["total_under18"]

    out = pivot.reset_index().sort_values("YEAR")
    out.to_csv(DATA / "under18_by_metro_ring.csv", index=False)
    print("Tabulation:")
    print(out.to_string(index=False))
    return out


def make_chart(df: pd.DataFrame, mode: str = "level"):
    """mode: 'level' (millions) or 'indexed' (1950 = 100)"""
    years = df["YEAR"].astype(int).tolist()
    rings = [
        ("central_city", "Central city", "#F4743B"),
        ("suburb",       "Suburbs",      "#0BB4FF"),
        ("non_metro",    "Non-metro",    "#67A275"),
        ("metro_ring_unknown", "Metro, ring unknown", "#7F7570"),
    ]
    series = []
    for col, name, color in rings:
        vals = df[col].tolist()
        if mode == "indexed":
            base = next((v for v in vals if v and v > 0), None)
            if base is None:
                continue
            vals = [None if (v is None or v == 0) else round(100 * v / base, 1) for v in vals]
        else:
            vals = [None if (v is None or v == 0) else int(round(v)) for v in vals]
        series.append({"id": col, "name": name, "color": color, "values": vals})

    title_lvl = "U.S. children under 18, by metropolitan ring"
    sub_lvl = ("Central city, suburbs (in metro area but outside central city), and non-metro counties. "
               "Decennial Census 1950-2000 + ACS 1-year 2005-2024 (skipping experimental 2020). "
               "Population in millions.")
    title_idx = "U.S. children under 18, indexed to 1950 = 100"
    sub_idx = ("Each ring's under-18 population as a % of its 1950 level. "
               "Decennial Census 1950-2000 + ACS 1-year 2005-2024.")

    title = title_idx if mode == "indexed" else title_lvl
    subtitle = sub_idx if mode == "indexed" else sub_lvl

    P = {"years": years, "series": series, "mode": mode, "title": title, "subtitle": subtitle}

    template = """<!DOCTYPE html><html><head><meta charset="utf-8">
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

// Title and subtitle
svg.append('text').attr('x',PAD).attr('y',PAD+32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',32).attr('font-weight',500).attr('fill',TEXT)
  .text(P.title);

// subtitle (wrap into two lines if very long)
const subLines = [];
{
  const words = P.subtitle.split(/\\s+/);
  let line = '';
  const maxChars = 110;
  for (const w of words) {
    if ((line + ' ' + w).length > maxChars) { subLines.push(line.trim()); line = w; }
    else { line += ' ' + w; }
  }
  if (line.trim()) subLines.push(line.trim());
}
const subT = svg.append('text').attr('x',PAD).attr('y',PAD+32+34)
  .attr('font-family','ABC Oracle Edu').attr('font-size',18).attr('font-weight',400).attr('fill',SUBTEXT);
subLines.forEach((l,i) => subT.append('tspan').attr('x',PAD).attr('dy', i===0 ? 0 : 22).text(l));

const chartTop = PAD + 32 + 34 + 22*subLines.length + 65;
const chartBottom = H - PAD - 90;
const chartLeft = PAD + 70;
const chartRight = W - PAD - 160;

const xs = P.years;
const x = d3.scaleLinear().domain(d3.extent(xs)).range([chartLeft, chartRight]);
const flat = P.series.flatMap(s => s.values.filter(v => v !== null));
const ymin = (P.mode === 'indexed') ? 0 : 0;
const ymax = d3.max(flat) * 1.08;
const y = d3.scaleLinear().domain([ymin, ymax]).range([chartBottom, chartTop]);

// Y-axis label format
function fmtY(v) {
  if (P.mode === 'indexed') return Math.round(v);
  return (v >= 1e6) ? (v/1e6).toFixed(1) + 'M' : Math.round(v/1000) + 'k';
}

const yTicks = y.ticks(7);
const gridG = svg.append('g').attr('id','grid');
yTicks.forEach(t => {
  gridG.append('line').attr('x1',chartLeft).attr('x2',chartRight)
    .attr('y1',y(t)).attr('y2',y(t)).attr('stroke',GRID).attr('stroke-width',0.5);
});
const yLabG = svg.append('g').attr('id','y-labels');
yTicks.forEach((t, i) => {
  const isTop = (i === yTicks.length - 1);
  const lbl = (isTop && P.mode === 'indexed') ? fmtY(t) : fmtY(t);
  yLabG.append('text').attr('x',chartLeft-8).attr('y',y(t)).attr('text-anchor','end').attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

// X-axis ticks: every decade
const xTickG = svg.append('g').attr('id','x-ticks');
const xLabG = svg.append('g').attr('id','x-labels');
const decades = [1950, 1960, 1970, 1980, 1990, 2000, 2010, 2020, 2024];
decades.forEach(yr => {
  if (yr < xs[0] || yr > xs[xs.length-1]) return;
  xTickG.append('line').attr('x1',x(yr)).attr('x2',x(yr))
    .attr('y1',chartBottom).attr('y2',chartBottom+10).attr('stroke',TEXT).attr('stroke-width',0.5);
  let lbl = String(yr);
  // abbreviated style for intermediate years
  if (yr !== 1950 && yr !== 2000 && yr !== 2024 && yr !== xs[xs.length-1]) {
    lbl = "'" + String(yr).slice(2);
  }
  xLabG.append('text').attr('x',x(yr)).attr('y',chartBottom+30).attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',300).attr('fill','#333')
    .text(lbl);
});

// Lines
const lineFn = d3.line().defined(v => v !== null).x((_,i)=>x(xs[i])).y(v=>y(v));
const linesG = svg.append('g').attr('id','lines');
P.series.forEach(s => {
  linesG.append('path').attr('d',lineFn(s.values))
    .attr('fill','none').attr('stroke',s.color).attr('stroke-width',2.5)
    .attr('style','mix-blend-mode: multiply');
});

// Right-side labels with collision avoidance
const labels = P.series.map(s => {
  let li = -1;
  for (let i = s.values.length - 1; i >= 0; i--) { if (s.values[i] !== null) { li = i; break; } }
  if (li < 0) return null;
  return { name: s.name, color: s.color, y: y(s.values[li]), v: s.values[li] };
}).filter(Boolean);
labels.sort((a,b) => a.y - b.y);
const minGap = 26;
for (let i = 1; i < labels.length; i++) {
  if (labels[i].y - labels[i-1].y < minGap) labels[i].y = labels[i-1].y + minGap;
}
const labG = svg.append('g').attr('id','labels');
labels.forEach(d => {
  labG.append('text').attr('x',chartRight+10).attr('y',d.y).attr('dy','0.32em')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',500).attr('fill',d.color)
    .text(d.name);
});

// Source note
const srcG = svg.append('g').attr('id','source');
const src = (P.mode === 'indexed')
 ? 'Source: IPUMS USA harmonized METRO variable (Ruggles et al.). Decennial Census 1950-2000 + ACS 1-year 2005-2024 (excl. experimental 2020). Each ring indexed to its own 1950 level. "Central city" = in metro area, in principal city; "Suburb" = in metro area, outside principal city; "Non-metro" = outside any MSA. Metro-status-unknown cases shown separately.'
 : 'Source: IPUMS USA harmonized METRO variable (Ruggles et al.). Decennial Census 1950-2000 + ACS 1-year 2005-2024 (excl. experimental 2020). "Central city" = in metro area, in principal city; "Suburb" = in metro area, outside principal city; "Non-metro" = outside any MSA. Metro-status-unknown cases shown separately.';
const srcLines = [];
{
  const words = src.split(/\\s+/);
  let line = '';
  const maxChars = 130;
  for (const w of words) {
    if ((line + ' ' + w).length > maxChars) { srcLines.push(line.trim()); line = w; }
    else { line += ' ' + w; }
  }
  if (line.trim()) srcLines.push(line.trim());
}
const srcT = srcG.append('text').attr('x',PAD).attr('y',H-PAD-15)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',200).attr('fill',TEXT);
const startY = H - PAD - 15 - (srcLines.length - 1) * 16;
srcLines.forEach((l,i) => srcT.append('tspan').attr('x',PAD).attr('y', startY + i*16).text(l));
</script>
</body></html>"""

    suffix = "_indexed" if mode == "indexed" else "_level"
    out_path = OUTPUTS / f"under18_by_metro_ring{suffix}.html"
    html = template.replace("__TITLE__", title).replace("__DATA__", json.dumps(P))
    out_path.write_text(html)
    print(f"Wrote {out_path}")


def main():
    if not PARQUET.exists():
        print(f"ERROR: {PARQUET} not found. Run pull_ipums_metro_kids.py first.")
        return
    df = tabulate()
    make_chart(df, mode="level")
    make_chart(df, mode="indexed")


if __name__ == "__main__":
    main()
