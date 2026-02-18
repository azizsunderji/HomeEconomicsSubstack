"""
All Flows Map - Top 100 flows with top 20 highlighted in yellow
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patheffects as pe
import geopandas as gpd
import duckdb
import numpy as np
import pandas as pd
from collections import defaultdict
from PIL import Image, ImageChops
import io

# Colors
BLUE = '#3DD4FF'
YELLOW = '#FEC439'
BACKGROUND = '#F6F7F3'
CREAM = '#DADFCE'
BLACK = '#3D3733'

# Font setup
FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'

ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'

STATE_ABBREV = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
    'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'District of Columbia': 'DC',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL',
    'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA',
    'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR',
    'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD',
    'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA',
    'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
}

# Load state geometries
states = gpd.read_file("/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp")
exclude = ['02', '15', '60', '66', '69', '72', '78']
states = states[~states['STATEFP'].isin(exclude)].to_crs(ALBERS)
centroids = {abbr: (pt.x, pt.y) for abbr, pt in states.set_index('STUSPS').geometry.centroid.to_dict().items()}

# Load migration data
conn = duckdb.connect()
raw = conn.execute("""
    SELECT origin, destination, flow
    FROM '/Users/azizsunderji/Dropbox/Home Economics/Data/State_Migration/state_to_state_migration_2024.parquet'
    WHERE flow IS NOT NULL
""").df()

# Calculate net flows
net_flows = []
seen = set()
for _, row in raw.iterrows():
    o, d = row['origin'], row['destination']
    if (o, d) in seen or (d, o) in seen:
        continue
    od_flow = row['flow']
    do_row = raw[(raw['origin'] == d) & (raw['destination'] == o)]
    do_flow = do_row['flow'].values[0] if len(do_row) > 0 else 0
    net = od_flow - do_flow
    if net > 0:
        net_flows.append({'origin': o, 'destination': d, 'net_flow': net})
    elif net < 0:
        net_flows.append({'origin': d, 'destination': o, 'net_flow': -net})
    seen.add((o, d))
    seen.add((d, o))

df = pd.DataFrame(net_flows)
df['origin_abbrev'] = df['origin'].map(STATE_ABBREV)
df['dest_abbrev'] = df['destination'].map(STATE_ABBREV)
df = df.dropna(subset=['origin_abbrev', 'dest_abbrev'])
df = df.sort_values('net_flow', ascending=False)

top_100 = df.head(100)
top_20 = df.head(20)
top_20_pairs = set(zip(top_20['origin_abbrev'], top_20['dest_abbrev']))

min_flow = top_100['net_flow'].min()
max_flow = top_100['net_flow'].max()

# Build endpoint positions
state_connections = defaultdict(lambda: {'inflows': [], 'outflows': []})
for _, row in top_100.iterrows():
    origin = row['origin_abbrev']
    dest = row['dest_abbrev']
    flow = row['net_flow']
    if origin in centroids:
        state_connections[origin]['outflows'].append((dest, flow))
    if dest in centroids:
        state_connections[dest]['inflows'].append((origin, flow))

SPREAD = 50000
state_point_positions = {}

for state, connections in state_connections.items():
    if state not in centroids:
        continue
    cx, cy = centroids[state]
    inflows = sorted(connections['inflows'], key=lambda x: -x[1])
    outflows = sorted(connections['outflows'], key=lambda x: x[1])
    all_connections = [('in', partner, flow) for partner, flow in inflows] + \
                      [('out', partner, flow) for partner, flow in outflows]
    n = len(all_connections)
    if n == 0:
        continue
    for i, (direction, partner, flow) in enumerate(all_connections):
        x_offset = 0 if n == 1 else -SPREAD/2 + (SPREAD * i / (n - 1))
        px, py = cx + x_offset, cy
        if direction == 'in':
            state_point_positions[(state, partner, False)] = (px, py)
        else:
            state_point_positions[(state, partner, True)] = (px, py)

# Manual endpoint adjustments
for key in list(state_point_positions.keys()):
    if key[0] == 'FL' and key[2] == False:
        fx, fy = state_point_positions[key]
        state_point_positions[key] = (fx + 50000, fy - 30000)

def get_arc_endpoints(origin, dest):
    start = state_point_positions.get((origin, dest, True), centroids.get(origin, (0, 0)))
    end = state_point_positions.get((dest, origin, False), centroids.get(dest, (0, 0)))
    return start, end

def draw_tapered_arc(ax, start, end, flow, min_flow, max_flow, color, alpha=1.0, 
                     min_arc_height=150000, arc_height_scale=0.25, min_width=1.0, max_width=12):
    """
    Draw a tapered arc with more consistent swoopiness.
    Arc height = min_arc_height + (distance * arc_height_scale)
    This ensures short-distance flows still have visible arcs.
    """
    x0, y0 = start
    x1, y1 = end
    normalized = (flow - min_flow) / (max_flow - min_flow) if max_flow > min_flow else 0
    base_width = min_width + (normalized ** 1.5) * (max_width - min_width)
    
    dist = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
    # More consistent arc height: minimum + scaled by distance
    arc_height = min_arc_height + dist * arc_height_scale
    
    # Control points for cubic bezier
    ctrl1_x = x0 + (x1 - x0) * 0.25
    ctrl1_y = max(y0, y1) + arc_height * 0.9
    ctrl2_x = x0 + (x1 - x0) * 0.75
    ctrl2_y = max(y0, y1) + arc_height * 0.9
    
    t = np.linspace(0, 1, 150)
    bx = (1-t)**3 * x0 + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * x1
    by = (1-t)**3 * y0 + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * y1
    
    for i in range(len(bx) - 1):
        progress = (i + 0.5) / (len(bx) - 1)
        width = base_width * (0.1 + 0.9 * progress)
        ax.plot([bx[i], bx[i+1]], [by[i], by[i+1]], color=color, linewidth=width, alpha=alpha, 
                solid_capstyle='butt', solid_joinstyle='round')
    
    return bx[len(bx)//2], by[len(by)//2]

# Map bounds
bounds = states.total_bounds
xlim = (bounds[0] - 100000, bounds[2] + 100000)
ylim = (bounds[1] - 100000, bounds[3] + 600000)
DPI, FIGSIZE = 300, (12, 10)

# Layer 1: Background with states
fig1, ax1 = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig1.patch.set_facecolor(BACKGROUND)
ax1.set_facecolor(BACKGROUND)
states.plot(ax=ax1, color=CREAM, edgecolor='white', linewidth=0.5)
ax1.set_xlim(xlim); ax1.set_ylim(ylim); ax1.set_aspect('equal'); ax1.axis('off')
buf1 = io.BytesIO()
fig1.savefig(buf1, format='png', dpi=DPI, bbox_inches='tight', facecolor=BACKGROUND, pad_inches=0)
buf1.seek(0)
bg_img = Image.open(buf1).convert('RGB')
plt.close(fig1)

# Layer 2: Arcs on white (for multiply blend)
fig2, ax2 = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig2.patch.set_facecolor('white')
ax2.set_facecolor('white')
ax2.set_xlim(xlim); ax2.set_ylim(ylim); ax2.set_aspect('equal'); ax2.axis('off')

# Draw flows 21-100 (blue)
for _, row in top_100.iloc[20:].iterrows():
    origin, dest = row['origin_abbrev'], row['dest_abbrev']
    if origin not in centroids or dest not in centroids:
        continue
    start, end = get_arc_endpoints(origin, dest)
    draw_tapered_arc(ax2, start, end, row['net_flow'], min_flow, max_flow, BLUE, 
                     alpha=0.6, min_arc_height=80000, arc_height_scale=0.12, min_width=1.5, max_width=6)

# Draw top 20 (yellow)
for _, row in top_20.iterrows():
    origin, dest = row['origin_abbrev'], row['dest_abbrev']
    if origin not in centroids or dest not in centroids:
        continue
    start, end = get_arc_endpoints(origin, dest)
    draw_tapered_arc(ax2, start, end, row['net_flow'], min_flow, max_flow, YELLOW,
                     alpha=0.9, min_arc_height=80000, arc_height_scale=0.12, min_width=3, max_width=14)

buf2 = io.BytesIO()
fig2.savefig(buf2, format='png', dpi=DPI, bbox_inches='tight', facecolor='white', pad_inches=0)
buf2.seek(0)
arc_img = Image.open(buf2).convert('RGB')
plt.close(fig2)

# Multiply blend
if bg_img.size != arc_img.size:
    arc_img = arc_img.resize(bg_img.size, Image.Resampling.LANCZOS)
result = ImageChops.multiply(bg_img, arc_img)

# Layer 3: Labels for top 20
fig3, ax3 = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig3.patch.set_alpha(0)
ax3.set_facecolor('none')
ax3.set_xlim(xlim); ax3.set_ylim(ylim); ax3.set_aspect('equal'); ax3.axis('off')

label_positions = []
for _, row in top_20.iterrows():
    origin, dest = row['origin_abbrev'], row['dest_abbrev']
    if origin not in centroids or dest not in centroids:
        continue
    start, end = get_arc_endpoints(origin, dest)
    x0, y0 = start
    x1, y1 = end
    dist = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
    arc_height = 80000 + dist * 0.12
    ctrl1_x = x0 + (x1 - x0) * 0.25
    ctrl1_y = max(y0, y1) + arc_height * 0.9
    ctrl2_x = x0 + (x1 - x0) * 0.75
    ctrl2_y = max(y0, y1) + arc_height * 0.9
    t = np.linspace(0, 1, 150)
    bx = (1-t)**3 * x0 + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * x1
    by = (1-t)**3 * y0 + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * y1
    label_positions.append((bx[len(bx)//2], by[len(by)//2], f"{origin}→{dest}", origin, dest))

# Manual label adjustments with leader lines
adjusted = []
for x, y, label, origin, dest in label_positions:
    nx, ny = x, y
    use_leader = False
    # Pacific Northwest cluster
    if origin == 'OR' and dest == 'WA': nx -= 100000; ny += 100000; use_leader = True
    elif origin == 'CA' and dest == 'WA': nx -= 50000; ny -= 40000
    # California outflows
    elif origin == 'CA' and dest == 'OR': nx -= 160000; ny -= 20000; use_leader = True
    elif origin == 'CA' and dest == 'TN': ny += 80000; nx -= 60000
    elif origin == 'CA' and dest == 'FL': ny -= 80000; nx += 60000
    # Northeast cluster - spread them out more
    elif origin == 'NY' and dest == 'FL': ny += 60000; nx -= 150000; use_leader = True
    elif origin == 'MA' and dest == 'FL': ny += 220000; nx += 60000; use_leader = True
    elif origin == 'NY' and dest == 'CT': nx += 250000; ny += 60000; use_leader = True
    elif origin == 'NY' and dest == 'SC': ny -= 60000; nx -= 80000
    elif origin == 'NY' and dest == 'NJ': nx += 150000; ny -= 140000; use_leader = True
    # Illinois outflows - move IL→WI up and left more
    elif origin == 'IL' and dest == 'WI': nx -= 200000; ny += 120000; use_leader = True
    elif origin == 'IL' and dest == 'IN': nx -= 220000; ny -= 100000; use_leader = True
    elif origin == 'IL' and dest == 'FL': ny -= 100000
    # New Jersey
    elif origin == 'NJ' and dest == 'FL': ny -= 180000; nx -= 80000; use_leader = True
    elif origin == 'NJ' and dest == 'PA': nx += 100000; ny -= 80000; use_leader = True
    # NY→TX - move down and right to avoid IL→WI
    elif origin == 'NY' and dest == 'TX': nx += 80000; ny -= 40000
    adjusted.append((x, y, nx, ny, label, use_leader))

# Draw leader lines first (so they're behind labels)
for ox, oy, lx, ly, label, use_leader in adjusted:
    if use_leader:
        ax3.plot([ox, lx], [oy, ly], color=BLACK, linewidth=1.0, alpha=0.7)

# Draw labels
for ox, oy, lx, ly, label, use_leader in adjusted:
    ax3.text(lx, ly, label, fontsize=10, ha='center', va='center',
             color=BLACK, fontweight='bold', fontfamily='ABC Oracle Edu',
             path_effects=[pe.withStroke(linewidth=1.5, foreground='white')])

buf3 = io.BytesIO()
fig3.savefig(buf3, format='png', dpi=DPI, bbox_inches='tight', transparent=True, pad_inches=0)
buf3.seek(0)
label_img = Image.open(buf3).convert('RGBA')
plt.close(fig3)

if result.size != label_img.size:
    label_img = label_img.resize(result.size, Image.Resampling.LANCZOS)
result = Image.alpha_composite(result.convert('RGBA'), label_img)
result.save('all_flows_map_top100_yellow20.png')
print("Saved all_flows_map_top100_yellow20.png")
