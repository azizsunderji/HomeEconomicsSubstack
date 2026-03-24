"""
Long-run FTB median age from CPS ASEC, 1976-2025.
Two approaches:
  1. Redfin method (2000+): WHYMOVE=9 (want to own) or 2 (establish own household), owner, recent mover
  2. Crude method (1976+): recent mover + now owner + head/spouse (no reason-for-move filter)
"""

import duckdb
import json

CPS1 = '/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec.parquet'
CPS2 = '/Users/azizsunderji/Dropbox/Home Economics/Data/Reference/Microdata/CPS/cps_asec_1962_2025.parquet'

con = duckdb.connect()

results = []

for year in range(1976, 2026):
    # Check if WHYMOVE available (nonzero count)
    has_why = con.execute(f"""
        SELECT COUNT(*) FROM '{CPS2}'
        WHERE YEAR={year} AND WHYMOVE NOT IN ('0','')
    """).fetchone()[0] > 100

    if has_why:
        # Redfin method: WHYMOVE in (9=want to own, 2=establish own household)
        method = 'redfin'
        query = f"""
            SELECT a.AGE, SUM(a.ASECWT) as wt
            FROM '{CPS1}' a
            JOIN '{CPS2}' b ON a.YEAR=b.YEAR AND a.SERIAL=b.SERIAL AND a.PERNUM=b.PERNUM
            WHERE a.YEAR = {year}
              AND a.OWNERSHP = 10
              AND b.MIGRATE1 IN ('3','4','5','6')
              AND b.WHYMOVE IN ('9','2')
              AND a.RELATE IN (101, 201, 202, 203)
              AND a.AGE BETWEEN 18 AND 85
            GROUP BY a.AGE ORDER BY a.AGE
        """
    else:
        # Crude method: recent mover + owner + head/spouse
        method = 'crude'
        query = f"""
            SELECT a.AGE, SUM(a.ASECWT) as wt
            FROM '{CPS1}' a
            JOIN '{CPS2}' b ON a.YEAR=b.YEAR AND a.SERIAL=b.SERIAL AND a.PERNUM=b.PERNUM
            WHERE a.YEAR = {year}
              AND a.OWNERSHP = 10
              AND b.MIGRATE1 IN ('3','4','5','6')
              AND a.RELATE IN (101, 201, 202, 203)
              AND a.AGE BETWEEN 18 AND 85
            GROUP BY a.AGE ORDER BY a.AGE
        """

    try:
        res = con.execute(query).fetchall()
    except Exception as e:
        print(f"{year}: error - {e}")
        continue

    if not res or len(res) < 5:
        print(f"{year}: insufficient data ({len(res) if res else 0} age bins), method={method}")
        continue

    total = sum(r[1] for r in res)
    cumul = 0
    median = None
    for r in res:
        cumul += r[1]
        if cumul >= total * 0.5 and median is None:
            median = r[0]

    mean_age = sum(r[0] * r[1] for r in res) / total

    results.append({
        'year': year, 'median': median, 'mean': round(mean_age, 1),
        'weighted_n': int(total), 'method': method
    })
    print(f"{year}: median={median}, mean={mean_age:.1f}, n={total:,.0f}, method={method}")

print("\n\n=== SUMMARY ===")
print(f"{'Year':>6}  {'Median':>6}  {'Mean':>6}  {'N':>12}  {'Method'}")
print("-" * 55)
for r in sorted(results, key=lambda x: x['year']):
    print(f"{r['year']:>6}  {r['median']:>6}  {r['mean']:>6}  {r['weighted_n']:>12,}  {r['method']}")

# Save
with open('/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/cps_ftb_longrun.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\nSaved to data/cps_ftb_longrun.json")

con.close()
