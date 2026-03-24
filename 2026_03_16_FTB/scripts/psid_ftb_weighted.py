"""
PSID FTB analysis — weighted, excluding Latino supplement.
Uses PSID longitudinal individual weights to account for SEO oversample.
Tracks household heads across waves, finds first rent→own transition.
Outputs weighted median FTB age with bootstrap 90% CIs.

IMPORTANT: Uses verified unique family ID columns (fam_id_cols dict).
The previous auto-detection approach picked non-unique columns (e.g. AGE_1)
in some years, causing many-to-many joins and inflated sample sizes.
"""
import duckdb, json, os, numpy as np

con = duckdb.connect()
XY = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/individual/cross_year.parquet'
FAM = '/Users/azizsunderji/Dropbox/Home Economics/Data/PSID/parquet/family'

# Cross-year individual file: year → (interview_num_col, age_col, relation_col)
year_map = {
    1968: ('ER30001','ER30004','ER30003'),
    1969: ('ER30020','ER30023','ER30022'),
    1970: ('ER30043','ER30046','ER30045'),
    1971: ('ER30067','ER30070','ER30069'),
    1972: ('ER30091','ER30094','ER30093'),
    1973: ('ER30117','ER30120','ER30119'),
    1974: ('ER30138','ER30141','ER30140'),
    1975: ('ER30160','ER30163','ER30162'),
    1976: ('ER30188','ER30191','ER30190'),
    1977: ('ER30217','ER30220','ER30219'),
    1978: ('ER30246','ER30249','ER30248'),
    1979: ('ER30283','ER30286','ER30285'),
    1980: ('ER30313','ER30316','ER30315'),
    1981: ('ER30343','ER30346','ER30345'),
    1982: ('ER30373','ER30376','ER30375'),
    1983: ('ER30399','ER30402','ER30401'),
    1984: ('ER30429','ER30432','ER30431'),
    1985: ('ER30463','ER30466','ER30465'),
    1986: ('ER30498','ER30501','ER30500'),
    1987: ('ER30535','ER30538','ER30537'),
    1988: ('ER30570','ER30573','ER30572'),
    1989: ('ER30606','ER30609','ER30608'),
    1990: ('ER30642','ER30645','ER30644'),
    1991: ('ER30689','ER30692','ER30691'),
    1992: ('ER30733','ER30736','ER30735'),
    1993: ('ER30806','ER30809','ER30808'),
    1994: ('ER33101','ER33104','ER33103'),
    1995: ('ER33201','ER33204','ER33203'),
    1996: ('ER33301','ER33304','ER33303'),
    1997: ('ER33401','ER33404','ER33403'),
    1999: ('ER33501','ER33504','ER33503'),
    2001: ('ER33601','ER33604','ER33603'),
    2003: ('ER33701','ER33704','ER33703'),
    2005: ('ER33801','ER33804','ER33803'),
    2007: ('ER33901','ER33904','ER33903'),
    2009: ('ER34001','ER34004','ER34003'),
    2011: ('ER34101','ER34104','ER34103'),
    2013: ('ER34201','ER34204','ER34203'),
    2015: ('ER34301','ER34305','ER34303'),
    2017: ('ER34501','ER34504','ER34503'),
    2019: ('ER34701','ER34704','ER34703'),
    2021: ('ER34901','ER34904','ER34903'),
    2023: ('ER35101','ER35104','ER35103'),
}

# Family file: year → own_rent variable (1=own, 5=rent)
own_rent_vars = {
    1968:'V103', 1969:'V593', 1970:'V1264', 1971:'V1967', 1972:'V2566',
    1973:'V3108', 1974:'V3522', 1975:'V3939', 1976:'V4450', 1977:'V5364',
    1978:'V5864', 1979:'V6479', 1980:'V7084', 1981:'V7675', 1982:'V8364',
    1983:'V8974', 1984:'V10437', 1985:'V11618', 1986:'V13023', 1987:'V14126',
    1988:'V15140', 1989:'V16641', 1990:'V18072', 1991:'V19372', 1992:'V20672',
    1993:'V22427', 1994:'ER2032', 1995:'ER5031', 1996:'ER7031', 1997:'ER10035',
    1999:'ER13040', 2001:'ER17043', 2003:'ER21042', 2005:'ER25028',
    2007:'ER36028', 2009:'ER42029', 2011:'ER47329', 2013:'ER53029',
    2015:'ER60030', 2017:'ER66030', 2019:'ER72030', 2021:'ER78031',
    2023:'ER82032',
}

# Individual longitudinal weight variables by year
weight_vars = {
    1968:'ER30019', 1969:'ER30042', 1970:'ER30066', 1971:'ER30090',
    1972:'ER30116', 1973:'ER30137', 1974:'ER30159', 1975:'ER30187',
    1976:'ER30216', 1977:'ER30245', 1978:'ER30282', 1979:'ER30312',
    1980:'ER30342', 1981:'ER30372', 1982:'ER30398', 1983:'ER30428',
    1984:'ER30462', 1985:'ER30497', 1986:'ER30534', 1987:'ER30569',
    1988:'ER30605', 1989:'ER30641', 1990:'ER30688', 1991:'ER30732',
    1992:'ER30805', 1993:'ER30866',
    1994:'ER33119', 1995:'ER33275', 1996:'ER33318',
    1997:'ER33430', 1999:'ER33546', 2001:'ER33637', 2003:'ER33740',
    2005:'ER33848', 2007:'ER33950', 2009:'ER34045', 2011:'ER34154',
    2013:'ER34268', 2015:'ER34413', 2017:'ER34650', 2019:'ER34863',
    2021:'ER35064', 2023:'ER35264',
}

# Verified unique family file interview number columns
# (auto-detection was picking non-unique cols like AGE_1, causing many-to-many joins)
fam_id_cols = {
    1968:'V3', 1969:'V1015', 1970:'V1102', 1971:'V1802', 1972:'V2402',
    1973:'V3002', 1974:'V3402', 1975:'V3802', 1976:'V4302', 1977:'V5202',
    1978:'V5702', 1979:'V6302', 1980:'V6902', 1981:'V7502', 1982:'V8202',
    1983:'V8802', 1984:'V10002', 1985:'V11102', 1986:'V12502', 1987:'V13702',
    1988:'V14802', 1989:'V16302', 1990:'V17702', 1991:'V19002', 1992:'V20302',
    1993:'V21602', 1994:'ER2002', 1995:'ER5002', 1996:'ER7002', 1997:'ER10002',
    1999:'ER13002', 2001:'ER17002', 2003:'ER21002', 2005:'ER25002',
    2007:'ER36002', 2009:'ER42002', 2011:'ER47302', 2013:'ER53002',
    2015:'ER60002', 2017:'ER66002', 2019:'ER72002', 2021:'ER78002',
    2023:'ER82002',
}

xy_cols = set(c[0] for c in con.execute(
    f'SELECT column_name FROM (DESCRIBE SELECT * FROM "{XY}")').fetchall())

# Verify all weight vars exist
missing = [(yr, wv) for yr, wv in weight_vars.items() if wv not in xy_cols]
if missing:
    print(f"MISSING weight vars: {missing}")
else:
    print("All weight variables found.")

# Build person-year-tenure panel
con.execute('CREATE TABLE person_tenure (person_key VARCHAR, year INT, age INT, own_rent INT, weight DOUBLE)')

print("\nBuilding panel (excluding Latino supplement, with weights)...")
for year in sorted(year_map.keys()):
    int_col, age_col, rel_col = year_map[year]
    own_var = own_rent_vars.get(year)
    wt_var = weight_vars.get(year)
    fid = fam_id_cols.get(year)
    if not own_var or not wt_var or not fid or wt_var not in xy_cols:
        continue
    fam_path = f'{FAM}/{year}.parquet'
    if not os.path.exists(fam_path):
        continue
    if int_col not in xy_cols or age_col not in xy_cols:
        continue
    fam_cols_set = set(c[0] for c in con.execute(
        f'SELECT column_name FROM (DESCRIBE SELECT * FROM "{fam_path}")').fetchall())
    if own_var not in fam_cols_set or fid not in fam_cols_set:
        continue

    # Head relation code: 1 for 1968-1982, 10 for 1983+
    head_code = 1 if year <= 1982 else 10

    try:
        con.execute(f'''
            INSERT INTO person_tenure
            SELECT
                CAST(xy."ER30001" AS VARCHAR) || '_' || CAST(xy."ER30002" AS VARCHAR),
                {year},
                CAST(xy."{age_col}" AS INT),
                CAST(fam."{own_var}" AS INT),
                CAST(xy."{wt_var}" AS DOUBLE)
            FROM "{XY}" xy
            JOIN "{fam_path}" fam ON CAST(xy."{int_col}" AS INT) = CAST(fam."{fid}" AS INT)
            WHERE CAST(xy."{int_col}" AS INT) > 0
              AND CAST(xy."{age_col}" AS INT) BETWEEN 18 AND 85
              AND CAST(xy."{rel_col}" AS INT) = {head_code}
              AND CAST(xy."ER30001" AS INT) NOT BETWEEN 7001 AND 9308
        ''')
        n = con.execute(f"SELECT COUNT(*) FROM person_tenure WHERE year={year}").fetchone()[0]
        nw = con.execute(f"SELECT COUNT(*) FROM person_tenure WHERE year={year} AND weight > 0").fetchone()[0]
        print(f"  {year}: {n} heads ({nw} with positive weight)")
    except Exception as e:
        print(f"  {year}: error - {e}")

# Find FTB transitions (first rent→own)
print("\nFinding rent→own transitions...")
transitions_df = con.execute('''
    WITH first_rent AS (
        SELECT person_key, MIN(year) as first_rent_year
        FROM person_tenure WHERE own_rent = 5
        GROUP BY person_key
    ),
    first_own AS (
        SELECT person_key, MIN(year) as first_own_year
        FROM person_tenure WHERE own_rent = 1
        GROUP BY person_key
    )
    SELECT DISTINCT ON (fo.person_key) fo.person_key, fo.first_own_year,
        f.age as age_at_transition, f.weight
    FROM first_own fo
    JOIN first_rent fr ON fo.person_key = fr.person_key
    JOIN person_tenure f ON f.person_key = fo.person_key AND f.year = fo.first_own_year
    WHERE fo.first_own_year > fr.first_rent_year
      AND f.age BETWEEN 18 AND 75
      AND f.weight > 0
''').fetchdf()

print(f"Total transitions: {len(transitions_df):,}")


def weighted_median(values, weights):
    """Compute weighted median: sort by value, cumulate weights, find 50th percentile."""
    idx = np.argsort(values)
    sv, sw = values[idx], weights[idx]
    cum = np.cumsum(sw)
    return float(sv[np.searchsorted(cum, cum[-1] / 2.0)])


def weighted_bootstrap_ci(values, weights, n_boot=1000, alpha=0.10):
    """Bootstrap 90% CI for weighted median."""
    np.random.seed(42)
    n = len(values)
    bm = []
    for _ in range(n_boot):
        i = np.random.choice(n, size=n, replace=True)
        bm.append(weighted_median(values[i], weights[i]))
    return float(np.percentile(bm, 100 * alpha / 2)), float(np.percentile(bm, 100 * (1 - alpha / 2)))


# Compute weighted medians with CIs
results = []
for year in sorted(transitions_df['first_own_year'].unique()):
    mask = transitions_df['first_own_year'] == year
    ages = transitions_df.loc[mask, 'age_at_transition'].values.astype(float)
    wts = transitions_df.loc[mask, 'weight'].values.astype(float)
    if len(ages) < 10:
        continue
    med = weighted_median(ages, wts)
    ci_lo, ci_hi = weighted_bootstrap_ci(ages, wts)
    results.append({
        'year': int(year), 'median': med,
        'ci_lo': ci_lo, 'ci_hi': ci_hi,
        'n': int(len(ages))
    })
    print(f"  {int(year)}: median={med:.1f}, CI=[{ci_lo:.1f}, {ci_hi:.1f}], n={len(ages)}")

outpath = '/Users/azizsunderji/Dropbox/Home Economics/2026_03_16_FTB/data/psid_ftb_heads_ci.json'
with open(outpath, 'w') as f:
    json.dump(results, f, indent=2)
print(f"\nSaved {len(results)} years to {outpath}")
con.close()
