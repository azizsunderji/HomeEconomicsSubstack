import duckdb
con = duckdb.connect()

# Get every unique activity code with counts and happiness, for ages 25-54 WB module
codes = con.execute("""
    SELECT 
        ACTIVITY // 10000 as major,
        ACTIVITY // 100 as subcat,
        ACTIVITY as full_code,
        COUNT(*) as n,
        SUM(CAST(AWBWT AS DOUBLE)) as total_wt,
        SUM(CAST(SCHAPPY AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as mean_happy
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND AGE BETWEEN 25 AND 54
    GROUP BY major, subcat, full_code
    ORDER BY full_code
""").df()

# Also get totals to compute shares
total_wt = codes['total_wt'].sum()

# BLS ATUS major category names
major_names = {
    1: "Personal Care",
    2: "Household Activities",
    3: "Caring for & Helping HH Members",
    4: "Caring for & Helping Non-HH Members",
    5: "Work & Work-Related Activities",
    6: "Education",
    7: "Consumer Purchases (Shopping)",
    8: "Professional & Personal Care Services",
    9: "Household Services (using services)",
    10: "Government Services & Civic Obligations",
    11: "Eating & Drinking",
    12: "Socializing, Relaxing, & Leisure",
    13: "Sports, Exercise, & Recreation",
    14: "Religious & Spiritual Activities",
    15: "Volunteer Activities",
    16: "Telephone Calls",
    18: "Traveling",
}

# BLS subcategory names (comprehensive)
subcat_names = {
    101: "Sleeping",
    102: "Grooming",
    103: "Health-Related Self Care",
    104: "Personal Activities",
    105: "Personal Care Emergencies",
    199: "Personal Care, NEC",
    201: "Housework (laundry, cleaning, sewing)",
    202: "Food & Drink Prep/Cleanup (cooking)",
    203: "Interior Maintenance & Repair",
    204: "Exterior Maintenance & Repair",
    205: "Lawn, Garden, & Houseplants",
    206: "Animals & Pets",
    207: "Vehicles",
    208: "Appliances, Tools, Toys (HH)",
    209: "Household Management",
    299: "Household Activities, NEC",
    301: "Caring for & Helping HH Children",
    302: "Activities Related to HH Children's Education",
    303: "Activities Related to HH Children's Health",
    304: "Caring for HH Adults",
    305: "Helping HH Adults",
    399: "Caring for HH Members, NEC",
    401: "Caring for & Helping Non-HH Children",
    402: "Activities Related to Non-HH Children's Education",
    403: "Activities Related to Non-HH Children's Health",
    404: "Caring for Non-HH Adults",
    405: "Helping Non-HH Adults",
    499: "Caring for Non-HH Members, NEC",
    501: "Working",
    502: "Work-Related Activities",
    503: "Other Income-Generating Activities",
    504: "Job Search & Interviewing",
    599: "Work, NEC",
    601: "Taking Class (for degree/certification)",
    602: "Extracurricular School Activities",
    603: "Research/Homework (for degree)",
    604: "Registration/Administrative",
    605: "Education-Related Activities (personal interest)",
    699: "Education, NEC",
    701: "Shopping (except groceries, gas, food)",
    702: "Researching Purchases",
    703: "Security Procedures Related to Shopping",
    799: "Consumer Purchases, NEC",
    801: "Using Childcare Services",
    802: "Using Financial Services & Banking",
    803: "Using Legal Services",
    804: "Using Medical Services",
    805: "Using Personal Care Services (haircut, spa)",
    806: "Using Real Estate Services",
    807: "Using Veterinary Services",
    899: "Using Prof./Personal Care Services, NEC",
    901: "Using Household Services (cleaning, pest control)",
    902: "Using Home Maint./Repair/Décor Services",
    903: "Using Pet Services (not vet)",
    904: "Using Lawn & Garden Services",
    905: "Using Vehicle Maintenance & Repair Services",
    999: "Using Household Services, NEC",
    1001: "Using Government Services",
    1002: "Civic Obligations & Participation",
    1099: "Government Services, NEC",
    1101: "Eating & Drinking",
    1102: "Waiting for Eating & Drinking",
    1199: "Eating & Drinking, NEC",
    1201: "Socializing & Communicating",
    1202: "Attending/Hosting Social Events",
    1203: "Relaxing & Leisure (TV, reading, thinking)",
    1204: "Arts & Entertainment (attending)",
    1205: "Waiting for Socializing",
    1299: "Socializing, NEC",
    1301: "Participating in Sports/Exercise/Recreation",
    1302: "Attending Sporting/Recreational Events",
    1399: "Sports, NEC",
    1401: "Religious/Spiritual Practice",
    1402: "Religious Education (attending)",
    1403: "Religious/Spiritual Activities, NEC",
    1499: "Religious, NEC",
    1501: "Administrative & Support (volunteering)",
    1502: "Social Service & Care (volunteering)",
    1503: "Indoor & Outdoor Maintenance (volunteering)",
    1504: "Participating in Performance & Cultural",
    1505: "Attending Meetings, Conferences (vol.)",
    1506: "Public Health & Safety (volunteering)",
    1599: "Volunteer Activities, NEC",
    1601: "Telephone Calls (to/from)",
    1602: "Waiting for Phone Calls",
    1699: "Telephone Calls, NEC",
    1801: "Travel Related to Personal Care",
    1802: "Travel Related to Household Activities",
    1803: "Travel Related to Caring for HH Members",
    1804: "Travel Related to Caring for Non-HH Members",
    1805: "Travel Related to Work",
    1806: "Travel Related to Education",
    1807: "Travel Related to Shopping",
    1808: "Travel Related to Using Services",
    1809: "Travel Related to Using HH Services",
    1810: "Travel Related to Using Gov. Services",
    1811: "Travel Related to Eating & Drinking",
    1812: "Travel Related to Socializing & Leisure",
    1813: "Travel Related to Sports & Exercise",
    1814: "Travel Related to Religious/Spiritual",
    1815: "Travel Related to Volunteering",
    1816: "Travel Related to Phone Calls",
    1818: "Security Procedures for Traveling",
    1819: "Travel, NEC",
}

# Print the full hierarchy
current_major = None
current_subcat = None

for _, row in codes.iterrows():
    major = int(row['major'])
    subcat = int(row['subcat'])
    full = int(row['full_code'])
    n = int(row['n'])
    wt = row['total_wt']
    happy = row['mean_happy']
    share = wt / total_wt * 100
    
    if major != current_major:
        current_major = major
        major_rows = codes[codes['major'] == major]
        major_share = major_rows['total_wt'].sum() / total_wt * 100
        print(f"\n{'='*90}")
        print(f"  {major:02d} — {major_names.get(major, 'Unknown')}  [{major_share:.1f}% of waking time]")
        print(f"{'='*90}")
        current_subcat = None
    
    if subcat != current_subcat:
        current_subcat = subcat
        sub_rows = codes[codes['subcat'] == subcat]
        sub_share = sub_rows['total_wt'].sum() / total_wt * 100
        sub_n = sub_rows['n'].sum()
        sub_happy = (sub_rows['total_wt'] * sub_rows['mean_happy']).sum() / sub_rows['total_wt'].sum()
        sub_name = subcat_names.get(subcat, "Unknown")
        print(f"\n    {subcat:04d} — {sub_name}")
        print(f"           {sub_share:.2f}% of time  |  happy: {sub_happy:.2f}  |  n={sub_n}")
    
    # Only print full codes if there are multiple under this subcat
    sub_code_count = len(codes[codes['subcat'] == subcat])
    if sub_code_count > 1 and n >= 5:
        print(f"        {full:06d}   {share:.3f}%  happy={happy:.2f}  n={n}")
