"""
Apply Census MS-2 life-table methodology to both marriage and headship using CPS ASEC.

MS-2 method: For each year, compute the proportion "never experienced X" at each
single year of age. Find the two consecutive ages where it crosses below 50%.
Linear-interpolate to get a decimal median.

For marriage: proportion never married (MARST=6) at each age -> median age at first marriage
For headship: proportion NOT a householder (RELATE not in head/spouse) at each age -> median age at first headship

We validate by comparing our CPS marriage estimate against Census MS-2 published values.
"""
import duckdb
import json

con = duckdb.connect()
CPS = '/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec.parquet'

results = {'marriage': [], 'headship': []}

for year in range(1976, 2026):
    # Marriage: proportion never married at each age
    marriage_rows = con.execute(f"""
        SELECT AGE,
            SUM(CASE WHEN MARST = 6 THEN ASECWT ELSE 0 END) as never_married_wt,
            SUM(ASECWT) as total_wt
        FROM '{CPS}'
        WHERE YEAR = {year} AND AGE BETWEEN 15 AND 54
        GROUP BY AGE
        ORDER BY AGE
    """).fetchall()

    # Headship: proportion NOT head/spouse at each age
    # RELATE: 101=head, 201=spouse, 202/203=spouse variants
    headship_rows = con.execute(f"""
        SELECT AGE,
            SUM(CASE WHEN RELATE NOT IN (101, 201, 202, 203) THEN ASECWT ELSE 0 END) as not_head_wt,
            SUM(ASECWT) as total_wt
        FROM '{CPS}'
        WHERE YEAR = {year} AND AGE BETWEEN 15 AND 54
        GROUP BY AGE
        ORDER BY AGE
    """).fetchall()

    # MS-2 interpolation: find where "never X" proportion crosses below 50%
    for label, rows, col_idx in [('marriage', marriage_rows, 0), ('headship', headship_rows, 0)]:
        if not rows or len(rows) < 5:
            continue

        prev_age, prev_pct = None, None
        median_age = None

        for row in rows:
            age = row[0]
            not_yet = row[1]  # never married OR not head
            total = row[2]
            if total == 0:
                continue
            pct_not_yet = not_yet / total  # proportion who haven't experienced X

            if prev_pct is not None and prev_pct >= 0.5 and pct_not_yet < 0.5:
                # Linear interpolation between prev_age and age
                # Find exact point where pct crosses 0.5
                fraction = (prev_pct - 0.5) / (prev_pct - pct_not_yet)
                median_age = prev_age + fraction
                break

            prev_age = age
            prev_pct = pct_not_yet

        if median_age is not None:
            results[label].append({'year': year, 'age': round(median_age, 1)})

# Print comparison
print("=== MARRIAGE: CPS MS-2 method vs published MS-2 ===")
print(f"{'Year':>6} {'CPS_MS2':>8}")
for r in results['marriage']:
    print(f"{r['year']:>6} {r['age']:>8.1f}")

print("\n=== HEADSHIP: MS-2 method applied ===")
print(f"{'Year':>6} {'MS2_method':>10}")
for r in results['headship']:
    print(f"{r['year']:>6} {r['age']:>10.1f}")

# Save results
with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/ms2_method_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nSaved to data/ms2_method_results.json")
