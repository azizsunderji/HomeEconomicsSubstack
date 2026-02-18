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

BLUE = '#3DD4FF'
BACKGROUND = '#F6F7F3'
CREAM = '#DADFCE'
BLACK = '#3D3733'

# Label colors by origin state
ORIGIN_COLORS = {
    'CA': '#0BB4FF',  # Blue - California
    'NY': '#F4743B',  # Red - New York
    'IL': '#67A275',  # Green - Illinois
    'FL': '#FEC439',  # Yellow - Florida
    'OR': '#888888',  # Gray - Oregon (softer than black)
    'MA': '#E6A030',  # Amber/orange - Massachusetts
    'NJ': '#E67E22',  # Orange - New Jersey
    'TX': '#1ABC9C',  # Teal - Texas
}

def get_label_color(origin):
    return ORIGIN_COLORS.get(origin, BLACK)

FONT_DIR = "/Users/azizsunderji/Dropbox/Home Economics/Brand Assets/OracleFont/Oracle Aziz Sunderji/Desktop"
for font_file in ['ABCOracle-Regular.otf', 'ABCOracle-Bold.otf', 'ABCOracle-Light.otf', 'ABCOracle-Medium.otf']:
    fm.fontManager.addfont(f"{FONT_DIR}/{font_file}")
plt.rcParams['font.family'] = 'ABC Oracle Edu'
plt.rcParams['svg.fonttype'] = 'none'

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

states = gpd.read_file("/Users/azizsunderji/Dropbox/Home Economics/Reference/Shapefiles/cb_2023_state/cb_2023_us_state_5m.shp")
exclude = ['02', '15', '60', '66', '69', '72', '78']
states = states[~states['STATEFP'].isin(exclude)].to_crs(ALBERS)
centroids = {abbr: (pt.x, pt.y) for abbr, pt in states.set_index('STUSPS').geometry.centroid.to_dict().items()}

conn = duckdb.connect()
raw = conn.execute("""
    SELECT origin, destination, flow
    FROM '/Users/azizsunderji/Dropbox/Home Economics/Data/State_Migration/state_to_state_migration_2024.parquet'
    WHERE flow IS NOT NULL
""").df()

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

top_20 = df.head(20)
top_20_pairs = set(zip(top_20['origin_abbrev'], top_20['dest_abbrev']))

min_flow = df['net_flow'].min()
max_flow = df['net_flow'].max()

state_connections = defaultdict(lambda: {'inflows': [], 'outflows': []})
for _, row in df.iterrows():
    origin = row['origin_abbrev']
    dest = row['dest_abbrev']
    flow = row['net_flow']
    if origin in centroids:
        state_connections[origin]['outflows'].append((dest, flow))
    if dest in centroids:
        state_connections[dest]['inflows'].append((origin, flow))

SPREAD = 60000
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
        if n == 1:
            x_offset = 0
        else:
            x_offset = -SPREAD/2 + (SPREAD * i / (n - 1))
        px = cx + x_offset
        py = cy
        if direction == 'in':
            state_point_positions[(state, partner, False)] = (px, py)
        else:
            state_point_positions[(state, partner, True)] = (px, py)

# Manual adjustments for specific arc endpoints
# TX→OK: move OK terminus right and down so it doesn't overlap with NY→TX
if ('OK', 'TX', False) in state_point_positions:
    ox, oy = state_point_positions[('OK', 'TX', False)]
    state_point_positions[('OK', 'TX', False)] = (ox + 60000, oy - 40000)

# CA→OR: move OR terminus to separate it
if ('OR', 'CA', False) in state_point_positions:
    ox, oy = state_point_positions[('OR', 'CA', False)]
    state_point_positions[('OR', 'CA', False)] = (ox + 40000, oy - 30000)

# Florida terminus: move all FL destinations right and down so arcs land on land, not sea
for key in list(state_point_positions.keys()):
    if key[0] == 'FL' and key[2] == False:  # FL as destination
        fx, fy = state_point_positions[key]
        state_point_positions[key] = (fx + 50000, fy - 30000)

def get_arc_endpoints(origin, dest):
    start_key = (origin, dest, True)
    start = state_point_positions.get(start_key, centroids.get(origin, (0, 0)))
    end_key = (dest, origin, False)
    end = state_point_positions.get(end_key, centroids.get(dest, (0, 0)))
    return start, end

def draw_tapered_arc(ax, start, end, flow, min_flow, max_flow, alpha=1.0, arc_height_ratio=0.35):
    x0, y0 = start
    x1, y1 = end
    normalized = (flow - min_flow) / (max_flow - min_flow) if max_flow > min_flow else 0
    base_width = 0.3 + (normalized ** 2) * 14
    dist = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
    arc_height = dist * arc_height_ratio
    ctrl1_x = x0 + (x1 - x0) * 0.25
    ctrl1_y = max(y0, y1) + arc_height * 0.9
    ctrl2_x = x0 + (x1 - x0) * 0.75
    ctrl2_y = max(y0, y1) + arc_height * 0.9
    n_segments = 150
    t = np.linspace(0, 1, n_segments)
    bx = (1-t)**3 * x0 + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * x1
    by = (1-t)**3 * y0 + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * y1
    for i in range(n_segments - 1):
        progress = (i + 0.5) / (n_segments - 1)
        width = base_width * (0.05 + 0.95 * progress)
        ax.plot([bx[i], bx[i+1]], [by[i], by[i+1]], 
                color=BLUE, linewidth=width, alpha=alpha, 
                solid_capstyle='butt', solid_joinstyle='round')
    mid_idx = len(bx) // 2
    return bx[mid_idx], by[mid_idx]

bounds = states.total_bounds
xlim = (bounds[0] - 100000, bounds[2] + 100000)
ylim = (bounds[1] - 100000, bounds[3] + 600000)

DPI = 300
FIGSIZE = (12, 10)

# Labels that go behind arcs (contiguous state flows)
labels_behind = {('TX', 'OK'), ('FL', 'GA')}

# --- Layer 1: Background with states AND behind-labels ---
fig1, ax1 = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig1.patch.set_facecolor(BACKGROUND)
ax1.set_facecolor(BACKGROUND)
states.plot(ax=ax1, color=CREAM, edgecolor='white', linewidth=0.5)
ax1.set_xlim(xlim)
ax1.set_ylim(ylim)
ax1.set_aspect('equal')
ax1.axis('off')

# Collect label positions first by doing a dry run
label_positions = []
for _, row in top_20.iterrows():
    origin = row['origin_abbrev']
    dest = row['dest_abbrev']
    if origin not in centroids or dest not in centroids:
        continue
    start, end = get_arc_endpoints(origin, dest)
    x0, y0 = start
    x1, y1 = end
    normalized = (row['net_flow'] - min_flow) / (max_flow - min_flow)
    dist = np.sqrt((x1 - x0)**2 + (y1 - y0)**2)
    arc_height = dist * 0.50
    ctrl1_x = x0 + (x1 - x0) * 0.25
    ctrl1_y = max(y0, y1) + arc_height * 0.9
    ctrl2_x = x0 + (x1 - x0) * 0.75
    ctrl2_y = max(y0, y1) + arc_height * 0.9
    t = np.linspace(0, 1, 150)
    bx = (1-t)**3 * x0 + 3*(1-t)**2*t * ctrl1_x + 3*(1-t)*t**2 * ctrl2_x + t**3 * x1
    by = (1-t)**3 * y0 + 3*(1-t)**2*t * ctrl1_y + 3*(1-t)*t**2 * ctrl2_y + t**3 * y1
    mid_idx = len(bx) // 2
    label_positions.append((bx[mid_idx], by[mid_idx], f"{origin}→{dest}", origin, dest))

def adjust_labels(positions):
    adjusted = []
    for i, (x, y, label, origin, dest) in enumerate(positions):
        new_x, new_y = x, y
        if origin == 'NY' and dest == 'FL':
            new_y += 80000
            new_x -= 50000
        elif origin == 'MA' and dest == 'FL':
            # Move down and right, closer to peak
            new_y += 100000  # was 180000
            new_x += 120000  # was 50000
        elif origin == 'NY' and dest == 'SC':
            new_y += 50000
            new_x += 80000
        elif origin == 'NY' and dest == 'NJ':
            new_x += 80000
            new_y -= 60000
        elif origin == 'NY' and dest == 'CT':
            new_x += 150000
            new_y += 40000
        elif origin == 'NY' and dest == 'TX':
            new_y += 80000
        elif origin == 'MA' and dest == 'NH':
            new_x += 100000
        elif origin == 'NJ' and dest == 'FL':
            new_y -= 120000
            new_x -= 60000
        elif origin == 'NJ' and dest == 'PA':
            new_y -= 80000
        elif origin == 'IL' and dest == 'FL':
            new_x -= 50000
        elif origin == 'IL' and dest == 'IN':
            new_x -= 180000
            new_y -= 50000
        elif origin == 'IL' and dest == 'WI':
            new_x -= 80000
        elif origin == 'CA' and dest == 'WA':
            new_x -= 80000
        elif origin == 'CA' and dest == 'OR':
            new_x -= 120000
            new_y -= 40000
        elif origin == 'CA' and dest == 'ID':
            new_x += 80000
            new_y += 40000
        elif origin == 'WA' and dest == 'AZ':
            new_y += 50000
        elif origin == 'WA' and dest == 'ID':
            new_x += 50000
        elif origin == 'OR' and dest == 'WA':
            new_y -= 50000
        elif origin == 'FL' and dest == 'GA':
            new_y -= 50000
        elif origin == 'FL' and dest == 'SC':
            new_x += 80000
        elif origin == 'DC' and dest == 'MD':
            new_y -= 100000
        adjusted.append((new_x, new_y, label, origin, dest))
    return adjusted

adjusted_labels = adjust_labels(label_positions)

# Draw behind-labels on background layer
for x, y, label, origin, dest in adjusted_labels:
    if (origin, dest) in labels_behind:
        ax1.text(x, y, label, fontsize=18, ha='center', va='center',
                 color=get_label_color(origin), fontweight='bold', fontfamily='ABC Oracle Edu',
                 path_effects=[pe.withStroke(linewidth=1.5, foreground='white')])

fig1.tight_layout(pad=0)
buf1 = io.BytesIO()
fig1.savefig(buf1, format='png', dpi=DPI, bbox_inches='tight', facecolor=BACKGROUND, pad_inches=0)
buf1.seek(0)
bg_img = Image.open(buf1).convert('RGB')
plt.close(fig1)

# --- Layer 2: Arcs on white background (for multiply) ---
fig2, ax2 = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig2.patch.set_facecolor('white')
ax2.set_facecolor('white')
ax2.set_xlim(xlim)
ax2.set_ylim(ylim)
ax2.set_aspect('equal')
ax2.axis('off')

for _, row in df.iterrows():
    origin = row['origin_abbrev']
    dest = row['dest_abbrev']
    if origin not in centroids or dest not in centroids:
        continue
    if (origin, dest) in top_20_pairs:
        continue
    start, end = get_arc_endpoints(origin, dest)
    draw_tapered_arc(ax2, start, end, row['net_flow'], min_flow, max_flow, 
                     alpha=0.4, arc_height_ratio=0.12)

for _, row in top_20.iterrows():
    origin = row['origin_abbrev']
    dest = row['dest_abbrev']
    if origin not in centroids or dest not in centroids:
        continue
    start, end = get_arc_endpoints(origin, dest)
    draw_tapered_arc(ax2, start, end, row['net_flow'], min_flow, max_flow, 
                     alpha=0.8, arc_height_ratio=0.50)

fig2.tight_layout(pad=0)
buf2 = io.BytesIO()
fig2.savefig(buf2, format='png', dpi=DPI, bbox_inches='tight', facecolor='white', pad_inches=0)
buf2.seek(0)
arc_img = Image.open(buf2).convert('RGB')
plt.close(fig2)

if bg_img.size != arc_img.size:
    arc_img = arc_img.resize(bg_img.size, Image.Resampling.LANCZOS)

result = ImageChops.multiply(bg_img, arc_img)

# --- Layer 3: Front labels (everything except behind-labels) ---
fig3, ax3 = plt.subplots(figsize=FIGSIZE, dpi=DPI)
fig3.patch.set_alpha(0)
ax3.set_facecolor('none')
ax3.set_xlim(xlim)
ax3.set_ylim(ylim)
ax3.set_aspect('equal')
ax3.axis('off')

for x, y, label, origin, dest in adjusted_labels:
    if (origin, dest) not in labels_behind:
        ax3.text(x, y, label, fontsize=18, ha='center', va='center',
                 color=get_label_color(origin), fontweight='bold', fontfamily='ABC Oracle Edu',
                 path_effects=[pe.withStroke(linewidth=1.5, foreground='white')])

fig3.tight_layout(pad=0)
buf3 = io.BytesIO()
fig3.savefig(buf3, format='png', dpi=DPI, bbox_inches='tight', transparent=True, pad_inches=0)
buf3.seek(0)
label_img = Image.open(buf3).convert('RGBA')
plt.close(fig3)

if result.size != label_img.size:
    label_img = label_img.resize(result.size, Image.Resampling.LANCZOS)

result = result.convert('RGBA')
result = Image.alpha_composite(result, label_img)

result.save('all_flows_map.png')
print(f"Saved all_flows_map.png at {result.size[0]}x{result.size[1]} pixels")