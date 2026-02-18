"""
Pull high-rise housing unit data from Census ACS 5-Year estimates.
Base year: 2010 (2006-2010 ACS 5-year)
Latest year: 2024 (2020-2024 ACS 5-year)
Geography: ALL metropolitan and micropolitan statistical areas
Definition: "High-rise" = units in buildings with 20+ units (B25024_008 + B25024_009)
"""

import requests
import pandas as pd
import geopandas as gpd
import numpy as np
import re
import time

API_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"
DATA_DIR = "/Users/azizsunderji/Dropbox/Home Economics/2026_02_04_BuildingUp/data"
REFERENCE = "/Users/azizsunderji/Dropbox/Home Economics/Reference"

# B25024 - Units in Structure
# _001E = Total housing units
# _008E = 20 to 49 units
# _009E = 50 or more units
VARIABLES = "NAME,B25024_001E,B25024_008E,B25024_009E"

# ============================================================================
# PULL FROM CENSUS API
# ============================================================================

def pull_acs(year):
    """Pull B25024 data for all CBSAs from ACS 5-year estimates."""
    url = f"https://api.census.gov/data/{year}/acs/acs5"
    params = {
        "get": VARIABLES,
        "for": "metropolitan statistical area/micropolitan statistical area:*",
        "key": API_KEY
    }
    print(f"  Pulling ACS 5-year {year}...")
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()

    df = pd.DataFrame(data[1:], columns=data[0])

    # Rename the geo column
    geo_col = [c for c in df.columns if 'metropolitan' in c.lower() or 'statistical' in c.lower()]
    if geo_col:
        df = df.rename(columns={geo_col[0]: 'CBSA'})

    # Convert numeric columns
    for col in ['B25024_001E', 'B25024_008E', 'B25024_009E']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Compute high-rise units (20+ unit buildings)
    df[f'total_units_{year}'] = df['B25024_001E']
    df[f'highrise_units_{year}'] = df['B25024_008E'].fillna(0) + df['B25024_009E'].fillna(0)

    df = df[['NAME', 'CBSA', f'total_units_{year}', f'highrise_units_{year}']]
    print(f"  Got {len(df)} CBSAs for {year}")
    return df


def extract_primary_city(name):
    """Extract primary city from metro name for fuzzy matching.
    'Los Angeles-Long Beach-Anaheim, CA Metro Area' -> 'los angeles'
    """
    # Get everything before the first comma
    city_part = name.split(',')[0]
    # Get the first city (before the first hyphen)
    primary = city_part.split('-')[0].strip().lower()
    return primary


print("Pulling Census data...")

# Pull 2010 (base year) and 2024 (latest)
df_2010 = pull_acs(2010)
time.sleep(1)
df_2024 = pull_acs(2024)

# ============================================================================
# MERGE - three-pass: manual crosswalk, CBSA code match, name-based fallback
# ============================================================================

print("\nMerging datasets...")

# Known CBSA code changes between 2010 and 2024 vintages
CBSA_CROSSWALK = {
    # 2024 code -> 2010 code
    '17410': '17460',   # Cleveland, OH (was Cleveland-Elyria-Mentor)
    '31080': '31100',   # Los Angeles (was Los Angeles-Long Beach-Santa Ana)
    '46520': '26180',   # Urban Honolulu (was Honolulu)
    '42200': '42060',   # Santa Maria-Santa Barbara (was Santa Barbara-Santa Maria-Goleta)
    '28880': '39100',   # Kiryas Joel-Poughkeepsie-Newburgh (was Poughkeepsie-Newburgh-Middletown)
    '47930': '49340',   # Waterbury-Shelton (was Worcester, or split from New Haven area)
}

# Apply crosswalk: create a mapping column in 2010 data
df_2010_xwalk = df_2010.copy()
# Reverse the crosswalk: map old 2010 codes to new 2024 codes
reverse_xwalk = {v: k for k, v in CBSA_CROSSWALK.items()}
df_2010_xwalk['CBSA_2024'] = df_2010_xwalk['CBSA'].map(reverse_xwalk).fillna(df_2010_xwalk['CBSA'])

# Pass 1: Merge on mapped CBSA code
merged = df_2024.merge(df_2010_xwalk, left_on='CBSA', right_on='CBSA_2024', how='left', suffixes=('', '_old'))
merged = merged.rename(columns={'NAME': 'metro_name'})
for col in ['NAME_old', 'CBSA_old', 'CBSA_2024']:
    if col in merged.columns:
        merged = merged.drop(columns=[col])

# Identify unmatched rows (2024 CBSAs with no 2010 CBSA match)
unmatched_mask = merged['total_units_2010'].isna()
n_unmatched = unmatched_mask.sum()
print(f"  Pass 1 (CBSA code): matched {(~unmatched_mask).sum()}, unmatched {n_unmatched}")

# Pass 2: Name-based matching for unmatched rows
if n_unmatched > 0:
    # Build lookup from 2010 data by primary city name
    df_2010['primary_city'] = df_2010['NAME'].apply(extract_primary_city)
    city_lookup = df_2010.set_index('primary_city')

    matched_by_name = 0
    for idx in merged[unmatched_mask].index:
        city = extract_primary_city(merged.loc[idx, 'metro_name'])
        if city in city_lookup.index:
            row_2010 = city_lookup.loc[city]
            # Handle case where multiple matches exist (take first)
            if isinstance(row_2010, pd.DataFrame):
                row_2010 = row_2010.iloc[0]
            merged.loc[idx, 'total_units_2010'] = row_2010['total_units_2010']
            merged.loc[idx, 'highrise_units_2010'] = row_2010['highrise_units_2010']
            matched_by_name += 1

    print(f"  Pass 2 (name match): matched {matched_by_name} more")

# Fill remaining missing 2010 values with 0
merged['total_units_2010'] = merged['total_units_2010'].fillna(0)
merged['highrise_units_2010'] = merged['highrise_units_2010'].fillna(0)

# Compute growth
merged['highrise_growth'] = merged['highrise_units_2024'] - merged['highrise_units_2010']
merged['highrise_pct_growth'] = np.where(
    merged['highrise_units_2010'] > 0,
    (merged['highrise_growth'] / merged['highrise_units_2010'] * 100).round(1),
    np.nan
)

still_missing = (merged['highrise_units_2010'] == 0).sum()
print(f"\nFinal merge: {len(merged)} CBSAs")
print(f"  With 2010 data: {(merged['highrise_units_2010'] > 0).sum()}")
print(f"  Still missing 2010: {still_missing}")

# Show which big metros are still missing
if still_missing > 0:
    big_missing = merged[(merged['highrise_units_2010'] == 0) & (merged['highrise_units_2024'] > 10000)]
    if len(big_missing) > 0:
        print("  Large metros still missing 2010:")
        for _, row in big_missing.iterrows():
            print(f"    {row['metro_name']} (CBSA {row['CBSA']}, 2024 units: {row['highrise_units_2024']:,.0f})")

# ============================================================================
# ADD COORDINATES FROM CBSA SHAPEFILE
# ============================================================================

print("\nAdding coordinates...")

cbsa_shp = gpd.read_file(f"{REFERENCE}/Shapefiles/cb_2023_us_cbsa_5m/cb_2023_us_cbsa_5m.shp")

# Project to Albers for proper centroids, then convert back to lat/lon
ALBERS = '+proj=aea +lat_1=29.5 +lat_2=45.5 +lat_0=37.5 +lon_0=-96 +x_0=0 +y_0=0 +datum=NAD83 +units=m +no_defs'
cbsa_projected = cbsa_shp.to_crs(ALBERS)
centroids_albers = cbsa_projected.geometry.centroid
centroids_latlon = gpd.GeoSeries(centroids_albers, crs=ALBERS).to_crs("EPSG:4326")

cbsa_shp['lat'] = centroids_latlon.y
cbsa_shp['lon'] = centroids_latlon.x

# The CBSA code in shapefile is GEOID
cbsa_coords = cbsa_shp[['GEOID', 'lat', 'lon']].rename(columns={'GEOID': 'CBSA'})

merged = merged.merge(cbsa_coords, on='CBSA', how='left')

missing_coords = merged['lat'].isna().sum()
if missing_coords > 0:
    print(f"  WARNING: {missing_coords} CBSAs missing coordinates")

# Drop rows with no coordinates
merged = merged.dropna(subset=['lat', 'lon'])
print(f"Final dataset: {len(merged)} CBSAs with coordinates")

# ============================================================================
# SORT AND SAVE
# ============================================================================

merged = merged.sort_values('highrise_growth', ascending=False)

# Select final columns
output = merged[[
    'metro_name', 'CBSA',
    'total_units_2010', 'highrise_units_2010',
    'total_units_2024', 'highrise_units_2024',
    'highrise_growth', 'highrise_pct_growth',
    'lat', 'lon'
]]

output_path = f"{DATA_DIR}/highrise_units_all_metros.csv"
output.to_csv(output_path, index=False)
print(f"\nSaved: {output_path}")

# Summary stats
print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Total CBSAs: {len(output)}")
print(f"Total high-rise units 2010: {output['highrise_units_2010'].sum():,.0f}")
print(f"Total high-rise units 2024: {output['highrise_units_2024'].sum():,.0f}")
print(f"Total growth: {output['highrise_growth'].sum():,.0f}")
print(f"\nTop 10 by absolute growth:")
for _, row in output.head(10).iterrows():
    print(f"  {row['metro_name'][:50]:50s}  +{row['highrise_growth']:>10,.0f}  ({row['highrise_pct_growth']:>6.1f}%)")

print(f"\nTop 10 by % growth (min 1000 units in 2010):")
pct_top = output[output['highrise_units_2010'] >= 1000].sort_values('highrise_pct_growth', ascending=False).head(10)
for _, row in pct_top.iterrows():
    print(f"  {row['metro_name'][:50]:50s}  +{row['highrise_pct_growth']:>6.1f}%  ({row['highrise_growth']:>8,.0f})")
