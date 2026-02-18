"""
04_within_metro.py
Within-metro analysis: compare happiness in red vs blue counties within the same metro.
Controls for region/climate/culture.
"""
import pandas as pd
import numpy as np
import duckdb

DATA_DIR = '/Users/azizsunderji/Dropbox/Home Economics/2026_02_08_RepublicanHappiness/data'
ATUS_PATH = '/Users/azizsunderji/Dropbox/Home Economics/Data/atus_ipums.parquet'

con = duckdb.connect()

# Load merged data (county-level only)
df = pd.read_parquet(f'{DATA_DIR}/atus_wb_politics.parquet')
county_df = df[df['geo_level'] == 'county'].copy()

# Get metro assignment from ATUS
metro_map = con.execute(f'''
SELECT DISTINCT CASEID, CAST(METFIPS AS INT) as METFIPS
FROM read_parquet("{ATUS_PATH}")
WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
  AND CAST(METFIPS AS INT) > 0
  AND CAST(METFIPS AS INT) < 99998
''').df()

county_df = county_df.merge(metro_map, on='CASEID', how='inner')

# CBSA name lookup (top metros)
METRO_NAMES = {
    35620: 'New York', 31100: 'Los Angeles', 16980: 'Chicago',
    19100: 'Dallas-Fort Worth', 26420: 'Houston', 47900: 'Washington DC',
    37980: 'Philadelphia', 12060: 'Atlanta', 33100: 'Miami',
    19820: 'Detroit', 41180: 'St. Louis', 38300: 'Pittsburgh',
    36740: 'Orlando', 40900: 'Sacramento', 19740: 'Denver',
    33460: 'Minneapolis', 16740: 'Charlotte', 12580: 'Baltimore',
    18140: 'Columbus OH', 47260: 'Virginia Beach', 14460: 'Boston',
    17460: 'Cleveland', 35380: 'New Orleans', 40060: 'Richmond',
}

# For each metro, split counties into above/below metro median Trump share
# Then compare happiness
metro_results = []

for metfips, group in county_df.groupby('METFIPS'):
    n_people = group['CASEID'].nunique()
    if n_people < 50:
        continue

    trump_range = group['trump_share'].max() - group['trump_share'].min()
    if trump_range < 15:
        continue

    median_trump = group.groupby('CASEID')['trump_share'].first().median()

    red_counties = group[group['trump_share'] > median_trump]
    blue_counties = group[group['trump_share'] <= median_trump]

    if red_counties['CASEID'].nunique() < 20 or blue_counties['CASEID'].nunique() < 20:
        continue

    red_happy = np.average(red_counties['SCHAPPY'], weights=red_counties['AWBWT'])
    blue_happy = np.average(blue_counties['SCHAPPY'], weights=blue_counties['AWBWT'])

    metro_results.append({
        'metfips': metfips,
        'metro_name': METRO_NAMES.get(metfips, str(metfips)),
        'n_people': n_people,
        'n_red': red_counties['CASEID'].nunique(),
        'n_blue': blue_counties['CASEID'].nunique(),
        'red_happy': round(red_happy, 3),
        'blue_happy': round(blue_happy, 3),
        'gap': round(red_happy - blue_happy, 3),
        'median_trump': round(median_trump, 1),
        'trump_range': round(trump_range, 1),
    })

metro_df = pd.DataFrame(metro_results).sort_values('n_people', ascending=False)

print("WITHIN-METRO HAPPINESS: Red vs Blue Counties")
print("="*80)
print(metro_df[['metro_name', 'n_people', 'n_red', 'n_blue',
                'red_happy', 'blue_happy', 'gap', 'trump_range']].to_string(index=False))

# Overall within-metro effect
print(f"\nWeighted average gap (by n_people): {np.average(metro_df['gap'], weights=metro_df['n_people']):.3f}")
print(f"Metros where red > blue: {(metro_df['gap'] > 0).sum()} of {len(metro_df)}")
print(f"Metros where blue > red: {(metro_df['gap'] < 0).sum()} of {len(metro_df)}")

metro_df.to_parquet(f'{DATA_DIR}/within_metro_happiness.parquet', index=False)
print(f"\nSaved within_metro_happiness.parquet")
