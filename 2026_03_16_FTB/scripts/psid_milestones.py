"""
PSID: Extract person-level milestone ages (headship, marriage, ownership)
using the cross-year individual file.

Marriage: ER32036 = "YEAR FIRST/ONLY MARRIAGE BEGAN" (directly reported)
Headship: Track relationship-to-head codes across waves, find first year as head (code 10)
Ownership: Track own/rent from family files, find first year as owner while head
"""
import duckdb
import json

con = duckdb.connect()
XY = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/individual/cross_year.parquet'
FAM = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/family'

# Year -> (interview_num_col, age_col, relation_col) from cross-year individual file
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

# Family file: year -> own_rent variable (1=own, 5=rent)
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

# Person ID = ER30001 (1968 interview #) + ER30002 (person #)
# Marriage year = ER32036
# Birth year approximation: from first observed age

print("Loading cross-year individual file...")
# Build person-level records
# Step 1: Get marriage year and person ID for everyone
persons = con.execute(f"""
    SELECT
        CAST(ER30001 AS INT) as fam68,
        CAST(ER30002 AS INT) as pn,
        CAST(ER30001 AS VARCHAR) || '_' || CAST(ER30002 AS VARCHAR) as person_id,
        CAST(ER32036 AS INT) as marriage_year,
        CAST(ER32034 AS INT) as num_marriages
    FROM '{XY}'
    WHERE CAST(ER30001 AS INT) > 0 AND CAST(ER30002 AS INT) > 0
""").fetchdf()

print(f"Total persons: {len(persons):,}")
print(f"With valid marriage year (>0, <9999): {((persons.marriage_year > 0) & (persons.marriage_year < 9999)).sum():,}")

# Step 2: For each person, track across waves to find:
#   - First year they appear as head (relation=10) -> headship age
#   - First year they appear in an owner household while head -> ownership age
#   - Their age in each wave (to compute birth year)

# Build a SQL query that extracts person_id, year, age, relation for each wave
union_parts = []
for year, (idn_col, age_col, rel_col) in sorted(year_map.items()):
    union_parts.append(f"""
        SELECT
            CAST(ER30001 AS VARCHAR) || '_' || CAST(ER30002 AS VARCHAR) as person_id,
            {year} as year,
            CAST({age_col} AS INT) as age,
            CAST({rel_col} AS INT) as relation,
            CAST({idn_col} AS INT) as interview_num
        FROM '{XY}'
        WHERE CAST({idn_col} AS INT) > 0 AND CAST({age_col} AS INT) > 0 AND CAST({age_col} AS INT) < 999
    """)

print("Building person-wave panel...")
panel_query = " UNION ALL ".join(union_parts)
con.execute(f"CREATE OR REPLACE TABLE panel AS {panel_query}")
panel_count = con.execute("SELECT COUNT(*) FROM panel").fetchone()[0]
print(f"Person-wave observations: {panel_count:,}")

# Step 3: Join family files for own/rent status
# For each year, join the family file on interview_num
print("Joining ownership data from family files...")
import os

for year in sorted(own_rent_vars.keys()):
    if year not in year_map:
        continue
    or_var = own_rent_vars[year]
    fam_file = os.path.join(FAM, f'fam{year}.parquet')
    if not os.path.exists(fam_file):
        continue

    # Get the first column name (interview number) from family file
    fam_cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM '{fam_file}' LIMIT 0").fetchall()]
    fam_id_col = fam_cols[0]  # First column is interview number

    if or_var not in fam_cols:
        continue

    con.execute(f"""
        UPDATE panel SET relation = panel.relation
        WHERE year = {year}
    """)  # no-op, just checking

    # We need to add own_rent to the panel. Let's do it differently.
    pass

# Simpler approach: build ownership lookup per year
print("Building ownership lookup...")
own_data = {}
for year in sorted(own_rent_vars.keys()):
    if year not in year_map:
        continue
    or_var = own_rent_vars[year]
    fam_file = os.path.join(FAM, f'fam{year}.parquet')
    if not os.path.exists(fam_file):
        continue
    fam_cols = [c[0] for c in con.execute(f"DESCRIBE SELECT * FROM '{fam_file}' LIMIT 0").fetchall()]
    fam_id_col = fam_cols[0]
    if or_var not in fam_cols:
        continue

    rows = con.execute(f"""
        SELECT {fam_id_col} as interview_num, {or_var} as own_rent
        FROM '{fam_file}'
    """).fetchall()
    own_data[year] = {r[0]: r[1] for r in rows}

# Step 4: For each person, find first headship, first ownership, and marriage year
print("Computing milestones per person...")
# Get all panel data sorted by person and year
all_rows = con.execute("""
    SELECT person_id, year, age, relation, interview_num
    FROM panel
    ORDER BY person_id, year
""").fetchall()

# Process person by person
from collections import defaultdict
person_data = defaultdict(list)
for row in all_rows:
    pid, year, age, relation, idn = row
    person_data[pid].append((year, age, relation, idn))

# Marriage years from the individual file
marriage_years = {}
for _, row in persons.iterrows():
    pid = row['person_id']
    my = row['marriage_year']
    if 1900 < my < 2025:
        marriage_years[pid] = my

print(f"Persons with panel data: {len(person_data):,}")
print(f"Persons with marriage year: {len(marriage_years):,}")

# Compute milestones
milestones = []
for pid, waves in person_data.items():
    # Estimate birth year from first observation
    first_year, first_age = waves[0][0], waves[0][1]
    birth_year = first_year - first_age

    if birth_year < 1920 or birth_year > 2005:
        continue

    first_head_age = None
    first_own_age = None
    marriage_age = None

    # Marriage age (from directly reported year)
    if pid in marriage_years:
        marriage_age = marriage_years[pid] - birth_year
        if marriage_age < 10 or marriage_age > 60:
            marriage_age = None

    # Track headship and ownership across waves
    for year, age, relation, idn in waves:
        # Head = relation code 10 (head of household)
        if first_head_age is None and relation == 10:
            first_head_age = age

        # Owner while head
        if first_own_age is None and relation == 10:
            if year in own_data and idn in own_data[year]:
                if own_data[year][idn] == 1:  # 1 = owns
                    first_own_age = age

    if first_head_age or marriage_age or first_own_age:
        milestones.append({
            'person_id': pid,
            'birth_year': birth_year,
            'first_head_age': first_head_age,
            'marriage_age': marriage_age,
            'first_own_age': first_own_age,
        })

print(f"\nPersons with any milestone: {len(milestones):,}")

# Aggregate by transition year (year the milestone occurred)
# For headship and ownership, transition year = birth_year + age
# For marriage, transition year = marriage_years[pid]

from statistics import median

# Group by decade of milestone occurrence for the chart
# But simpler: group by the year the milestone happened
results = {'headship': [], 'marriage': [], 'ownership': []}

for label, age_key in [('headship', 'first_head_age'), ('marriage', 'marriage_age'), ('ownership', 'first_own_age')]:
    by_year = defaultdict(list)
    for m in milestones:
        age = m[age_key]
        if age and 15 <= age <= 55:
            event_year = m['birth_year'] + age
            by_year[event_year].append(age)

    for year in sorted(by_year.keys()):
        if 1970 <= year <= 2023 and len(by_year[year]) >= 10:
            med = median(by_year[year])
            results[label].append({'year': year, 'age': round(med, 1), 'n': len(by_year[year])})

print("\n=== PSID Milestones by year of event ===")
for label in ['headship', 'marriage', 'ownership']:
    print(f"\n{label.upper()}:")
    for r in results[label]:
        print(f"  {r['year']}: {r['age']} (n={r['n']})")

# Save
with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/psid_milestones.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved to data/psid_milestones.json")
