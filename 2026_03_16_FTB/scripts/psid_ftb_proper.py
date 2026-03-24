"""
PSID: Proper rent→own transition tracking using cross-year individual file.
Links persons across waves via the individual file, then joins to family files
for own/rent status. Finds first year each person becomes head of owner household.
"""
import duckdb
import json

XY = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/individual/cross_year.parquet'
FAM = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/family'
con = duckdb.connect()

# Cross-year individual file: year → (interview_num_col, age_col, relation_col)
year_map = {
    1968: ('ER30001','ER30004','ER30003'),
    1969: ('ER30020','ER30023','ER30022'),
    1970: ('ER30043','ER30046','ER30045'),
    1971: ('ER30067','ER30070','ER30069'),
    1972: ('ER30091','ER30094','ER30093'),
    1973: ('ER30117','ER30120','ER30119'),
    1974: ('ER30138','ER30141','ER30140'),
    1975: ('ER30160','ER30163','ER30162'),
    1976: ('ER30188','ER30191','ER30190'),
    1977: ('ER30217','ER30220','ER30219'),
    1978: ('ER30246','ER30249','ER30248'),
    1979: ('ER30283','ER30286','ER30285'),
    1980: ('ER30313','ER30316','ER30315'),
    1981: ('ER30343','ER30346','ER30345'),
    1982: ('ER30373','ER30376','ER30375'),
    1983: ('ER30399','ER30402','ER30401'),
    1984: ('ER30429','ER30432','ER30431'),
    1985: ('ER30463','ER30466','ER30465'),
    1986: ('ER30498','ER30501','ER30500'),
    1987: ('ER30535','ER30538','ER30537'),
    1988: ('ER30570','ER30573','ER30572'),
    1989: ('ER30606','ER30609','ER30608'),
    1990: ('ER30642','ER30645','ER30644'),
    1991: ('ER30689','ER30692','ER30691'),
    1992: ('ER30733','ER30736','ER30735'),
    1993: ('ER30806','ER30809','ER30808'),
    1994: ('ER33101','ER33104','ER33103'),
    1995: ('ER33201','ER33204','ER33203'),
    1996: ('ER33301','ER33304','ER33303'),
    1997: ('ER33401','ER33404','ER33403'),
    1999: ('ER33501','ER33504','ER33503'),
    2001: ('ER33601','ER33604','ER33603'),
    2003: ('ER33701','ER33704','ER33703'),
    2005: ('ER33801','ER33804','ER33803'),
    2007: ('ER33901','ER33904','ER33903'),
    2009: ('ER34001','ER34004','ER34003'),
    2011: ('ER34101','ER34104','ER34103'),
    2013: ('ER34201','ER34204','ER34203'),
    2015: ('ER34301','ER34305','ER34303'),
    2017: ('ER34501','ER34504','ER34503'),
    2019: ('ER34701','ER34704','ER34703'),
    2021: ('ER34901','ER34904','ER34903'),
    2023: ('ER35101','ER35104','ER35103'),
}

# Family file: year → own_rent variable (1=own, 5=rent)
own_rent_vars = {
    1968:'V103', 1969:'V593', 1970:'V1264', 1971:'V1967', 1972:'V2566',
    1973:'V3108', 1974:'V3522', 1975:'V3939', 1976:'V4450', 1977:'V5364',
    1978:'V5864', 1979:'V6479', 1980:'V7084', 1981:'V7675', 1982:'V8364',
    1983:'V8974', 1984:'V10437', 1985:'V11618', 1986:'V13023', 1987:'V14126',
    1988:'V15140', 1989:'V16641', 1990:'V18072', 1991:'V19372', 1992:'V20672',
    1993:'V22427', 1994:'ER2032', 1995:'ER5031', 1996:'ER7031', 1997:'ER10035',
    1999:'ER13040', 2001:'ER17043', 2003:'ER21042', 2005:'ER25028',
    2007:'ER36028', 2009:'ER42029', 2011:'ER47329', 2013:'ER53029',
    2015:'ER60030', 2017:'ER66030', 2019:'ER72030', 2021:'ER78031',
    2023:'ER82032',
}

# Family file: year → interview_number variable
fam_id_vars = {
    1968:'V1',
}
# For 1969+, the first column of the family file is typically the interview number
# In the PSID SPS files, it's documented. Let me use V-prefix pattern.
# Actually for most years the interview # is the first variable, but its name varies.
# I'll query it from the family file — it's the variable that matches the cross-year interview#.

# Step 1: Build person-year panel with own_rent
# For each year: get each person's interview#, age, relation from cross-year file,
# then join to family file on interview# to get own_rent.

print("Building person-year-tenure panel...")
con.execute("CREATE TABLE person_tenure (person_id INT, year INT, age INT, relation INT, own_rent INT)")

import os
for year in sorted(year_map.keys()):
    int_col, age_col, rel_col = year_map[year]
    own_var = own_rent_vars.get(year)
    if not own_var:
        continue

    fam_path = f"{FAM}/{year}.parquet"
    if not os.path.exists(fam_path):
        continue

    # Check columns exist in cross-year file
    xy_cols = set(c[0] for c in con.execute(
        f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{XY}')").fetchall())
    if int_col not in xy_cols or age_col not in xy_cols:
        print(f"  {year}: missing {int_col} or {age_col} in cross-year file")
        continue

    # Check own_var exists in family file
    fam_cols = set(c[0] for c in con.execute(
        f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{fam_path}')").fetchall())
    if own_var not in fam_cols:
        print(f"  {year}: missing {own_var} in family file")
        continue

    # Find the interview number column in the family file
    # It should match values from the cross-year int_col
    # For 1968, it's V1. For other years, use the labels or try common patterns.
    # The first variable in family files is usually interview-related.
    fam_first_col = sorted(fam_cols)[0]  # Alphabetical first, might not be right

    # Better: get a sample interview# from cross-year, find which fam column matches
    sample_int = con.execute(f"""
        SELECT DISTINCT CAST("{int_col}" AS INT) FROM '{XY}'
        WHERE CAST("{int_col}" AS INT) > 0 LIMIT 5
    """).fetchall()
    sample_vals = [r[0] for r in sample_int]

    # Try to find matching column in family file
    fam_id_col = None
    for candidate in sorted(fam_cols):
        try:
            match = con.execute(f"""
                SELECT COUNT(*) FROM '{fam_path}'
                WHERE CAST("{candidate}" AS INT) IN ({','.join(str(v) for v in sample_vals)})
            """).fetchone()[0]
            if match >= 3:  # At least 3 of 5 sample values match
                fam_id_col = candidate
                break
        except:
            continue

    if not fam_id_col:
        print(f"  {year}: couldn't find family ID column")
        continue

    # Now join: person (from cross-year) → family (own/rent)
    try:
        con.execute(f"""
            INSERT INTO person_tenure
            SELECT
                ROW_NUMBER() OVER () + (SELECT COALESCE(MAX(person_id),0) FROM person_tenure) as pid,
                {year},
                CAST(xy."{age_col}" AS INT),
                CAST(xy."{rel_col}" AS INT),
                CAST(fam."{own_var}" AS INT)
            FROM '{XY}' xy
            JOIN '{fam_path}' fam ON CAST(xy."{int_col}" AS INT) = CAST(fam."{fam_id_col}" AS INT)
            WHERE CAST(xy."{int_col}" AS INT) > 0
              AND CAST(xy."{age_col}" AS INT) BETWEEN 18 AND 85
              AND CAST(xy."{rel_col}" AS INT) = 1  -- heads only
        """)
        n = con.execute(f"SELECT COUNT(*) FROM person_tenure WHERE year={year}").fetchone()[0]
        print(f"  {year}: {n} heads loaded (fam_id={fam_id_col})")
    except Exception as e:
        print(f"  {year}: error - {e}")

# Hmm, the person_id approach above won't work for tracking across years
# because ROW_NUMBER gives different IDs each year.
# I need a STABLE person identifier. In the cross-year file, ER30001+ER30002
# (1968 interview# + person#) uniquely identifies each person.

print("\n\nRebuilding with stable person IDs...")
con.execute("DROP TABLE person_tenure")
con.execute("CREATE TABLE person_tenure (person_key VARCHAR, year INT, age INT, own_rent INT)")

for year in sorted(year_map.keys()):
    int_col, age_col, rel_col = year_map[year]
    own_var = own_rent_vars.get(year)
    if not own_var:
        continue

    fam_path = f"{FAM}/{year}.parquet"
    if not os.path.exists(fam_path):
        continue

    fam_cols = set(c[0] for c in con.execute(
        f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{fam_path}')").fetchall())
    if own_var not in fam_cols:
        continue

    xy_cols = set(c[0] for c in con.execute(
        f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{XY}')").fetchall())
    if int_col not in xy_cols or age_col not in xy_cols:
        continue

    # Find family ID column (same approach as above but cached)
    sample_int = con.execute(f"""
        SELECT DISTINCT CAST("{int_col}" AS INT) FROM '{XY}'
        WHERE CAST("{int_col}" AS INT) > 0 LIMIT 5
    """).fetchall()
    sample_vals = [r[0] for r in sample_int]

    fam_id_col = None
    for candidate in sorted(fam_cols):
        try:
            match = con.execute(f"""
                SELECT COUNT(*) FROM '{fam_path}'
                WHERE CAST("{candidate}" AS INT) IN ({','.join(str(v) for v in sample_vals)})
            """).fetchone()[0]
            if match >= 3:
                fam_id_col = candidate
                break
        except:
            continue

    if not fam_id_col:
        continue

    try:
        con.execute(f"""
            INSERT INTO person_tenure
            SELECT
                CAST(xy."ER30001" AS VARCHAR) || '_' || CAST(xy."ER30002" AS VARCHAR),
                {year},
                CAST(xy."{age_col}" AS INT),
                CAST(fam."{own_var}" AS INT)
            FROM '{XY}' xy
            JOIN '{fam_path}' fam ON CAST(xy."{int_col}" AS INT) = CAST(fam."{fam_id_col}" AS INT)
            WHERE CAST(xy."{int_col}" AS INT) > 0
              AND CAST(xy."{age_col}" AS INT) BETWEEN 18 AND 85
              AND CAST(xy."{rel_col}" AS INT) = 1
        """)
        n = con.execute(f"SELECT COUNT(*) FROM person_tenure WHERE year={year}").fetchone()[0]
        print(f"  {year}: {n} heads")
    except Exception as e:
        print(f"  {year}: error - {e}")

# Step 2: For each person, find first year they own
print("\n\nFinding first ownership year per person...")
first_own = con.execute("""
    SELECT person_key, MIN(year) as first_own_year,
        (SELECT age FROM person_tenure p2
         WHERE p2.person_key = p.person_key AND p2.year = MIN(p.year)) as age_at_first_own
    FROM person_tenure p
    WHERE own_rent = 1
    GROUP BY person_key
""").fetchdf()

# But we also need to verify they were renting BEFORE (not just always owned)
# A true FTB is someone who was renting at some point, then owned.
first_own_after_rent = con.execute("""
    WITH first_rent AS (
        SELECT person_key, MIN(year) as first_rent_year
        FROM person_tenure WHERE own_rent = 5
        GROUP BY person_key
    ),
    first_own AS (
        SELECT person_key, MIN(year) as first_own_year
        FROM person_tenure WHERE own_rent = 1
        GROUP BY person_key
    )
    SELECT fo.person_key, fo.first_own_year,
        (SELECT age FROM person_tenure p
         WHERE p.person_key = fo.person_key AND p.year = fo.first_own_year) as age_at_transition
    FROM first_own fo
    JOIN first_rent fr ON fo.person_key = fr.person_key
    WHERE fo.first_own_year > fr.first_rent_year  -- owned AFTER renting
""").fetchdf()

print(f"Total persons who transitioned rent→own: {len(first_own_after_rent):,}")

# Step 3: Compute median transition age by year
print("\n=== MEDIAN AGE AT FIRST HOMEOWNERSHIP (rent→own) ===")
results = []
for year in sorted(first_own_after_rent['first_own_year'].unique()):
    cohort = first_own_after_rent[first_own_after_rent['first_own_year'] == year]
    ages = cohort['age_at_transition'].dropna()
    ages = ages[(ages >= 18) & (ages <= 75)]
    if len(ages) < 10:
        continue
    median = ages.median()
    mean = ages.mean()
    results.append({'year': int(year), 'median': int(median), 'mean': round(float(mean), 1), 'n': len(ages)})
    print(f"  {year}: median={int(median)}, mean={mean:.1f}, n={len(ages)}")

with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/psid_ftb_transitions.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved.")
con.close()
