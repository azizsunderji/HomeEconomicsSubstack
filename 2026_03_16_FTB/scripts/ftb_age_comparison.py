"""
Compare First-Time Homebuyer median age across data sources:
  1. AHS (American Housing Survey) 1985-2023
  2. NY Fed CCP/Equifax (from published figures) 2000-2025

Goal: reconcile rising marriage age with reportedly flat FTB age.
"""

import duckdb
import json

AHS_DIR = '/Users/azizsunderji/Dropbox/Home Economics/Data/AHS'
con = duckdb.connect()

# ── NY Fed CCP data (from Liberty Street Economics + AEI) ──────────────────
# Source: https://libertystreeteconomics.newyorkfed.org/2025/08/
#         who-is-still-on-first-an-update-of-characteristics-of-first-time-homebuyers/
# Source: https://www.aei.org/research-products/report/
#         median-first-time-homebuyer-age-at-34-years-in-2025-little-changed-from-2024/

nyfed_data = [
    # (year, median, average) — from published NY Fed CCP/Equifax data
    (2000, 35, 37.9),
    (2007, 33, 37.4),
    (2016, 32, 35.4),
    (2019, 33, 36.4),
    (2024, 33, 36.3),
    (2025, 34, 36.2),
]

# ── AHS: Era 1 (1985-1995) — AGE1, FRSTHO=2, TENURE=1, MOVE1 ─────────────

ahs_results = []

for year in range(1985, 1996, 2):
    hh_csv = f'{AHS_DIR}/ahs{year}n.csv'
    try:
        cols = [c[0] for c in con.execute(
            f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{hh_csv}')").fetchall()]
    except:
        # Try year subdirectory
        hh_csv = f'{AHS_DIR}/{year}/household.csv'
        try:
            cols = [c[0] for c in con.execute(
                f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{hh_csv}')").fetchall()]
        except:
            print(f"{year}: no file found")
            continue

    if 'AGE1' not in cols or 'FRSTHO' not in cols or 'MOVE1' not in cols:
        print(f"{year}: missing required variables")
        continue

    wt_col = 'WEIGHT' if 'WEIGHT' in cols else 'WGT90GEO' if 'WGT90GEO' in cols else None
    if not wt_col:
        for cn in cols:
            if 'WGT' in cn or 'WEIGHT' in cn:
                wt_col = cn
                break
    if not wt_col:
        print(f"{year}: no weight column")
        continue

    yy = year % 100
    move_cutoff = yy - 2

    res = con.execute(f"""
        SELECT
            CAST(AGE1 AS INTEGER) as age,
            SUM(CAST("{wt_col}" AS DOUBLE)) as wt
        FROM '{hh_csv}'
        WHERE FRSTHO = '2'
          AND TENURE = '1'
          AND TRY_CAST(MOVE1 AS INTEGER) >= {move_cutoff}
          AND TRY_CAST(AGE1 AS INTEGER) IS NOT NULL
          AND TRY_CAST("{wt_col}" AS DOUBLE) > 0
        GROUP BY CAST(AGE1 AS INTEGER)
        ORDER BY age
    """).fetchall()

    if not res:
        print(f"{year}: no matching records")
        continue

    total = sum(r[1] for r in res)
    cumul = 0
    median = None
    for r in res:
        cumul += r[1]
        if cumul >= total * 0.5 and median is None:
            median = r[0]

    mean_age = sum(r[0] * r[1] for r in res) / total
    n = sum(r[1] for r in res)

    ahs_results.append({
        'year': year, 'median': median, 'mean': round(mean_age, 1),
        'weighted_n': int(n), 'era': 'old', 'method': 'AGE1+MOVE1'
    })
    print(f"AHS {year}: median={median}, mean={mean_age:.1f}, n={n:,.0f}")


# ── AHS: Era 2 (2001-2013) — HHAGE, FRSTHO=2, TENURE=1, HHMOVE ───────────

for year in range(2001, 2014, 2):
    hh_csv = f'{AHS_DIR}/{year}/household.csv'
    try:
        cols = [c[0] for c in con.execute(
            f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{hh_csv}')").fetchall()]
    except:
        print(f"{year}: no file found")
        continue

    if 'HHAGE' not in cols or 'FRSTHO' not in cols or 'HHMOVE' not in cols:
        print(f"{year}: missing required variables (HHAGE={('HHAGE' in cols)}, FRSTHO={('FRSTHO' in cols)}, HHMOVE={('HHMOVE' in cols)})")
        continue

    wt_col = 'WEIGHT' if 'WEIGHT' in cols else 'WGT90GEO' if 'WGT90GEO' in cols else None
    if not wt_col:
        for cn in cols:
            if 'WGT' in cn or 'WEIGHT' in cn:
                wt_col = cn
                break
    if not wt_col:
        print(f"{year}: no weight column")
        continue

    # Recent movers: moved within last 2 years
    move_cutoff = year - 2

    res = con.execute(f"""
        SELECT
            TRY_CAST(HHAGE AS INTEGER) - ({year} - TRY_CAST(HHMOVE AS INTEGER)) as age_at_purchase,
            SUM(CAST("{wt_col}" AS DOUBLE)) as wt
        FROM '{hh_csv}'
        WHERE FRSTHO = '2'
          AND TENURE = '1'
          AND TRY_CAST(HHMOVE AS INTEGER) >= {move_cutoff}
          AND TRY_CAST(HHAGE AS INTEGER) IS NOT NULL
          AND TRY_CAST(HHMOVE AS INTEGER) IS NOT NULL
          AND CAST("{wt_col}" AS DOUBLE) > 0
          AND (TRY_CAST(HHAGE AS INTEGER) - ({year} - TRY_CAST(HHMOVE AS INTEGER))) BETWEEN 18 AND 85
        GROUP BY age_at_purchase
        ORDER BY age_at_purchase
    """).fetchall()

    if not res:
        print(f"{year}: no matching records")
        continue

    total = sum(r[1] for r in res)
    cumul = 0
    median = None
    for r in res:
        cumul += r[1]
        if cumul >= total * 0.5 and median is None:
            median = r[0]

    mean_age = sum(r[0] * r[1] for r in res) / total
    n = sum(r[1] for r in res)

    ahs_results.append({
        'year': year, 'median': median, 'mean': round(mean_age, 1),
        'weighted_n': int(n), 'era': 'mid', 'method': 'HHAGE-HHMOVE'
    })
    print(f"AHS {year}: median={median}, mean={mean_age:.1f}, n={n:,.0f}")


# ── AHS: Era 3 (2015-2023) — HHAGE, FIRSTHOME=1, TENURE=1, HHMOVE ────────

for year in range(2015, 2024, 2):
    hh_csv = f'{AHS_DIR}/{year}/household.csv'
    try:
        cols = [c[0] for c in con.execute(
            f"SELECT column_name FROM (DESCRIBE SELECT * FROM '{hh_csv}')").fetchall()]
    except:
        print(f"{year}: no file found")
        continue

    ftb_col = 'FIRSTHOME' if 'FIRSTHOME' in cols else 'FRSTHO' if 'FRSTHO' in cols else None
    ftb_val = "'1'" if ftb_col == 'FIRSTHOME' else "'2'"

    if not ftb_col or 'HHAGE' not in cols or 'HHMOVE' not in cols:
        print(f"{year}: missing required variables")
        continue

    wt_col = 'WEIGHT' if 'WEIGHT' in cols else None
    if not wt_col:
        for cn in cols:
            if cn.upper() == 'WEIGHT' or cn.upper() == 'WGT90GEO':
                wt_col = cn
                break
    if not wt_col:
        print(f"{year}: no weight column, looking...")
        wt_candidates = [c for c in cols if 'WGT' in c.upper() or 'WEIGHT' in c.upper()]
        print(f"  candidates: {wt_candidates}")
        if wt_candidates:
            wt_col = wt_candidates[0]
        else:
            continue

    move_cutoff = year - 2

    res = con.execute(f"""
        SELECT
            TRY_CAST(HHAGE AS INTEGER) - ({year} - TRY_CAST(HHMOVE AS INTEGER)) as age_at_purchase,
            SUM(CAST("{wt_col}" AS DOUBLE)) as wt
        FROM '{hh_csv}'
        WHERE {ftb_col} = {ftb_val}
          AND TENURE = '1'
          AND TRY_CAST(HHMOVE AS INTEGER) >= {move_cutoff}
          AND TRY_CAST(HHAGE AS INTEGER) IS NOT NULL
          AND TRY_CAST(HHMOVE AS INTEGER) IS NOT NULL
          AND CAST("{wt_col}" AS DOUBLE) > 0
          AND (TRY_CAST(HHAGE AS INTEGER) - ({year} - TRY_CAST(HHMOVE AS INTEGER))) BETWEEN 18 AND 85
        GROUP BY age_at_purchase
        ORDER BY age_at_purchase
    """).fetchall()

    if not res:
        print(f"{year}: no matching records")
        continue

    total = sum(r[1] for r in res)
    cumul = 0
    median = None
    for r in res:
        cumul += r[1]
        if cumul >= total * 0.5 and median is None:
            median = r[0]

    mean_age = sum(r[0] * r[1] for r in res) / total
    n = sum(r[1] for r in res)

    ahs_results.append({
        'year': year, 'median': median, 'mean': round(mean_age, 1),
        'weighted_n': int(n), 'era': 'new', 'method': f'{ftb_col}+HHMOVE'
    })
    print(f"AHS {year}: median={median}, mean={mean_age:.1f}, n={n:,.0f}")


# ── Summary comparison ─────────────────────────────────────────────────────

print("\n\n" + "=" * 70)
print("AHS FIRST-TIME HOMEBUYER AGE AT PURCHASE")
print("=" * 70)
print(f"{'Year':>6}  {'Median':>6}  {'Mean':>6}  {'Weighted N':>12}  {'Method'}")
print("-" * 60)
for r in sorted(ahs_results, key=lambda x: x['year']):
    print(f"{r['year']:>6}  {r['median']:>6}  {r['mean']:>6}  {r['weighted_n']:>12,}  {r['method']}")

print("\n" + "=" * 70)
print("NY FED CCP/EQUIFAX FIRST-TIME HOMEBUYER AGE")
print("=" * 70)
print(f"{'Year':>6}  {'Median':>6}  {'Mean':>6}")
print("-" * 30)
for yr, med, avg in nyfed_data:
    print(f"{yr:>6}  {med:>6}  {avg:>6}")

print("\n" + "=" * 70)
print("SIDE-BY-SIDE COMPARISON (overlapping years)")
print("=" * 70)
ahs_by_year = {r['year']: r for r in ahs_results}
for yr, med, avg in nyfed_data:
    ahs = ahs_by_year.get(yr)
    if ahs:
        print(f"{yr}: AHS median={ahs['median']}, NYFed median={med}  (gap={ahs['median']-med:+d})")
    else:
        # Find nearest AHS year
        closest = min(ahs_results, key=lambda x: abs(x['year'] - yr), default=None)
        if closest and abs(closest['year'] - yr) <= 2:
            print(f"{yr}: AHS {closest['year']} median={closest['median']}, NYFed median={med}  (gap={closest['median']-med:+d})")

# Save results for charting
output = {
    'ahs': [{'year': r['year'], 'median': r['median'], 'mean': r['mean'],
             'method': r['method']} for r in sorted(ahs_results, key=lambda x: x['year'])],
    'nyfed': [{'year': yr, 'median': med, 'mean': avg} for yr, med, avg in nyfed_data]
}
with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/ftb_age_comparison.json', 'w') as f:
    json.dump(output, f, indent=2)
print("\nSaved to data/ftb_age_comparison.json")

con.close()
