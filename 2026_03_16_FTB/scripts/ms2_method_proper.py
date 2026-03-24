"""
Proper Census MS-2 methodology applied to both marriage and headship.

Census Bureau method (Shryock & Siegel 1971):
1. Tabulate proportion "never experienced X" (S_a) by single year of age
2. Estimate proportion who will EVENTUALLY experience X: P = 1 - S_old
   (using 45-54 age group's rate as the lifetime ceiling)
3. Target = P / 2 (half of eventual experiencers)
4. Walk through ever-experienced proportions (1 - S_a), find where it crosses target
5. Linearly interpolate

For marriage: "never experienced X" = never married (MARST=6)
For headship: "never experienced X" = not currently a householder
   (RELATE not in head/spouse codes)

Note: headship is reversible, so "not currently head" != "never been head".
This is a known limitation but is the best available proxy from cross-sectional data.
"""
import duckdb
import json

con = duckdb.connect()
CPS = '/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec.parquet'

results = {'marriage_ms2_method': [], 'headship_ms2_method': [], 'marriage_naive': [], 'headship_naive': []}

for year in range(1976, 2026):
    for label, condition in [
        ('marriage', 'MARST = 6'),      # never married
        ('headship', 'RELATE NOT IN (101, 201, 202, 203)'),  # not head/spouse
    ]:
        # Get proportion "not yet X" at each single year of age
        rows = con.execute(f"""
            SELECT AGE,
                SUM(CASE WHEN {condition} THEN ASECWT ELSE 0 END) as not_yet_wt,
                SUM(ASECWT) as total_wt
            FROM '{CPS}'
            WHERE YEAR = {year} AND AGE BETWEEN 15 AND 54
            GROUP BY AGE
            ORDER BY AGE
        """).fetchall()

        if not rows or len(rows) < 10:
            continue

        # Build age -> proportion "not yet" dict
        age_pcts = {}
        for row in rows:
            age, not_yet, total = row
            if total > 0:
                age_pcts[age] = not_yet / total  # S_a = proportion who haven't experienced X

        # Step 1: Estimate proportion who will EVENTUALLY experience X
        # Use average of ages 45-54 as the "permanently never" rate
        never_rates = [age_pcts[a] for a in range(45, 55) if a in age_pcts]
        if not never_rates:
            continue
        perm_never = sum(never_rates) / len(never_rates)  # S_old
        prop_eventual = 1 - perm_never  # P = proportion who will ever experience X

        if prop_eventual <= 0:
            continue

        # Step 2: Target = P / 2 (half of eventual experiencers)
        target = prop_eventual / 2

        # Step 3: Walk through ever-experienced proportions, find crossing
        # ever_experienced_a = 1 - S_a
        # We want: 1 - S_a >= target, i.e., S_a <= 1 - target
        threshold = 1 - target  # S_a must drop below this

        prev_age, prev_s = None, None
        median_ms2 = None
        median_naive = None

        for age in sorted(age_pcts.keys()):
            s_a = age_pcts[age]

            # MS-2 method: crossing the adjusted target
            if prev_s is not None and prev_s >= threshold and s_a < threshold:
                if median_ms2 is None:
                    fraction = (prev_s - threshold) / (prev_s - s_a)
                    median_ms2 = prev_age + fraction

            # Naive method: raw 50% crossing
            if prev_s is not None and prev_s >= 0.5 and s_a < 0.5:
                if median_naive is None:
                    fraction = (prev_s - 0.5) / (prev_s - s_a)
                    median_naive = prev_age + fraction

            prev_age = age
            prev_s = s_a

        if median_ms2 is not None:
            results[f'{label}_ms2_method'].append({'year': year, 'age': round(median_ms2, 1)})
        if median_naive is not None:
            results[f'{label}_naive'].append({'year': year, 'age': round(median_naive, 1)})

# Print comparison
print("=== MARRIAGE ===")
print(f"{'Year':>6} {'MS2_method':>10} {'Naive':>8} {'Diff':>6}")
ms2_by_year = {r['year']: r['age'] for r in results['marriage_ms2_method']}
naive_by_year = {r['year']: r['age'] for r in results['marriage_naive']}
for year in sorted(set(list(ms2_by_year.keys()) + list(naive_by_year.keys()))):
    ms2 = ms2_by_year.get(year, None)
    naive = naive_by_year.get(year, None)
    if ms2 and naive:
        print(f"{year:>6} {ms2:>10.1f} {naive:>8.1f} {ms2-naive:>+6.1f}")
    elif ms2:
        print(f"{year:>6} {ms2:>10.1f} {'--':>8}")
    elif naive:
        print(f"{year:>6} {'--':>10} {naive:>8.1f}")

print("\n=== HEADSHIP ===")
print(f"{'Year':>6} {'MS2_method':>10} {'Naive':>8} {'Diff':>6}")
ms2_by_year = {r['year']: r['age'] for r in results['headship_ms2_method']}
naive_by_year = {r['year']: r['age'] for r in results['headship_naive']}
for year in sorted(set(list(ms2_by_year.keys()) + list(naive_by_year.keys()))):
    ms2 = ms2_by_year.get(year, None)
    naive = naive_by_year.get(year, None)
    if ms2 and naive:
        print(f"{year:>6} {ms2:>10.1f} {naive:>8.1f} {ms2-naive:>+6.1f}")
    elif ms2:
        print(f"{year:>6} {ms2:>10.1f} {'--':>8}")
    elif naive:
        print(f"{year:>6} {'--':>10} {naive:>8.1f}")

# Save
with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/ms2_method_proper.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nSaved to data/ms2_method_proper.json")
