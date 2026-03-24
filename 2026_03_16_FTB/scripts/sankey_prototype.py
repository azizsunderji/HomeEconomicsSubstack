"""
Build a true Sankey/alluvial for a single cohort (born ~1993).
4 age columns, 4 states, computed net flows as links.
Uses d3-sankey for proper node+link layout.
"""
import json, base64, os

# State distributions at each age
nodes_data = [
    {'age': 18, 'with_parents': 95, 'head_unmarried': 2, 'married_renting': 0, 'owning': 2},
    {'age': 22, 'with_parents': 70, 'head_unmarried': 18, 'married_renting': 5, 'owning': 7},
    {'age': 26, 'with_parents': 48, 'head_unmarried': 21, 'married_renting': 13, 'owning': 17},
    {'age': 30, 'with_parents': 36, 'head_unmarried': 17, 'married_renting': 14, 'owning': 33},
]

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

# Build d3-sankey nodes and links
# Node naming: "state_age" e.g. "with_parents_18"
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

# Compute links (net flows between consecutive age columns)
links = []
for i in range(len(nodes_data) - 1):
    a = nodes_data[i]
    b = nodes_data[i + 1]
    age_a = a['age']
    age_b = b['age']

    # For each state: if it stays or grows, some flow stays within it
    # If it shrinks, flow goes to states that grew
    outflows = {}  # states that shrank: {state: amount}
    inflows = {}   # states that grew: {state: amount}
    stays = {}     # states that stayed same or shrank: min(a, b)

    for s in states:
        va = a[s]
        vb = b[s]
        if va == 0 and vb == 0:
            continue
        stay = min(va, vb)
        if stay > 0:
            stays[s] = stay
            # Link from state_age_a to state_age_b (staying in same state)
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

    # Distribute outflows to inflow states proportionally
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

LOGO = '/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/HomeEconomics-Logo-versions/HE-Large-Black.png'
with open(LOGO, 'rb') as f:
    logo_b64 = base64.b64encode(f.read()).decode()

nodes_js = json.dumps(nodes)
links_js = json.dumps(links)

html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Thin.otf'); font-weight:200; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Light.otf'); font-weight:300; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Regular.otf'); font-weight:400; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Medium.otf'); font-weight:500; }}
  @font-face {{ font-family:'ABC Oracle Edu'; src:url('/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop/ABCOracle-Bold.otf'); font-weight:700; }}
  body {{ margin:20px; background:#fff; font-family:'ABC Oracle Edu',system-ui,sans-serif; }}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
</head><body>
<script>
const W = 960, H = 700;
const pad = 40;
const titleY = pad + 32;
const subtitleY = titleY + 30;
const chartTop = subtitleY + 50;
const chartBottom = H - 100;
const chartLeft = 40, chartRight = W - 160;
const chartW = chartRight - chartLeft;
const chartH = chartBottom - chartTop;
const gridLeftEdge = chartLeft;

const svg = d3.select("body").append("svg").attr("width",W).attr("height",H)
  .attr("font-family","ABC Oracle Edu");
svg.append("rect").attr("width",W).attr("height",H).attr("fill","#F6F7F3");

svg.append("text").attr("x",gridLeftEdge).attr("y",titleY)
  .attr("font-size","32px").attr("font-weight","500").attr("fill","#3D3733")
  .text("The path to homeownership: born 1993");
svg.append("text").attr("x",gridLeftEdge).attr("y",subtitleY)
  .attr("font-size","23px").attr("font-weight","400").attr("fill","#7F7570")
  .text("How a cohort flows through life stages, ages 18\\u201330");

const nodesRaw = {nodes_js};
const linksRaw = {links_js};

// Build the sankey layout
const sankey = d3.sankey()
  .nodeId(d => d.index)
  .nodeWidth(12)
  .nodePadding(14)
  .nodeSort(null) // preserve input order
  .extent([[chartLeft, chartTop], [chartRight, chartBottom]]);

const graph = sankey({{
  nodes: nodesRaw.map((d,i) => ({{...d, index: i}})),
  links: linksRaw.map(d => ({{...d}})),
}});

// Draw links
svg.append("g")
  .selectAll("path")
  .data(graph.links)
  .join("path")
  .attr("d", d3.sankeyLinkHorizontal())
  .attr("fill", "none")
  .attr("stroke", d => d.color || "#ccc")
  .attr("stroke-opacity", 0.35)
  .attr("stroke-width", d => Math.max(1, d.width));

// Draw nodes
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

// Node labels (right side of last column, left side of others)
svg.append("g")
  .selectAll("text")
  .data(graph.nodes)
  .join("text")
  .attr("x", d => d.age === 30 ? d.x1 + 8 : d.x0 + (d.x1 - d.x0)/2)
  .attr("y", d => (d.y0 + d.y1) / 2 + 4)
  .attr("text-anchor", d => d.age === 30 ? "start" : "middle")
  .attr("font-size", d => d.age === 30 ? "14px" : "12px")
  .attr("font-weight", d => d.age === 30 ? "400" : "500")
  .attr("fill", d => d.age === 30 ? "#3D3733" : "white")
  .text(d => {{
    if (d.age === 30) return d.label + " " + d.value + "%";
    if (d.y1 - d.y0 > 20) return d.value + "%";
    return "";
  }});

// Age labels below each column
const ages = [18, 22, 26, 30];
const agePositions = {{}};
graph.nodes.forEach(n => {{
  if (!agePositions[n.age]) agePositions[n.age] = (n.x0 + n.x1) / 2;
}});
ages.forEach(age => {{
  if (agePositions[age]) {{
    svg.append("text")
      .attr("x", agePositions[age])
      .attr("y", chartBottom + 30)
      .attr("text-anchor", "middle")
      .attr("font-size", "20px").attr("font-weight", "300").attr("fill", "#333")
      .text("Age " + age);
  }}
}});

// Source
svg.append("text").attr("x",gridLeftEdge).attr("y",H-35)
  .attr("font-size","15px").attr("font-weight","200").attr("fill","#3D3733")
  .text("Source: CPS ASEC 2011\\u20132023. Cross-sectional state at each age for people born ~1993.");

// Logo
svg.append("image").attr("x",W-40-130).attr("y",H-35-42+10)
  .attr("width",130).attr("height",42).attr("opacity",0.6)
  .each(function() {{
    this.setAttributeNS("http://www.w3.org/1999/xlink","xlink:href",
      "data:image/png;base64,{logo_b64}");
  }});
</script>
</body></html>"""

out = "/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/outputs/sankey_cohort.html"
with open(out, "w") as f:
    f.write(html)
print(f"Saved to {out}")
os.system(f'open "{out}"')
