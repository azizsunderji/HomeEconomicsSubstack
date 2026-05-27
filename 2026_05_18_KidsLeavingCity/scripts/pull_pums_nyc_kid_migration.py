"""
Pull ACS PUMS microdata via Census API for NYC kid migration analysis.

For each year, request all persons whose state-1-year-ago = NY (MIGSP=036)
and who are under 18 (AGEP<18). Save raw records to the project data lake.

Output:
  data/pums_nyc_kid_migration_raw.parquet   — all NY-origin kid-movers, all years
  data/pums_nyc_kid_migration_destinations.csv — aggregated destinations table

Years: 2021, 2022 ACS 1-year (2023 not yet exposed via API as of 2026-05).
Re-run when 2023 1-yr opens up.

Variables pulled:
  AGEP     age
  MIG      migration status (1=same house, 2=abroad, 3=different US house)
  MIGSP    state-of-residence 1-year-ago (filtered to 036 = NY)
  MIGPUMA  PUMA-of-residence 1-year-ago
  ST       current state
  PUMA     current PUMA
  PWGTP    person weight
"""
from __future__ import annotations
import urllib.request, json
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
CENSUS_KEY = "06048dc3bd32068702b5ef9b49875ec0c5ca56ce"

NYC_MIGPUMAS = {'03700': 'Bronx', '03800': 'Manhattan', '03900': 'Staten Island',
                '04000': 'Brooklyn', '04100': 'Queens'}

YEARS = [2021, 2022]   # add 2023 when available
VARS = "AGEP,MIG,MIGPUMA,ST,PUMA,PWGTP"


def pull_year(year: int) -> pd.DataFrame:
    URL = (f"https://api.census.gov/data/{year}/acs/acs1/pums"
           f"?get={VARS}&MIGSP=036&AGEP=0:17&key={CENSUS_KEY}")
    with urllib.request.urlopen(URL, timeout=120) as r:
        rows = json.loads(r.read())
    df = pd.DataFrame(rows[1:], columns=rows[0])
    # Census echoes filter column names at the end — drop duplicates
    df = df.loc[:, ~df.columns.duplicated()]
    df['year'] = year
    return df


def consolidated_puma(p: str) -> str:
    return p[:3] + "00" if isinstance(p, str) and len(p) >= 3 else p


def classify_destination(row) -> str:
    st, cp = row['ST'], row['PUMA']
    if st == '36':
        if cp.startswith('031'): return 'Westchester / Rockland / Putnam (NY)'
        if cp.startswith('032'): return 'Nassau (NY, Long Island)'
        if cp.startswith('033'): return 'Suffolk (NY, Long Island)'
        return 'Other New York State (Hudson Valley / upstate)'
    state_buckets = {
        '34': 'New Jersey (mostly NYC MSA suburbs)',
        '09': 'Connecticut', '42': 'Pennsylvania', '12': 'Florida',
        '48': 'Texas', '06': 'California', '37': 'North Carolina',
        '13': 'Georgia',
    }
    if st in state_buckets: return state_buckets[st]
    SOUTHEAST = {'45','47','51','54','21','24','11','01','22','05','28','10'}
    MIDWEST = {'17','18','26','39','55','19','27','29','31','38','46','20'}
    WEST = {'04','08','32','35','49','30','16','41','53','56','15','02'}
    NE = {'25','23','33','50','44'}
    if st in SOUTHEAST: return 'Other Southeast (VA/MD/SC/TN/etc.)'
    if st in MIDWEST: return 'Midwest (OH/IL/MI/etc.)'
    if st in WEST: return 'Other West (CO/UT/AZ/OR/etc.)'
    if st in NE: return 'Other Northeast (MA/RI/NH/etc.)'
    return 'Other US'


def main():
    parts = [pull_year(y) for y in YEARS]
    raw = pd.concat(parts, ignore_index=True)
    for col in ['AGEP', 'MIG', 'PWGTP']:
        raw[col] = raw[col].astype(int)
    raw['borough_origin'] = raw['MIGPUMA'].map(NYC_MIGPUMAS)
    raw['cons_puma'] = raw['PUMA'].apply(consolidated_puma)
    raw['stayed_in_origin_borough'] = (
        (raw['ST'] == '36') & (raw['cons_puma'] == raw['MIGPUMA']))
    raw['left_nyc'] = (raw['borough_origin'].notna()
                       & (raw['MIG'] == 3)
                       & ~((raw['ST'] == '36') & raw['cons_puma'].isin(NYC_MIGPUMAS)))
    raw['destination_bucket'] = raw.apply(classify_destination, axis=1)

    out_parquet = DATA / "pums_nyc_kid_migration_raw.parquet"
    raw.to_parquet(out_parquet, index=False)
    print(f"Wrote {out_parquet}  ({len(raw):,} records, {YEARS} pooled)")

    # Aggregated destination summary (kids who left the 5 boroughs)
    left = raw[raw['left_nyc']]
    agg = (left.groupby('destination_bucket')['PWGTP'].sum()
                .sort_values(ascending=False).reset_index())
    agg['pct'] = agg['PWGTP'] / agg['PWGTP'].sum() * 100
    agg.columns = ['destination', 'weighted_kids', 'pct']
    out_csv = DATA / "pums_nyc_kid_migration_destinations.csv"
    agg.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv}")
    print(f"\nTotal weighted kids leaving NYC's 5 boroughs: {agg['weighted_kids'].sum():,.0f}")
    print(agg.to_string(index=False))


if __name__ == "__main__":
    main()
