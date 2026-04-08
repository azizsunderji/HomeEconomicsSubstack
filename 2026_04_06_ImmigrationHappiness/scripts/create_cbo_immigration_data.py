import pandas as pd
import os

# CBO Net Immigration Estimates by Category (thousands)
# Source: CBO Demographic Outlook reports (Jan 2024 vintage for 2001-2023, 
# updated with Jan 2025/Sep 2025/Jan 2026 revisions for 2024-2025)
# Originally extracted from Voronoi visualization of CBO data
# Cross-referenced with Brookings Hamilton Project (Edelberg & Watson, March 2024)
# and CBO publication 61879 (Jan 2026), 61390 (Sep 2025), 61735 (Sep 2025)

data = {
    'year': list(range(2001, 2026)),
    'lpr_plus': [
        794, 728, 575, 749, 869, 910, 800, 835, 832, 786,  # 2001-2010
        791, 766, 748, 769, 813, 877, 840, 810, 713, 537,  # 2011-2020
        551, 714, 807, 809, 830  # 2021-2025 (2025 from Jan 2026 CBO)
    ],
    'ina_nonimmigrant': [
        50, 302, 182, 321, 463, 449, -273, -411, 529, 117,  # 2001-2010
        42, -125, -63, 824, 376, -18, 473, -339, -64, 58,  # 2011-2020
        20, 60, 90, 90, -120  # 2021-2025 (2025: reduced by 210k from Jan 2025 proj)
    ],
    'other_foreign_nationals': [
        529, 278, 398, 259, 552, 329, 362, -250, -462, -100,  # 2001-2010
        -104, 13, 132, 46, 289, 26, -213, 200, -234, 213,  # 2011-2020
        600, 1900, 2400, 1800, -290  # 2021-2025 (2024 revised Jan 2025; 2025 from Sep 2025 CBO)
    ],
    'source_vintage': [
        'CBO Jan 2024'] * 20 + [  # 2001-2020 from Jan 2024 Demographic Outlook
        'CBO Jan 2024',  # 2021
        'CBO Jan 2024',  # 2022
        'CBO Jan 2024',  # 2023
        'CBO Jan 2025 (revised)',  # 2024 revised in Jan 2025 outlook
        'CBO Sep 2025 / Jan 2026',  # 2025 from Sep 2025 update
    ]
}

df = pd.DataFrame(data)
df['total_net_immigration'] = df['lpr_plus'] + df['ina_nonimmigrant'] + df['other_foreign_nationals']

# Add notes
notes = {
    'notes': [
        'LPR+ = Lawful Permanent Residents + people eligible to apply for LPR status (asylees, refugees)',
        'INA Nonimmigrant = people admitted as nonimmigrants under the Immigration and Nationality Act (students, temporary workers)',
        'Other Foreign Nationals = people not in first two categories who have not become US citizens or received LPR status',
        'All figures in thousands of people',
        'Years 2001-2020: From CBO Demographic Outlook 2024 to 2054 (January 2024)',
        'Years 2021-2023: CBO projections/estimates from January 2024 report',
        'Year 2024: Revised by CBO in January 2025 Demographic Outlook (OFN revised down from 2.4M to 1.8M)',
        'Year 2025: From CBO September 2025 update (61390) - reflects Trump admin policy effects',
        'CBO Sep 2025 notes OFN at -290k in 2025 (net emigration), INA reduced by 210k from Jan 2025 projection',
        'CBO Jan 2026 (61879): LPR+ projected at 870k in 2026, growing to 930k by 2056',
    ]
}

out_path = "/Users/azizsunderji/Dropbox/Home Economics/2026_04_06_ImmigrationHappiness/data/cbo_net_immigration_by_category.csv"
df.to_csv(out_path, index=False)
print(f"Saved to {out_path}")
print(f"\nShape: {df.shape}")
print(f"\n{df.to_string(index=False)}")

# Also save as Excel with notes sheet
xlsx_path = out_path.replace('.csv', '.xlsx')
with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Net Immigration by Category', index=False)
    pd.DataFrame(notes).to_excel(writer, sheet_name='Notes', index=False)
print(f"\nAlso saved Excel to {xlsx_path}")
