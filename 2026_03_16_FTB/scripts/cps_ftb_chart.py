"""
CPS ASEC FTB median age, Redfin methodology (WHYMOVE=9 or 2), 1999-2025.
"""
import json

with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/cps_ftb_longrun.json') as f:
    data = json.load(f)

# Only Redfin method
redfin = [(d['year'], d['median']) for d in data if d['method'] == 'redfin']
rjson = "[" + ",".join(f'{{"year":{y},"age":{a}}}' for y, a in redfin) + "]"

html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<style>
  body {{ margin:0; background:#F6F7F3; font-family:'ABC Oracle Edu',system-ui,sans-serif; }}
  .title {{ font-size:18px; font-weight:700; fill:#3D3733; }}
  .subtitle {{ font-size:12.5px; fill:#3D3733; opacity:0.8; }}
  .source {{ font-size:9.5px; fill:#999; font-style:italic; }}
  .axis text {{ font-size:11px; fill:#3D3733; }}
  .grid line {{ stroke:#fff; stroke-width:1; }}
  .grid path {{ stroke:none; }}
  .label {{ font-size:11px; font-weight:600; }}
  .dot {{ stroke:#fff; stroke-width:1.5; }}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
</head><body>
<script>
const data = {rjson};

const W = 900, H = 480;
const m = {{top:65, right:50, bottom:55, left:50}};
const w = W-m.left-m.right, h = H-m.top-m.bottom;

const svg = d3.select("body").append("svg").attr("width",W).attr("height",H)
  .style("background","#F6F7F3");
const g = svg.append("g").attr("transform",`translate(${{m.left}},${{m.top}})`);

svg.append("text").attr("class","title").attr("x",m.left).attr("y",25)
  .text("Median age of first-time homebuyers");
svg.append("text").attr("class","subtitle").attr("x",m.left).attr("y",46)
  .text("CPS ASEC, Redfin methodology: moved to own rather than rent, or to establish own household. 1999\u20132025.");

const x = d3.scaleLinear().domain([1998,2026]).range([0,w]);
const y = d3.scaleLinear().domain([28,40]).range([h,0]);

g.append("g").attr("class","grid")
  .call(d3.axisLeft(y).tickSize(-w).tickFormat("").ticks(6));

g.append("g").attr("class","axis").attr("transform",`translate(0,${{h}})`)
  .call(d3.axisBottom(x).tickFormat(d3.format("d"))
    .tickValues([2000,2005,2010,2015,2020,2025]));

const yAx = g.append("g").attr("class","axis")
  .call(d3.axisLeft(y).ticks(6).tickSize(0)
    .tickFormat((d,i,nodes) => i===nodes.length-1 ? d+" yrs" : d));
yAx.select(".domain").remove();

const line = d3.line().x(d=>x(d.year)).y(d=>y(d.age));

g.append("path").datum(data).attr("d",line)
  .attr("fill","none").attr("stroke","#0BB4FF").attr("stroke-width",2.5);

data.forEach(d => {{
  g.append("circle").attr("class","dot")
    .attr("cx",x(d.year)).attr("cy",y(d.age))
    .attr("r",3).attr("fill","#0BB4FF");
}});

// Start and end labels
const first = data[0], last = data[data.length-1];
g.append("text").attr("class","label").attr("fill","#0BB4FF")
  .attr("x",x(first.year)-8).attr("y",y(first.age)+4)
  .attr("text-anchor","end").text(first.age);
g.append("text").attr("class","label").attr("fill","#0BB4FF")
  .attr("x",x(last.year)+8).attr("y",y(last.age)+4)
  .text(last.age);

svg.append("text").attr("class","source")
  .attr("x",m.left).attr("y",H-15)
  .text("Source: CPS ASEC (IPUMS), 1999\u20132025. FTB = moved to own (WHYMOVE=9) or establish own household (WHYMOVE=2). Heads/spouses only, weighted.");
</script>
</body></html>"""

with open("/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/outputs/cps_ftb_redfin.html", "w") as f:
    f.write(html)
print("Saved to outputs/cps_ftb_redfin.html")
