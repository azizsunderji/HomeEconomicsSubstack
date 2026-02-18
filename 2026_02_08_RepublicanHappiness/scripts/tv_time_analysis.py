import duckdb
import json

con = duckdb.connect()

activity_map = """
    CASE
        WHEN ACTIVITY // 10000 = 1 THEN 'Personal Care'
        WHEN ACTIVITY // 10000 IN (2, 9) THEN 'Housework'
        WHEN ACTIVITY // 10000 IN (3, 4, 10) THEN 'Childcare'
        WHEN ACTIVITY // 10000 = 5 THEN 'Work'
        WHEN ACTIVITY // 10000 = 6 THEN 'Education'
        WHEN ACTIVITY // 10000 = 7 THEN 'Shopping'
        WHEN ACTIVITY // 10000 = 8 THEN 'Prof. Services'
        WHEN ACTIVITY // 10000 = 11 THEN 'Eating & Drinking'
        WHEN ACTIVITY // 100 IN (1201, 1202) THEN 'Socializing'
        WHEN ACTIVITY // 100 IN (1203, 1204, 1205, 1299) THEN 'TV & Leisure'
        WHEN ACTIVITY // 10000 = 13 THEN 'Sports & Exercise'
        WHEN ACTIVITY // 10000 = 14 THEN 'Religious'
        WHEN ACTIVITY // 10000 = 15 THEN 'Volunteering'
        WHEN ACTIVITY // 10000 = 16 THEN 'Phone Calls'
        WHEN ACTIVITY // 10000 = 18 THEN 'Travel'
        ELSE 'Other'
    END
"""

# 1. Activity rankings by happiness AND meaning (ages 25-54)
print("=" * 60)
print("ACTIVITY RANKINGS: HAPPINESS AND MEANING (ages 25-54)")
print("=" * 60)
df = con.execute(f"""
    SELECT
        {activity_map} as activity_cat,
        SUM(CAST(AWBWT AS DOUBLE)) as total_wt,
        SUM(CAST(SCHAPPY AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as mean_happy,
        SUM(CAST(MEANING AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as mean_meaning,
        COUNT(*) as n
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND CAST(MEANING AS INT) BETWEEN 0 AND 6
      AND {activity_map} NOT IN ('Other', 'Personal Care')
      AND AGE BETWEEN 25 AND 54
    GROUP BY activity_cat
    ORDER BY mean_meaning DESC
""").df()
for _, row in df.iterrows():
    time_pct = row['total_wt'] / df['total_wt'].sum() * 100
    print(f"  {row['activity_cat']:20s}  Happy={row['mean_happy']:.2f}  Meaning={row['mean_meaning']:.2f}  Time={time_pct:.1f}%  n={int(row['n'])}")

# 2. TV subcategories breakdown
print("\n" + "=" * 60)
print("TV & LEISURE SUBCATEGORIES (ages 25-54)")
print("=" * 60)
df2 = con.execute(f"""
    SELECT
        CASE
            WHEN ACTIVITY // 100 = 1203 THEN 'TV watching'
            WHEN ACTIVITY // 100 = 1204 THEN 'Reading'
            WHEN ACTIVITY // 100 = 1205 THEN 'Playing games'
            WHEN ACTIVITY // 100 = 1299 THEN 'Other leisure'
        END as sub,
        SUM(CAST(AWBWT AS DOUBLE)) as total_wt,
        SUM(CAST(SCHAPPY AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as mean_happy,
        SUM(CAST(MEANING AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as mean_meaning,
        COUNT(*) as n
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND CAST(MEANING AS INT) BETWEEN 0 AND 6
      AND ACTIVITY // 100 IN (1203, 1204, 1205, 1299)
      AND AGE BETWEEN 25 AND 54
    GROUP BY sub
    ORDER BY total_wt DESC
""").df()
for _, row in df2.iterrows():
    time_pct = row['total_wt'] / df2['total_wt'].sum() * 100
    print(f"  {row['sub']:20s}  Happy={row['mean_happy']:.2f}  Meaning={row['mean_meaning']:.2f}  Share={time_pct:.1f}%  n={int(row['n'])}")

# 3. Time allocation in minutes per day (all adults 25-54, using WT06)
print("\n" + "=" * 60)
print("TIME ALLOCATION: MINUTES PER DAY (ages 25-54, all ATUS respondents)")
print("=" * 60)
df3 = con.execute(f"""
    WITH person_time AS (
        SELECT
            CASEID,
            {activity_map} as activity_cat,
            SUM(DURATION) as total_minutes,
            MAX(CAST(WT06 AS DOUBLE)) as wt
        FROM 'data/atus_ipums.parquet'
        WHERE AGE BETWEEN 25 AND 54
          AND {activity_map} NOT IN ('Other', 'Personal Care')
        GROUP BY CASEID, activity_cat
    )
    SELECT
        activity_cat,
        SUM(total_minutes * wt) / SUM(wt) as avg_minutes,
        COUNT(DISTINCT CASEID) as n_persons
    FROM person_time
    GROUP BY activity_cat
    ORDER BY avg_minutes DESC
""").df()

# Also get total waking minutes
total_wake = con.execute("""
    WITH person_wake AS (
        SELECT CASEID, SUM(DURATION) as total_min, MAX(CAST(WT06 AS DOUBLE)) as wt
        FROM 'data/atus_ipums.parquet'
        WHERE AGE BETWEEN 25 AND 54
          AND ACTIVITY // 10000 != 1
        GROUP BY CASEID
    )
    SELECT SUM(total_min * wt) / SUM(wt) as avg_waking FROM person_wake
""").df()['avg_waking'].iloc[0]

print(f"  Average waking minutes: {total_wake:.0f} ({total_wake/60:.1f} hours)")
for _, row in df3.iterrows():
    pct_waking = row['avg_minutes'] / total_wake * 100
    print(f"  {row['activity_cat']:20s}  {row['avg_minutes']:.0f} min/day ({row['avg_minutes']/60:.1f} hrs)  {pct_waking:.1f}% of waking")

# 4. TV time specifically in minutes per day
print("\n" + "=" * 60)
print("TV WATCHING SPECIFICALLY (code 1203, ages 25-54)")
print("=" * 60)
tv_min = con.execute("""
    WITH person_tv AS (
        SELECT CASEID, SUM(DURATION) as tv_min, MAX(CAST(WT06 AS DOUBLE)) as wt
        FROM 'data/atus_ipums.parquet'
        WHERE AGE BETWEEN 25 AND 54
          AND ACTIVITY // 100 = 1203
        GROUP BY CASEID
    )
    SELECT 
        SUM(tv_min * wt) / SUM(wt) as avg_tv_min,
        COUNT(*) as n_watchers
    FROM person_tv
""").df()
print(f"  TV watching: {tv_min['avg_tv_min'].iloc[0]:.0f} min/day among watchers ({tv_min['avg_tv_min'].iloc[0]/60:.1f} hrs)")

# 5. Hours per year calculation
tv_daily = df3[df3['activity_cat'] == 'TV & Leisure']['avg_minutes'].iloc[0]
print(f"\n  TV & Leisure daily: {tv_daily:.0f} min = {tv_daily/60:.1f} hrs")
print(f"  TV & Leisure yearly: {tv_daily * 365 / 60:.0f} hrs = {tv_daily * 365 / 60 / 24:.0f} full days")

# 6. Compare TV time to other key activities
print("\n" + "=" * 60)
print("KEY COMPARISONS")
print("=" * 60)
for act in ['Work', 'Childcare', 'Sports & Exercise', 'Socializing', 'Religious', 'Volunteering']:
    if act in df3['activity_cat'].values:
        mins = df3[df3['activity_cat'] == act]['avg_minutes'].iloc[0]
        ratio = tv_daily / mins if mins > 0 else float('inf')
        print(f"  TV & Leisure vs {act}: {tv_daily:.0f} vs {mins:.0f} min/day ({ratio:.1f}x more TV)")

# 7. What's the MOST meaningful activity? What's the LEAST?
print("\n" + "=" * 60)
print("MEANING EXTREMES (ages 25-54)")
print("=" * 60)
most_meaningful = df.iloc[0]
least_meaningful = df.iloc[-1]
print(f"  Most meaningful: {most_meaningful['activity_cat']} ({most_meaningful['mean_meaning']:.2f})")
print(f"  Least meaningful: {least_meaningful['activity_cat']} ({least_meaningful['mean_meaning']:.2f})")
tv_meaning = df[df['activity_cat'] == 'TV & Leisure']['mean_meaning'].iloc[0]
tv_happy = df[df['activity_cat'] == 'TV & Leisure']['mean_happy'].iloc[0]
print(f"  TV & Leisure: meaning={tv_meaning:.2f}, happiness={tv_happy:.2f}")

# 8. How does TV rank in happiness vs meaning?
print("\n" + "=" * 60)
print("TV RANK IN HAPPINESS VS MEANING")
print("=" * 60)
df_h = df.sort_values('mean_happy', ascending=False).reset_index(drop=True)
df_m = df.sort_values('mean_meaning', ascending=False).reset_index(drop=True)
tv_h_rank = df_h[df_h['activity_cat'] == 'TV & Leisure'].index[0] + 1
tv_m_rank = df_m[df_m['activity_cat'] == 'TV & Leisure'].index[0] + 1
n_acts = len(df)
print(f"  TV happiness rank: {tv_h_rank}/{n_acts}")
print(f"  TV meaning rank: {tv_m_rank}/{n_acts}")

# 9. What fraction of waking time is TV for different groups?
print("\n" + "=" * 60)
print("TV TIME BY DEMOGRAPHICS (ages 25-54)")
print("=" * 60)
for demo_label, demo_filter in [
    ("Parents", "AGEYCHILD < 999"),
    ("Non-parents", "AGEYCHILD >= 999"),
    ("Men", "SEX = 1"),
    ("Women", "SEX = 2"),
    ("College+", "EDUC >= 40"),
    ("No college", "EDUC < 40"),
]:
    result = con.execute(f"""
        WITH person_tv AS (
            SELECT CASEID, 
                   SUM(CASE WHEN ACTIVITY // 100 IN (1203, 1204, 1205, 1299) THEN DURATION ELSE 0 END) as tv_min,
                   SUM(CASE WHEN ACTIVITY // 10000 != 1 THEN DURATION ELSE 0 END) as waking_min,
                   MAX(CAST(WT06 AS DOUBLE)) as wt
            FROM 'data/atus_ipums.parquet'
            WHERE AGE BETWEEN 25 AND 54 AND {demo_filter}
            GROUP BY CASEID
        )
        SELECT 
            SUM(tv_min * wt) / SUM(wt) as avg_tv,
            SUM(waking_min * wt) / SUM(wt) as avg_waking,
            COUNT(*) as n
        FROM person_tv
    """).df()
    avg_tv = result['avg_tv'].iloc[0]
    avg_wk = result['avg_waking'].iloc[0]
    print(f"  {demo_label:15s}  {avg_tv:.0f} min/day ({avg_tv/60:.1f} hrs)  {avg_tv/avg_wk*100:.1f}% of waking  n={int(result['n'].iloc[0])}")

# 10. Happiness and meaning gap: what if people replaced TV with something else?
print("\n" + "=" * 60)
print("COUNTERFACTUAL: WHAT IF TV TIME WENT TO OTHER ACTIVITIES?")
print("=" * 60)
tv_time_share = df[df['activity_cat'] == 'TV & Leisure']['total_wt'].iloc[0] / df['total_wt'].sum()
overall_happy = (df['mean_happy'] * df['total_wt']).sum() / df['total_wt'].sum()
overall_meaning = (df['mean_meaning'] * df['total_wt']).sum() / df['total_wt'].sum()
non_tv = df[df['activity_cat'] != 'TV & Leisure']
non_tv_happy = (non_tv['mean_happy'] * non_tv['total_wt']).sum() / non_tv['total_wt'].sum()
non_tv_meaning = (non_tv['mean_meaning'] * non_tv['total_wt']).sum() / non_tv['total_wt'].sum()
print(f"  Overall happiness (excl sleep): {overall_happy:.2f}")
print(f"  Overall meaning (excl sleep): {overall_meaning:.2f}")
print(f"  Non-TV happiness: {non_tv_happy:.2f}")
print(f"  Non-TV meaning: {non_tv_meaning:.2f}")
print(f"  TV happiness: {tv_happy:.2f}")
print(f"  TV meaning: {tv_meaning:.2f}")
print(f"  If TV time → avg non-TV activities:")
print(f"    Happiness gain: {(non_tv_happy - tv_happy) * tv_time_share:.3f}")
print(f"    Meaning gain: {(non_tv_meaning - tv_meaning) * tv_time_share:.3f}")
