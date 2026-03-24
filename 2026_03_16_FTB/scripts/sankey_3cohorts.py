"""
Build three Sankey diagrams (Boomer, Gen X, Millennial) showing population flows
between life stages at ages 18, 25, 30, 35, 40. Uses d3-sankey for layout.
"""
import json, base64, os
import duckdb

# --- Query CPS ASEC data ---
con = duckdb.connect()
pq = '/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec.parquet'

cohorts_def = {
    'Boomer (born 1958)': [(18, 1976), (25, 1983), (30, 1988), (35, 1993), (40, 1998)],
    'Gen X (born 1970)': [(18, 1988), (25, 1995), (30, 2000), (35, 2005), (40, 2010)],
    'Millennial (born 1985)': [(18, 2003), (25, 2010), (30, 2015), (35, 2020), (40, 2025)],
}

states = ['with_parents', 'head_unmarried', 'married_renting', 'owning']
state_labels = {
    'with_parents': 'With parents',
    'head_unmarried': 'Independent, unmarried',
    'married_renting': 'Married, renting',
    'owning': 'Owning',
}
state_colors = {
    'with_parents': '#C6DCCB',
    'head_unmarried': '#67A275',
    'married_renting': '#F4743B',
    'owning': '#0BB4FF',
}

all_cohorts_data = {}  # cohort_name -> list of dicts

for cohort_name, ages_years in cohorts_def.items():
    nodes_data = []
    for age, year in ages_years:
        r = con.execute(f"""
            SELECT
              SUM(CASE WHEN RELATE NOT IN (101,201,202,203) THEN ASECWT ELSE 0 END) as with_parents,
              SUM(CASE WHEN RELATE IN (101,201,202,203) AND MARST NOT IN (1,2) AND OWNERSHP != 10 THEN ASECWT ELSE 0 END) as head_unmarried,
              SUM(CASE WHEN RELATE IN (101,201,202,203) AND MARST IN (1,2) AND OWNERSHP != 10 THEN ASECWT ELSE 0 END) as married_renting,
              SUM(CASE WHEN RELATE IN (101,201,202,203) AND OWNERSHP = 10 THEN ASECWT ELSE 0 END) as owning,
              SUM(ASECWT) as total
            FROM '{pq}'
            WHERE YEAR = {year} AND AGE = {age}
        """).df()
        total = r['total'].iloc[0]
        row = {'age': age}
        for s in states:
            row[s] = round(r[s].iloc[0] / total * 100)
        nodes_data.append(row)
    all_cohorts_data[cohort_name] = nodes_data

# --- Build nodes and links for each cohort ---
all_charts = {}  # cohort_name -> (nodes, links)

for cohort_name, nodes_data in all_cohorts_data.items():
    nodes = []
    node_index = {}
    idx = 0
    for col in nodes_data:
        age = col['age']
        for s in states:
            val = col[s]
            if val > 0:
                name = f"{s}_{age}"
                node_index[name] = idx
                nodes.append({
                    'name': name,
                    'label': state_labels[s],
                    'age': age,
                    'value': val,
                    'color': state_colors[s],
                })
                idx += 1

    links = []
    for i in range(len(nodes_data) - 1):
        a = nodes_data[i]
        b = nodes_data[i + 1]
        age_a = a['age']
        age_b = b['age']

        outflows = {}
        inflows = {}

        for s in states:
            va = a[s]
            vb = b[s]
            if va == 0 and vb == 0:
                continue
            stay = min(va, vb)
            if stay > 0:
                src = f"{s}_{age_a}"
                tgt = f"{s}_{age_b}"
                if src in node_index and tgt in node_index:
                    links.append({
                        'source': node_index[src],
                        'target': node_index[tgt],
                        'value': stay,
                        'color': state_colors[s],
                    })
            diff = vb - va
            if diff < 0:
                outflows[s] = -diff
            elif diff > 0:
                inflows[s] = diff

        total_in = sum(inflows.values()) if inflows else 1
        for src_state, out_amt in outflows.items():
            for dst_state, in_amt in inflows.items():
                flow = round(out_amt * (in_amt / total_in))
                if flow > 0:
                    src = f"{src_state}_{age_a}"
                    tgt = f"{dst_state}_{age_b}"
                    if src in node_index and tgt in node_index:
                        links.append({
                            'source': node_index[src],
                            'target': node_index[tgt],
                            'value': flow,
                            'color': state_colors[src_state],
                        })

    all_charts[cohort_name] = (nodes, links)

# --- Logo ---
LOGO = '/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png'
with open(LOGO, 'rb') as f:
    logo_b64 = base64.b64encode(f.read()).decode()

# --- Build HTML ---
ages = [18, 25, 30, 35, 40]
chart_names = list(all_charts.keys())

# Build JS data for each cohort
charts_js_blocks = []
for i, cohort_name in enumerate(chart_names):
    nodes, links = all_charts[cohort_name]
    charts_js_blocks.append(f"""
    {{
      name: {json.dumps(cohort_name)},
      nodes: {json.dumps(nodes)},
      links: {json.dumps(links)},
    }}""")

charts_js = "[" + ",".join(charts_js_blocks) + "\n  ]"

html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Thin.otf'); font-weight:200; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Light.otf'); font-weight:300; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Regular.otf'); font-weight:400; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Medium.otf'); font-weight:500; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Bold.otf'); font-weight:700; }}
  body {{ margin:0; padding:20px; background:#F6F7F3; font-family:'ABC Oracle Edu',system-ui,sans-serif; }}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
</head><body>
<script>
const W = 960, H = 500;
const ages = {json.dumps(ages)};
const lastAge = ages[ages.length - 1];
const chartsData = {charts_js};
const logoB64 = "{logo_b64}";

chartsData.forEach((chartData, ci) => {{
  const svg = d3.select("body").append("svg").attr("width", W).attr("height", H)
    .attr("font-family", "ABC Oracle Edu")
    .style("display", "block")
    .style("margin-bottom", ci < chartsData.length - 1 ? "10px" : "0");
  svg.append("rect").attr("width", W).attr("height", H).attr("fill", "#F6F7F3");

  const chartLeft = 40, chartRight = W - 200;
  const chartTop = 60, chartBottom = H - 70;

  // Title
  svg.append("text").attr("x", chartLeft).attr("y", 38)
    .attr("font-size", "26px").attr("font-weight", "500").attr("fill", "#3D3733")
    .text(chartData.name);

  const nodesRaw = chartData.nodes;
  const linksRaw = chartData.links;

  const sankey = d3.sankey()
    .nodeId(d => d.index)
    .nodeWidth(12)
    .nodePadding(14)
    .nodeSort(null)
    .extent([[chartLeft, chartTop], [chartRight, chartBottom]]);

  const graph = sankey({{
    nodes: nodesRaw.map((d, i) => ({{...d, index: i}})),
    links: linksRaw.map(d => ({{...d}})),
  }});

  // Links
  svg.append("g")
    .selectAll("path")
    .data(graph.links)
    .join("path")
    .attr("d", d3.sankeyLinkHorizontal())
    .attr("fill", "none")
    .attr("stroke", d => d.color || "#ccc")
    .attr("stroke-opacity", 0.35)
    .attr("stroke-width", d => Math.max(1, d.width));

  // Nodes
  svg.append("g")
    .selectAll("rect")
    .data(graph.nodes)
    .join("rect")
    .attr("x", d => d.x0)
    .attr("y", d => d.y0)
    .attr("width", d => d.x1 - d.x0)
    .attr("height", d => Math.max(1, d.y1 - d.y0))
    .attr("fill", d => d.color)
    .attr("rx", 2);

  // Percentage labels on nodes
  svg.append("g")
    .selectAll("text")
    .data(graph.nodes.filter(d => d.age !== lastAge))
    .join("text")
    .attr("x", d => d.x0 + (d.x1 - d.x0) / 2)
    .attr("y", d => (d.y0 + d.y1) / 2 + 4)
    .attr("text-anchor", "middle")
    .attr("font-size", "11px")
    .attr("font-weight", "500")
    .attr("fill", d => {{
      // Use dark text for light backgrounds
      if (d.color === '#C6DCCB') return '#3D3733';
      return 'white';
    }})
    .text(d => (d.y1 - d.y0) > 18 ? d.value + "%" : "");

  // Right-side labels on last column
  svg.append("g")
    .selectAll("text")
    .data(graph.nodes.filter(d => d.age === lastAge))
    .join("text")
    .attr("x", d => d.x1 + 8)
    .attr("y", d => (d.y0 + d.y1) / 2 + 4)
    .attr("text-anchor", "start")
    .attr("font-size", "14px")
    .attr("font-weight", "400")
    .attr("fill", "#3D3733")
    .text(d => d.label + " " + d.value + "%");

  // Age labels
  const agePositions = {{}};
  graph.nodes.forEach(n => {{
    if (!agePositions[n.age]) agePositions[n.age] = (n.x0 + n.x1) / 2;
  }});
  ages.forEach(age => {{
    if (agePositions[age]) {{
      svg.append("text")
        .attr("x", agePositions[age])
        .attr("y", chartBottom + 25)
        .attr("text-anchor", "middle")
        .attr("font-size", "18px").attr("font-weight", "300").attr("fill", "#3D3733")
        .text("Age " + age);
    }}
  }});

  // Source text and logo on last chart only
  if (ci === chartsData.length - 1) {{
    svg.append("text").attr("x", chartLeft).attr("y", H - 15)
      .attr("font-size", "15px").attr("font-weight", "200").attr("fill", "#3D3733")
      .text("Source: CPS ASEC. Cross-sectional state distribution at each age.");

    svg.append("image").attr("x", W - 40 - 130).attr("y", H - 15 - 42 + 5)
      .attr("width", 130).attr("height", 42).attr("opacity", 0.6)
      .each(function() {{
        this.setAttributeNS("http://www.w3.org/1999/xlink", "xlink:href",
          "data:image/png;base64," + logoB64);
      }});
  }}
}});
</script>
</body></html>"""

out = "/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/outputs/sankey_3cohorts.html"
with open(out, "w") as f:
    f.write(html)
print(f"Saved to {out}")
os.system(f'open "{out}"')
