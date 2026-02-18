"""
01_build_election_data.py
Build county-level and state-level 2020 election results.
Source: MIT Election Data + Science Lab via tonmcg/GitHub
"""
import pandas as pd
import os

OUT_DIR = '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_RepublicanHappiness/data'

# Load pre-aggregated county results
raw = pd.read_csv(os.path.join(OUT_DIR, 'county_votes_2020_raw.csv'))

# Build county-level file
county = raw[['county_fips', 'state_name', 'county_name', 'votes_gop', 'votes_dem', 'total_votes']].copy()
county['county_fips'] = county['county_fips'].astype(str).str.zfill(5)
county['state_fips'] = county['county_fips'].str[:2]
county['trump_share'] = (county['votes_gop'] / county['total_votes'] * 100).round(2)
county['biden_share'] = (county['votes_dem'] / county['total_votes'] * 100).round(2)
county.to_parquet(os.path.join(OUT_DIR, 'county_votes_2020.parquet'), index=False)
print(f"County-level: {len(county)} counties, {county['state_fips'].nunique()} states")

# Build state-level file
state = county.groupby('state_fips').agg(
    votes_gop=('votes_gop', 'sum'),
    votes_dem=('votes_dem', 'sum'),
    total_votes=('total_votes', 'sum')
).reset_index()
state['trump_share'] = (state['votes_gop'] / state['total_votes'] * 100).round(2)
state['biden_share'] = (state['votes_dem'] / state['total_votes'] * 100).round(2)
state['state_fips_int'] = state['state_fips'].astype(int)
state.to_parquet(os.path.join(OUT_DIR, 'state_votes_2020.parquet'), index=False)
print(f"State-level: {len(state)} states")

# Spot checks
print("\nSpot checks:")
for sf, name, exp in [('48', 'TX', 52), ('06', 'CA', 34), ('12', 'FL', 51), ('13', 'GA', 49)]:
    row = state[state['state_fips'] == sf]
    if len(row):
        print(f"  {name}: Trump {row['trump_share'].values[0]:.1f}% (expected ~{exp}%)")
