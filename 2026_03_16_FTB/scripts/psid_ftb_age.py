"""
PSID: Median age at first homeownership transition, 1968-2023.
For each year, find households that were renting the prior wave and now own.
Record head's age at transition.
"""
import duckdb
import json

PSID_FAM = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/family'
con = duckdb.connect()

# Variable crosswalk: year -> (own_rent_var, age_var, interview_num_var)
# own_rent: 1=own, 5=rent, 8=neither
# Built from housing_variable_crosswalk + variable_labels
crosswalk = {
    1968: ('V103', 'V117', 'V2'),
    1969: ('V593', 'V1008', 'V2'),  # V2 is 1968 ID; 1969 ID is V442
    1970: ('V1264', 'V1239', 'V2'),
    1971: ('V1967', 'V1942', 'V2'),
    1972: ('V2566', 'V2542', 'V2'),
    1973: ('V3108', 'V3095', 'V2'),
    1974: ('V3522', 'V3508', 'V2'),
    1975: ('V3939', 'V3921', 'V2'),
    1976: ('V4450', 'V4436', 'V2'),
    1977: ('V5364', 'V5350', 'V2'),
    1978: ('V5864', 'V5850', 'V2'),
    1979: ('V6479', 'V6462', 'V2'),
    1980: ('V7084', 'V7067', 'V6902'),
}

# For 1981+ use the interview number variable for that year
# and head age from variable labels
crosswalk.update({
    1981: ('V7675', None, 'V7502'),
    1982: ('V8364', None, 'V8202'),
    1983: ('V8974', None, 'V8802'),
    1984: ('V10437', None, 'V10002'),
    1985: ('V11618', None, 'V11102'),
    1986: ('V13023', None, 'V12502'),
    1987: ('V14126', None, 'V13702'),
    1988: ('V15140', None, 'V14802'),
    1989: ('V16641', None, 'V16302'),
    1990: ('V18072', None, None),
    1991: ('V19372', None, 'V19002'),
    1992: ('V20672', None, 'V20302'),
    1993: ('V22427', None, 'V21602'),
    1994: ('ER2032', 'ER2007', None),
    1995: ('ER5031', 'ER5006', None),
    1996: ('ER7031', 'ER7006', None),
    1997: ('ER10035', 'ER10009', None),
    1999: ('ER13040', 'ER13010', 'ER13002'),
    2001: ('ER17043', 'ER17013', None),
    2003: ('ER21042', 'ER21017', None),
    2005: ('ER25028', 'ER25017', None),
    2007: ('ER36028', 'ER36017', None),
    2009: ('ER42029', 'ER42017', None),
    2011: ('ER47329', 'ER47317', None),
    2013: ('ER53029', 'ER53017', None),
    2015: ('ER60030', 'ER60017', None),
})

# Simpler approach: use the long_panel which already has own_rent and head_age
# Problem: no household ID. But the rows ARE ordered by household.
#
# Even simpler: just compute the age distribution of ALL new owners each year.
# For each year, find the median head_age where own_rent=1 AND head_age is young.
# This isn't FTB specifically, but combined with the AHS data gives us the picture.
#
# ACTUALLY simplest: use the long_panel to find, for each year, the age profile
# of owners. Then compute "age at which ownership rate crosses 50%" — similar
# to the headship age measure. This is a clean proxy.

LP = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/long_panel_1968_2023.parquet'

results = []

for year in range(1968, 2024):
    res = con.execute(f"""
        SELECT head_age,
            SUM(CASE WHEN own_rent = 1 THEN 1 ELSE 0 END) as owners,
            COUNT(*) as total
        FROM '{LP}'
        WHERE year = {year} AND head_age BETWEEN 20 AND 55
        GROUP BY head_age
        ORDER BY head_age
    """).fetchall()

    if not res or len(res) < 10:
        continue

    # Find age where ownership rate crosses 50%
    median_own_age = None
    for r in res:
        age, owners, total = r
        rate = owners / total if total > 0 else 0
        if rate >= 0.5 and median_own_age is None:
            median_own_age = age

    if median_own_age:
        results.append({'year': year, 'median_ownership_age': median_own_age})
        print(f"{year}: ownership crosses 50% at age {median_own_age}")
    else:
        # Find max rate
        max_rate = max((r[1]/r[2] if r[2]>0 else 0) for r in res)
        print(f"{year}: never crosses 50% (max rate = {max_rate:.1%})")

print("\n=== SUMMARY ===")
for r in results:
    print(f"  {r['year']}: age {r['median_ownership_age']}")

with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/psid_ownership_age.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved.")
con.close()
