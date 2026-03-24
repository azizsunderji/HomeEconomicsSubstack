"""
PSID: Track rent→own transitions to get median age at first homeownership.
Uses 1968 family ID to link households across waves.
"""
import duckdb
import json
import os

PSID_FAM = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/family'
con = duckdb.connect()

# Variable crosswalk: year -> (own_rent, head_age, family_68_id)
xwalk = {
    1968: ('V103', 'V117', None),  # No prior year to compare
    1969: ('V593', 'V1008', None),  # 1968 ID is implicitly V2 in 1968 file
    1970: ('V1264', 'V1239', 'V1230'),
    1971: ('V1967', 'V1942', 'V1932'),
    1972: ('V2566', 'V2542', 'V2533'),
    1973: ('V3108', 'V3095', None),
    1974: ('V3522', 'V3508', 'V3497'),
    1975: ('V3939', 'V3921', 'V3909'),
    1976: ('V4450', 'V4436', 'V4423'),
    1977: ('V5364', 'V5350', 'V5336'),
    1978: ('V5864', 'V5850', 'V5835'),
    1979: ('V6479', 'V6462', 'V6446'),
    1980: ('V7084', 'V7067', 'V7050'),
    1981: ('V7675', None, 'V7642'),
    1982: ('V8364', None, 'V8335'),
    1983: ('V8974', None, 'V8943'),
    1984: ('V10437', None, 'V10400'),
    1985: ('V11618', None, 'V11581'),
    1986: ('V13023', None, 'V12988'),
    1987: ('V14126', None, 'V14090'),
    1988: ('V15140', None, 'V15105'),
    1989: ('V16641', None, 'V16605'),
    1990: ('V18072', None, 'V18021'),
    1991: ('V19372', None, 'V19321'),
    1992: ('V20672', None, 'V20621'),
    1993: ('V22427', None, 'V22400'),
    1994: ('ER2032', 'ER2007', None),
    1995: ('ER5031', 'ER5006', None),
    1996: ('ER7031', 'ER7006', None),
    1997: ('ER10035', 'ER10009', None),
    1999: ('ER13040', 'ER13010', 'ER13019'),
    2001: ('ER17043', 'ER17013', None),
    2003: ('ER21042', 'ER21017', None),
    2005: ('ER25028', 'ER25017', None),
    2007: ('ER36028', 'ER36017', None),
    2009: ('ER42029', 'ER42017', None),
    2011: ('ER47329', 'ER47317', None),
    2013: ('ER53029', 'ER53017', None),
    2015: ('ER60030', 'ER60017', None),
    2017: ('ER66030', None, None),
    2019: ('ER72030', None, None),
    2021: ('ER78031', None, None),
    2023: ('ER82032', None, None),
}

# Step 1: Build a long panel of (family_68_id, year, own_rent, head_age)
# using the long_panel which already has own_rent and head_age
LP = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/long_panel_1968_2023.parquet'

# Check if long_panel has enough info — it has own_rent, head_age, year
# but no family ID. Let me check if there's a row_number that's consistent.
# Actually: the file has 277K rows. If families are in consistent order per year,
# I could assign IDs. But that's fragile.

# Better approach: use the family files directly for consecutive year pairs.
# For years with both family_68_id and own_rent, extract (id, own_rent, head_age).
# Then join consecutive years on family_68_id to find transitions.

print("Building year-by-year extracts...")
year_data = {}

for year, (own_var, age_var, id_var) in sorted(xwalk.items()):
    fpath = f'{PSID_FAM}/{year}.parquet'
    if not os.path.exists(fpath):
        continue

    cols = [c[0] for c in con.execute(
        f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{fpath}')").fetchall()]

    if own_var not in cols:
        print(f"  {year}: own_rent var {own_var} missing")
        continue

    # Find head_age variable if not specified
    if age_var and age_var in cols:
        pass
    else:
        # Search for it
        age_candidates = [c for c in cols if c in [
            f'V{n}' for n in range(1, 99999)] and False]  # skip
        age_var = None
        # Try common patterns
        for candidate_label in ['AGE OF HEAD']:
            res = con.execute(f"""
                SELECT variable FROM '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/variable_labels.parquet'
                WHERE year={year} AND label='{candidate_label}'
            """).fetchall()
            if res and res[0][0] in cols:
                age_var = res[0][0]
                break

    if not age_var:
        print(f"  {year}: no age variable found")
        continue

    # Find family_68_id if not specified
    if not id_var:
        res = con.execute(f"""
            SELECT variable FROM '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/variable_labels.parquet'
            WHERE year={year} AND (label ILIKE '1968 id%' OR label ILIKE '1968 family%')
        """).fetchall()
        if res and res[0][0] in cols:
            id_var = res[0][0]

    if not id_var:
        print(f"  {year}: no family ID variable")
        continue

    # Extract
    df = con.execute(f"""
        SELECT
            TRY_CAST({id_var} AS INTEGER) as fam68,
            TRY_CAST({own_var} AS INTEGER) as own_rent,
            TRY_CAST({age_var} AS INTEGER) as head_age
        FROM '{fpath}'
        WHERE TRY_CAST({id_var} AS INTEGER) > 0
          AND TRY_CAST({age_var} AS INTEGER) BETWEEN 18 AND 85
    """).fetchdf()

    year_data[year] = df
    n_own = (df['own_rent'] == 1).sum()
    n_rent = (df['own_rent'] == 5).sum()
    print(f"  {year}: {len(df)} families, {n_own} owners, {n_rent} renters")

# Step 2: Find transitions (rent in year T → own in year T+1)
print("\n\nFinding rent→own transitions...")
results = []
years_sorted = sorted(year_data.keys())

for i in range(1, len(years_sorted)):
    y_prev = years_sorted[i-1]
    y_curr = years_sorted[i]

    # Only compare consecutive or near-consecutive years
    gap = y_curr - y_prev
    if gap > 3:  # skip large gaps
        continue

    prev = year_data[y_prev]
    curr = year_data[y_curr]

    # Join on fam68 ID
    merged = prev.merge(curr, on='fam68', suffixes=('_prev', '_curr'))

    # Transitions: was renting, now owns
    transitions = merged[
        (merged['own_rent_prev'] == 5) &  # was renting
        (merged['own_rent_curr'] == 1) &  # now owns
        (merged['head_age_curr'] >= 18) &
        (merged['head_age_curr'] <= 75)
    ]

    if len(transitions) < 10:
        print(f"  {y_prev}→{y_curr}: only {len(transitions)} transitions, skipping")
        continue

    median_age = transitions['head_age_curr'].median()
    mean_age = transitions['head_age_curr'].mean()

    results.append({
        'year': y_curr,
        'median': int(median_age),
        'mean': round(float(mean_age), 1),
        'n_transitions': len(transitions),
        'gap': gap,
    })
    print(f"  {y_prev}→{y_curr}: {len(transitions)} transitions, median age={median_age:.0f}, mean={mean_age:.1f}")

print("\n\n=== PSID RENT→OWN TRANSITION AGE ===")
print(f"{'Year':>6}  {'Median':>6}  {'Mean':>6}  {'N':>6}")
for r in results:
    print(f"{r['year']:>6}  {r['median']:>6}  {r['mean']:>6}  {r['n_transitions']:>6}")

with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/psid_ftb_transitions.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved.")
con.close()
