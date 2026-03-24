"""
PSID: Rent→own transitions. Fast version using DuckDB only.
Hardcoded variable names from the crosswalk we already built.
"""
import duckdb
import json

FAM = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/family'
con = duckdb.connect()

# (year, own_rent_var, age_var, fam68_id_var)
# own_rent: 1=own, 5=rent
years = [
    (1968, 'V103', 'V117', 'V2'),
    (1970, 'V1264', 'V1239', 'V1230'),
    (1971, 'V1967', 'V1942', 'V1932'),
    (1972, 'V2566', 'V2542', 'V2533'),
    (1974, 'V3522', 'V3508', 'V3497'),
    (1975, 'V3939', 'V3921', 'V3909'),
    (1976, 'V4450', 'V4436', 'V4423'),
    (1977, 'V5364', 'V5350', 'V5336'),
    (1978, 'V5864', 'V5850', 'V5835'),
    (1979, 'V6479', 'V6462', 'V6446'),
    (1980, 'V7084', 'V7067', 'V7050'),
]

# Step 1: Build a unified table in DuckDB
con.execute("CREATE TABLE psid_panel (year INT, fam68 INT, own_rent INT, head_age INT)")

for yr, own_var, age_var, id_var in years:
    fpath = f'{FAM}/{yr}.parquet'
    con.execute(f"""
        INSERT INTO psid_panel
        SELECT {yr},
            TRY_CAST({id_var} AS INTEGER),
            TRY_CAST({own_var} AS INTEGER),
            TRY_CAST({age_var} AS INTEGER)
        FROM '{fpath}'
        WHERE TRY_CAST({id_var} AS INTEGER) > 0
          AND TRY_CAST({age_var} AS INTEGER) BETWEEN 18 AND 85
    """)
    n = con.execute(f"SELECT COUNT(*) FROM psid_panel WHERE year={yr}").fetchone()[0]
    print(f"  {yr}: {n} rows loaded")

# 1994+ uses ER-style variables
years_er = [
    (1994, 'ER2032', 'ER2007', 'ER2005G'),
    (1995, 'ER5031', 'ER5006', 'ER5005G'),
    (1996, 'ER7031', 'ER7006', 'ER7005G'),
    (1997, 'ER10035', 'ER10009', 'ER10005G'),
    (1999, 'ER13040', 'ER13010', 'ER13019'),
    (2001, 'ER17043', 'ER17013', 'ER17016'),
    (2003, 'ER21042', 'ER21017', 'ER21020'),
    (2005, 'ER25028', 'ER25017', 'ER25020'),
    (2007, 'ER36028', 'ER36017', 'ER36020'),
    (2009, 'ER42029', 'ER42017', 'ER42020'),
    (2011, 'ER47329', 'ER47317', 'ER47320'),
    (2013, 'ER53029', 'ER53017', 'ER53020'),
    (2015, 'ER60030', 'ER60017', 'ER60020'),
    (2017, 'ER66030', 'ER66017', 'ER66020'),
    (2019, 'ER72030', 'ER72017', 'ER72020'),
    (2021, 'ER78031', 'ER78017', 'ER78020'),
    (2023, 'ER82032', 'ER82017', 'ER82020'),
]

for yr, own_var, age_var, id_var in years_er:
    fpath = f'{FAM}/{yr}.parquet'
    # Check columns exist
    cols = [c[0] for c in con.execute(f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{fpath}')").fetchall()]
    if own_var not in cols:
        print(f"  {yr}: {own_var} missing, skipping")
        continue
    if age_var not in cols:
        print(f"  {yr}: {age_var} missing, trying alternatives...")
        # Try common patterns
        for alt in [f'ER{int(age_var[2:])-10}', f'ER{int(age_var[2:])+10}']:
            if alt in cols:
                age_var = alt
                break
        else:
            print(f"  {yr}: no age var found, skipping")
            continue
    if id_var not in cols:
        # Try to find 1968 family identifier
        id_candidates = [c for c in cols if '68' in c or 'G' in c]
        # Search labels
        res = con.execute(f"""
            SELECT variable FROM '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/variable_labels.parquet'
            WHERE year={yr} AND (label ILIKE '1968 id%' OR label ILIKE '1968 family%')
        """).fetchall()
        if res and res[0][0] in cols:
            id_var = res[0][0]
        else:
            print(f"  {yr}: no family ID ({id_var}), skipping")
            continue

    con.execute(f"""
        INSERT INTO psid_panel
        SELECT {yr},
            TRY_CAST("{id_var}" AS INTEGER),
            TRY_CAST("{own_var}" AS INTEGER),
            TRY_CAST("{age_var}" AS INTEGER)
        FROM '{fpath}'
        WHERE TRY_CAST("{id_var}" AS INTEGER) > 0
          AND TRY_CAST("{age_var}" AS INTEGER) BETWEEN 18 AND 85
    """)
    n = con.execute(f"SELECT COUNT(*) FROM psid_panel WHERE year={yr}").fetchone()[0]
    print(f"  {yr}: {n} rows loaded")

# Step 2: Find rent→own transitions
print("\n=== RENT→OWN TRANSITIONS ===")
results = con.execute("""
    WITH pairs AS (
        SELECT
            curr.year as year,
            curr.head_age as age,
            prev.own_rent as prev_tenure,
            curr.own_rent as curr_tenure
        FROM psid_panel curr
        JOIN psid_panel prev ON curr.fam68 = prev.fam68
            AND prev.year = (
                SELECT MAX(p2.year) FROM psid_panel p2
                WHERE p2.fam68 = curr.fam68 AND p2.year < curr.year
            )
        WHERE curr.own_rent = 1 AND prev.own_rent = 5  -- rent→own
    )
    SELECT year,
        MEDIAN(age) as median_age,
        ROUND(AVG(age), 1) as mean_age,
        COUNT(*) as n
    FROM pairs
    GROUP BY year
    ORDER BY year
""").fetchall()

print(f"{'Year':>6}  {'Median':>6}  {'Mean':>6}  {'N':>6}")
print("-" * 35)
output = []
for r in results:
    print(f"{r[0]:>6}  {r[1]:>6}  {r[2]:>6}  {r[3]:>6}")
    output.append({'year': r[0], 'median': int(r[1]), 'mean': float(r[2]), 'n': int(r[3])})

with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/psid_ftb_transitions.json', 'w') as f:
    json.dump(output, f, indent=2)
print("\nSaved.")
con.close()
