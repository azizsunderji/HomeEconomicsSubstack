"""
02_merge_atus_politics.py
Join political lean (2020 election results) to ATUS WB module respondents.
- County-level join for ~45% with county IDs
- State-level fallback for the rest
- Create trump_share (continuous) and political_lean (tercile: Red/Purple/Blue)
"""
import duckdb
import pandas as pd
import numpy as np

DATA_DIR = '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_RepublicanHappiness/data'
ATUS_PATH = '/Users/azizsunderji/Dropbox/Home Economics/Data/atus_ipums.parquet'

con = duckdb.connect()

# Extract WB module records with geography
print("Extracting ATUS WB module records...")
atus = con.execute(f"""
SELECT
    CASEID,
    CAST(YEAR AS INT) as YEAR,
    CAST(STATEFIP AS INT) as STATEFIP,
    CAST(COUNTY AS INT) as COUNTY,
    CAST(ACTIVITY AS INT) as ACTIVITY,
    CAST(DURATION AS INT) as DURATION,
    CAST(SCHAPPY AS INT) as SCHAPPY,
    CAST(WBWT AS DOUBLE) as WBWT,
    CAST(AWBWT AS DOUBLE) as AWBWT,
    CAST(WT06 AS DOUBLE) as WT06,
    CAST(AGE AS INT) as AGE,
    SEX,
    CAST(EDUC AS INT) as EDUC,
    CAST(RACE AS INT) as RACE,
    CAST(MARST AS INT) as MARST,
    CAST(EMPSTAT AS INT) as EMPSTAT
FROM read_parquet('{ATUS_PATH}')
WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
""").df()

print(f"  {len(atus)} activity-happiness observations, {atus['CASEID'].nunique()} respondents")

# Build county FIPS for those with county IDs
# IPUMS COUNTY: first digits = state FIPS, last 3 = county FIPS within state
# County ending in 000 = not identified
atus['has_county'] = (atus['COUNTY'] % 1000) > 0
atus['county_fips'] = np.where(
    atus['has_county'],
    atus['STATEFIP'].astype(str).str.zfill(2) + (atus['COUNTY'] % 1000).astype(str).str.zfill(3),
    None
)
atus['state_fips'] = atus['STATEFIP'].astype(str).str.zfill(2)

print(f"  County-identified: {atus['has_county'].sum()} obs ({atus['has_county'].mean()*100:.0f}%)")

# Load election results
county_votes = pd.read_parquet(f'{DATA_DIR}/county_votes_2020.parquet')
state_votes = pd.read_parquet(f'{DATA_DIR}/state_votes_2020.parquet')

# Join county-level trump share
county_map = county_votes.set_index('county_fips')['trump_share'].to_dict()
state_map = state_votes.set_index('state_fips')['trump_share'].to_dict()

# Assign trump_share: county where available, state otherwise
atus['trump_share_county'] = atus['county_fips'].map(county_map)
atus['trump_share_state'] = atus['state_fips'].map(state_map)
atus['trump_share'] = atus['trump_share_county'].fillna(atus['trump_share_state'])
atus['geo_level'] = np.where(atus['trump_share_county'].notna(), 'county', 'state')

print(f"\nTrump share assignment:")
print(f"  County-level: {(atus['geo_level'] == 'county').sum()} obs")
print(f"  State-level:  {(atus['geo_level'] == 'state').sum()} obs")
print(f"  Missing:      {atus['trump_share'].isna().sum()} obs")

# Create tercile buckets based on person-level trump_share
# Use respondent-level (not activity-level) for tercile cutoffs
person_trump = atus.groupby('CASEID')['trump_share'].first()
tercile_cuts = person_trump.quantile([1/3, 2/3]).values
print(f"\nTercile cutoffs: Blue < {tercile_cuts[0]:.1f}% | Purple | Red > {tercile_cuts[1]:.1f}%")

atus['political_lean'] = pd.cut(
    atus['trump_share'],
    bins=[-1, tercile_cuts[0], tercile_cuts[1], 101],
    labels=['Blue', 'Purple', 'Red']
)

# Summary
print("\nPolitical lean distribution (activity observations):")
print(atus['political_lean'].value_counts().sort_index())
print()
print("Mean trump_share by lean:")
print(atus.groupby('political_lean')['trump_share'].mean().round(1))

# Map ACTIVITY codes to BLS major categories
# BLS 2-digit major groups from the ATUS activity coding
def map_activity(code):
    major = code // 10000  # First 2 digits
    if major == 1: return 'Personal Care'
    elif major == 2: return 'Housework'
    elif major == 3: return 'Caring for Household Members'
    elif major == 4: return 'Caring for Non-HH Members'
    elif major == 5: return 'Work'
    elif major == 6: return 'Education'
    elif major == 7: return 'Shopping'
    elif major == 8: return 'Professional Services'
    elif major == 9: return 'Household Services'
    elif major == 10: return 'Government Services'
    elif major == 11: return 'Eating & Drinking'
    elif major == 12: return 'Socializing & Leisure'
    elif major == 13: return 'Sports & Exercise'
    elif major == 14: return 'Religious & Spiritual'
    elif major == 15: return 'Volunteering'
    elif major == 16: return 'Telephone Calls'
    elif major == 18: return 'Travel'
    elif major == 50: return 'Data Codes'
    else: return 'Other'

atus['activity_category'] = atus['ACTIVITY'].apply(map_activity)

# Check category distribution
print("\nActivity category distribution:")
cat_dist = atus.groupby('activity_category').agg(
    n=('CASEID', 'count'),
    mean_happy=('SCHAPPY', 'mean')
).sort_values('n', ascending=False)
print(cat_dist.to_string())

# Save merged dataset
atus.to_parquet(f'{DATA_DIR}/atus_wb_politics.parquet', index=False)
print(f"\nSaved atus_wb_politics.parquet ({len(atus)} rows)")
