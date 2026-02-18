import duckdb
import numpy as np

con = duckdb.connect()

# Get subcategory-level data (4-digit codes = first 4 of 6-digit code)
# Show: major category, subcategory code, time share, happiness, sample size
# For ages 25-54 only

print("=" * 100)
print("SUBCATEGORY BREAKDOWN (25-54, WB module)")
print("=" * 100)

subcats = con.execute("""
    WITH base AS (
        SELECT 
            ACTIVITY // 10000 as major,
            ACTIVITY // 100 as subcat_code,
            ACTIVITY as full_code,
            CAST(SCHAPPY AS DOUBLE) as happy,
            CAST(AWBWT AS DOUBLE) as wt,
            CAST(DURATION AS DOUBLE) as dur
        FROM 'data/atus_ipums.parquet'
        WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
          AND AGE BETWEEN 25 AND 54
    )
    SELECT 
        major,
        subcat_code,
        SUM(wt) as total_wt,
        SUM(happy * wt) / SUM(wt) as mean_happy,
        COUNT(*) as n,
        SUM(wt) / (SELECT SUM(wt) FROM base) * 100 as pct_of_total
    FROM base
    GROUP BY major, subcat_code
    ORDER BY major, total_wt DESC
""").df()

print("\nAll subcategories with >0.5% of total time or >100 observations:")
print(f"{'Major':>5s}  {'SubCode':>7s}  {'% Time':>7s}  {'Happy':>6s}  {'N':>6s}")
print("-" * 40)
for _, row in subcats.iterrows():
    if row['pct_of_total'] > 0.5 or row['n'] > 100:
        print(f"{row['major']:5.0f}  {row['subcat_code']:7.0f}  {row['pct_of_total']:6.1f}%  {row['mean_happy']:6.2f}  {row['n']:6.0f}")

# Now focus on category 12 (Socializing, Relaxing, Leisure) - the big one
print("\n\n" + "=" * 100)
print("CATEGORY 12 DEEP DIVE: Socializing, Relaxing, and Leisure")
print("=" * 100)

cat12 = con.execute("""
    WITH base AS (
        SELECT 
            ACTIVITY // 100 as subcat,
            ACTIVITY as full_code,
            CAST(SCHAPPY AS DOUBLE) as happy,
            CAST(AWBWT AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD < 98 THEN 'Parent' ELSE 'Non-parent' END as grp
        FROM 'data/atus_ipums.parquet'
        WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
          AND AGE BETWEEN 25 AND 54
          AND ACTIVITY // 10000 = 12
    )
    SELECT 
        subcat,
        grp,
        SUM(wt) as total_wt,
        SUM(happy * wt) / SUM(wt) as mean_happy,
        COUNT(*) as n
    FROM base
    GROUP BY subcat, grp
    ORDER BY subcat, grp
""").df()

print("\nSubcategory breakdown by parent status:")
print(cat12.to_string())

# Also get the total for each group to compute shares
totals = con.execute("""
    SELECT 
        CASE WHEN AGEYCHILD < 98 THEN 'Parent' ELSE 'Non-parent' END as grp,
        SUM(CAST(AWBWT AS DOUBLE)) as total_wt
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND AGE BETWEEN 25 AND 54
      AND ACTIVITY // 10000 != 1  -- exclude personal care
    GROUP BY grp
""").df()
print("\nGroup totals (excl personal care):")
print(totals.to_string())

p_total = totals[totals['grp']=='Parent']['total_wt'].values[0]
np_total = totals[totals['grp']=='Non-parent']['total_wt'].values[0]

print("\nCategory 12 subcategories as % of waking time:")
print(f"{'SubCode':>7s}  {'P_share':>8s}  {'NP_share':>9s}  {'P_happy':>8s}  {'NP_happy':>9s}  {'P_n':>5s}  {'NP_n':>5s}")
for sc in sorted(cat12['subcat'].unique()):
    p_row = cat12[(cat12['subcat']==sc) & (cat12['grp']=='Parent')]
    np_row = cat12[(cat12['subcat']==sc) & (cat12['grp']=='Non-parent')]
    p_wt = p_row['total_wt'].values[0] if len(p_row) > 0 else 0
    np_wt = np_row['total_wt'].values[0] if len(np_row) > 0 else 0
    p_h = p_row['mean_happy'].values[0] if len(p_row) > 0 else 0
    np_h = np_row['mean_happy'].values[0] if len(np_row) > 0 else 0
    p_n = p_row['n'].values[0] if len(p_row) > 0 else 0
    np_n = np_row['n'].values[0] if len(np_row) > 0 else 0
    print(f"{sc:7.0f}  {p_wt/p_total*100:7.1f}%  {np_wt/np_total*100:8.1f}%  {p_h:8.2f}  {np_h:9.2f}  {p_n:5.0f}  {np_n:5.0f}")


# Now look at ALL major categories for potential splits
print("\n\n" + "=" * 100)
print("ALL MAJOR CATEGORIES: Subcategory variation in happiness")
print("=" * 100)
print("Looking for categories where subcategories have meaningfully different happiness scores")
print("(Only showing subcats with >200 obs)")

all_subcats = con.execute("""
    WITH base AS (
        SELECT 
            ACTIVITY // 10000 as major,
            ACTIVITY // 100 as subcat,
            CAST(SCHAPPY AS DOUBLE) as happy,
            CAST(AWBWT AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD < 98 THEN 'Parent' ELSE 'Non-parent' END as grp
        FROM 'data/atus_ipums.parquet'
        WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
          AND AGE BETWEEN 25 AND 54
    )
    SELECT 
        major,
        subcat,
        SUM(wt) as total_wt,
        SUM(happy * wt) / SUM(wt) as mean_happy,
        COUNT(*) as n,
        SUM(CASE WHEN grp='Parent' THEN wt ELSE 0 END) / NULLIF(SUM(CASE WHEN grp='Parent' THEN wt ELSE NULL END), 0) as p_happy_placeholder,
        SUM(CASE WHEN grp='Parent' THEN wt END) as p_wt,
        SUM(CASE WHEN grp='Non-parent' THEN wt END) as np_wt
    FROM base
    GROUP BY major, subcat
    HAVING COUNT(*) > 200
    ORDER BY major, mean_happy DESC
""").df()

# For each major category, show range of happiness across subcategories
current_major = None
for _, row in all_subcats.iterrows():
    if row['major'] != current_major:
        current_major = row['major']
        major_rows = all_subcats[all_subcats['major'] == current_major]
        rng = major_rows['mean_happy'].max() - major_rows['mean_happy'].min()
        print(f"\n  Major {int(current_major):02d} -- Range: {rng:.2f}  ({len(major_rows)} subcats with >200 obs)")
    print(f"    {int(row['subcat']):6d}  happy={row['mean_happy']:.2f}  n={int(row['n']):5d}  share={row['total_wt']/all_subcats['total_wt'].sum()*100:.1f}%")


# Finally: what are the ATUS subcategory NAMES for code 12?
print("\n\n" + "=" * 100)
print("ATUS CATEGORY 12 SUBCATEGORY NAMES (from BLS coding)")
print("=" * 100)
print("""
1201xx = Socializing and Communicating (talking, visiting)
1202xx = Attending or Hosting Social Events (parties, ceremonies)
1203xx = Relaxing and Leisure (TV, movies, reading, relaxing/thinking, tobacco/drugs, arts)
1204xx = Arts and Entertainment (not as participant -- attending museums, concerts, movies)
1205xx = Waiting Associated with Socializing
1299xx = Socializing, NEC
""")

# Check what codes actually appear
print("\nActual codes in our data for major 12:")
codes12 = con.execute("""
    SELECT DISTINCT ACTIVITY // 100 as subcat, COUNT(*) as n
    FROM 'data/atus_ipums.parquet'
    WHERE ACTIVITY // 10000 = 12
      AND AGE BETWEEN 25 AND 54
    GROUP BY subcat
    ORDER BY subcat
""").df()
print(codes12.to_string())
