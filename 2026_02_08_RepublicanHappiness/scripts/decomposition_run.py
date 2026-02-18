import duckdb
import numpy as np

con = duckdb.connect()

activity_map = """
    CASE 
        WHEN ACTIVITY // 10000 = 1 THEN 'Personal Care'
        WHEN ACTIVITY // 10000 = 2 THEN 'Housework'
        WHEN ACTIVITY // 10000 = 3 THEN 'Caring for Others'
        WHEN ACTIVITY // 10000 = 4 THEN 'Childcare'
        WHEN ACTIVITY // 10000 = 5 THEN 'Work'
        WHEN ACTIVITY // 10000 = 6 THEN 'Education'
        WHEN ACTIVITY // 10000 = 7 THEN 'Shopping'
        WHEN ACTIVITY // 10000 = 8 THEN 'Prof. Services'
        WHEN ACTIVITY // 10000 = 9 THEN 'Housework'
        WHEN ACTIVITY // 10000 = 10 THEN 'Childcare'
        WHEN ACTIVITY // 10000 = 11 THEN 'Eating & Drinking'
        WHEN ACTIVITY // 10000 = 12 THEN 'Socializing'
        WHEN ACTIVITY // 10000 = 13 THEN 'Sports & Leisure'
        WHEN ACTIVITY // 10000 = 14 THEN 'Religious'
        WHEN ACTIVITY // 10000 = 15 THEN 'Volunteering'
        WHEN ACTIVITY // 10000 = 16 THEN 'Phone Calls'
        WHEN ACTIVITY // 10000 = 18 THEN 'Travel'
        ELSE 'Other'
    END
"""

for label, age_filter in [('ALL AGES', '1=1'), ('AGES 25-54', 'AGE BETWEEN 25 AND 54')]:
    df = con.execute(f"""
        WITH base AS (
            SELECT 
                CASEID,
                {activity_map} as activity_cat,
                CAST(SCHAPPY AS DOUBLE) as happy,
                CAST(AWBWT AS DOUBLE) as wt,
                CASE WHEN AGEYCHILD < 999 THEN 1 ELSE 0 END as is_parent,
                AGE
            FROM 'data/atus_ipums.parquet'
            WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
              AND {activity_map} != 'Other'
              AND {activity_map} != 'Personal Care'
              AND {age_filter}
        )
        SELECT 
            is_parent,
            activity_cat,
            SUM(wt) as total_wt,
            SUM(happy * wt) / SUM(wt) as mean_happy,
            COUNT(*) as n
        FROM base
        GROUP BY is_parent, activity_cat
    """).df()

    sep = '=' * 60
    print(f"\n{sep}")
    print(f"DECOMPOSITION: {label}")
    print(f"{sep}")
    
    parents = df[df['is_parent']==1].set_index('activity_cat')
    nonparents = df[df['is_parent']==0].set_index('activity_cat')
    
    p_total_wt = parents['total_wt'].sum()
    np_total_wt = nonparents['total_wt'].sum()
    
    activities = sorted(set(parents.index) & set(nonparents.index))
    
    results = []
    for act in activities:
        p_time = parents.loc[act, 'total_wt'] / p_total_wt
        np_time = nonparents.loc[act, 'total_wt'] / np_total_wt
        p_happy = parents.loc[act, 'mean_happy']
        np_happy = nonparents.loc[act, 'mean_happy']
        
        avg_time = (p_time + np_time) / 2
        avg_happy = (p_happy + np_happy) / 2
        
        delta_time = p_time - np_time
        delta_happy = p_happy - np_happy
        
        comp = delta_time * avg_happy
        level = avg_time * delta_happy
        
        results.append({
            'activity': act,
            'p_time': p_time, 'np_time': np_time,
            'p_happy': p_happy, 'np_happy': np_happy,
            'comp': comp, 'level': level,
            'total': comp + level
        })
    
    total_comp = sum(r['comp'] for r in results)
    total_level = sum(r['level'] for r in results)
    total_gap = total_comp + total_level
    
    p_overall = sum(r['p_time'] * r['p_happy'] for r in results)
    np_overall = sum(r['np_time'] * r['np_happy'] for r in results)
    
    print(f"\nParent overall happiness: {p_overall:.4f}")
    print(f"Non-parent overall happiness: {np_overall:.4f}")
    print(f"Gap: {p_overall - np_overall:.4f}")
    print(f"\nComposition effect: {total_comp:.4f}")
    print(f"Level effect: {total_level:.4f}")
    print(f"Total (comp+level): {total_gap:.4f}")
    if abs(total_gap) > 0.0001:
        print(f"Composition share: {total_comp/total_gap*100:.1f}%")
        print(f"Level share: {total_level/total_gap*100:.1f}%")
    
    print(f"\nBy activity (sorted by |total contribution|):")
    for r in sorted(results, key=lambda x: abs(x['total']), reverse=True):
        d_time = r['p_time'] - r['np_time']
        d_happy = r['p_happy'] - r['np_happy']
        print(f"  {r['activity']:20s}  comp={r['comp']:+.4f}  level={r['level']:+.4f}  total={r['total']:+.4f}  Δtime={d_time:+.4f}  Δhappy={d_happy:+.3f}")

    print(f"\n  Sample: Parents {parents['n'].sum():.0f} obs, Non-parents {nonparents['n'].sum():.0f} obs")
