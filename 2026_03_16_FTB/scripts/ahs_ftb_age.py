"""
Median age of recent first-time homebuyers, AHS 1975-2013.
Uses FRSTHO=2 (first home ever owned), TENURE=1 (owner),
and MOVE1 >= survey_year-2 (recent mover).
"""

import duckdb
import os
import zipfile
import glob

AHS_DIR = '/Users/azizsunderji/Dropbox/Home Economics/Data/AHS'
con = duckdb.connect()

# Unzip all files first
for zf in glob.glob(f'{AHS_DIR}/ahs_*_national.zip'):
    size = os.path.getsize(zf)
    if size > 50000:  # skip failed downloads
        year = zf.split('ahs_')[1].split('_')[0]
        outdir = f'{AHS_DIR}/{year}'
        os.makedirs(outdir, exist_ok=True)
        try:
            with zipfile.ZipFile(zf, 'r') as z:
                z.extractall(outdir)
        except:
            print(f"  Failed to unzip {zf}")

# For each year, find the national CSV and compute FTB median age
results = []

for year in range(1975, 2014):
    year_dir = f'{AHS_DIR}/{year}'
    if not os.path.isdir(year_dir):
        continue

    # Find the household-level CSV
    csvs = glob.glob(f'{year_dir}/*.csv')
    if not csvs:
        # Also check root AHS dir
        csvs = glob.glob(f'{AHS_DIR}/ahs{year}n.csv')

    if not csvs:
        continue

    # For 2003+ the format splits into household.csv, person.csv, rmov.csv
    # For pre-2003 it's a single flat file
    hh_csv = None
    for c in csvs:
        bn = os.path.basename(c).lower()
        if 'household' in bn or f'ahs{year}n' in bn or (bn.endswith('.csv') and 'metro' not in bn and 'person' not in bn and 'project' not in bn and 'rmov' not in bn):
            hh_csv = c
            break

    if not hh_csv:
        # Try the first CSV
        hh_csv = csvs[0]

    try:
        # Check if FRSTHO exists
        cols = con.execute(f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{hh_csv}')").fetchall()
        col_names = [c[0] for c in cols]

        if 'FRSTHO' not in col_names:
            print(f"{year}: No FRSTHO variable in {os.path.basename(hh_csv)}")
            continue

        if 'MOVE1' not in col_names:
            print(f"{year}: No MOVE1 variable in {os.path.basename(hh_csv)}")
            continue

        # Determine move year cutoff (2-digit year, last 3 years)
        yy = year % 100
        move_cutoff = yy - 2

        # Weight column
        wt_col = 'WEIGHT' if 'WEIGHT' in col_names else 'WGT90GEO' if 'WGT90GEO' in col_names else None
        if not wt_col:
            # Try to find any weight column
            for cn in col_names:
                if 'WGT' in cn or 'WEIGHT' in cn:
                    wt_col = cn
                    break

        if not wt_col:
            print(f"{year}: No weight column found")
            continue

        res = con.execute(f"""
            SELECT
                CAST(AGE1 AS INTEGER) as age,
                SUM(CAST("{wt_col}" AS DOUBLE)) as weighted_n
            FROM '{hh_csv}'
            WHERE FRSTHO = '2'
              AND TENURE = '1'
              AND TRY_CAST(MOVE1 AS INTEGER) >= {move_cutoff}
              AND TRY_CAST(AGE1 AS INTEGER) IS NOT NULL
              AND TRY_CAST("{wt_col}" AS DOUBLE) IS NOT NULL
              AND TRY_CAST("{wt_col}" AS DOUBLE) > 0
            GROUP BY CAST(AGE1 AS INTEGER)
            ORDER BY age
        """).fetchall()

        if not res:
            print(f"{year}: No matching records")
            continue

        total = sum(r[1] for r in res)
        cumul = 0
        median = None
        p25 = None
        p75 = None
        for r in res:
            cumul += r[1]
            if cumul >= total * 0.25 and p25 is None:
                p25 = r[0]
            if cumul >= total * 0.5 and median is None:
                median = r[0]
            if cumul >= total * 0.75 and p75 is None:
                p75 = r[0]

        mean_age = sum(r[0]*r[1] for r in res) / total
        n_unweighted = sum(1 for r in res)

        print(f"{year}: median={median}, mean={mean_age:.1f}, p25={p25}, p75={p75}, weighted_n={total:,.0f}")
        results.append({
            'year': year, 'median': median, 'mean': round(mean_age, 1),
            'p25': p25, 'p75': p75, 'weighted_n': int(total)
        })

    except Exception as e:
        print(f"{year}: Error - {e}")

print("\n\n=== SUMMARY ===")
print(f"{'Year':>6}  {'Median':>6}  {'Mean':>6}  {'P25':>4}  {'P75':>4}  {'Weighted N':>12}")
for r in results:
    print(f"{r['year']:>6}  {r['median']:>6}  {r['mean']:>6}  {r['p25']:>4}  {r['p75']:>4}  {r['weighted_n']:>12,}")
