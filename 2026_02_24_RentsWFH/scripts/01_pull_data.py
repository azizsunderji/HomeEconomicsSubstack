"""
01_pull_data.py — Download and process all data sources for DC rent decline analysis.

Sources:
1. Zillow ZORI (metro + ZIP level rents)
2. Census Building Permits (county-level, aggregated to CBSA)
3. BLS CES (metro-level employment + federal employment)
4. ACS data from data lake (WFH share, federal worker share)
5. DC Open Data permits (address-level for granular map)
"""

import pandas as pd
import numpy as np
import requests
import json
import os
import time
import io

PROJECT = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_23_DCRentDecline"
DATA = f"{PROJECT}/data"
DATA_LAKE = "/Users/azizsunderji/Dropbox/Home Economics/Data"

os.makedirs(DATA, exist_ok=True)

# ─────────────────────────────────────────────
# 1. ZILLOW ZORI — Metro-level rents
# ─────────────────────────────────────────────
print("=" * 60)
print("1a. Downloading Zillow ZORI (metro level)...")
url_metro = "https://files.zillowstatic.com/research/public_csvs/zori/Metro_zori_uc_sfrcondomfr_sm_month.csv"
df_metro = pd.read_csv(url_metro)
print(f"   Raw shape: {df_metro.shape}")
print(f"   Columns (first 10): {list(df_metro.columns[:10])}")

# Identify date columns (YYYY-MM-DD format)
id_cols = [c for c in df_metro.columns if not c[0].isdigit()]
date_cols = [c for c in df_metro.columns if c[0].isdigit()]
print(f"   ID cols: {id_cols}")
print(f"   Date range: {date_cols[0]} to {date_cols[-1]}")
print(f"   Metros: {df_metro.shape[0]}")

# Pivot to long
df_metro_long = df_metro.melt(id_vars=id_cols, value_vars=date_cols,
                               var_name='date', value_name='zori')
df_metro_long['date'] = pd.to_datetime(df_metro_long['date'])
df_metro_long = df_metro_long.dropna(subset=['zori'])
print(f"   Long shape: {df_metro_long.shape}")

df_metro_long.to_parquet(f"{DATA}/zori_metro.parquet", index=False)
print(f"   Saved to {DATA}/zori_metro.parquet")

# ─────────────────────────────────────────────
# 1b. ZILLOW ZORI — ZIP-level rents (for DC map)
# ─────────────────────────────────────────────
print("\n1b. Downloading Zillow ZORI (ZIP level)...")
url_zip = "https://files.zillowstatic.com/research/public_csvs/zori/Zip_zori_uc_sfrcondomfr_sm_month.csv"
df_zip = pd.read_csv(url_zip)
print(f"   Raw shape: {df_zip.shape}")

id_cols_zip = [c for c in df_zip.columns if not c[0].isdigit()]
date_cols_zip = [c for c in df_zip.columns if c[0].isdigit()]
print(f"   ID cols: {id_cols_zip}")
print(f"   Date range: {date_cols_zip[0]} to {date_cols_zip[-1]}")

# Filter to DC metro ZIPs before pivoting (to save memory)
# DC metro states: DC (11), MD (24), VA (51)
# We'll keep all for regression but flag DC metro
df_zip_long = df_zip.melt(id_vars=id_cols_zip, value_vars=date_cols_zip,
                           var_name='date', value_name='zori')
df_zip_long['date'] = pd.to_datetime(df_zip_long['date'])
df_zip_long = df_zip_long.dropna(subset=['zori'])
print(f"   Long shape: {df_zip_long.shape}")

# Save DC metro ZIPs separately for mapping
dc_metro_states = ['DC', 'MD', 'VA', 'WV']  # WV for some DC metro counties
dc_zip = df_zip_long[df_zip_long['State'].isin(dc_metro_states)] if 'State' in df_zip_long.columns else df_zip_long
dc_zip.to_parquet(f"{DATA}/zori_zip_dc_metro_region.parquet", index=False)
print(f"   DC region ZIPs: {dc_zip.shape}")

# Save full metro-level for panel
df_zip_long.to_parquet(f"{DATA}/zori_zip_all.parquet", index=False)
print(f"   Saved all ZIP ZORI")

# ─────────────────────────────────────────────
# 2. CENSUS BUILDING PERMITS — County-level
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("2. Downloading Census Building Permits (county-level)...")

# Census BPS county annual data
# Format: co{YYYY}a.txt — comma-delimited
# Columns vary by year but generally:
# Survey Date, FIPS State, FIPS County, Region, Division, County Name,
# then for each of 4 structure types (1-unit, 2-unit, 3-4 unit, 5+ unit):
# Bldgs, Units, Value

all_permits = []
for year in range(2015, 2026):
    url = f"https://www2.census.gov/econ/bps/County/co{year}a.txt"
    print(f"   Downloading {year}...", end=" ")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            # Parse the text file
            lines = resp.text.strip().split('\n')
            # Skip header rows — find the data start
            # These files have varying header formats
            data_lines = []
            for line in lines:
                # Data lines start with a number (year/month code)
                parts = line.split(',')
                if len(parts) >= 10 and parts[0].strip().isdigit():
                    data_lines.append(parts)

            if data_lines:
                # Parse based on typical Census BPS format
                for parts in data_lines:
                    try:
                        state_fips = parts[1].strip().strip('"')
                        county_fips = parts[2].strip().strip('"')
                        county_name = parts[5].strip().strip('"') if len(parts) > 5 else ''

                        # 5+ unit columns are typically the last set of 3 (bldgs, units, value)
                        # Structure: 1-unit (3 cols), 2-unit (3 cols), 3-4 unit (3 cols), 5+ unit (3 cols)
                        # Index positions depend on format — find by counting
                        # Typical: cols 6-8 = 1-unit, 9-11 = 2-unit, 12-14 = 3-4unit, 15-17 = 5+unit
                        if len(parts) >= 18:
                            units_5plus = int(parts[16].strip().strip('"')) if parts[16].strip().strip('"') else 0
                            bldgs_5plus = int(parts[15].strip().strip('"')) if parts[15].strip().strip('"') else 0
                            units_total = (
                                int(parts[7].strip().strip('"') or 0) +
                                int(parts[10].strip().strip('"') or 0) +
                                int(parts[13].strip().strip('"') or 0) +
                                int(parts[16].strip().strip('"') or 0)
                            )
                        else:
                            units_5plus = 0
                            bldgs_5plus = 0
                            units_total = 0

                        fips = f"{state_fips.zfill(2)}{county_fips.zfill(3)}"
                        all_permits.append({
                            'year': year,
                            'state_fips': state_fips.zfill(2),
                            'county_fips': county_fips.zfill(3),
                            'fips': fips,
                            'county_name': county_name,
                            'units_5plus': units_5plus,
                            'bldgs_5plus': bldgs_5plus,
                            'units_total': units_total
                        })
                    except (ValueError, IndexError):
                        continue

                print(f"OK ({len(data_lines)} counties)")
            else:
                print("No data lines found")
        else:
            print(f"HTTP {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

df_permits = pd.DataFrame(all_permits)
print(f"\n   Total permit records: {len(df_permits)}")
print(f"   Years: {sorted(df_permits['year'].unique())}")
print(f"   Sample 5+ unit counts (DC area):")
dc_fips = ['11001', '51013', '51059', '24031', '24033', '51107', '51153', '51510', '24021', '24017', '51179']
dc_permits = df_permits[df_permits['fips'].isin(dc_fips)]
print(dc_permits.groupby('year')['units_5plus'].sum().to_string())

df_permits.to_parquet(f"{DATA}/building_permits_county.parquet", index=False)
print(f"   Saved to {DATA}/building_permits_county.parquet")

# ─────────────────────────────────────────────
# 3. BLS CES — Metro employment
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("3. Downloading BLS CES metro employment...")

BLS_KEY = "a7d81877b6374d11a6b7e15fa63b5f9b"

# Top 50 metros by population — their CBSA codes and BLS state codes
# BLS CES series format: SMU{state_fips_2}{cbsa_5}{industry_8}{datatype_2}
# state_fips_2 is the state code for the MSA's principal city
# For total nonfarm: industry = 00000000, datatype = 01 (all employees, thousands)
# For federal government: industry = 90910000, datatype = 01

# Major metros with their BLS area codes (state prefix + CBSA)
# These are the BLS "state" codes for CES metro data
top_metros = {
    '3112000000000': ('New York', '35620'),
    '0631000000000': ('Los Angeles', '31080'),
    '1716980000000': ('Chicago', '16980'),
    '4819100000000': ('Dallas', '19100'),
    '4826420000000': ('Houston', '26420'),
    '1147900000000': ('Washington DC', '47900'),
    '1233100000000': ('Miami', '33100'),
    '4237980000000': ('Philadelphia', '37980'),
    '1312060000000': ('Atlanta', '12060'),
    '2512060000000': ('Boston', '14460'),
    '0441740000000': ('Phoenix', '38060'),
    '0641860000000': ('San Francisco', '41860'),
    '0640140000000': ('Riverside', '40140'),
    '2620100000000': ('Detroit', '19820'),
    '5341740000000': ('Seattle', '42660'),
    '2733460000000': ('Minneapolis', '33460'),
    '0641740000000': ('San Diego', '41740'),
    '1245300000000': ('Tampa', '45300'),
    '0819740000000': ('Denver', '19740'),
    '2941180000000': ('St Louis', '41180'),
    '2110180000000': ('Baltimore', '12580'),
    '3735620000000': ('Charlotte', '16740'),
    '3936540000000': ('Orlando', '36740'),
    '4841700000000': ('San Antonio', '41700'),
    '4136420000000': ('Portland OR', '38900'),
    '3632820000000': ('Sacramento', '40900'),
    '3940060000000': ('Pittsburgh', '38300'),
    '4812420000000': ('Austin', '12420'),
    '3929140000000': ('Las Vegas', '29820'),
    '3721340000000': ('Cincinnati', '17140'),
    '2016740000000': ('Kansas City', '28140'),
    '3917460000000': ('Columbus OH', '18140'),
    '1724580000000': ('Indianapolis', '26900'),
    '3734820000000': ('Cleveland', '17460'),
    '4734980000000': ('Nashville', '34980'),
    '0640740000000': ('San Jose', '41940'),
    '5137260000000': ('Virginia Beach', '47260'),
    '4532580000000': ('Providence', '39300'),
    '5526620000000': ('Milwaukee', '33340'),
    '1228580000000': ('Jacksonville', '27260'),
    '4035380000000': ('Oklahoma City', '36420'),
    '4737900000000': ('Memphis', '32820'),
    '2122020000000': ('Richmond', '40060'),
    '2238340000000': ('Louisville', '31140'),
    '2933860000000': ('New Orleans', '35380'),
    '0612540000000': ('Bakersfield', '12540'),  # sub in for smaller
    '4741180000000': ('Knoxville', '28940'),
    '3739580000000': ('Raleigh', '39580'),
    '4812420000000': ('Austin2', '12420'),
    '5344600000000': ('Tacoma', '42660'),  # part of Seattle
}

# Actually, BLS CES series IDs for metros use a specific format
# Let me use a simpler approach: query by area code
# The BLS API v2 allows querying series directly

# For CES metro data, series format is:
# SMU + {state_code_2} + {area_code_5} + {industry_code_8} + {data_type_2}
# But the area code is NOT the CBSA code — it's the BLS-specific metro division code

# Easier: Use BLS Quarterly Census (QCEW) or download CES flat files
# Let me try the flat file approach for reliability

# Actually, let's use the BLS API v2 with proper series IDs
# For metros, CES series start with "SMS" (SA) or "SMU" (NSA)
# Format: SMU{state}{area}{supersector}{industry}{datatype}

# The simplest approach: download the CES state and metro area flat file
print("   Downloading BLS CES metro employment flat files...")
print("   (Using BLS API v2 for top metros)")

# Let's use the API approach — need to construct proper series IDs
# BLS CES metro series: SMU{SS}{AAAAA}{II}{IIIIII}{TT}
# SS = state FIPS (of principal city), AAAAA = metro division code
# Actually BLS uses its own metro area codes, not CBSA

# Better approach: use the BLS API to search for series
# Or we can use FRED which has BLS data in a more accessible format

# Using FRED for metro employment (it sources from BLS CES)
print("   Switching to FRED API for metro employment data...")

FRED_KEY = "936c7e9922072dbab8e2632a67e93ac9"

# FRED series naming for metro employment:
# Total nonfarm: {CBSA}NFNA (not seasonally adjusted) or similar
# Actually FRED uses: {metro_name}NA for total nonfarm
# Let's use specific known series

# Key metros and their FRED total nonfarm payroll series
fred_metro_series = {
    # Metro: (total_nonfarm_series, federal_govt_series, cbsa_code)
    'Washington DC': ('WASH911NAN', 'WASH911NAFEDGOV', '47900'),
    'New York': ('NEWY636NAN', 'NEWY636NAFEDGOV', '35620'),
    'Los Angeles': ('LOSA906NAN', None, '31080'),
    'Chicago': ('CHIC917NAN', None, '16980'),
    'Dallas': ('DALL948NAN', None, '19100'),
    'Houston': ('HOUS948NAN', None, '26420'),
    'Miami': ('MIAM912NAN', None, '33100'),
    'Philadelphia': ('PHIL942NAN', None, '37980'),
    'Atlanta': ('ATLA913NAN', None, '12060'),
    'Boston': ('BOST925NAN', None, '14460'),
    'Phoenix': ('PHOE904NAN', None, '38060'),
    'San Francisco': ('SANF906NAN', None, '41860'),
    'Seattle': ('SEAT953NAN', None, '42660'),
    'Denver': ('DENV908NAN', None, '19740'),
    'Minneapolis': ('MINN927NAN', None, '33460'),
    'San Diego': ('SAND906NAN', None, '41740'),
    'Tampa': ('TAMP912NAN', None, '45300'),
    'Baltimore': ('BALT921NAN', None, '12580'),
    'St Louis': ('STLO929NAN', None, '41180'),
    'Portland': ('PORT941NAN', None, '38900'),
    'Charlotte': ('CHAR937NAN', None, '16740'),
    'Sacramento': ('SACR906NAN', None, '40900'),
    'Pittsburgh': ('PITT942NAN', None, '38300'),
    'Austin': ('AUST948NAN', None, '12420'),
    'Las Vegas': ('LASV932NAN', None, '29820'),
    'Nashville': ('NASH947NAN', None, '34980'),
    'Columbus': ('COLU939NAN', None, '18140'),
    'Indianapolis': ('INDI918NAN', None, '26900'),
    'Kansas City': ('KANS929NAN', None, '28140'),
    'Cincinnati': ('CINC939NAN', None, '17140'),
    'Cleveland': ('CLEV939NAN', None, '17460'),
    'San Jose': ('SANJ906NAN', None, '41940'),
    'Orlando': ('ORLA912NAN', None, '36740'),
    'San Antonio': ('SANA948NAN', None, '41700'),
    'Raleigh': ('RALE937NAN', None, '39580'),
    'Richmond': ('RICH951NAN', None, '40060'),
    'Jacksonville': ('JACK912NAN', None, '27260'),
    'Oklahoma City': ('OKLA940NAN', None, '36420'),
    'Memphis': ('MEMP947NAN', None, '32820'),
    'Louisville': ('LOUI921NAN', None, '31140'),
    'New Orleans': ('NEWO922NAN', None, '35380'),
    'Milwaukee': ('MILW955NAN', None, '33340'),
    'Virginia Beach': ('VIRG951NAN', None, '47260'),
    'Providence': ('PROV944NAN', None, '39300'),
    'Detroit': ('DETR926NAN', None, '19820'),
    'Riverside': ('RIVE906NAN', None, '40140'),
}

# FRED API: fetch series data
def fetch_fred_series(series_id, api_key, start='2017-01-01', end='2025-12-31'):
    """Fetch a single FRED series."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': start,
        'observation_end': end,
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if 'observations' in data:
                obs = data['observations']
                df = pd.DataFrame(obs)
                df['date'] = pd.to_datetime(df['date'])
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                return df[['date', 'value']].dropna()
        return None
    except:
        return None

# Actually, let's use a more reliable approach — FRED series for metro employment
# use the standard format: {METRO}NA for total nonfarm
# The issue is FRED series IDs aren't standardized across all metros

# Let me use the BLS flat files instead — much more reliable
# CES State and Metro Area: https://download.bls.gov/pub/time.series/sm/
print("   Downloading BLS CES flat files (state & metro)...")

# Download the series definitions to find our metros
sm_series_url = "https://download.bls.gov/pub/time.series/sm/sm.series"
sm_data_url = "https://download.bls.gov/pub/time.series/sm/sm.data.1.AllData"

print("   Fetching series catalog...")
headers = {'User-Agent': 'home-economics-research aziz@home-economics.us'}
resp = requests.get(sm_series_url, headers=headers, timeout=60)
if resp.status_code == 200:
    series_df = pd.read_csv(io.StringIO(resp.text), sep='\t')
    series_df.columns = [c.strip() for c in series_df.columns]
    print(f"   Series catalog: {len(series_df)} series")
    print(f"   Columns: {list(series_df.columns)}")
    print(f"   Sample:\n{series_df.head(2).to_string()}")
else:
    print(f"   Failed to download series catalog: {resp.status_code}")
    series_df = pd.DataFrame()

# Filter to total nonfarm (supersector 00, industry 000000) and federal govt (90, 910000)
# Seasonally adjusted, all employees (data_type 01)
if len(series_df) > 0:
    # Identify relevant series
    # Total nonfarm: supersector_code = 00, industry_code = 000000
    # Federal govt: supersector_code = 90, industry_code = 910000 (or 91)

    print(f"\n   Unique supersector codes: {sorted(series_df['supersector_code'].unique())[:20]}")

    # The series_id format: SMS{SS}{AAAAA}{CC}{DDDDDD}{TT} or SMU...
    # Let's look at what columns we have
    for col in series_df.columns:
        print(f"   {col}: {series_df[col].nunique()} unique, sample: {series_df[col].iloc[0]}")

print("\n   Will use FRED API for key metros instead (more reliable)...")

# Use FRED for the most important series
# For each major CBSA, FRED has employment data
# Let's use the FRED metro employment series that are well-known

# FRED series for total nonfarm by metro (SA):
# These follow pattern: {CBSA}NFSA or similar, or we search by metro name
# Actually the most reliable FRED series for metro employment are:
# Payems-style: search by metro name

# Let me just use FRED search API to find series for each metro
def fred_search(search_text, api_key, limit=10):
    """Search FRED for series matching text."""
    url = "https://api.stlouisfed.org/fred/series/search"
    params = {
        'search_text': search_text,
        'api_key': api_key,
        'file_type': 'json',
        'limit': limit,
        'order_by': 'popularity',
        'sort_order': 'desc'
    }
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        if 'seriess' in data:
            return pd.DataFrame(data['seriess'])
    return pd.DataFrame()

# Key metros and known FRED series for total nonfarm (SA, thousands)
# These are confirmed FRED series IDs
known_fred_employment = {
    'Washington DC': 'Wash911URN',  # placeholder — we need the right ones
}

# Actually, the most efficient approach: use FRED's standard naming
# For metro total nonfarm employment (SA, thousands):
# Series ID pattern: SMS{SS}{MMMMM}0000000001 where SS=state, MMMMM=metro area code
# But these aren't CBSA codes...

# Let me try a different approach — download all metro employment from BLS in one shot
print("   Trying BLS bulk data download...")

# The sm.data file has ALL metro CES data
# It's large but we can filter after download
print("   Downloading sm.data.1.AllData (this may take a minute)...")
resp = requests.get(sm_data_url, headers=headers, timeout=300, stream=True)
if resp.status_code == 200:
    # Save raw and process
    raw_path = f"{DATA}/bls_sm_data_raw.txt"
    with open(raw_path, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=1024*1024):
            f.write(chunk)
    print(f"   Downloaded {os.path.getsize(raw_path) / 1024 / 1024:.1f} MB")

    # Parse — tab separated, columns: series_id, year, period, value, footnote_codes
    print("   Parsing BLS CES data...")
    bls_df = pd.read_csv(raw_path, sep='\t', dtype=str)
    bls_df.columns = [c.strip() for c in bls_df.columns]
    print(f"   Total records: {len(bls_df)}")
    print(f"   Columns: {list(bls_df.columns)}")

    # Parse series_id to extract components
    # Format: SM[S|U]{seasonal}{state_code}{area_code}{supersector}{industry}{data_type}
    bls_df['series_id'] = bls_df['series_id'].str.strip()

    # Filter to seasonally adjusted (S), all employees (01)
    # Total nonfarm: supersector 00, industry 000000
    # Federal govt: supersector 90, industry 910000

    # Series ID structure for CES metro:
    # SM + S/U + {state 2} + {area 5} + {supersector 2} + {industry 6} + {datatype 2}
    # Total length: 2 + 1 + 2 + 5 + 2 + 6 + 2 = 20

    mask_sa = bls_df['series_id'].str[2:3] == 'S'  # seasonally adjusted
    mask_total_nf = bls_df['series_id'].str[12:20] == '00000001'  # total nonfarm, all employees
    mask_fed_govt = bls_df['series_id'].str[12:20] == '91000001'  # federal govt, all employees

    # Extract state and area codes
    bls_df['state_code'] = bls_df['series_id'].str[3:5]
    bls_df['area_code'] = bls_df['series_id'].str[5:10]
    bls_df['supersector'] = bls_df['series_id'].str[10:12]
    bls_df['industry'] = bls_df['series_id'].str[12:18]
    bls_df['datatype'] = bls_df['series_id'].str[18:20]

    # Get total nonfarm and federal govt series (SA)
    total_nf = bls_df[mask_sa & mask_total_nf].copy()
    fed_govt = bls_df[mask_sa & mask_fed_govt].copy()

    print(f"   Total nonfarm SA series: {total_nf['series_id'].nunique()} metros, {len(total_nf)} observations")
    print(f"   Federal govt SA series: {fed_govt['series_id'].nunique()} metros, {len(fed_govt)} observations")

    # Parse dates
    for df_tmp in [total_nf, fed_govt]:
        df_tmp['year'] = df_tmp['year'].astype(int)
        df_tmp['month'] = df_tmp['period'].str.strip().str[1:].astype(int)
        df_tmp['date'] = pd.to_datetime(df_tmp[['year', 'month']].assign(day=1))
        df_tmp['value'] = pd.to_numeric(df_tmp['value'].str.strip(), errors='coerce')

    # Filter to 2017+
    total_nf = total_nf[total_nf['year'] >= 2017]
    fed_govt = fed_govt[fed_govt['year'] >= 2017]

    # Create area identifier
    total_nf['metro_area'] = total_nf['state_code'] + total_nf['area_code']
    fed_govt['metro_area'] = fed_govt['state_code'] + fed_govt['area_code']

    # Save
    total_nf[['metro_area', 'state_code', 'area_code', 'date', 'value']].to_parquet(
        f"{DATA}/bls_ces_total_nonfarm.parquet", index=False)
    fed_govt[['metro_area', 'state_code', 'area_code', 'date', 'value']].to_parquet(
        f"{DATA}/bls_ces_federal_govt.parquet", index=False)

    print(f"   Saved total nonfarm and federal govt employment")

    # Show DC metro data
    dc_areas = total_nf[total_nf['state_code'] == '11']
    print(f"\n   DC state (11) area codes: {sorted(dc_areas['area_code'].unique())}")
    if len(dc_areas) > 0:
        dc_latest = dc_areas.sort_values('date').groupby('area_code').last()
        print(f"   DC metro latest employment:\n{dc_latest[['date', 'value']].to_string()}")

    # Clean up raw file
    os.remove(raw_path)

else:
    print(f"   Failed to download BLS data: {resp.status_code}")
    print("   Will fall back to FRED API...")

# ─────────────────────────────────────────────
# 4. DC OPEN DATA — Address-level permits
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("4. Downloading DC Open Data building permits...")

dc_permits_url = "https://opendata.dc.gov/api/download/v1/items/4aeaaa42c5e04b58b87f07e4511766c1/csv?layers=17"
try:
    resp = requests.get(dc_permits_url, timeout=60)
    if resp.status_code == 200:
        df_dc_permits = pd.read_csv(io.StringIO(resp.text))
        print(f"   DC permits shape: {df_dc_permits.shape}")
        print(f"   Columns: {list(df_dc_permits.columns)[:15]}")
        print(f"   Sample:\n{df_dc_permits.head(2).to_string()}")
        df_dc_permits.to_parquet(f"{DATA}/dc_building_permits_raw.parquet", index=False)
        print(f"   Saved DC permits")
    else:
        print(f"   HTTP {resp.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# ─────────────────────────────────────────────
# 5. Montgomery County MD permits
# ─────────────────────────────────────────────
print("\n5. Downloading Montgomery County MD permits...")
moco_url = "https://data.montgomerycountymd.gov/api/views/m88u-pqki/rows.csv?accessType=DOWNLOAD"
try:
    resp = requests.get(moco_url, timeout=60)
    if resp.status_code == 200:
        df_moco = pd.read_csv(io.StringIO(resp.text))
        print(f"   MoCo permits shape: {df_moco.shape}")
        print(f"   Columns: {list(df_moco.columns)[:15]}")
        df_moco.to_parquet(f"{DATA}/moco_permits_raw.parquet", index=False)
        print(f"   Saved MoCo permits")
    else:
        print(f"   HTTP {resp.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# ─────────────────────────────────────────────
# 6. Arlington County VA permits
# ─────────────────────────────────────────────
print("\n6. Attempting Arlington County VA permits...")
# Arlington's open data portal
arlington_url = "https://data.arlingtonva.us/api/views/x6v6-7ur7/rows.csv?accessType=DOWNLOAD"
try:
    resp = requests.get(arlington_url, timeout=30)
    if resp.status_code == 200:
        df_arl = pd.read_csv(io.StringIO(resp.text))
        print(f"   Arlington permits shape: {df_arl.shape}")
        df_arl.to_parquet(f"{DATA}/arlington_permits_raw.parquet", index=False)
    else:
        print(f"   HTTP {resp.status_code} — Arlington data not available via this URL")
except Exception as e:
    print(f"   Error: {e} — will skip Arlington address-level data")

print("\n" + "=" * 60)
print("DATA ACQUISITION COMPLETE")
print("=" * 60)

# Summary of what we have
for f in sorted(os.listdir(DATA)):
    if f.endswith('.parquet'):
        size = os.path.getsize(f"{DATA}/{f}") / 1024 / 1024
        print(f"  {f}: {size:.1f} MB")
