import duckdb
import numpy as np

con = duckdb.connect()

# Activity mapping
activity_map = """
    CASE
        WHEN ACTIVITY // 10000 = 1 THEN 'Sleep & Grooming'
        WHEN ACTIVITY // 100 IN (101, 102) THEN 'Sleep'
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

base_filter = "AGE BETWEEN 25 AND 54 AND DAY BETWEEN 2 AND 6 AND EMPSTAT IN (1,2)"

# ============================
# 1. Total childcare minutes/day for parents of young kids (AGEYCHILD <= 5)
# ============================
print("=== 1. CHILDCARE MINUTES PER DAY ===")
r = con.execute(f"""
    SELECT 
        CASE WHEN AGEYCHILD <= 5 THEN 'parent' ELSE 'nonparent' END as grp,
        SUM(CASE WHEN ACTIVITY // 10000 IN (3, 4, 10) THEN DURATION * CAST(WT06 AS DOUBLE) ELSE 0 END) / SUM(DISTINCT CAST(WT06 AS DOUBLE)) as childcare_min_per_day
    FROM 'data/atus_ipums.parquet'
    WHERE {base_filter} AND (AGEYCHILD <= 5 OR AGEYCHILD >= 999)
    GROUP BY grp
""").df()
print(r)

# Better approach: per-person childcare minutes, then weighted average
r2 = con.execute(f"""
    WITH person_childcare AS (
        SELECT 
            CASEID,
            MAX(CAST(WT06 AS DOUBLE)) as wt,
            MAX(AGEYCHILD) as ageychild,
            SUM(CASE WHEN ACTIVITY // 10000 IN (3, 4, 10) THEN DURATION ELSE 0 END) as childcare_min
        FROM 'data/atus_ipums.parquet'
        WHERE {base_filter} AND (AGEYCHILD <= 5 OR AGEYCHILD >= 999)
        GROUP BY CASEID
    )
    SELECT 
        CASE WHEN ageychild <= 5 THEN 'parent' ELSE 'nonparent' END as grp,
        SUM(childcare_min * wt) / SUM(wt) as avg_childcare_min,
        COUNT(*) as n
    FROM person_childcare
    GROUP BY grp
""").df()
print(r2)

# ============================
# 2. Time-of-day analysis: what do parents trade in morning vs evening?
# Morning = 4am-9am, Evening = 5pm-9pm
# ============================
print("\n=== 2. MORNING VS EVENING TRADE-OFFS ===")
r3 = con.execute(f"""
    WITH activities AS (
        SELECT
            CASE
                WHEN ACTIVITY // 100 IN (101, 102) THEN 'Sleep'
                WHEN ACTIVITY // 10000 = 1 THEN 'Grooming'
                WHEN ACTIVITY // 10000 IN (3, 4, 10) THEN 'Childcare'
                WHEN ACTIVITY // 10000 = 5 THEN 'Work'
                WHEN ACTIVITY // 100 IN (1203, 1204, 1205, 1299) THEN 'TV & Leisure'
                WHEN ACTIVITY // 10000 IN (2, 9) THEN 'Housework'
                WHEN ACTIVITY // 10000 = 18 THEN 'Travel'
                WHEN ACTIVITY // 10000 = 11 THEN 'Eating & Drinking'
                WHEN ACTIVITY // 100 IN (1201, 1202) THEN 'Socializing'
                ELSE 'Other'
            END as act_cat,
            (EXTRACT(HOUR FROM CAST(START AS TIME)) * 60 + EXTRACT(MINUTE FROM CAST(START AS TIME)))::INT as start_min,
            DURATION::INT as dur,
            CAST(WT06 AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD <= 5 THEN 1 ELSE 0 END as is_parent
        FROM 'data/atus_ipums.parquet'
        WHERE {base_filter} AND (AGEYCHILD <= 5 OR AGEYCHILD >= 999)
    ),
    exploded AS (
        SELECT
            act_cat,
            ((start_min + slot_offset) % 1440) as minute_of_day,
            wt,
            is_parent
        FROM activities, UNNEST(GENERATE_SERIES(0, dur - 1, 1)) as t(slot_offset)
    ),
    binned AS (
        SELECT
            act_cat,
            CASE 
                WHEN minute_of_day >= 240 AND minute_of_day < 540 THEN 'morning_4am_9am'
                WHEN minute_of_day >= 1020 AND minute_of_day < 1320 THEN 'evening_5pm_10pm'
                ELSE 'other'
            END as period,
            wt,
            is_parent
        FROM exploded
    )
    SELECT 
        period,
        act_cat,
        is_parent,
        SUM(wt) as total_wt
    FROM binned
    WHERE period IN ('morning_4am_9am', 'evening_5pm_10pm')
    GROUP BY period, act_cat, is_parent
    ORDER BY period, act_cat, is_parent
""").df()

# Compute shares
for period in ['morning_4am_9am', 'evening_5pm_10pm']:
    print(f"\n--- {period} ---")
    pdf = r3[r3['period'] == period]
    for is_p in [0, 1]:
        sub = pdf[pdf['is_parent'] == is_p]
        total = sub['total_wt'].sum()
        sub = sub.copy()
        sub['share'] = sub['total_wt'] / total * 100
        label = 'Parent' if is_p == 1 else 'Non-parent'
        print(f"\n{label}:")
        for _, row in sub.sort_values('share', ascending=False).iterrows():
            print(f"  {row['act_cat']:20s} {row['share']:5.1f}%")
    
    # Differences
    print(f"\nDifference (parent - nonparent):")
    parent_sub = pdf[pdf['is_parent'] == 1].set_index('act_cat')
    nonparent_sub = pdf[pdf['is_parent'] == 0].set_index('act_cat')
    parent_total = parent_sub['total_wt'].sum()
    nonparent_total = nonparent_sub['total_wt'].sum()
    
    all_cats = set(parent_sub.index) | set(nonparent_sub.index)
    diffs = {}
    for cat in sorted(all_cats):
        p_share = parent_sub.loc[cat, 'total_wt'] / parent_total * 100 if cat in parent_sub.index else 0
        np_share = nonparent_sub.loc[cat, 'total_wt'] / nonparent_total * 100 if cat in nonparent_sub.index else 0
        diffs[cat] = p_share - np_share
    
    for cat, diff in sorted(diffs.items(), key=lambda x: abs(x[1]), reverse=True):
        print(f"  {cat:20s} {diff:+5.1f}pp  ({diff * 0.6 * (5 if period == 'morning_4am_9am' else 5):+.0f} min over {5}hrs)")

# ============================  
# 3. Cumulative sleep deficit at key times
# ============================
print("\n=== 3. CUMULATIVE SLEEP DEFICIT ===")
n_bins = 144
r4 = con.execute(f"""
    WITH activities AS (
        SELECT
            CASE WHEN ACTIVITY // 100 IN (101, 102) THEN 'Sleep' ELSE 'Other' END as act_cat,
            (EXTRACT(HOUR FROM CAST(START AS TIME)) * 60 + EXTRACT(MINUTE FROM CAST(START AS TIME)))::INT as start_min,
            DURATION::INT as dur,
            CAST(WT06 AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD <= 5 THEN 1 ELSE 0 END as is_parent
        FROM 'data/atus_ipums.parquet'
        WHERE {base_filter} AND (AGEYCHILD <= 5 OR AGEYCHILD >= 999)
    ),
    exploded AS (
        SELECT
            act_cat,
            ((start_min + slot_offset) % 1440) // 10 as bin_idx,
            wt,
            is_parent
        FROM activities, UNNEST(GENERATE_SERIES(0, dur - 1, 10)) as t(slot_offset)
    )
    SELECT bin_idx, is_parent, act_cat, SUM(wt) as total_wt
    FROM exploded
    WHERE act_cat = 'Sleep'
    GROUP BY bin_idx, is_parent, act_cat
""").df()

total_r4 = con.execute(f"""
    WITH activities AS (
        SELECT
            (EXTRACT(HOUR FROM CAST(START AS TIME)) * 60 + EXTRACT(MINUTE FROM CAST(START AS TIME)))::INT as start_min,
            DURATION::INT as dur,
            CAST(WT06 AS DOUBLE) as wt,
            CASE WHEN AGEYCHILD <= 5 THEN 1 ELSE 0 END as is_parent
        FROM 'data/atus_ipums.parquet'
        WHERE {base_filter} AND (AGEYCHILD <= 5 OR AGEYCHILD >= 999)
    ),
    exploded AS (
        SELECT
            ((start_min + slot_offset) % 1440) // 10 as bin_idx,
            wt,
            is_parent
        FROM activities, UNNEST(GENERATE_SERIES(0, dur - 1, 10)) as t(slot_offset)
    )
    SELECT bin_idx, is_parent, SUM(wt) as total_wt
    FROM exploded
    GROUP BY bin_idx, is_parent
""").df()

# Build arrays
totals = {0: np.zeros(n_bins), 1: np.zeros(n_bins)}
sleep_wt = {0: np.zeros(n_bins), 1: np.zeros(n_bins)}

for _, row in total_r4.iterrows():
    totals[int(row['is_parent'])][int(row['bin_idx'])] = row['total_wt']

for _, row in r4.iterrows():
    sleep_wt[int(row['is_parent'])][int(row['bin_idx'])] = row['total_wt']

# Reorder to start at 4am
reorder = list(range(24, 144)) + list(range(0, 24))

parent_sleep_share = np.where(totals[1] > 0, sleep_wt[1] / totals[1], 0)[reorder]
nonparent_sleep_share = np.where(totals[0] > 0, sleep_wt[0] / totals[0], 0)[reorder]
sleep_diff = (parent_sleep_share - nonparent_sleep_share) * 100  # pp

# Cumulative sleep deficit in minutes
cumulative = np.cumsum(sleep_diff / 100 * 10)  # each bin = 10 min

# Print at key times
for label, bin_from_4am in [('6am', 12), ('8am', 24), ('10am', 36), ('12pm', 48), ('3pm', 66), ('5pm', 78), ('8pm', 96), ('10pm', 108), ('midnight', 120), ('2am', 132), ('4am', 143)]:
    print(f"  {label:10s}: cumulative sleep deficit = {cumulative[bin_from_4am]:.1f} min")

print(f"\n  Peak deficit: {cumulative.min():.1f} min at bin {np.argmin(cumulative)} (={4 + np.argmin(cumulative)*10//60}:{np.argmin(cumulative)*10%60:02d})")
print(f"  End-of-day deficit: {cumulative[-1]:.1f} min")

# ============================
# 4. Sleep deficit for parents of <1 year olds specifically
# ============================
print("\n=== 4. BABY PARENT (<1yr) SLEEP DEFICIT ===")
r5 = con.execute(f"""
    WITH person_sleep AS (
        SELECT 
            CASEID,
            MAX(CAST(WT06 AS DOUBLE)) as wt,
            MAX(AGEYCHILD) as ageychild,
            SUM(CASE WHEN ACTIVITY // 100 IN (101, 102) THEN DURATION ELSE 0 END) as sleep_min
        FROM 'data/atus_ipums.parquet'
        WHERE {base_filter} AND (AGEYCHILD <= 5 OR AGEYCHILD >= 999)
        GROUP BY CASEID
    )
    SELECT 
        CASE 
            WHEN ageychild = 0 THEN 'baby_0'
            WHEN ageychild = 1 THEN 'toddler_1'
            WHEN ageychild <= 3 THEN 'toddler_2_3'
            WHEN ageychild <= 5 THEN 'preschool_4_5'
            ELSE 'nonparent'
        END as grp,
        SUM(sleep_min * wt) / SUM(wt) as avg_sleep_min,
        COUNT(*) as n
    FROM person_sleep
    GROUP BY grp
    ORDER BY grp
""").df()
print(r5)

# ============================
# 5. Happiness scores for parents by child age
# ============================
print("\n=== 5. HAPPINESS BY CHILD AGE (from WB module) ===")
r6 = con.execute(f"""
    SELECT 
        CASE 
            WHEN AGEYCHILD = 0 THEN 'baby_0'
            WHEN AGEYCHILD = 1 THEN 'toddler_1'
            WHEN AGEYCHILD <= 3 THEN 'toddler_2_3'
            WHEN AGEYCHILD <= 5 THEN 'preschool_4_5'
            ELSE 'nonparent'
        END as grp,
        SUM(CAST(SCHAPPY AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as avg_happiness,
        SUM(CAST(MEANING AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as avg_meaning,
        COUNT(*) as n_activities
    FROM 'data/atus_ipums.parquet'
    WHERE {base_filter} AND (AGEYCHILD <= 5 OR AGEYCHILD >= 999)
        AND SCHAPPY != '96' AND SCHAPPY != '97' AND SCHAPPY != '98' AND SCHAPPY != '99'
        AND MEANING != '96' AND MEANING != '97' AND MEANING != '98' AND MEANING != '99'
        AND CAST(AWBWT AS DOUBLE) > 0
    GROUP BY grp
    ORDER BY grp
""").df()
print(r6)

# Also get overall parent vs nonparent happiness (AGEYCHILD <= 5)
print("\n=== 5b. OVERALL PARENT VS NONPARENT HAPPINESS ===")
r7 = con.execute(f"""
    SELECT 
        CASE WHEN AGEYCHILD <= 5 THEN 'parent' ELSE 'nonparent' END as grp,
        SUM(CAST(SCHAPPY AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as avg_happiness,
        SUM(CAST(MEANING AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as avg_meaning,
        COUNT(DISTINCT CASEID) as n_people,
        COUNT(*) as n_activities
    FROM 'data/atus_ipums.parquet'
    WHERE {base_filter} AND (AGEYCHILD <= 5 OR AGEYCHILD >= 999)
        AND SCHAPPY != '96' AND SCHAPPY != '97' AND SCHAPPY != '98' AND SCHAPPY != '99'
        AND MEANING != '96' AND MEANING != '97' AND MEANING != '98' AND MEANING != '99'
        AND CAST(AWBWT AS DOUBLE) > 0
    GROUP BY grp
""").df()
print(r7)

# ============================
# 6. Total minutes per day by activity for parents vs non-parents
# ============================
print("\n=== 6. TOTAL MINUTES PER DAY BY ACTIVITY ===")
r8 = con.execute(f"""
    WITH person_time AS (
        SELECT 
            CASEID,
            MAX(CAST(WT06 AS DOUBLE)) as wt,
            MAX(AGEYCHILD) as ageychild,
            SUM(CASE WHEN ACTIVITY // 10000 IN (3, 4, 10) THEN DURATION ELSE 0 END) as childcare_min,
            SUM(CASE WHEN ACTIVITY // 100 IN (1203, 1204, 1205, 1299) THEN DURATION ELSE 0 END) as tv_leisure_min,
            SUM(CASE WHEN ACTIVITY // 100 IN (101, 102) THEN DURATION ELSE 0 END) as sleep_min,
            SUM(CASE WHEN ACTIVITY // 10000 = 5 THEN DURATION ELSE 0 END) as work_min,
            SUM(CASE WHEN ACTIVITY // 10000 IN (2, 9) THEN DURATION ELSE 0 END) as housework_min,
            SUM(CASE WHEN ACTIVITY // 10000 = 18 THEN DURATION ELSE 0 END) as travel_min,
            SUM(CASE WHEN ACTIVITY // 10000 = 11 THEN DURATION ELSE 0 END) as eating_min
        FROM 'data/atus_ipums.parquet'
        WHERE {base_filter} AND (AGEYCHILD <= 5 OR AGEYCHILD >= 999)
        GROUP BY CASEID
    )
    SELECT 
        CASE WHEN ageychild <= 5 THEN 'parent' ELSE 'nonparent' END as grp,
        SUM(childcare_min * wt) / SUM(wt) as childcare,
        SUM(tv_leisure_min * wt) / SUM(wt) as tv_leisure,
        SUM(sleep_min * wt) / SUM(wt) as sleep,
        SUM(work_min * wt) / SUM(wt) as work,
        SUM(housework_min * wt) / SUM(wt) as housework,
        SUM(travel_min * wt) / SUM(wt) as travel,
        SUM(eating_min * wt) / SUM(wt) as eating,
        COUNT(*) as n
    FROM person_time
    GROUP BY grp
""").df()
print(r8)
