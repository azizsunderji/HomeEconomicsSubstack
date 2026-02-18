import duckdb
con = duckdb.connect()

codes = con.execute("""
    SELECT 
        ACTIVITY as code,
        COUNT(*) as n,
        SUM(CAST(AWBWT AS DOUBLE)) as total_wt,
        SUM(CAST(SCHAPPY AS DOUBLE) * CAST(AWBWT AS DOUBLE)) / SUM(CAST(AWBWT AS DOUBLE)) as mean_happy
    FROM 'data/atus_ipums.parquet'
    WHERE CAST(SCHAPPY AS INT) BETWEEN 0 AND 6
      AND AGE BETWEEN 25 AND 54
    GROUP BY code
    ORDER BY code
""").df()

total_wt = codes['total_wt'].sum()

major_names = {
    1: "Personal Care", 2: "Household Activities",
    3: "Caring for & Helping HH Members", 4: "Caring for & Helping Non-HH Members",
    5: "Work & Work-Related", 6: "Education",
    7: "Consumer Purchases (Shopping)", 8: "Professional & Personal Care Services",
    9: "Household Services", 10: "Government Services & Civic Obligations",
    11: "Eating & Drinking", 12: "Socializing, Relaxing & Leisure",
    13: "Sports, Exercise & Recreation", 14: "Religious & Spiritual",
    15: "Volunteer Activities", 16: "Telephone Calls",
    18: "Traveling", 50: "Data Codes / Unable to Classify"
}

subcat_names = {
    101: "Sleeping", 102: "Grooming", 103: "Health-Related Self Care",
    104: "Personal Activities", 105: "Personal Care Emergencies", 199: "Personal Care NEC",
    201: "Housework", 202: "Food & Drink Prep/Cleanup",
    203: "Interior Maintenance/Repair/Decoration", 204: "Exterior Maintenance/Repair",
    205: "Lawn, Garden & Houseplants", 206: "Animals & Pets",
    207: "Vehicles", 208: "Appliances, Tools & Toys",
    209: "Household & Personal Organization/Planning", 299: "Household Activities NEC",
    301: "Caring for & Helping HH Children",
    302: "HH Children's Education", 303: "HH Children's Health",
    304: "Caring for HH Adults", 305: "Helping HH Adults",
    399: "Caring for HH Members NEC",
    401: "Caring for & Helping Non-HH Children",
    402: "Non-HH Children's Education", 403: "Non-HH Children's Health",
    404: "Caring for Non-HH Adults", 405: "Helping Non-HH Adults",
    499: "Caring for Non-HH Members NEC",
    501: "Working", 502: "Work-Related Activities",
    503: "Other Income-Generating", 504: "Job Search & Interviewing", 599: "Work NEC",
    601: "Taking Class", 602: "Extracurricular", 603: "Research/Homework",
    604: "Registration/Admin", 605: "Personal Interest Education", 699: "Education NEC",
    701: "Shopping", 702: "Researching Purchases", 703: "Security for Shopping", 799: "Shopping NEC",
    801: "Using Childcare Services", 802: "Using Financial Services/Banking",
    803: "Using Legal Services", 804: "Using Medical Services",
    805: "Using Personal Care Services", 806: "Using Real Estate Services",
    807: "Using Veterinary Services", 899: "Using Prof Services NEC",
    901: "Using Household Services", 902: "Using Home Maint Services",
    903: "Using Pet Services", 904: "Using Lawn & Garden Services",
    905: "Using Vehicle Services", 999: "Using HH Services NEC",
    1001: "Using Government Services", 1002: "Civic Obligations & Participation", 1099: "Gov NEC",
    1101: "Eating & Drinking", 1102: "Waiting for Eating & Drinking", 1199: "Eating NEC",
    1201: "Socializing & Communicating", 1202: "Attending/Hosting Social Events",
    1203: "Relaxing & Leisure (TV, reading, relaxing)",
    1204: "Arts & Entertainment (attending)", 1205: "Waiting for Socializing", 1299: "Socializing NEC",
    1301: "Participating in Sports/Exercise/Recreation",
    1302: "Attending Sporting Events", 1399: "Sports NEC",
    1401: "Religious/Spiritual Practice", 1402: "Religious Services",
    1403: "Religious Activities NEC", 1499: "Religious NEC",
    1501: "Administrative (vol)", 1502: "Social Service (vol)",
    1503: "Maintenance (vol)", 1504: "Performance (vol)",
    1505: "Meetings (vol)", 1506: "Public Health/Safety (vol)", 1599: "Volunteering NEC",
    1601: "Telephone Calls", 1602: "Waiting for Calls", 1699: "Telephone NEC",
    1801: "Travel: Personal Care", 1802: "Travel: Household",
    1803: "Travel: HH Members", 1804: "Travel: Non-HH Members",
    1805: "Travel: Work", 1806: "Travel: Education",
    1807: "Travel: Shopping", 1808: "Travel: Prof Services",
    1809: "Travel: HH Services", 1810: "Travel: Gov Services",
    1811: "Travel: Eating & Drinking", 1812: "Travel: Socializing & Leisure",
    1813: "Travel: Sports & Exercise", 1814: "Travel: Religious",
    1815: "Travel: Volunteering", 1816: "Travel: Telephone",
    1818: "Security for Traveling", 1819: "Travel NEC",
}

code_names = {
    10101: "Sleeping", 10102: "Sleeplessness", 10199: "Sleeping NEC",
    10201: "Washing/dressing/grooming", 10299: "Grooming NEC",
    10301: "Health-related self care", 10399: "Health-related self care NEC",
    10401: "Personal/private activities", 10499: "Personal activities NEC",
    10501: "Personal emergencies", 19999: "Personal care NEC",
    20101: "Interior cleaning", 20102: "Laundry", 20103: "Sewing/repairing textiles",
    20104: "Storing interior HH items", 20199: "Housework NEC",
    20201: "Food and drink preparation", 20202: "Food presentation/table setting",
    20203: "Kitchen/food cleanup", 20299: "Food prep NEC",
    20301: "Interior arrangement/decoration", 20302: "Building/repairing furniture",
    20303: "Heating/cooling", 20399: "Interior maintenance NEC",
    20401: "Exterior cleaning", 20402: "Exterior repair/improvements", 20499: "Exterior NEC",
    20501: "Lawn/garden/houseplant care", 20502: "Ponds/pools/hot tubs", 20599: "Lawn NEC",
    20601: "Care for animals/pets (not vet)", 20602: "Walking/exercising/playing with animals",
    20699: "Animals & pets NEC",
    20701: "Vehicle repair/maintenance (by self)", 20799: "Vehicles NEC",
    20801: "Appliance/tool/toy set-up/repair", 20899: "Appliances NEC",
    20901: "Financial management", 20902: "HH & personal organization/planning",
    20903: "HH & personal mail/messages (not email)", 20904: "HH & personal email/messages",
    20999: "HH management NEC", 29999: "Household activities NEC",
    30101: "Physical care for HH children", 30102: "Reading to/with HH children",
    30103: "Playing with HH children", 30104: "Arts and crafts with HH children",
    30105: "Playing sports with HH children", 30106: "Talking with/listening to HH children",
    30107: "Organization & planning for HH children",
    30108: "Looking after HH children (primary)", 30109: "Attending HH children's events",
    30110: "Waiting for/with HH children", 30111: "Picking up/dropping off HH children",
    30112: "Caring for HH children NEC", 30199: "Caring for HH children NEC",
    30201: "Homework (HH children)", 30202: "Meetings & school conferences (HH children)",
    30203: "Home schooling HH children", 30204: "Waiting for HH children school",
    30299: "HH children education NEC",
    30301: "Providing medical care to HH children", 30302: "Obtaining medical care for HH children",
    30303: "Waiting for HH children health care", 30399: "HH children health NEC",
    30401: "Physical care for HH adults", 30402: "Looking after HH adults (primary)",
    30403: "Providing medical care to HH adults", 30404: "Obtaining medical care for HH adults",
    30405: "Waiting for/with HH adults", 30499: "Caring for HH adults NEC",
    30501: "Helping HH adults", 30502: "Organization & planning for HH adults",
    30503: "Picking up/dropping off HH adults", 30504: "Waiting for/with HH adults",
    30599: "Helping HH adults NEC", 39999: "Caring for HH members NEC",
    40101: "Physical care for non-HH children", 40102: "Reading to/with non-HH children",
    40103: "Playing with non-HH children", 40104: "Arts and crafts with non-HH children",
    40105: "Playing sports with non-HH children", 40106: "Talking with/listening to non-HH children",
    40107: "Organization & planning for non-HH children",
    40108: "Looking after non-HH children", 40109: "Attending non-HH children events",
    40110: "Waiting for/with non-HH children", 40111: "Picking up/dropping off non-HH children",
    40112: "Caring for non-HH children NEC", 40199: "Caring for non-HH children NEC",
    40201: "Homework (non-HH children)", 40202: "School conferences (non-HH children)",
    40299: "Non-HH children education NEC",
    40301: "Medical care to non-HH children", 40302: "Obtaining medical care for non-HH children",
    40399: "Non-HH children health NEC",
    40401: "Physical care for non-HH adults", 40402: "Looking after non-HH adults",
    40403: "Providing medical care to non-HH adults", 40404: "Obtaining medical care for non-HH adults",
    40405: "Waiting for/with non-HH adults", 40499: "Caring for non-HH adults NEC",
    40501: "Housework/cooking/shopping for non-HH adults",
    40502: "House/lawn maintenance for non-HH adults",
    40503: "Animal/pet care for non-HH adults",
    40504: "Vehicle/appliance maint for non-HH adults",
    40505: "Financial management for non-HH adults",
    40506: "HH management for non-HH adults",
    40507: "Picking up/dropping off non-HH adults",
    40508: "Waiting for/with non-HH adults", 40599: "Helping non-HH adults NEC",
    49999: "Caring for non-HH members NEC",
    50101: "Work, main job", 50102: "Work, other job(s)",
    50103: "Security procedures as part of job", 50104: "Waiting associated with working",
    50199: "Working NEC",
    50201: "Eating & drinking as part of job", 50202: "Waiting as part of job",
    50299: "Work-related NEC",
    50301: "Income from other jobs", 50399: "Other income-generating NEC",
    50401: "Job search activities", 50403: "Job interviewing",
    50404: "Waiting for job search", 50499: "Job search NEC", 59999: "Work NEC",
    60101: "Taking class for degree", 60102: "Taking class for personal interest",
    60103: "Waiting for class", 60199: "Taking class NEC",
    60201: "Extracurricular club", 60202: "Extracurricular music/performance",
    60203: "Student government", 60299: "Extracurricular NEC",
    60301: "Research/homework for degree", 60302: "Research/homework personal interest",
    60399: "Research/homework NEC",
    60401: "Admin for education", 60499: "Admin education NEC",
    60501: "Personal interest education", 69999: "Education NEC",
    70101: "Shopping", 70102: "Comparison shopping (in store)", 70103: "Buying gas",
    70104: "Shopping (unclassified store)", 70105: "Waiting while shopping", 70199: "Shopping NEC",
    70201: "Online comparison shopping", 70299: "Researching purchases NEC",
    70301: "Security for shopping", 79999: "Shopping NEC",
    80101: "Using childcare services", 80201: "Using financial services/banking",
    80301: "Using legal services",
    80401: "Using medical services", 80402: "Using dental services",
    80403: "Using mental health services", 80499: "Medical services NEC",
    80501: "Using personal care services (haircut, spa)",
    80601: "Real estate services", 80701: "Using veterinary services",
    80899: "Prof/personal services NEC", 89999: "Prof services NEC",
    90101: "Using interior cleaning services", 90102: "Using meal prep services",
    90103: "Using clothing repair/cleaning", 90104: "Waiting for HH services",
    90199: "HH services NEC",
    90201: "Using home maint/repair services", 90202: "Waiting for home maint",
    90299: "Home maint NEC",
    90301: "Using pet services", 90399: "Pet services NEC",
    90401: "Using lawn & garden services",
    90501: "Using vehicle maint services", 90502: "Waiting for vehicle maint",
    90599: "Vehicle services NEC", 99999: "HH services NEC",
    100101: "Using police/fire services", 100102: "Using social services",
    100103: "Obtaining licenses/permits", 100199: "Gov services NEC",
    100201: "Civic obligations (jury duty)", 100202: "Civic participation (voting)",
    100299: "Civic NEC", 109999: "Gov services NEC",
    110101: "Eating and drinking", 110199: "Eating NEC",
    110201: "Waiting for eating & drinking", 110299: "Waiting eating NEC", 119999: "Eating NEC",
    120101: "Socializing and communicating", 120199: "Socializing NEC",
    120201: "Attending/hosting parties/receptions/ceremonies",
    120202: "Attending meetings for personal interest (clubs)",
    120299: "Social events NEC",
    120301: "Relaxing, thinking", 120302: "Tobacco and drug use",
    120303: "Television and movies (at home)", 120304: "Television and movies (in theater)",
    120305: "Listening to/playing music", 120306: "Listening to the radio",
    120307: "Listening to/reading audio content", 120308: "Writing for personal interest",
    120309: "Computer use for leisure (not games)", 120310: "Playing games",
    120311: "Reading for personal interest", 120312: "Arts and crafts as hobby",
    120313: "Collecting as hobby", 120399: "Relaxing & leisure NEC",
    120401: "Attending performing arts", 120402: "Attending museums",
    120403: "Attending movies/film", 120404: "Attending gambling establishments",
    120405: "Security for arts/entertainment", 120499: "Arts & entertainment NEC",
    120501: "Waiting for socializing", 120599: "Waiting socializing NEC",
    129999: "Socializing/leisure NEC",
    130101: "Aerobics", 130102: "Baseball/softball", 130103: "Basketball",
    130104: "Biking", 130105: "Billiards", 130106: "Boating", 130107: "Bowling",
    130108: "Climbing/spelunking", 130109: "Dancing", 130110: "Equestrian sports",
    130111: "Fencing", 130112: "Fishing", 130113: "Football", 130114: "Golfing",
    130115: "Gymnastics", 130116: "Hiking", 130117: "Hockey", 130118: "Hunting",
    130119: "Martial arts", 130120: "Racquet sports", 130121: "Rodeo",
    130122: "Rollerblading", 130123: "Rugby", 130124: "Running",
    130125: "Skiing/ice skating/snowboarding", 130126: "Soccer", 130127: "Softball",
    130128: "Cardiovascular equipment", 130129: "Swimming", 130130: "Tennis",
    130131: "Yoga", 130132: "Volleyball", 130133: "Walking",
    130134: "Water sports", 130135: "Weightlifting", 130136: "Working out (unspecified)",
    130199: "Sports NEC",
    130201: "Attending sporting events", 130202: "Waiting for sporting events",
    130299: "Attending sports NEC", 130301: "Waiting for sports/exercise", 130399: "Sports NEC",
    139999: "Sports NEC",
    140101: "Attending religious services", 140102: "Religious practices",
    140103: "Waiting for religious activities", 140104: "Security for religious",
    140105: "Religious education", 149999: "Religious NEC",
    150101: "Computer use (vol)", 150102: "Organizing & preparing (vol)",
    150103: "Reading (vol)", 150104: "Telephone calls (vol)", 150105: "Writing (vol)",
    150106: "Fundraising (vol)", 150199: "Admin (vol) NEC",
    150201: "Food prep/distribution (vol)", 150202: "Collecting/delivering (vol)",
    150203: "Providing care (vol)", 150204: "Teaching/training (vol)",
    150205: "Counseling (vol)", 150299: "Social service (vol) NEC",
    150301: "Building/repair (vol)", 150302: "Cleaning (vol)", 150399: "Maint (vol) NEC",
    150401: "Performing (vol)", 150402: "Serving at events (vol)", 150499: "Performance (vol) NEC",
    150501: "Attending meetings (vol)", 150599: "Meetings (vol) NEC",
    150601: "Public health (vol)", 150602: "Public safety (vol)", 150699: "Public health (vol) NEC",
    159999: "Volunteering NEC",
    160101: "Telephone calls (to/from)", 160102: "Waiting for phone calls",
    160199: "Telephone NEC", 169999: "Telephone NEC",
    180101: "Travel: personal care",
    180201: "Travel: housework", 180202: "Travel: HH shopping",
    180280: "Travel: household NEC",
    180301: "Travel: caring for HH children", 180302: "Travel: caring for HH adults",
    180303: "Travel: helping HH adults", 180380: "Travel: HH members NEC",
    180401: "Travel: caring for non-HH children", 180402: "Travel: caring for non-HH adults",
    180403: "Travel: helping non-HH adults", 180480: "Travel: non-HH NEC",
    180501: "Travel: working", 180502: "Travel: work-related",
    180503: "Travel: income-generating", 180504: "Travel: job search",
    180580: "Travel: work NEC",
    180601: "Travel: education", 180680: "Travel: education NEC",
    180701: "Travel: grocery shopping", 180702: "Travel: gas",
    180703: "Travel: shopping (non-grocery)", 180704: "Travel: comparison shopping",
    180780: "Travel: shopping NEC",
    180801: "Travel: childcare services", 180802: "Travel: financial services",
    180803: "Travel: legal services", 180804: "Travel: medical/dental",
    180805: "Travel: personal care services", 180806: "Travel: real estate",
    180807: "Travel: veterinary", 180880: "Travel: services NEC",
    180901: "Travel: HH services", 180902: "Travel: home maint",
    180903: "Travel: pet services", 180904: "Travel: lawn/garden",
    180905: "Travel: vehicle services", 180980: "Travel: HH services NEC",
    181001: "Travel: gov services", 181002: "Travel: civic",
    181080: "Travel: gov NEC",
    181101: "Travel: eating & drinking", 181180: "Travel: eating NEC",
    181201: "Travel: socializing", 181202: "Travel: social events",
    181203: "Travel: relaxing/leisure", 181204: "Travel: arts & entertainment",
    181280: "Travel: socializing NEC",
    181301: "Travel: exercise", 181302: "Travel: attending sports",
    181380: "Travel: sports NEC",
    181401: "Travel: religious", 181480: "Travel: religious NEC",
    181501: "Travel: volunteering", 181580: "Travel: volunteering NEC",
    181601: "Travel: telephone",
    181801: "Security for traveling", 181899: "Security NEC",
    189999: "Travel NEC",
    500101: "Unable to code", 500103: "Interviewer coding error",
    500105: "Uncodable", 500106: "NEC", 500107: "NEC",
}

lines = []
lines.append("COMPLETE ATUS ACTIVITY CODE HIERARCHY")
lines.append("Ages 25-54, Well-Being Module (2010, 2012, 2013, 2021)")
lines.append(f"Total: {len(codes)} unique 6-digit codes, {codes['n'].sum():,} observations")
lines.append("")

current_major = None
current_subcat = None

for _, row in codes.iterrows():
    code = int(row['code'])
    major = code // 10000
    subcat = code // 100
    n = int(row['n'])
    wt = row['total_wt']
    happy = row['mean_happy']
    share = wt / total_wt * 100

    if major != current_major:
        current_major = major
        major_rows = codes[codes['code'] // 10000 == major]
        major_share = major_rows['total_wt'].sum() / total_wt * 100
        major_n = major_rows['n'].sum()
        lines.append("")
        lines.append("=" * 100)
        lines.append(f"  {major:02d} — {major_names.get(major, 'Unknown'):50s}  [{major_share:5.1f}% of time, {major_n:,} obs]")
        lines.append("=" * 100)
        current_subcat = None

    if subcat != current_subcat:
        current_subcat = subcat
        sub_rows = codes[codes['code'] // 100 == subcat]
        sub_share = sub_rows['total_wt'].sum() / total_wt * 100
        sub_n = sub_rows['n'].sum()
        sub_happy_wt = (sub_rows['total_wt'] * sub_rows['mean_happy']).sum() / sub_rows['total_wt'].sum()
        sub_name = subcat_names.get(subcat, "")
        lines.append("")
        lines.append(f"    {subcat:04d} — {sub_name:45s}  [{sub_share:5.2f}%, happy={sub_happy_wt:.2f}, n={sub_n:,}]")

    cn = code_names.get(code, "")
    lines.append(f"      {code:06d}  {cn:55s}  {share:6.3f}%  happy={happy:.2f}  n={n:,}")

output = "\n".join(lines)
print(output)

with open('data/atus_activity_hierarchy.txt', 'w') as f:
    f.write(output)
print(f"\n\nSaved to data/atus_activity_hierarchy.txt")
