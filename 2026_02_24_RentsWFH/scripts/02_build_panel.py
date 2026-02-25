"""
02_build_panel.py — Build metro×year panel for regression analysis.

Merges:
- Zillow ZORI (metro rents)
- BLS CES (metro employment)
- Census BPS (building permits → CBSA)
- ACS (WFH share, federal worker share) — carried forward for 2025
- QCEW (CBSA-level federal employment) — replaces state-level proxy
- Population estimates (for per-capita normalization)

Output: data/metro_panel_annual.parquet, data/metro_panel_monthly.parquet

Changes from v1:
- Fixed BLS date alignment (first-of-month → end-of-month to match ZORI)
- Extended panel through 2025 (was capped at 2024)
- Added QCEW CBSA-level federal employment (replaces state-level CES proxy)
- Carry forward 2024 ACS WFH/fed_pct for 2025
"""

import pandas as pd
import numpy as np
import duckdb
import json

PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_23_DCRentDecline"
DATA = f"{PROJECT}/data"
DATA_LAKE = "/Users/azizsunderji/Dropbox/Home Economics/Data"

con = duckdb.connect()

# ═══════════════════════════════════════════
# STEP 1: Build CBSA crosswalk
# ═══════════════════════════════════════════
print("=" * 60)
print("STEP 1: Build crosswalk between data sources")

# Zillow uses metro names like "Washington, DC"
# BLS CES uses state_code + area_code where area_code = CBSA code for metros
# Census permits are at county level — need county-to-CBSA mapping

# First, get Zillow metro names and try to extract CBSA-like identifiers
zori_metros = con.execute(f"""
    SELECT DISTINCT RegionID, RegionName, StateName
    FROM '{DATA}/zori_metro.parquet'
    WHERE RegionType = 'msa'
    ORDER BY RegionName
""").df()
print(f"Zillow metros: {len(zori_metros)}")

# BLS metro areas (total nonfarm)
bls_metros = con.execute(f"""
    SELECT DISTINCT metro_area, state_code, area_code
    FROM '{DATA}/bls_ces_total_nonfarm.parquet'
    WHERE area_code != '00000'  -- exclude statewide
""").df()
print(f"BLS CES metro areas: {len(bls_metros)}")

# The BLS area_code IS the CBSA code for metro areas
# Let's verify by checking DC: area_code = 47900, which is DC-Arlington-Alexandria CBSA
# Zillow RegionID might map to CBSA — let's check

# Known mapping for major metros (Zillow RegionID → CBSA code)
# Actually, Zillow's RegionID is their own ID system, not CBSA
# We need to match by name

# Let's create a mapping by name matching
# Zillow format: "City, ST" — BLS we need to look up from the series catalog

# Alternative: use the Zillow metro name to match
# Top 50 metros we care about — manual CBSA mapping
metro_cbsa_map = {
    'New York, NY': '35620',
    'Los Angeles, CA': '31080',  # actually Long Beach-Anaheim
    'Chicago, IL': '16980',
    'Dallas, TX': '19100',  # actually Fort Worth-Arlington
    'Houston, TX': '26420',
    'Washington, DC': '47900',
    'Miami, FL': '33100',  # actually Fort Lauderdale-Pompano Beach
    'Philadelphia, PA': '37980',
    'Atlanta, GA': '12060',
    'Boston, MA': '14460',  # actually Cambridge-Newton
    'Phoenix, AZ': '38060',
    'San Francisco, CA': '41860',
    'Riverside, CA': '40140',
    'Detroit, MI': '19820',
    'Seattle, WA': '42660',
    'Minneapolis, MN': '33460',
    'San Diego, CA': '41740',
    'Tampa, FL': '45300',
    'Denver, CO': '19740',
    'St. Louis, MO': '41180',
    'Baltimore, MD': '12580',
    'Charlotte, NC': '16740',
    'Orlando, FL': '36740',
    'San Antonio, TX': '41700',
    'Portland, OR': '38900',
    'Sacramento, CA': '40900',
    'Pittsburgh, PA': '38300',
    'Austin, TX': '12420',
    'Las Vegas, NV': '29820',
    'Cincinnati, OH': '17140',
    'Kansas City, MO': '28140',
    'Columbus, OH': '18140',
    'Indianapolis, IN': '26900',
    'Cleveland, OH': '17460',
    'Nashville, TN': '34980',
    'San Jose, CA': '41940',
    'Virginia Beach, VA': '47260',
    'Providence, RI': '39300',
    'Milwaukee, WI': '33340',
    'Jacksonville, FL': '27260',
    'Oklahoma City, OK': '36420',
    'Memphis, TN': '32820',
    'Richmond, VA': '40060',
    'Louisville, KY': '31140',
    'New Orleans, LA': '35380',
    'Raleigh, NC': '39580',
    'Hartford, CT': '25540',
    'Salt Lake City, UT': '41620',
    'Birmingham, AL': '13820',
    'Buffalo, NY': '15380',
    'Rochester, NY': '40380',
    'Tucson, AZ': '46060',
    'Tulsa, OK': '46140',
    'Fresno, CA': '23420',
    'Bridgeport, CT': '71950',  # Stamford-Norwalk
    'Urban Honolulu, HI': '46520',
    'United States': 'US',
}

# Add CBSA to Zillow data
zori_metros['cbsa'] = zori_metros['RegionName'].map(metro_cbsa_map)
matched = zori_metros[zori_metros['cbsa'].notna()]
print(f"Matched Zillow metros to CBSA: {len(matched)}")

# County-to-CBSA mapping for building permits
# Major CBSAs and their component counties
# Using 2023 CBSA definitions
county_to_cbsa = {}

# Load from reference if available, otherwise use manual mapping for top metros
# Key counties for each CBSA (not exhaustive but covers the big ones)
cbsa_counties = {
    '35620': ['36061', '36047', '36081', '36005', '36085', '34013', '34017', '34023', '34025', '34027', '34029', '34035', '34037', '34039', '34003', '36027', '36059', '36071', '36079', '36087', '36103', '36119', '42103'],  # NYC
    '31080': ['06037', '06059'],  # LA-Long Beach
    '16980': ['17031', '17043', '17089', '17093', '17097', '17111', '17197', '18089', '55059'],  # Chicago
    '19100': ['48085', '48113', '48121', '48139', '48221', '48231', '48251', '48257', '48367', '48397', '48425', '48439', '48497'],  # Dallas
    '26420': ['48015', '48039', '48071', '48157', '48167', '48201', '48291', '48339', '48473'],  # Houston
    '47900': ['11001', '24009', '24017', '24021', '24031', '24033', '51013', '51043', '51059', '51061', '51107', '51153', '51177', '51179', '51187', '51510', '51600', '51610', '51630', '51683', '51685'],  # DC
    '33100': ['12011', '12086', '12099'],  # Miami
    '37980': ['34005', '34007', '34015', '42017', '42029', '42045', '42091', '42101', '24015', '10003'],  # Philadelphia
    '12060': ['13013', '13015', '13035', '13045', '13057', '13063', '13067', '13077', '13085', '13089', '13097', '13113', '13117', '13121', '13135', '13143', '13149', '13151', '13159', '13171', '13199', '13211', '13217', '13223', '13227', '13231', '13247', '13255', '13297'],  # Atlanta
    '14460': ['25009', '25017', '25021', '25023', '25025', '33015', '33017'],  # Boston
    '38060': ['04013', '04021'],  # Phoenix
    '41860': ['06001', '06013', '06041', '06075', '06081'],  # SF
    '40140': ['06065', '06071'],  # Riverside
    '19820': ['26087', '26093', '26099', '26125', '26147', '26163'],  # Detroit
    '42660': ['53033', '53053', '53061'],  # Seattle
    '33460': ['27003', '27019', '27025', '27037', '27053', '27059', '27079', '27095', '27123', '27139', '27141', '27163', '27171', '55093', '55109'],  # Minneapolis
    '41740': ['06073'],  # San Diego
    '45300': ['12057', '12101', '12103'],  # Tampa
    '19740': ['08001', '08005', '08013', '08014', '08019', '08031', '08035', '08039', '08047', '08059', '08093'],  # Denver
    '41180': ['17005', '17013', '17027', '17083', '17117', '17119', '17133', '17163', '29071', '29099', '29113', '29183', '29189', '29219', '29510'],  # St. Louis
    '12580': ['24003', '24005', '24013', '24025', '24027', '24035', '24510'],  # Baltimore
    '16740': ['37025', '37071', '37097', '37109', '37119', '37159', '37167', '37179', '45023', '45057', '45091'],  # Charlotte
    '36740': ['12069', '12095', '12097', '12117'],  # Orlando
    '41700': ['48013', '48019', '48029', '48091', '48187', '48259', '48325', '48493'],  # San Antonio
    '38900': ['41005', '41009', '41051', '41067', '41071', '53011'],  # Portland
    '40900': ['06017', '06061', '06067', '06113'],  # Sacramento
    '38300': ['42003', '42005', '42007', '42019', '42051', '42059', '42063', '42073', '42125', '42129', '54009', '54029', '54051'],  # Pittsburgh
    '12420': ['48021', '48053', '48055', '48209', '48453', '48491'],  # Austin
    '29820': ['32003'],  # Las Vegas
    '17140': ['21015', '21023', '21037', '21077', '21081', '21117', '39015', '39017', '39025', '39061', '39165', '18029', '18047', '18115'],  # Cincinnati
    '28140': ['20091', '20103', '20107', '20121', '20209', '29013', '29025', '29037', '29047', '29049', '29095', '29107', '29165', '29177'],  # Kansas City
    '18140': ['39041', '39045', '39049', '39057', '39073', '39089', '39097', '39117', '39129', '39159'],  # Columbus
    '26900': ['18011', '18013', '18057', '18059', '18063', '18081', '18097', '18109', '18145'],  # Indianapolis
    '17460': ['39035', '39055', '39085', '39093', '39103'],  # Cleveland
    '34980': ['47021', '47037', '47043', '47081', '47119', '47147', '47149', '47159', '47165', '47169', '47187', '47189'],  # Nashville
    '41940': ['06069', '06085'],  # San Jose
    '47260': ['51073', '51093', '51095', '51115', '51131', '51149', '51199', '51550', '51620', '51650', '51700', '51710', '51735', '51740', '51800', '51810', '37029', '37053'],  # Virginia Beach
    '39300': ['44001', '44003', '44005', '44007', '44009', '25005'],  # Providence
    '33340': ['55079', '55089', '55131', '55133'],  # Milwaukee
    '27260': ['12003', '12019', '12031', '12089', '12109'],  # Jacksonville
    '36420': ['40017', '40027', '40051', '40083', '40087', '40109', '40125'],  # OKC
    '32820': ['28033', '28093', '47047', '47157'],  # Memphis
    '40060': ['51007', '51033', '51036', '51041', '51049', '51075', '51085', '51087', '51101', '51127', '51145', '51183', '51570', '51670', '51730', '51760'],  # Richmond
    '31140': ['18019', '18043', '18061', '18143', '21015', '21029', '21103', '21111', '21163', '21179', '21185', '21211', '21215'],  # Louisville
    '35380': ['22051', '22071', '22075', '22087', '22089', '22093', '22095', '22103'],  # New Orleans
    '39580': ['37037', '37063', '37069', '37101', '37135'],  # Raleigh
    '25540': ['09003', '09007', '09013'],  # Hartford
    '41620': ['49011', '49035', '49045', '49049', '49057'],  # SLC
    '13820': ['01007', '01009', '01073', '01115', '01117', '01127'],  # Birmingham
}

# Build reverse mapping
for cbsa, counties in cbsa_counties.items():
    for county in counties:
        county_to_cbsa[county] = cbsa

# Save mapping
with open(f"{DATA}/county_to_cbsa.json", 'w') as f:
    json.dump(county_to_cbsa, f, indent=2)

print(f"County-to-CBSA mapping: {len(county_to_cbsa)} counties → {len(cbsa_counties)} CBSAs")

# ═══════════════════════════════════════════
# STEP 2: Process ZORI monthly by CBSA
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 2: Process ZORI rent data")

# Map Zillow metro names to CBSA
zori = con.execute(f"""
    SELECT *
    FROM '{DATA}/zori_metro.parquet'
    WHERE RegionType = 'msa'
""").df()

zori['cbsa'] = zori['RegionName'].map(metro_cbsa_map)
zori = zori[zori['cbsa'].notna() & (zori['cbsa'] != 'US')]

# Compute YoY rent change
zori = zori.sort_values(['cbsa', 'date'])
zori['zori_yoy'] = zori.groupby('cbsa')['zori'].pct_change(12) * 100

# Also compute change from Jan 2019
baseline = zori[zori['date'] == '2019-01-31'].set_index('cbsa')['zori'].to_dict()
zori['zori_pct_from_2019'] = zori.apply(
    lambda r: (r['zori'] / baseline.get(r['cbsa'], np.nan) - 1) * 100
    if r['cbsa'] in baseline else np.nan, axis=1)

print(f"ZORI with CBSA: {zori['cbsa'].nunique()} metros, {len(zori)} obs")
print(f"DC latest rent: ${zori[zori['cbsa']=='47900'].sort_values('date').iloc[-1]['zori']:.0f}")
print(f"DC YoY latest: {zori[zori['cbsa']=='47900'].sort_values('date').iloc[-1]['zori_yoy']:.1f}%")

# ═══════════════════════════════════════════
# STEP 3: Process BLS employment
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 3: Process BLS employment data")

# Total nonfarm by metro
emp = con.execute(f"""
    SELECT metro_area, state_code, area_code, date, value as emp_total
    FROM '{DATA}/bls_ces_total_nonfarm.parquet'
    WHERE area_code != '00000'
""").df()

# The area_code should be the CBSA code
# But BLS uses 5-digit area codes that may not exactly match CBSA
# Let's check what area codes are available
print(f"BLS metro areas: {emp['area_code'].nunique()}")

# Map BLS area_code to our CBSA codes
# BLS area codes for metros ARE the CBSA codes
emp['cbsa'] = emp['area_code']

# Check overlap with ZORI CBSAs
zori_cbsas = set(zori['cbsa'].unique())
bls_cbsas = set(emp['cbsa'].unique())
overlap = zori_cbsas & bls_cbsas
print(f"ZORI CBSAs: {len(zori_cbsas)}, BLS CBSAs: {len(bls_cbsas)}")
print(f"Overlap: {len(overlap)}")
print(f"In ZORI but not BLS: {zori_cbsas - bls_cbsas}")

# Some BLS area codes use metro divisions instead of full CBSA
# E.g., DC might be 47764 (DC-Arlington-Alexandria metro division) under 47900 (full CBSA)
# Let's check what's around our target CBSAs
for cbsa in sorted(zori_cbsas - bls_cbsas)[:10]:
    metro_name = [k for k, v in metro_cbsa_map.items() if v == cbsa]
    close = [a for a in bls_cbsas if abs(int(a) - int(cbsa)) < 500]
    print(f"  Missing: {cbsa} ({metro_name}) — nearby BLS: {close}")

# Fix date alignment: BLS uses first-of-month, ZORI uses end-of-month
# Shift BLS dates to end-of-month so merge works
emp['date'] = emp['date'] + pd.offsets.MonthEnd(0)

# Compute YoY employment growth
emp = emp.sort_values(['cbsa', 'date'])
emp['emp_yoy'] = emp.groupby('cbsa')['emp_total'].pct_change(12) * 100

print(f"BLS date range after alignment: {emp['date'].min()} to {emp['date'].max()}")

# Federal government by state (kept for reference, but QCEW replaces this)
fed = con.execute(f"""
    SELECT state_code, area_code, date, value as fed_emp
    FROM '{DATA}/bls_ces_federal_govt.parquet'
""").df()
fed['date'] = pd.to_datetime(fed['date'])
print(f"\nFederal employment: {fed['state_code'].nunique()} states")

# DC federal employment trend
dc_fed = fed[fed['state_code'] == '11'].sort_values('date')
print(f"DC federal employment latest: {dc_fed.iloc[-1]['fed_emp']:.1f}K ({dc_fed.iloc[-1]['date'].strftime('%Y-%m')})")
print(f"DC federal employment Jan 2019: {dc_fed[dc_fed['date']=='2019-01-01'].iloc[0]['fed_emp']:.1f}K")

# ═══════════════════════════════════════════
# STEP 4: Building permits by CBSA
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 4: Aggregate building permits to CBSA")

permits = con.execute(f"SELECT * FROM '{DATA}/building_permits_county.parquet'").df()
permits['cbsa'] = permits['fips'].map(county_to_cbsa)

# Aggregate to CBSA
permits_cbsa = permits[permits['cbsa'].notna()].groupby(['cbsa', 'year']).agg(
    units_5plus=('units_5plus', 'sum'),
    units_total=('units_total', 'sum'),
    bldgs_5plus=('bldgs_5plus', 'sum')
).reset_index()

print(f"Permits by CBSA: {permits_cbsa['cbsa'].nunique()} CBSAs, {len(permits_cbsa)} obs")

# DC permits trend
dc_permits = permits_cbsa[permits_cbsa['cbsa'] == '47900'].sort_values('year')
print(f"\nDC metro 5+ unit permits by year:")
print(dc_permits[['year', 'units_5plus', 'units_total']].to_string(index=False))

# ═══════════════════════════════════════════
# STEP 5: ACS annual data (WFH, federal workers)
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 5: ACS data — WFH and federal worker shares by metro")

# Get all metros' WFH share and federal worker share
acs_path = f"{DATA_LAKE}/ACS_1Y/acs_1y.parquet"

acs_metro = con.execute(f"""
    SELECT
        YEAR as year,
        MET2013 as met2013,
        CAST(MET2013 AS VARCHAR) as cbsa,
        SUM(CASE WHEN TRANWORK = 80 THEN PERWT ELSE 0 END) * 100.0 /
            NULLIF(SUM(CASE WHEN TRANWORK > 0 THEN PERWT ELSE 0 END), 0) as wfh_pct,
        SUM(CASE WHEN CLASSWKRD = 25 THEN PERWT ELSE 0 END) * 100.0 /
            NULLIF(SUM(CASE WHEN EMPSTAT = 1 THEN PERWT ELSE 0 END), 0) as fed_pct,
        SUM(CASE WHEN EMPSTAT = 1 THEN PERWT ELSE 0 END) as employed_pop
    FROM '{acs_path}'
    WHERE MET2013 > 0
        AND AGE BETWEEN 16 AND 64
    GROUP BY YEAR, MET2013
    HAVING employed_pop > 50000
    ORDER BY YEAR, MET2013
""").df()

# Fix CBSA codes — ACS MET2013 uses CBSA codes but some differ
# They should match since both use CBSA
print(f"ACS metros: {acs_metro['cbsa'].nunique()}, years: {sorted(acs_metro['year'].unique())}")

# Check overlap
acs_cbsas = set(acs_metro['cbsa'].unique())
print(f"Overlap with ZORI: {len(zori_cbsas & acs_cbsas)}")

# DC WFH trend
dc_acs = acs_metro[acs_metro['cbsa'] == '47900'].sort_values('year')
print(f"\nDC metro WFH and Federal shares:")
print(dc_acs[['year', 'wfh_pct', 'fed_pct']].to_string(index=False))

# ═══════════════════════════════════════════
# STEP 6: Population data for per-capita normalization
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 6: Metro population")

pop_path = f"{DATA_LAKE}/PopulationEstimates/metro_cbsa_v2024.parquet"
pop = con.execute(f"""
    SELECT * FROM '{pop_path}' LIMIT 3
""").df()
print(f"Population columns: {list(pop.columns)}")

# Get population by CBSA
pop = con.execute(f"""
    SELECT * FROM '{pop_path}'
""").df()
print(f"Population rows: {len(pop)}")
print(pop.head(3).to_string())

# ═══════════════════════════════════════════
# STEP 6b: Load QCEW CBSA-level federal employment
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 6b: QCEW CBSA-level federal employment")

import os
qcew_path = f"{DATA}/qcew_cbsa_quarterly.parquet"
if os.path.exists(qcew_path):
    qcew = con.execute(f"SELECT * FROM '{qcew_path}'").df()
    qcew['cbsa'] = qcew['cbsa'].astype(str)
    qcew['year'] = qcew['year'].astype(int)
    print(f"QCEW data: {qcew.shape}, {qcew['cbsa'].nunique()} CBSAs, years {int(qcew['year'].min())}-{int(qcew['year'].max())}")

    # Rename to distinguish from ACS-based fed_pct
    qcew_annual = qcew[['cbsa', 'year', 'total_emp', 'fed_emp', 'fed_pct', 'fed_emp_yoy']].rename(
        columns={
            'total_emp': 'qcew_total_emp',
            'fed_emp': 'qcew_fed_emp',
            'fed_pct': 'qcew_fed_pct',
            'fed_emp_yoy': 'qcew_fed_emp_yoy',
        })

    # DC sanity check
    dc_qcew = qcew_annual[qcew_annual['cbsa'] == '47900'].sort_values('year')
    print(f"\nDC QCEW federal employment:")
    print(dc_qcew.to_string(index=False))
else:
    print("WARNING: QCEW data not found. Run 01b_pull_qcew.py first.")
    print("Proceeding without QCEW data — will use ACS fed_pct only.")
    qcew_annual = pd.DataFrame()

# ═══════════════════════════════════════════
# STEP 7: Merge into annual panel
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 7: Build annual panel")

# Annual ZORI (December of each year)
zori_annual = zori[zori['date'].dt.month == 12].copy()
zori_annual['year'] = zori_annual['date'].dt.year
zori_annual = zori_annual[['cbsa', 'year', 'zori', 'zori_yoy', 'RegionName']].copy()

# Annual employment (December)
emp_annual = emp[emp['date'].dt.month == 12].copy()
emp_annual['year'] = emp_annual['date'].dt.year
emp_annual = emp_annual[['cbsa', 'year', 'emp_total', 'emp_yoy']].copy()

# Permits (already annual) — add lag
permits_cbsa_lag = permits_cbsa.copy()
permits_cbsa_lag['year_lag1'] = permits_cbsa_lag['year'] + 1
permits_cbsa_lag['year_lag2'] = permits_cbsa_lag['year'] + 2
permits_lag1 = permits_cbsa_lag[['cbsa', 'year_lag1', 'units_5plus', 'units_total']].rename(
    columns={'year_lag1': 'year', 'units_5plus': 'permits_5plus_lag1', 'units_total': 'permits_total_lag1'})
permits_lag2 = permits_cbsa_lag[['cbsa', 'year_lag2', 'units_5plus', 'units_total']].rename(
    columns={'year_lag2': 'year', 'units_5plus': 'permits_5plus_lag2', 'units_total': 'permits_total_lag2'})

# ACS annual — carry forward 2024 values for 2025 (ACS 2025 not released until mid-2026)
acs_annual = acs_metro[['cbsa', 'year', 'wfh_pct', 'fed_pct', 'employed_pop']].copy()
acs_2024 = acs_annual[acs_annual['year'] == acs_annual['year'].max()].copy()
acs_2025 = acs_2024.copy()
acs_2025['year'] = 2025
acs_annual = pd.concat([acs_annual, acs_2025], ignore_index=True)
print(f"ACS extended to 2025 (carried forward from {int(acs_2024['year'].iloc[0])})")

# Merge everything
panel = zori_annual.merge(emp_annual, on=['cbsa', 'year'], how='left')
panel = panel.merge(permits_lag1, on=['cbsa', 'year'], how='left')
panel = panel.merge(permits_lag2, on=['cbsa', 'year'], how='left')
panel = panel.merge(permits_cbsa[['cbsa', 'year', 'units_5plus', 'units_total']].rename(
    columns={'units_5plus': 'permits_5plus_current', 'units_total': 'permits_total_current'}),
    on=['cbsa', 'year'], how='left')
panel = panel.merge(acs_annual, on=['cbsa', 'year'], how='left')

# Merge QCEW federal employment
if len(qcew_annual) > 0:
    panel = panel.merge(qcew_annual, on=['cbsa', 'year'], how='left')
    print(f"QCEW merged: {panel['qcew_fed_pct'].notna().sum()} of {len(panel)} rows have QCEW data")

# Normalize permits per capita (using employed_pop as proxy when available)
for col in ['permits_5plus_lag1', 'permits_5plus_lag2', 'permits_5plus_current']:
    pc_col = col + '_pc'
    panel[pc_col] = panel[col] / panel['employed_pop'] * 1000  # per 1000 workers

print(f"Annual panel: {panel.shape}")
print(f"Metros: {panel['cbsa'].nunique()}, Years: {sorted(panel['year'].unique())}")
print(f"Non-null counts:")
print(panel.count())

# Filter to years with good coverage — NOW INCLUDES 2025
panel = panel[panel['year'].between(2017, 2025)]
print(f"\nFiltered panel (2017-2025): {panel.shape}")

# Save
panel.to_parquet(f"{DATA}/metro_panel_annual.parquet", index=False)
print(f"Saved annual panel")

# ═══════════════════════════════════════════
# STEP 8: Build monthly panel
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("STEP 8: Build monthly panel")

# Monthly ZORI
zori_monthly = zori[['cbsa', 'date', 'zori', 'zori_yoy', 'zori_pct_from_2019', 'RegionName']].copy()

# Monthly employment (dates now aligned to end-of-month)
emp_monthly = emp[['cbsa', 'date', 'emp_total', 'emp_yoy']].copy()

# Merge
monthly = zori_monthly.merge(emp_monthly, on=['cbsa', 'date'], how='left')

# Add annual permits (same value for all months in a year)
monthly['year'] = monthly['date'].dt.year
monthly = monthly.merge(permits_lag1, on=['cbsa', 'year'], how='left')
monthly = monthly.merge(permits_lag2, on=['cbsa', 'year'], how='left')

# Add ACS annual variables (same for all months, with 2025 carry-forward)
monthly = monthly.merge(acs_annual, on=['cbsa', 'year'], how='left')

# Add QCEW federal employment (annual → same for all months in that year)
if len(qcew_annual) > 0:
    monthly = monthly.merge(qcew_annual, on=['cbsa', 'year'], how='left')

# Also keep state-level CES federal employment for reference (but QCEW is primary)
fed_state = fed[fed['area_code'] == '00000'].copy()
fed_state['date'] = pd.to_datetime(fed_state['date'])
# Align fed_state dates to end-of-month
fed_state['date'] = fed_state['date'] + pd.offsets.MonthEnd(0)
fed_state = fed_state.sort_values(['state_code', 'date'])
fed_state['fed_emp_yoy_ces'] = fed_state.groupby('state_code')['fed_emp'].pct_change(12) * 100

metro_state_map = {}
for metro_name, cbsa in metro_cbsa_map.items():
    if cbsa == 'US':
        continue
    parts = metro_name.split(', ')
    if len(parts) >= 2:
        metro_state_map[cbsa] = parts[-1]

state_fips = {
    'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08', 'CT': '09',
    'DE': '10', 'DC': '11', 'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16', 'IL': '17',
    'IN': '18', 'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23', 'MD': '24',
    'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29', 'MT': '30', 'NE': '31',
    'NV': '32', 'NH': '33', 'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38',
    'OH': '39', 'OK': '40', 'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45', 'SD': '46',
    'TN': '47', 'TX': '48', 'UT': '49', 'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54',
    'WI': '55', 'WY': '56'
}

cbsa_to_state_fips = {}
for cbsa, state in metro_state_map.items():
    if state in state_fips:
        cbsa_to_state_fips[cbsa] = state_fips[state]

monthly['state_fips'] = monthly['cbsa'].map(cbsa_to_state_fips)
monthly = monthly.merge(
    fed_state[['state_code', 'date', 'fed_emp', 'fed_emp_yoy_ces']].rename(
        columns={'fed_emp': 'ces_fed_emp', 'fed_emp_yoy_ces': 'ces_fed_emp_yoy'}),
    left_on=['state_fips', 'date'],
    right_on=['state_code', 'date'],
    how='left'
)

monthly = monthly[monthly['date'] >= '2019-01-01']
print(f"Monthly panel: {monthly.shape}")
print(f"Metros: {monthly['cbsa'].nunique()}, Date range: {monthly['date'].min()} to {monthly['date'].max()}")

# Check 2025 emp coverage
emp_2025 = monthly[(monthly['year'] == 2025) & monthly['emp_total'].notna()]
print(f"2025 months with employment data: {emp_2025['date'].nunique()} unique dates, {emp_2025['cbsa'].nunique()} metros")

monthly.to_parquet(f"{DATA}/metro_panel_monthly.parquet", index=False)
print(f"Saved monthly panel")

# ═══════════════════════════════════════════
# Quick sanity check: DC in the panel
# ═══════════════════════════════════════════
print("\n" + "=" * 60)
print("DC SANITY CHECK")

dc = panel[panel['cbsa'] == '47900'].sort_values('year')
cols = ['year', 'zori', 'zori_yoy', 'emp_total', 'emp_yoy', 'permits_5plus_lag1', 'wfh_pct', 'fed_pct']
if 'qcew_fed_pct' in dc.columns:
    cols.append('qcew_fed_pct')
print(dc[cols].to_string(index=False))

dc_m = monthly[monthly['cbsa'] == '47900'].sort_values('date')
print(f"\nDC monthly latest 6 months:")
mcols = ['date', 'zori', 'zori_yoy', 'emp_total']
if 'qcew_fed_pct' in dc_m.columns:
    mcols.append('qcew_fed_pct')
print(dc_m[mcols].tail(6).to_string(index=False))
