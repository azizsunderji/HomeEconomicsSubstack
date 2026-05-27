#!/usr/bin/env python3
"""
Parse the Census Bureau 1950 SMA delineation file (50mfips.txt) into a clean CSV.

Source:
  https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/1950/historical-delineation-files/50mfips.txt
  (Standard Metropolitan Areas defined by the Bureau of the Budget, October 13, 1950)

Output: data/sma_1950_counties.csv with columns:
  sma_code            : 4-digit SMA code (1950 definition)
  sma_name            : official SMA title (e.g. "Akron, OH SMA")
  central_cities      : pipe-separated list of central cities parsed from SMA name
  state               : state postal abbrev of the county
  county_fips         : 5-digit county FIPS
  county_name         : county/parish/independent-city name (as in the source)
  is_central_county   : 1 if county contains a central city of the SMA, else 0
  partial_county      : 1 if only part of the county is in the SMA (NE only)
  new_england_towns   : pipe-separated list of MCDs included (NE only)

Central-county designation methodology:
  - For New England SMAs, the source file lists the exact MCDs (cities/towns)
    that comprise each SMA. A county is flagged central when any listed MCD
    name matches the central-city name(s) parsed from the SMA title.
  - For non-New England SMAs (which are county-based in the source file),
    each SMA's central city or cities are mapped to the county that contained
    that city in 1950 using a hand-curated lookup keyed on the 4-digit SMA
    FIPS code from the source file (CENTRAL_COUNTIES_BY_SMA below).

The hand-curated lookup was built by cross-referencing the SMA name against
the standard place-to-county mapping; independent cities (VA, MD-Baltimore)
appear in the source with their own 5-digit "county" FIPS code (e.g. Baltimore
city = 24510; Norfolk city = 51710), and those are used as the central county.
"""

import csv
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SRC = DATA_DIR / "50mfips.txt"
OUT = DATA_DIR / "sma_1950_counties.csv"

STATE_FIPS_TO_ABBR = {
    "01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT",
    "10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL",
    "18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD",
    "25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE",
    "32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND",
    "39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD",
    "47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV",
    "55":"WI","56":"WY","72":"PR",
}

# Manual central-county mapping for the 1950 SMAs by their actual file SMA code.
# Built by mapping each central city named in the SMA title to its 1950 county.
# Independent cities (VA, MD) use the 5-digit county-equivalent FIPS that
# appears in the source file (e.g. Baltimore city = 24510).
CENTRAL_COUNTIES_BY_SMA = {
    "0080": ["39153"],                              # Akron -> Summit OH
    "0160": ["36001", "36083", "36093"],            # Albany-Schenectady-Troy -> Albany, Rensselaer (Troy), Schenectady
    "0200": ["35001"],                              # Albuquerque -> Bernalillo NM
    "0240": ["42077", "42095"],                     # Allentown(Lehigh)-Bethlehem(Northampton, w/ part Lehigh)-Easton(Northampton)
    "0280": ["42013"],                              # Altoona -> Blair PA
    "0320": ["48375"],                              # Amarillo -> Potter TX (city extends slightly into Randall)
    "0480": ["37021"],                              # Asheville -> Buncombe NC
    "0520": ["13121"],                              # Atlanta -> Fulton GA (DeKalb has small part; Fulton is primary)
    "0560": ["34001"],                              # Atlantic City -> Atlantic NJ
    "0600": ["13245"],                              # Augusta GA-SC -> Richmond GA (Augusta city)
    "0640": ["48453"],                              # Austin -> Travis TX
    "0720": ["24510"],                              # Baltimore -> Baltimore city (independent)
    "0760": ["22033"],                              # Baton Rouge -> East Baton Rouge Parish
    "0800": ["26017"],                              # Bay City -> Bay MI
    "0840": ["48245"],                              # Beaumont-Port Arthur -> Jefferson TX (both cities in Jefferson)
    "0960": ["36007"],                              # Binghamton -> Broome NY
    "1000": ["01073"],                              # Birmingham -> Jefferson AL
    # 1120 Boston: NE - handled by MCD logic
    # 1160 Bridgeport CT: NE
    # 1200 Brockton MA: NE
    "1280": ["36029"],                              # Buffalo -> Erie NY
    "1320": ["39151"],                              # Canton -> Stark OH
    "1360": ["19113"],                              # Cedar Rapids -> Linn IA
    "1440": ["45019"],                              # Charleston SC -> Charleston SC
    "1480": ["54039"],                              # Charleston WV -> Kanawha WV
    "1520": ["37119"],                              # Charlotte -> Mecklenburg NC
    "1560": ["47065"],                              # Chattanooga -> Hamilton TN
    "1600": ["17031"],                              # Chicago -> Cook IL
    "1640": ["39061"],                              # Cincinnati -> Hamilton OH
    "1680": ["39035"],                              # Cleveland -> Cuyahoga OH
    "1760": ["45079"],                              # Columbia SC -> Richland
    "1800": ["13215"],                              # Columbus GA-AL -> Muscogee GA (Columbus city)
    "1840": ["39049"],                              # Columbus OH -> Franklin
    "1880": ["48355"],                              # Corpus Christi -> Nueces TX
    "1920": ["48113"],                              # Dallas -> Dallas TX
    "1960": ["19163", "17161"],                     # Davenport(Scott IA) - Rock Island & Moline (Rock Island IL)
    "2000": ["39113"],                              # Dayton -> Montgomery OH
    "2040": ["17115"],                              # Decatur IL -> Macon
    "2080": ["08031"],                              # Denver -> Denver
    "2120": ["19153"],                              # Des Moines -> Polk IA
    "2160": ["26163"],                              # Detroit -> Wayne MI
    "2240": ["27137", "55031"],                     # Duluth(St Louis MN) - Superior(Douglas WI)
    "2280": ["37063"],                              # Durham -> Durham NC
    "2320": ["48141"],                              # El Paso -> El Paso TX
    "2360": ["42049"],                              # Erie -> Erie PA
    "2440": ["18163"],                              # Evansville -> Vanderburgh IN
    # 2480 Fall River MA-RI: NE
    "2640": ["26049"],                              # Flint -> Genesee MI
    "2760": ["18003"],                              # Fort Wayne -> Allen IN
    "2800": ["48439"],                              # Fort Worth -> Tarrant TX
    "2840": ["06019"],                              # Fresno -> Fresno
    "2880": ["01055"],                              # Gadsden -> Etowah AL
    "2920": ["48167"],                              # Galveston -> Galveston TX
    "3000": ["26081"],                              # Grand Rapids -> Kent MI
    "3080": ["55009"],                              # Green Bay -> Brown WI
    "3120": ["37081"],                              # Greensboro-High Point -> Guilford NC (both cities)
    "3160": ["45045"],                              # Greenville SC -> Greenville
    "3200": ["39017"],                              # Hamilton-Middletown OH -> Butler
    "3240": ["42043"],                              # Harrisburg -> Dauphin PA
    # 3280 Hartford CT: NE
    "3320": ["15003"],                              # Honolulu -> Honolulu County HI
    "3360": ["48201"],                              # Houston -> Harris TX
    "3400": ["54011", "21019"],                     # Huntington (Cabell WV=54011) - Ashland (Boyd KY=21019)
    "3480": ["18097"],                              # Indianapolis -> Marion IN
    "3520": ["26075"],                              # Jackson MI -> Jackson MI
    "3560": ["28049"],                              # Jackson MS -> Hinds
    "3600": ["12031"],                              # Jacksonville FL -> Duval
    "3680": ["42021"],                              # Johnstown -> Cambria PA
    "3720": ["26077"],                              # Kalamazoo -> Kalamazoo MI
    "3760": ["29095", "20209"],                     # Kansas City MO-KS -> Jackson MO + Wyandotte KS
    "3800": ["55059"],                              # Kenosha -> Kenosha WI
    "3840": ["47093"],                              # Knoxville -> Knox TN
    "4000": ["42071"],                              # Lancaster PA -> Lancaster
    "4040": ["26065"],                              # Lansing -> Ingham MI (Lansing extends to Eaton & Clinton)
    "4080": ["48479"],                              # Laredo -> Webb TX
    # 4160 Lawrence MA: NE
    "4280": ["21067"],                              # Lexington KY -> Fayette KY
    "4320": ["39003"],                              # Lima OH -> Allen OH
    "4360": ["31109"],                              # Lincoln NE -> Lancaster NE
    "4400": ["05119"],                              # Little Rock - North Little Rock -> Pulaski AR (both)
    "4440": ["39093"],                              # Lorain-Elyria -> Lorain OH (both cities in Lorain)
    "4480": ["06037"],                              # Los Angeles -> Los Angeles
    "4520": ["21111"],                              # Louisville KY-IN -> Jefferson KY
    # 4560 Lowell MA: NE
    "4600": ["48303"],                              # Lubbock -> Lubbock TX
    "4680": ["13021"],                              # Macon GA -> Bibb
    "4720": ["55025"],                              # Madison WI -> Dane
    # 4760 Manchester NH: NE
    "4840": ["72097"],                              # Mayaguez PR -> Mayaguez Municipio
    "4920": ["47157"],                              # Memphis -> Shelby TN
    "5000": ["12025"],                              # Miami -> Dade FL  (NOTE: file uses 5000? -- check)
    # Actually file lists Miami at code 5000 in 1950? Let me leave; file uses code 5000.
    "5080": ["55079"],                              # Milwaukee -> Milwaukee WI
    "5120": ["27053", "27123"],                     # Minneapolis-St Paul -> Hennepin + Ramsey
    "5160": ["01097"],                              # Mobile -> Mobile AL
    "5240": ["01101"],                              # Montgomery AL -> Montgomery
    "5280": ["18035"],                              # Muncie IN -> Delaware
    "5360": ["47037"],                              # Nashville -> Davidson TN
    # 5400 New Bedford MA: NE
    # 5440 New Britain-Bristol CT: NE
    # 5480 New Haven CT: NE
    "5560": ["22071"],                              # New Orleans -> Orleans Parish
    # 5600 New York-Northeastern NJ: see below (complex; multiple central counties)
    "5600": ["36005","36047","36061","36081","36085","34013","34017"],
    # New York central counties: 5 NYC boroughs (Bronx, Kings, NY, Queens, Richmond)
    # plus "Northeastern NJ" portion: in the 1950 New York-NE NJ SMA the NJ side
    # included Newark (Essex Co = 34013) and Jersey City (Hudson Co = 34017) as
    # central cities of the consolidated area.
    "5720": ["51710", "51740"],                     # Norfolk-Portsmouth -> Norfolk city + Portsmouth city (both independent)
    "5840": ["49057"],                              # Ogden UT -> Weber
    "5880": ["40109"],                              # Oklahoma City -> Oklahoma
    "5920": ["31055"],                              # Omaha NE-IA -> Douglas NE (Omaha city)
    "5960": ["12095"],                              # Orlando FL -> Orange
    "6120": ["17143"],                              # Peoria -> Peoria IL  (17143 = Peoria IL? actually Peoria=17143; check)
    "6160": ["42101"],                              # Philadelphia -> Philadelphia County (= city)
    "6200": ["04013"],                              # Phoenix -> Maricopa
    "6280": ["42003"],                              # Pittsburgh -> Allegheny
    # 6320 Pittsfield MA: NE
    "6360": ["72113"],                              # Ponce PR -> Ponce Municipio
    # 6400 Portland ME: NE
    "6440": ["41051"],                              # Portland OR-WA -> Multnomah
    # 6480 Providence RI: NE
    "6560": ["08101"],                              # Pueblo -> Pueblo CO
    "6600": ["55101"],                              # Racine -> Racine WI
    "6640": ["37183"],                              # Raleigh -> Wake NC
    "6680": ["42011"],                              # Reading -> Berks PA
    "6760": ["51760"],                              # Richmond VA -> Richmond city (independent)
    "6800": ["51770", "51161"],                     # Roanoke -> Roanoke city + Roanoke County (city is independent)
    "6840": ["36055"],                              # Rochester NY -> Monroe
    "6880": ["17201"],                              # Rockford -> Winnebago IL
    "6920": ["06067"],                              # Sacramento -> Sacramento
    "6960": ["26145"],                              # Saginaw MI -> Saginaw
    "7000": ["29021"],                              # St. Joseph MO -> Buchanan
    "7040": ["29510"],                              # St. Louis MO-IL -> St. Louis city (independent)
    "7160": ["49035"],                              # Salt Lake City -> Salt Lake
    "7200": ["48451"],                              # San Angelo TX -> Tom Green
    "7240": ["48029"],                              # San Antonio -> Bexar
    "7280": ["06071"],                              # San Bernardino -> San Bernardino CA
    "7320": ["06073"],                              # San Diego -> San Diego
    "7360": ["06075", "06001"],                     # San Francisco-Oakland -> San Francisco + Alameda (Oakland)
    "7400": ["06085"],                              # San Jose -> Santa Clara
    "7440": ["72127"],                              # San Juan-Rio Piedras PR -> San Juan Municipio (Rio Piedras consolidated 1951)
    "7520": ["13051"],                              # Savannah -> Chatham GA
    "7560": ["42069"],                              # Scranton -> Lackawanna PA
    "7600": ["53033"],                              # Seattle -> King WA
    "7680": ["22017"],                              # Shreveport -> Caddo Parish LA
    "7720": ["19193"],                              # Sioux City IA -> Woodbury IA
    "7760": ["46099"],                              # Sioux Falls SD -> Minnehaha
    "7800": ["18141"],                              # South Bend -> St. Joseph IN
    "7840": ["53063"],                              # Spokane -> Spokane WA
    "7880": ["17167"],                              # Springfield IL -> Sangamon
    "7920": ["29077"],                              # Springfield MO -> Greene
    "7960": ["39023"],                              # Springfield OH -> Clark
    # 8000 Springfield-Holyoke MA-CT: NE
    # 8040 Stamford-Norwalk CT: NE
    "8120": ["06077"],                              # Stockton CA -> San Joaquin
    "8160": ["36067"],                              # Syracuse NY -> Onondaga
    "8200": ["53053"],                              # Tacoma WA -> Pierce
    "8280": ["12057", "12103"],                     # Tampa-St Petersburg -> Hillsborough + Pinellas
    "8320": ["18167"],                              # Terre Haute -> Vigo IN
    "8400": ["39095"],                              # Toledo OH-MI -> Lucas OH
    "8440": ["20177"],                              # Topeka KS -> Shawnee
    "8480": ["34021"],                              # Trenton NJ -> Mercer
    "8560": ["40143"],                              # Tulsa -> Tulsa
    "8680": ["36065", "36043"],                     # Utica-Rome NY -> Oneida (Utica & Rome both in Oneida; Herkimer non-central)
    # 8680 actually file lists Herkimer + Oneida; both Utica and Rome are in Oneida (36065). So only 36065 central.
    "8680": ["36065"],
    "8800": ["48309"],                              # Waco TX -> McLennan
    "8840": ["11001"],                              # Washington DC-MD-VA -> District of Columbia
    # 8880 Waterbury CT: NE
    "8920": ["19013"],                              # Waterloo IA -> Black Hawk
    "9000": ["54069", "39081"],                     # Wheeling (Ohio Co WV=54069) - Steubenville (Jefferson OH=39081)
    "9040": ["20173"],                              # Wichita KS -> Sedgwick
    "9080": ["48485"],                              # Wichita Falls TX -> Wichita TX
    "9120": ["42079"],                              # Wilkes-Barre-Hazleton -> Luzerne (both in Luzerne)
    "9160": ["10003"],                              # Wilmington DE-NJ -> New Castle DE
    "9220": ["37067"],                              # Winston-Salem NC -> Forsyth
    # 9240 Worcester MA: NE
    "9280": ["42133"],                              # York PA -> York
    "9320": ["39099"],                              # Youngstown OH-PA -> Mahoning OH
}

# ---- Parsing -----------------------------------------------------------

COMPOUNDS = [
    "Wilkes-Barre", "Winston-Salem", "St. Paul", "St. Petersburg",
    "St. Louis", "St. Joseph", "Rio Piedras", "Rock Island", "North Little Rock",
    "High Point", "Port Arthur", "San Bernardino", "San Antonio", "San Francisco",
    "San Diego", "San Jose", "San Juan", "San Angelo", "Los Angeles", "Las Vegas",
    "Long Beach", "Atlantic City", "Bay City", "Baton Rouge", "Salt Lake City",
    "Sioux Falls", "Sioux City", "South Bend", "Fall River", "Fort Worth",
    "Fort Wayne", "Fort Smith", "Grand Rapids", "Green Bay", "Cedar Rapids",
    "Colorado Springs", "Corpus Christi", "Des Moines", "El Paso", "Kansas City",
    "Lake Charles", "Little Rock", "New Bedford", "New Britain", "New Haven",
    "New Orleans", "New York", "Oklahoma City", "Palm Beach", "West Palm Beach",
    "Wichita Falls", "Lake Charles", "Cape Girardeau", "Terre Haute",
    "Mt. Vernon", "Bossier City", "East Chicago", "East St. Louis",
    "Fitchburg-Leominster", "Greensboro-High Point", "Pawtucket",
]

def parse_central_cities(title: str):
    """Extract central-city names from an SMA title like
       'Albany-Schenectady-Troy, NY SMA' -> ['Albany','Schenectady','Troy']
    """
    m = re.match(r"^(.*?),\s*[^,]+\s*SMA\s*$", title)
    if not m:
        return []
    name_part = m.group(1).strip()
    # Protect compound city names with embedded hyphens
    for c in COMPOUNDS:
        if c in name_part:
            placeholder = c.replace("-", "\x00")
            name_part = name_part.replace(c, placeholder)
    # Some titles use "--" as a separator (e.g. "Wilkes-Barre--Hazleton")
    name_part = name_part.replace("--", "-")
    parts = [p.replace("\x00", "-").strip() for p in name_part.split("-") if p.strip()]
    return parts


def main():
    sma_records: dict[str, dict] = {}
    current_sma = None

    with open(SRC, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            if line.startswith("File Layout") or line.startswith("Character"):
                break
            if line.startswith("Footnote"):
                continue
            ex = raw.expandtabs(8).rstrip("\n")
            if len(ex) < 4 or not ex[:4].isdigit():
                continue
            code = ex[:4]
            state_fips      = ex[12:14].strip() if len(ex) > 13 else ""
            county_fips_part= ex[14:17].strip() if len(ex) > 16 else ""
            place_fips      = ex[20:25].strip() if len(ex) > 24 else ""
            name            = ex[32:].strip() if len(ex) > 32 else ""

            if not state_fips and not county_fips_part and not place_fips:
                # SMA title line
                cities = parse_central_cities(name)
                sma_records[code] = {
                    "title": name,
                    "central_cities": cities,
                    "counties": {},
                }
                current_sma = code
                continue

            if state_fips and county_fips_part and not place_fips:
                full = state_fips + county_fips_part
                # Some New England records are MCDs that are missing their
                # place FIPS in the source file (e.g. Enfield town in the
                # Springfield-Holyoke SMA). Heuristic: if this county FIPS
                # is already present in the current SMA's record AND the
                # name does not contain "County"/"Parish"/"Municipio", treat
                # this line as a town within that county.
                looks_like_county = any(
                    kw in name for kw in
                    ("County", "Parish", "Municipio", "city", "Borough")
                ) and "town" not in name.lower()
                if full in sma_records[current_sma]["counties"] and not looks_like_county:
                    sma_records[current_sma]["counties"][full]["towns"].append(name)
                    continue
                partial = "(pt." in name
                cname = re.sub(r"\s*\(pt\.\)\s*$", "", name).strip()
                sma_records[current_sma]["counties"][full] = {
                    "name": cname,
                    "partial": partial,
                    "towns": [],
                }
                continue

            if state_fips and county_fips_part and place_fips:
                full = state_fips + county_fips_part
                if current_sma in sma_records and full in sma_records[current_sma]["counties"]:
                    sma_records[current_sma]["counties"][full]["towns"].append(name)
                continue

    def norm(s: str) -> str:
        s = re.sub(r"\b(city|town|borough|village)\b\s*$", "", s, flags=re.I).strip()
        return s.lower()

    # Determine central counties
    for code, rec in sma_records.items():
        central = set()
        cities_norm = [norm(c) for c in rec["central_cities"]]
        # NE: any county containing a town whose name matches a central city
        for fips, cinfo in rec["counties"].items():
            for town in cinfo["towns"]:
                if norm(town) in cities_norm:
                    central.add(fips)
        # Add hand-curated lookup
        for f in CENTRAL_COUNTIES_BY_SMA.get(code, []):
            if f in rec["counties"]:
                central.add(f)
            else:
                # Lookup mismatch - report
                pass
        rec["central_set"] = central

    # Write CSV
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "sma_code","sma_name","central_cities","state",
            "county_fips","county_name","is_central_county","partial_county","new_england_towns",
        ])
        for code in sorted(sma_records.keys()):
            rec = sma_records[code]
            cities_str = "|".join(rec["central_cities"])
            for fips, cinfo in sorted(rec["counties"].items()):
                state_abbr = STATE_FIPS_TO_ABBR.get(fips[:2], "")
                w.writerow([
                    code, rec["title"], cities_str, state_abbr,
                    fips, cinfo["name"],
                    1 if fips in rec["central_set"] else 0,
                    1 if cinfo["partial"] else 0,
                    "|".join(cinfo["towns"]),
                ])

    # Audit / report
    n_sma = len(sma_records)
    n_rows = sum(len(r["counties"]) for r in sma_records.values())
    n_central = sum(len(r["central_set"]) for r in sma_records.values())
    no_central = [c for c,r in sma_records.items() if not r["central_set"]]
    mismatches = []
    for code, rec in sma_records.items():
        for f in CENTRAL_COUNTIES_BY_SMA.get(code, []):
            if f not in rec["counties"]:
                mismatches.append((code, rec["title"], f, list(rec["counties"].keys())))

    print(f"Parsed {n_sma} SMAs, {n_rows} county rows, {n_central} central-county flags.")
    print(f"SMAs with NO central county flagged: {len(no_central)}")
    for c in no_central:
        print(f"  {c}: {sma_records[c]['title']}  counties={list(sma_records[c]['counties'].keys())}  towns={[t for ci in sma_records[c]['counties'].values() for t in ci['towns']]}")
    if mismatches:
        print(f"\nMismatches (central FIPS not found in SMA's county list): {len(mismatches)}")
        for code, title, f, got in mismatches:
            print(f"  {code} {title}: expected {f}, got {got}")
    print(f"\nOutput: {OUT}")


if __name__ == "__main__":
    main()
