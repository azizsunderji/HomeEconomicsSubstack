"""
All-sources comparison: Median FTB age at purchase.
AHS (our analysis), NY Fed CCP, NAR, CFPB/NMDB.
"""

# AHS median (our analysis, 1985-2023)
ahs = [
    (1985,30),(1987,31),(1989,31),(1991,31),(1993,32),(1995,32),
    (2001,31),(2003,31),(2005,30),(2007,30),(2009,30),(2011,30),(2013,30),
    (2015,32),(2017,32),(2019,32),(2021,33),(2023,34),
]

# NY Fed CCP median (from Liberty Street Economics + AEI)
nyfed = [
    (2000,35),(2007,33),(2016,32),(2019,33),(2024,33),(2025,34),
]

# NAR median (from NAR Profile of Home Buyers & Sellers, various years)
# Confirmed data points from published sources
nar = [
    (1981,29),(1991,28),(1993,32),(1997,32),(2000,32),(2003,32),(2005,32),
    (2007,30),(2009,30),(2010,30),(2011,31),(2012,31),(2013,31),(2014,31),
    (2015,30),(2016,32),(2017,32),(2018,32),(2019,33),(2020,33),(2021,33),
    (2022,36),(2023,35),(2024,38),(2025,40),
]

# CFPB/NMDB median (from Figure 7 of March 2020 Market Snapshot)
# Read off their chart: 32 in 2002, dips to ~30 in 2009-2011, back to 32 by 2018
cfpb = [
    (2002,32),(2003,31),(2004,31),(2005,31),(2006,30),(2007,30),
    (2008,30),(2009,30),(2010,30),(2011,30),(2012,30),(2013,30),
    (2014,30),(2015,31),(2016,31),(2017,32),(2018,32),
]

# Redfin median (CPS March Supplement, "moved to own rather than rent")
# Read off their chart at redfin.com/news/median-homebuying-age-2025/
redfin = [
    (2008,33),(2009,33),(2010,33),(2011,34),(2012,34),(2013,35),
    (2014,35),(2015,35),(2016,36),(2017,37),(2018,38),(2019,37),
    (2020,36),(2021,35),(2022,36),(2023,36),(2024,36),(2025,35),
]

def to_json(data, name):
    return "[" + ",".join(f'{{"year":{y},"age":{a}}}' for y,a in data) + "]"

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
  .label {{ font-size:10.5px; font-weight:600; }}
  .dot {{ stroke:#fff; stroke-width:1; }}
  .annotation {{ font-size:9.5px; fill:#999; font-style:italic; }}
</style>
<script src="https://d3js.org/d3.v7.min.js"></script>
</head><body>
<script>
const ahs = {to_json(ahs, 'ahs')};
const nyfed = {to_json(nyfed, 'nyfed')};
const nar = {to_json(nar, 'nar')};
const cfpb = {to_json(cfpb, 'cfpb')};
const redfin = {to_json(redfin, 'redfin')};

const W = 900, H = 520;
const m = {{top:75, right:110, bottom:55, left:50}};
const w = W-m.left-m.right, h = H-m.top-m.bottom;

const svg = d3.select("body").append("svg").attr("width",W).attr("height",H)
  .style("background","#F6F7F3");
const g = svg.append("g").attr("transform",`translate(${{m.left}},${{m.top}})`);

svg.append("text").attr("class","title").attr("x",m.left).attr("y",25)
  .text("Median age of first-time homebuyers, by data source");
svg.append("text").attr("class","subtitle").attr("x",m.left).attr("y",46)
  .text("Five independent measures tell different stories about whether FTBs are getting older.");

const x = d3.scaleLinear().domain([1980,2027]).range([0,w]);
const y = d3.scaleLinear().domain([26,42]).range([h,0]);

// Grid
g.append("g").attr("class","grid")
  .call(d3.axisLeft(y).tickSize(-w).tickFormat("").ticks(8));

// X axis
g.append("g").attr("class","axis").attr("transform",`translate(0,${{h}})`)
  .call(d3.axisBottom(x).tickFormat(d3.format("d"))
    .tickValues([1985,1990,1995,2000,2005,2010,2015,2020,2025]));

// Y axis
const yAx = g.append("g").attr("class","axis")
  .call(d3.axisLeft(y).ticks(8).tickSize(0)
    .tickFormat((d,i,nodes) => i===nodes.length-1 ? d+" yrs" : d));
yAx.select(".domain").remove();

const line = d3.line().x(d=>x(d.year)).y(d=>y(d.age));

const BLUE = "#0BB4FF";
const RED = "#F4743B";
const GREEN = "#67A275";
const YELLOW = "#FEC439";
const LIGHTRED = "#FBCAB5";

// Helper: draw segmented line (gap at 1996-2000 for AHS)
function drawLine(data, color, dash, width) {{
  // Split AHS at gap
  if (data === ahs) {{
    const pre = data.filter(d=>d.year<=1995);
    const post = data.filter(d=>d.year>=2001);
    [pre,post].forEach(seg => {{
      g.append("path").datum(seg).attr("d",line)
        .attr("fill","none").attr("stroke",color)
        .attr("stroke-width",width).attr("stroke-dasharray",dash||"none");
    }});
  }} else {{
    g.append("path").datum(data).attr("d",line)
      .attr("fill","none").attr("stroke",color)
      .attr("stroke-width",width).attr("stroke-dasharray",dash||"none");
  }}
  data.forEach(d => {{
    g.append("circle").attr("class","dot")
      .attr("cx",x(d.year)).attr("cy",y(d.age))
      .attr("r",2.5).attr("fill",color);
  }});
}}

// Draw in order: background first, foreground last
drawLine(cfpb, GREEN, "4,3", 2);
drawLine(redfin, LIGHTRED, null, 2);
drawLine(nyfed, YELLOW, null, 2.5);
drawLine(ahs, BLUE, null, 2.5);
drawLine(nar, RED, null, 2);

// No end labels — legend only

// AHS gap annotation
g.append("text").attr("class","annotation")
  .attr("x",(x(1995)+x(2001))/2).attr("y",y(33)-6)
  .attr("text-anchor","middle").text("AHS gap");

// Source
svg.append("text").attr("class","source")
  .attr("x",m.left).attr("y",H-30)
  .text("Sources: AHS (Census/HUD); NY Fed CCP/Equifax; NAR Profile of Home Buyers & Sellers; Redfin (CPS March Supplement);");
svg.append("text").attr("class","source")
  .attr("x",m.left).attr("y",H-17)
  .text("CFPB National Mortgage Database. All series show median age.");

// Legend
const legend = svg.append("g").attr("transform",`translate(${{m.left+10}},${{m.top-15}})`);
const items = [
  {{color:BLUE, label:"AHS (Census)", dash:null}},
  {{color:YELLOW, label:"NY Fed CCP", dash:null}},
  {{color:RED, label:"NAR Survey", dash:null}},
  {{color:LIGHTRED, label:"Redfin (CPS)", dash:null}},
  {{color:GREEN, label:"CFPB/NMDB", dash:"4,3"}},
];
items.forEach((it,i) => {{
  const gx = i * 130;
  legend.append("line").attr("x1",gx).attr("x2",gx+20)
    .attr("y1",0).attr("y2",0).attr("stroke",it.color)
    .attr("stroke-width",2.5).attr("stroke-dasharray",it.dash||"none");
  legend.append("text").attr("x",gx+25).attr("y",4)
    .attr("font-size","10.5px").attr("fill","#3D3733").text(it.label);
}});
</script>
</body></html>"""

with open("/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/outputs/ftb_all_sources.html", "w") as f:
    f.write(html)
print("Saved to outputs/ftb_all_sources.html")
