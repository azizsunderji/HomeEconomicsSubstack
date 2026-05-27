"""
Beeswarm small-multiples for the 10 biggest MSAs.

Each panel = one MSA. Each bubble = one county.
  - Bubble size ∝ 2011 under-18 population
  - Bubble color ∝ % change in under-18 (blue = gain, light = small gain/no change)
  - Bubble position: anchored by physical distance from MSA center
  - Inner counties: outlined with thick "webbing" outline grouping them

Output: outputs/beeswarm_msa.html
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
OUTPUTS = PROJECT / "outputs"
CENPOP = PROJECT / "data" / "cenpop2020.txt"
CSA_DATA = PROJECT / "data" / "csa_decomposition.csv"

# Display names for each CSA in our analysis
SHORT_CSA = {
    "New York":      "New York (CSA)",
    "Los Angeles":   "Los Angeles (CSA)",
    "Chicago":       "Chicago (CSA)",
    "Dallas":        "Dallas-Fort Worth (CSA)",
    "Houston":       "Houston (CSA)",
    "Atlanta":       "Atlanta (CSA)",
    "Washington":    "Washington-Baltimore (CSA)",
    "Philadelphia":  "Philadelphia (CSA)",
    "Miami":         "Miami (CSA)",
    "Phoenix":       "Phoenix (CSA)",
}


def load_county_centroids() -> dict[str, tuple[float, float]]:
    """Return {fips_5: (lat, lon)} from Census population-weighted centroids."""
    df = pd.read_csv(CENPOP, dtype={"STATEFP": str, "COUNTYFP": str})
    df["STATEFP"] = df["STATEFP"].str.zfill(2)
    df["COUNTYFP"] = df["COUNTYFP"].str.zfill(3)
    df["fips_5"] = df["STATEFP"] + df["COUNTYFP"]
    out = {}
    for _, r in df.iterrows():
        out[r["fips_5"]] = (float(r["LATITUDE"]), float(r["LONGITUDE"]))
    return out


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def main():
    print("Loading county centroids...")
    centroids = load_county_centroids()
    print(f"  {len(centroids)} county centroids loaded")

    # CSA-level data: 199 counties across 10 CSAs
    dec = pd.read_csv(CSA_DATA, dtype={"fips_5": str})
    dec["fips_5"] = dec["fips_5"].str.zfill(5)

    panels = []
    for csa_short in SHORT_CSA:
        msa_counties = dec[dec["csa_short"] == csa_short].copy()
        if msa_counties.empty:
            continue
        # Inner counties already flagged in csa_decomposition.csv (is_inner column)
        inner_set = set(msa_counties.loc[msa_counties["is_inner"] == True, "fips_5"])
        msa_name = csa_short
        # MSA "center" = centroid of inner counties (lat/lon average weighted by population if available, else mean)
        inner_centroids = [centroids[f] for f in inner_set if f in centroids]
        if not inner_centroids:
            print(f"  ⚠ no inner-county centroids for {msa_name}")
            continue
        # Pop-weighted center (use 2011 under-18 pop as weights)
        weights, lats, lons = [], [], []
        for f in inner_set:
            if f in centroids:
                row = msa_counties[msa_counties["fips_5"] == f]
                w = float(row["pop_under18"].iloc[0]) if not row.empty and pd.notna(row["pop_under18"].iloc[0]) else 1.0
                weights.append(w)
                lats.append(centroids[f][0])
                lons.append(centroids[f][1])
        w_total = sum(weights)
        center_lat = sum(l * w for l, w in zip(lats, weights)) / w_total
        center_lon = sum(l * w for l, w in zip(lons, weights)) / w_total

        nodes = []
        for _, r in msa_counties.iterrows():
            fips = r["fips_5"]
            if fips not in centroids:
                continue
            if pd.isna(r["pop_under18"]) or pd.isna(r["pop_under18_2024"]):
                continue
            lat, lon = centroids[fips]
            dist_km = haversine_km(lat, lon, center_lat, center_lon)
            pop = int(r["pop_under18"])
            pop24 = int(r["pop_under18_2024"])
            delta_abs = pop24 - pop
            delta_pct = delta_abs / pop * 100 if pop > 0 else 0
            # Common names for NYC boroughs (the official county names confuse viewers)
            COMMON = {
                "36005": "Bronx", "36047": "Brooklyn", "36061": "Manhattan",
                "36081": "Queens", "36085": "Staten Island",
            }
            name = COMMON.get(fips, str(r["County/County Equivalent"])
                              .replace(" County", "").replace(" Parish", "").replace(" city", ""))
            nodes.append({
                "fips": fips,
                "name": name,
                "is_inner": bool(r["is_inner"]),
                "dist_km": dist_km,
                "pop_2011": pop,
                "delta_pct": delta_pct,
                "delta_abs": delta_abs,
            })
        panels.append({
            "msa": SHORT_CSA[csa_short],
            "msa_full": csa_short,
            "n_counties": len(nodes),
            "nodes": nodes,
        })
        print(f"  {SHORT_CSA[csa_short]:30s} {len(nodes):>3} counties (center {center_lat:.3f}, {center_lon:.3f})")

    payload = json.dumps(panels)
    out = OUTPUTS / "beeswarm_msa.html"

    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>10 MSAs — beeswarm of county-level under-18 change</title>
<style>
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Regular.otf') format('opentype'); font-weight:400; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Medium.otf') format('opentype'); font-weight:500; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Bold.otf') format('opentype'); font-weight:700; }}
@font-face {{ font-family:'ABC Oracle Edu'; src:url('file:///Users/azizsunderji/Dropbox/Home%20Economics/Brand%20Assets/OracleFont/Oracle%20Aziz%20Sunderji/Desktop/ABCOracleEdu-Light.otf') format('opentype'); font-weight:300; }}
body {{ margin:0; background:#fff; font-family:'ABC Oracle Edu',sans-serif; }}
svg {{ display:block; margin:20px auto; }}
.tooltip {{ position:absolute; pointer-events:none; background:rgba(61,55,51,0.95); color:#F6F7F3; padding:8px 12px; font-size:13px; border-radius:4px; font-family:'ABC Oracle Edu',sans-serif; }}
</style></head><body>
<svg id="chart" viewBox="0 0 1600 1900" xmlns="http://www.w3.org/2000/svg"></svg>
<div class="tooltip" style="display:none"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
const PANELS = {payload};
const BG = '#F6F7F3', TEXT = '#3D3733', SUBTEXT = '#7F7570';
const W = 1600, H = 1900, PAD = 40;
const COLS = 2, ROWS = 5;
const headerH = 110;
const panelW = (W - 3*PAD) / COLS;
const panelH = (H - headerH - PAD - 70) / ROWS;

const svg = d3.select('#chart');
svg.append('rect').attr('width', W).attr('height', H).attr('fill', BG);

svg.append('text').attr('x', PAD).attr('y', PAD + 32)
  .attr('font-family','ABC Oracle Edu').attr('font-size',30).attr('font-weight',700).attr('fill',TEXT)
  .text('Where the kids are — and where they are going');
svg.append('text').attr('x', PAD).attr('y', PAD + 32 + 28)
  .attr('font-family','ABC Oracle Edu').attr('font-size',17).attr('font-weight',400).attr('fill',TEXT)
  .text('Top 10 MSAs. Each bubble = one county, size ∝ 2011 under-18 population, color ∝ % change 2011-2024. Inner counties grouped.');

// 10-bin categorical palette: black/grey for negative, blue for positive.
// No pure white in the middle — transitions through cream and pale blue.
const colorBins   = ['#1A1715', '#3D3733', '#6B635C', '#9B948D', '#C7BFB7',
                     '#DADFCE', '#BCE8FF', '#7DD4FF', '#0BB4FF', '#005C99'];
const colorBreaks = [-20, -10, -5, -2, 1, 3, 6, 15, 30];  // 9 breakpoints → 10 bins
const colorScale  = d3.scaleThreshold().domain(colorBreaks).range(colorBins);

// Bubble size scale (sqrt for area-proportional)
const allPops = PANELS.flatMap(p => p.nodes.map(n => n.pop_2011));
const popExtent = [d3.min(allPops), d3.max(allPops)];
// Each panel will scale within its own range for visual clarity
function rScale(panel) {{
  const m = d3.min(panel.nodes, n => n.pop_2011);
  const M = d3.max(panel.nodes, n => n.pop_2011);
  return d3.scaleSqrt().domain([m, M]).range([6, 38]);
}}

const tip = d3.select('.tooltip');

PANELS.forEach((p, i) => {{
  const col = i % COLS, row = Math.floor(i / COLS);
  const x0 = PAD + col * (panelW + PAD);
  const y0 = headerH + row * (panelH);

  // Panel title
  svg.append('text').attr('x', x0 + panelW/2).attr('y', y0 + 16)
    .attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',16).attr('font-weight',700).attr('fill',TEXT)
    .text(p.msa);
  svg.append('text').attr('x', x0 + panelW/2).attr('y', y0 + 32)
    .attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',11).attr('font-weight',300).attr('fill',SUBTEXT)
    .text(`${{p.n_counties}} counties · highlighted = urban core`);

  const cx = x0 + panelW/2;
  const cy = y0 + 36 + (panelH - 60)/2;
  const rs = rScale(p);

  // Assign radius and SORT by distance from MSA center (closest first)
  p.nodes.forEach(n => {{ n.r = rs(n.pop_2011); }});
  p.nodes.sort((a, b) => a.dist_km - b.dist_km);

  // Pack with inflated radii so gaps appear between actual bubbles —
  // the dark webbing under inner counties fills those gaps visibly.
  const PACK_PAD = 4;
  p.nodes.forEach(n => {{ n.r += PACK_PAD; }});
  d3.packSiblings(p.nodes);
  p.nodes.forEach(n => {{ n.r -= PACK_PAD; }});

  // Center the cluster in the panel
  const cxAvg = d3.mean(p.nodes, n => n.x), cyAvg = d3.mean(p.nodes, n => n.y);
  p.nodes.forEach(n => {{ n.x += cx - cxAvg; n.y += cy - cyAvg; }});

  const g = svg.append('g');

  // Webbing for inner counties: dark "halo" extending into the inter-bubble gap.
  // The packing pad above leaves PAD px of gap between adjacent bubbles; the
  // webbing halo just exceeds that pad so adjacent inner bubbles' halos merge
  // into a continuous dark blob.
  const inners = p.nodes.filter(n => n.is_inner);
  const HALO = PACK_PAD + 3;  // a touch wider than the packing pad
  inners.forEach(n => {{
    g.append('circle')
      .attr('cx', n.x).attr('cy', n.y).attr('r', n.r + HALO)
      .attr('fill', '#3D3733');
  }});

  // All bubbles on top
  p.nodes.forEach(n => {{
    g.append('circle')
      .attr('cx', n.x).attr('cy', n.y).attr('r', n.r)
      .attr('fill', colorScale(n.delta_pct))
      .attr('stroke', '#F6F7F3').attr('stroke-width', 1)
      .style('cursor', 'pointer')
      .on('mousemove', e => {{
        tip.style('display','block').style('left', (e.pageX + 12) + 'px').style('top', (e.pageY + 12) + 'px')
          .html(
            `<b>${{n.name}}</b><br>` +
            (n.is_inner ? '<span style="opacity:0.7">Inner / core</span><br>' : '') +
            `2011 under-18 pop: ${{n.pop_2011.toLocaleString()}}<br>` +
            `Δ 2011-24: ${{n.delta_abs > 0 ? '+' : ''}}${{n.delta_abs.toLocaleString()}} (${{n.delta_pct.toFixed(1)}}%)<br>` +
            `Distance from MSA center: ${{n.dist_km.toFixed(0)}} km`
          );
      }})
      .on('mouseout', () => tip.style('display','none'));
  }});

  // Label the biggest (inner) counties only — avoid clutter
  inners.sort((a, b) => b.r - a.r).slice(0, 2).forEach(n => {{
    g.append('text').attr('x', n.x).attr('y', n.y + 4)
      .attr('text-anchor','middle')
      .attr('font-family','ABC Oracle Edu').attr('font-size', Math.min(11, n.r/2.5)).attr('font-weight',700)
      .attr('fill', '#F6F7F3').attr('pointer-events','none')
      .text(n.name);
  }});
}});

// Categorical color legend — discrete swatches with breakpoint labels below
const lgX = W - 460, lgY = PAD + 40, swW = 38, swH = 14;
svg.append('text').attr('x', lgX).attr('y', lgY - 8)
  .attr('font-family','ABC Oracle Edu').attr('font-size',12).attr('font-weight',500).attr('fill',TEXT)
  .text('Δ under-18 population, 2011 → 2024');
colorBins.forEach((c, i) => {{
  svg.append('rect').attr('x', lgX + i * swW).attr('y', lgY)
    .attr('width', swW).attr('height', swH).attr('fill', c);
}});
// Breakpoint labels under boundaries
colorBreaks.forEach((v, i) => {{
  svg.append('text').attr('x', lgX + (i + 1) * swW).attr('y', lgY + swH + 14)
    .attr('text-anchor','middle')
    .attr('font-family','ABC Oracle Edu').attr('font-size',10).attr('font-weight',300).attr('fill',TEXT)
    .text((v > 0 ? '+' : '') + v + '%');
}});

// Source
svg.append('text').attr('x', PAD).attr('y', H - PAD - 16)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill',TEXT)
  .text('Source: Census Population Estimates Program (V2019 + V2024) for under-18 populations; Census TIGER 2023 county centroids for distance to MSA center.');
svg.append('text').attr('x', PAD).attr('y', H - PAD - 0)
  .attr('font-family','ABC Oracle Edu').attr('font-size',13).attr('font-weight',300).attr('fill',SUBTEXT)
  .text('Bubble position: counties closer to the MSA center plot near the middle; outer counties plot farther out. "Urban core" = central principal counties (Manhattan/Brooklyn/etc. for NYC, Cook for Chicago, LA County for LA, etc.).');
</script>
</body></html>"""
    out.write_text(html)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
