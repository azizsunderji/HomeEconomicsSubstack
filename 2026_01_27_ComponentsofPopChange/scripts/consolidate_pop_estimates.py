"""
Consolidate Census Population Estimates into clean long-format parquets
"""

import pandas as pd
from pathlib import Path

DATA_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/PopulationEstimates")

# =============================================================================
# STATE-LEVEL: Combine 2010s and 2020s into one long-format file
# =============================================================================
print("=== Building consolidated STATE dataset ===")

# Read the latest vintage (2025)
df_2020s = pd.read_parquet(DATA_DIR / "state_v2025.parquet")
df_2010s = pd.read_parquet(DATA_DIR / "state_2010s.parquet")

# Extract population columns and reshape to long format
def reshape_pop_estimates(df, pop_col_prefix="POPESTIMATE"):
    """Reshape wide format to long format"""
    # Get just the identifying columns and population columns
    id_cols = ['STATE', 'NAME', 'REGION', 'DIVISION']
    pop_cols = [c for c in df.columns if c.startswith(pop_col_prefix)]

    df_subset = df[id_cols + pop_cols].copy()

    # Melt to long format
    df_long = df_subset.melt(
        id_vars=id_cols,
        value_vars=pop_cols,
        var_name='variable',
        value_name='population'
    )

    # Extract year from column name
    df_long['year'] = df_long['variable'].str.extract(r'(\d{4})').astype(int)
    df_long = df_long.drop(columns=['variable'])

    return df_long

# Also extract components
def extract_components(df):
    """Extract all components into long format"""
    id_cols = ['STATE', 'NAME']

    components = {
        'population': 'POPESTIMATE',
        'births': 'BIRTHS',
        'deaths': 'DEATHS',
        'natural_change': 'NATURALCHG',
        'international_migration': 'INTERNATIONALMIG',
        'domestic_migration': 'DOMESTICMIG',
        'net_migration': 'NETMIG',
    }

    all_long = []
    for measure, prefix in components.items():
        cols = [c for c in df.columns if c.startswith(prefix) and c[len(prefix):].isdigit()]
        if not cols:
            continue

        df_subset = df[id_cols + cols].copy()
        df_long = df_subset.melt(
            id_vars=id_cols,
            value_vars=cols,
            var_name='variable',
            value_name='value'
        )
        df_long['year'] = df_long['variable'].str.extract(r'(\d{4})').astype(int)
        df_long['measure'] = measure
        df_long = df_long.drop(columns=['variable'])
        all_long.append(df_long)

    return pd.concat(all_long, ignore_index=True)

# Process 2020s data (Vintage 2025)
state_2020s = extract_components(df_2020s)
state_2020s['vintage'] = 2025
state_2020s['decade'] = '2020s'

# Process 2010s data
state_2010s = extract_components(df_2010s)
state_2010s['vintage'] = 2020
state_2010s['decade'] = '2010s'

# Combine (use 2010s for 2010-2019, 2020s for 2020+)
state_2010s_filtered = state_2010s[state_2010s['year'] < 2020]
state_combined = pd.concat([state_2010s_filtered, state_2020s], ignore_index=True)

# Clean up state codes
state_combined['state_fips'] = state_combined['STATE'].astype(str).str.zfill(2)

print(f"  Total rows: {len(state_combined):,}")
print(f"  Years: {state_combined['year'].min()} - {state_combined['year'].max()}")
print(f"  States: {state_combined['NAME'].nunique()}")
print(f"  Measures: {state_combined['measure'].unique().tolist()}")

# Save
outfile = DATA_DIR / "state_pop_estimates_long.parquet"
state_combined.to_parquet(outfile, index=False)
print(f"  Saved to {outfile.name}")

# =============================================================================
# COUNTY-LEVEL: Same process
# =============================================================================
print("\n=== Building consolidated COUNTY dataset ===")

df_county_2020s = pd.read_parquet(DATA_DIR / "county_v2024.parquet")  # V2025 not available yet
df_county_2010s = pd.read_parquet(DATA_DIR / "county_2010s.parquet")

def extract_county_components(df, vintage):
    """Extract all components into long format for counties"""
    id_cols = ['STATE', 'COUNTY', 'STNAME', 'CTYNAME']

    # Check which columns exist
    sample_col = df.columns[0]

    components = {
        'population': 'POPESTIMATE',
        'births': 'BIRTHS',
        'deaths': 'DEATHS',
        'natural_change': 'NATURALCHG',
        'international_migration': 'INTERNATIONALMIG',
        'domestic_migration': 'DOMESTICMIG',
        'net_migration': 'NETMIG',
    }

    all_long = []
    for measure, prefix in components.items():
        cols = [c for c in df.columns if c.startswith(prefix) and any(c[len(prefix):].startswith(y) for y in ['20', '19'])]
        if not cols:
            continue

        df_subset = df[id_cols + cols].copy()
        df_long = df_subset.melt(
            id_vars=id_cols,
            value_vars=cols,
            var_name='variable',
            value_name='value'
        )
        df_long['year'] = df_long['variable'].str.extract(r'(\d{4})').astype(int)
        df_long['measure'] = measure
        df_long['vintage'] = vintage
        df_long = df_long.drop(columns=['variable'])
        all_long.append(df_long)

    return pd.concat(all_long, ignore_index=True)

county_2020s = extract_county_components(df_county_2020s, 2024)
county_2020s['decade'] = '2020s'

county_2010s = extract_county_components(df_county_2010s, 2020)
county_2010s['decade'] = '2010s'

# Combine
county_2010s_filtered = county_2010s[county_2010s['year'] < 2020]
county_combined = pd.concat([county_2010s_filtered, county_2020s], ignore_index=True)

# Clean up FIPS
county_combined['state_fips'] = county_combined['STATE'].astype(str).str.zfill(2)
county_combined['county_fips'] = county_combined['COUNTY'].astype(str).str.zfill(3)
county_combined['fips'] = county_combined['state_fips'] + county_combined['county_fips']

print(f"  Total rows: {len(county_combined):,}")
print(f"  Years: {county_combined['year'].min()} - {county_combined['year'].max()}")
print(f"  Counties: {county_combined['CTYNAME'].nunique()}")

outfile = DATA_DIR / "county_pop_estimates_long.parquet"
county_combined.to_parquet(outfile, index=False)
print(f"  Saved to {outfile.name}")

# =============================================================================
# Summary
# =============================================================================
print("\n=== FINAL DATA LAKE INVENTORY ===")
for f in sorted(DATA_DIR.iterdir()):
    if f.suffix == '.parquet':
        df = pd.read_parquet(f)
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name}: {len(df):,} rows, {size_mb:.1f} MB")
