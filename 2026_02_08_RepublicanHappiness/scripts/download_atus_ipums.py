"""
Download comprehensive ATUS data from IPUMS via API.
Includes: core ATUS + Well-Being Module + Eating & Health Module + Leave Module + COVID + Eldercare
All years 2003-2024.
"""

import os
import sys
import time
import json
import requests
import zipfile
import gzip
import io
from pathlib import Path

# === CONFIG ===
IPUMS_API_KEY = "59cba10d8a5da536fc06b59d2762e4c5859b48dbb5215e13b449ba09"
DATA_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Data")
EXTRACT_DIR = Path("/Users/azizsunderji/Dropbox/Home Economics/Explorations/data")
BASE_URL = "https://api.ipums.org/extracts"
COLLECTION = "atus"

HEADERS = {
    "Authorization": IPUMS_API_KEY,
    "Content-Type": "application/json"
}

# All available ATUS samples 2003-2024
SAMPLES = {f"at{year}": {} for year in range(2003, 2025)}

# Comprehensive variable list organized by group
# Note: preselected vars (YEAR, CASEID, SERIAL, PERNUM, LINENO, WT06) are auto-included

VARIABLES = {
    # === HOUSEHOLD: Technical ===
    "PHONE": {},
    "CLUSTER": {},
    "STRATA": {},

    # === HOUSEHOLD: Geographic ===
    "REGION": {},
    "STATEFIP": {},
    "METRO": {},
    "MSASIZE": {},
    "COUNTY": {},
    "METAREA": {},
    "METFIPS": {},

    # === HOUSEHOLD: Economic ===
    "FAMINCOME": {},
    "HHTENURE": {},
    "HOUSETYPE": {},
    "FAMBUS": {},
    "FAMBUS_RESP": {},
    "FAMBUS_SPOUSE": {},
    "FAMBUS_OTHER": {},
    "POVERTY185": {},
    "POVERTY130": {},
    "POVERTYLEVEL": {},
    "FOODSTAMP": {},
    "WIC": {},
    "ANYBRK": {},
    "ANYLNCH": {},

    # === HOUSEHOLD: Constructed Composition ===
    "HH_SIZE": {},
    "HH_CHILD": {},
    "HH_NUMKIDS": {},
    "AGEYCHILD": {},
    "HH_NUMADULTS": {},

    # === HOUSEHOLD: Technical Activity ===
    "KIDWAKETIME": {},
    "KIDBEDTIME": {},

    # === PERSON: Technical ===
    "PRESENCE": {},
    "MONTH": {},
    "DAY": {},
    "HOLIDAY": {},
    "DATE": {},
    "CPSIDP": {},

    # === PERSON: Weights (beyond auto-included WT06) ===
    "RWT06": {},
    "WT20": {},
    "RWT20": {},
    "WT04": {},
    "WT03": {},
    "BWT": {},
    "RBWT": {},
    "EHWT": {},
    "REHWT": {},
    "WBWT": {},
    "RWBWT": {},
    "LVWT": {},
    "RLVWT": {},

    # === PERSON: Core Demographic ===
    "AGE": {},
    "SEX": {},
    "RACE": {},
    "HISPAN": {},
    "ASIAN": {},
    "MARST": {},
    "YRIMMIG": {},
    "CITIZEN": {},
    "BPL": {},
    "MBPL": {},
    "FBPL": {},
    "RELATE": {},
    "POPSTAT": {},
    "GENHEALTH": {},
    "HEIGHT": {},
    "WEIGHT": {},
    "BMI": {},

    # === PERSON: Disability ===
    "DIFFANY": {},
    "DIFFCARE": {},
    "DIFFEYE": {},
    "DIFFHEAR": {},
    "DIFFMOB": {},
    "DIFFPHYS": {},
    "DIFFREM": {},

    # === PERSON: Education ===
    "EDUC": {},
    "EDUCYRS": {},
    "SCHLCOLL": {},

    # === PERSON: Work Status ===
    "EMPSTAT": {},
    "MULTJOBS": {},
    "CLWKR": {},
    "OCC2": {},
    "OCC": {},
    "OCC2010": {},
    "IND2": {},
    "IND": {},
    "WHYABSNT": {},
    "FAMBUS_PAY": {},
    "FAMBUS_WRK": {},
    "LOOKING": {},
    "RETIRED": {},

    # === PERSON: Hours and Earnings ===
    "FULLPART": {},
    "UHRSWORKT": {},
    "UHRSWORK1": {},
    "UHRSWORK2": {},
    "EARNWEEK": {},
    "PAIDHOUR": {},
    "EARNRPT": {},
    "HOURWAGE": {},
    "HRSATRATE": {},
    "OTUSUAL": {},
    "OTPAY": {},

    # === PERSON: Job Search ===
    "FWK_EMPLR": {},
    "FWK_PUBAG": {},
    "FWK_PVTAG": {},
    "FWK_RELATE": {},
    "FWK_SCHOOL": {},
    "FWK_RESUME": {},
    "FWK_UNION": {},
    "FWK_ADS": {},
    "FWK_OTHERA": {},
    "FWK_READADS": {},
    "FWK_JOBPRGM": {},
    "FWK_NOTHING": {},
    "FWK_OTHERP": {},

    # === PERSON: Veteran Status ===
    "VETSTAT": {},
    "VETLAST": {},
    "VET1": {},
    "VET2": {},
    "VET3": {},
    "VET4": {},
    "AFNOW": {},

    # === PERSON: Eldercare ===
    "ECYEST": {},
    "ECPRIOR": {},
    "ECNUM": {},
    "ECFREQ": {},

    # === PERSON: Methodology ===
    "INTRODATE": {},
    "INTROMONTH": {},
    "INTROYEAR": {},
    "ATUSDP": {},
    "OTHERLANG": {},
    "INCENT": {},
    "TOTACT": {},
    "AVGDUR": {},
    "DATAQUAL": {},
    "OUTCOME": {},
    "OUTCOME_ALT": {},

    # === PERSON: COVID-19 Module ===
    "COVIDTELEW": {},
    "COVIDPAID": {},
    "COVIDUNAW": {},
    "COVIDLOOK": {},
    "COVIDMED": {},

    # === PERSON: Well-Being Module (person-level) ===
    "WB_RESP": {},
    "RESTED": {},
    "HIGHBP": {},
    "PAINMED": {},
    "WBELIGTIME": {},
    "WBTYPICAL": {},
    "WBLADDER": {},

    # === ACTIVITY: Well-Being Module (activity-level) ===
    "SCPAIN": {},
    "SCHAPPY": {},
    "SCSAD": {},
    "SCTIRED": {},
    "SCSTRESS": {},
    "INTERACT": {},
    "MEANING": {},
    "OSAD": {},
    "OHAPPY": {},
    "OPAIN": {},
    "OTIRED": {},
    "OSTRESS": {},
    "WBELIG": {},
    "AWBWT": {},

    # === PERSON: Eating & Health Module ===
    "EH_RESP": {},
    "PED": {},
    "SED_DRINK": {},
    "SED_EAT": {},
    "FOODSHOP": {},
    "MEALPREP": {},
    "SODA": {},
    "DIETSODA": {},
    "MILK": {},
    "MEAT": {},
    "STORE": {},
    "STREASON": {},
    "EXERCISE": {},
    "EXFREQ": {},
    "FASTFD": {},
    "FASTFDFREQ": {},
    "ALLDAYDRK": {},
    "FDTHERM": {},
    "ENOUGHFD": {},
    "ALLDAYEAT": {},
    "ANYSECDRK": {},
    "ANYSECEAT": {},
    "SCHLBRK": {},
    "SCHLLNCH": {},
    "DIETQUAL": {},
    "EXINT": {},
    "FASTFDATE": {},
    "GROSHPAMT": {},
    "GROSHPENJOY": {},
    "ONGROSHPFREQ": {},
    "ONGROSHPGET": {},
    "ONGROSHPWHY": {},
    "ONGROSHPWHYNOT": {},
    "PRPMELAMT": {},
    "PRPMELENJOY": {},

    # === PERSON: Leave Module - General ===
    "LV_RESP": {},
    "LEAVELW": {},
    "TKLVWK": {},
    "HRSLVWK": {},
    "PAINLWK": {},
    "TKLVWKTYPE": {},

    # === PERSON: Leave Module - Paid Leave ===
    "RCVPDLV": {},
    "RCVPDSELF": {},
    "RCVPDFAM": {},
    "RCVPDCHCARE": {},
    "RCVPDELCARE": {},
    "RCVPDVAC": {},
    "RCVPDPERS": {},
    "RCVPDCHILD": {},
    "TKLVWKPD": {},

    # === PERSON: Leave Module - Unpaid Leave ===
    "RCVUNPDLV": {},
    "RCVUNSELF": {},
    "RCVUNFAM": {},
    "RCVUNCHCARE": {},
    "RCVUNELCARE": {},
    "RCVUNVAC": {},
    "RCVUNPERS": {},
    "RCVUNCHILD": {},
    "EVTKUNLV": {},
    "EVTKUNSELF": {},
    "EVTKUNFAM": {},
    "EVTKUNCHCARE": {},
    "EVTKUNELCARE": {},
    "EVTKUNVAC": {},
    "EVTKUNPERS": {},
    "EVTKUNCHILD": {},
    "TKRCVUNLVEV": {},

    # === PERSON: Leave Module - Work Schedule ===
    "WRKSCHEDUS": {},
    "WRKSHIFTRSN": {},
    "WRKNUMUS": {},
    "WRKSCHEDWK": {},
    "WRKSCHEDMON": {},
    "WRKSCHEDTUE": {},
    "WRKSCHEDWED": {},
    "WRKSCHEDTHU": {},
    "WRKSCHEDFRI": {},
    "WRKSCHEDSAT": {},
    "WRKSCHEDSUN": {},
    "WRKSCHEDVARY": {},
    "WRKDAYSAVG": {},

    # === PERSON: Leave Module - Reasons ===
    "NOLVLWWORK": {},
    "NOLVLWSAVE": {},
    "NOLVLWDENY": {},
    "NOLVLWLACK": {},
    "NOLVLWFEAR": {},
    "NOLVLWINC": {},
    "NOLVLWOTH": {},
    "TKLVWKMAIN": {},
    "TKLVYEST": {},
    "TKLVWKRSN": {},
    "NOLEAVEMO": {},
    "NOTKLVMOCHILD": {},
    "NOTKLVMOCHCARE": {},
    "NOTKLVMOELCARE": {},
    "NOTKLVMOPERS": {},
    "NOTKLVMOFAM": {},
    "NOTKLVMOSELF": {},
    "NOTKLVMOOTH": {},
    "NOTKLVMOVAC": {},
    "NOLVMOINC": {},
    "NOLVMOSHFT": {},
    "NOLVMODENY": {},
    "NOLVMOALT": {},
    "NOLVMOFEAR": {},
    "NOLVMOLACK": {},
    "NOLVMOOTH": {},
    "NOLVMOSAVE": {},
    "NOLVMOWORK": {},

    # === PERSON: Leave Module - Work Policies ===
    "CANVARY": {},
    "VARYLW": {},
    "WRKFLEXHRS": {},
    "WRKFLEXFREQ": {},
    "WRKFLEXPOL": {},
    "WRKFLEXINPUT": {},
    "WRKFLEXADV": {},

    # === PERSON: Leave Module - Working from Home ===
    "WRKHOMEABLE": {},
    "WRKHOMEEV": {},
    "WRKHOMEPD": {},
    "WRKHOMERSN": {},
    "WRKHOMEDAYS": {},
    "WRKHOMEOFTEN": {},

    # === ACTIVITY: Core ===
    "ACTLINE": {},
    "ACTIVITY": {},
    "WHERE": {},
    "DURATION_EXT": {},
    "DURATION": {},
    "METVALUE": {},
    "WHO_ASK": {},
    "START": {},
    "STOP": {},

    # === ACTIVITY: Secondary Activity ===
    "SCC_HHNHHOWN_LN": {},
    "SCC_ALL_LN": {},
    "SCC_NOWNNHH_LN": {},
    "SCC_HH_LN": {},
    "SCC_NOWNHH_LN": {},
    "SCC_OWN_LN": {},
    "SCC_OWNHH_LN": {},
    "SCC_OWNNHH_LN": {},
    "SED_DRINK_LN": {},
    "SED_EAT_LN": {},
    "SED_ALL_LN": {},
    "SEC_ALL_LN": {},

    # Note: WHO record vars (ACTLINEW, LINENOW, WHOLINE, RELATEW, RELATEWU, AGEW, SEXW)
    # and ELDERCARE record vars (LINENOR, HH_EC, RELATER, ECAGE, ECYEAR, ECMONTH)
    # require hierarchical format. We use rectangular on Activity for CSV compatibility.
    # Who-with info is captured via WHO_ASK at activity level.
}

# System time use variables
TIME_USE_VARIABLES = {
    # === Activity Coding Structure (major categories) ===
    "ACT_PCARE": {},
    "ACT_HHACT": {},
    "ACT_CAREHH": {},
    "ACT_CARENHH": {},
    "ACT_WORK": {},
    "ACT_EDUC": {},
    "ACT_PURCH": {},
    "ACT_PROFSERV": {},
    "ACT_HHSERV": {},
    "ACT_GOVSERV": {},
    "ACT_FOOD": {},
    "ACT_SOCIAL": {},
    "ACT_SPORTS": {},
    "ACT_RELIG": {},
    "ACT_VOL": {},
    "ACT_PHONE": {},
    "ACT_TRAVEL": {},

    # === BLS Published Tables (top-level + detailed) ===
    # Personal Care
    "BLS_PCARE": {},
    "BLS_PCARE_SLEEP": {},
    "BLS_PCARE_GROOM": {},
    "BLS_PCARE_HEALTH": {},
    "BLS_PCARE_ACT": {},
    "BLS_PCARE_TRAVEL": {},
    # Eating & Drinking
    "BLS_FOOD": {},
    "BLS_FOOD_FOOD": {},
    "BLS_FOOD_TRAVEL": {},
    # Household Activities
    "BLS_HHACT": {},
    "BLS_HHACT_HWORK": {},
    "BLS_HHACT_FOOD": {},
    "BLS_HHACT_LAWN": {},
    "BLS_HHACT_HHMGMT": {},
    "BLS_HHACT_INTER": {},
    "BLS_HHACT_EXTER": {},
    "BLS_HHACT_PET": {},
    "BLS_HHACT_VEHIC": {},
    "BLS_HHACT_TOOL": {},
    "BLS_HHACT_TRAVEL": {},
    # Purchasing
    "BLS_PURCH": {},
    "BLS_PURCH_CONS": {},
    "BLS_PURCH_GROC": {},
    "BLS_PURCH_PROF": {},
    "BLS_PURCH_BANK": {},
    "BLS_PURCH_HEALTH": {},
    "BLS_PURCH_PCARE": {},
    "BLS_PURCH_HHSERV": {},
    "BLS_PURCH_HOME": {},
    "BLS_PURCH_VEHIC": {},
    "BLS_PURCH_GOV": {},
    "BLS_PURCH_TRAVEL": {},
    # Care
    "BLS_CAREHH": {},
    "BLS_CAREHH_KID": {},
    "BLS_CAREHH_KIDOTHER": {},
    "BLS_CAREHH_KIDEDUC": {},
    "BLS_CAREHH_KIDHEALTH": {},
    "BLS_CAREHH_ADULT": {},
    "BLS_CAREHH_TRAVEL": {},
    "BLS_CARENHH": {},
    "BLS_CARENHH_KID": {},
    "BLS_CARENHH_ADULT": {},
    "BLS_CARENHH_ADULTCARE": {},
    "BLS_CARENHH_ADULTHELP": {},
    "BLS_CARENHH_TRAVEL": {},
    # Work
    "BLS_WORK": {},
    "BLS_WORK_WORKING": {},
    "BLS_WORK_WORKREL": {},
    "BLS_WORK_OTHER": {},
    "BLS_WORK_SEARCH": {},
    "BLS_WORK_TRAVEL": {},
    # Education
    "BLS_EDUC": {},
    "BLS_EDUC_CLASS": {},
    "BLS_EDUC_HWORK": {},
    "BLS_EDUC_TRAVEL": {},
    # Social/Civic/Religious
    "BLS_SOCIAL": {},
    "BLS_SOCIAL_RELIG": {},
    "BLS_SOCIAL_VOL": {},
    "BLS_SOCIAL_VOLACT": {},
    "BLS_SOCIAL_ADMIN": {},
    "BLS_SOCIAL_SOCSERV": {},
    "BLS_SOCIAL_MAINTEN": {},
    "BLS_SOCIAL_CULTURE": {},
    "BLS_SOCIAL_ATTEND": {},
    "BLS_SOCIAL_CIVIC": {},
    "BLS_SOCIAL_TRAVEL": {},
    # Leisure & Sports
    "BLS_LEIS": {},
    "BLS_LEIS_SOC": {},
    "BLS_LEIS_SOCCOM": {},
    "BLS_LEIS_SOCCOMEX": {},
    "BLS_LEIS_ATTEND": {},
    "BLS_LEIS_SPORT": {},
    "BLS_LEIS_RELAX": {},
    "BLS_LEIS_TV": {},
    "BLS_LEIS_ARTS": {},
    "BLS_LEIS_PARTSPORT": {},
    "BLS_LEIS_ATTSPORT": {},
    "BLS_LEIS_TRAVEL": {},
    # Communication
    "BLS_COMM": {},
    "BLS_COMM_TELE": {},
    "BLS_COMM_MSG": {},
    "BLS_COMM_MSGMAIL": {},
    "BLS_COMM_MSGEMAIL": {},
    "BLS_COMM_TRAVEL": {},
    # Other
    "BLS_OTHER": {},

    # === ERS Eating & Drinking ===
    "ERS_PRIM": {},
    "ERS_ASSOC": {},
}


def submit_extract():
    """Submit the ATUS extract request."""
    payload = {
        "description": "Comprehensive ATUS extract: all years 2003-2024, all modules (WB, EH, Leave, COVID, Eldercare), all variables",
        "dataFormat": "csv",
        "dataStructure": {"rectangular": {"on": "A"}},
        "samples": SAMPLES,
        "variables": VARIABLES,
        "timeUseVariables": TIME_USE_VARIABLES,
        "sampleMembers": {
            "includeNonRespondents": True,
            "includeHouseholdMembers": True
        }
    }

    url = f"{BASE_URL}?collection={COLLECTION}&version=2"
    print(f"Submitting extract to {url}...")
    print(f"  Samples: {len(SAMPLES)} years (2003-2024)")
    print(f"  Variables: {len(VARIABLES)}")
    print(f"  Time use variables: {len(TIME_USE_VARIABLES)}")

    resp = requests.post(url, headers=HEADERS, json=payload)

    if resp.status_code not in (200, 201):
        print(f"ERROR {resp.status_code}: {resp.text}")
        sys.exit(1)

    result = resp.json()
    extract_number = result.get("number")
    print(f"Extract #{extract_number} submitted successfully. Status: {result.get('status')}")
    return extract_number


def check_status(extract_number):
    """Check extract status."""
    url = f"{BASE_URL}/{extract_number}?collection={COLLECTION}&version=2"
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def wait_for_extract(extract_number, poll_interval=30):
    """Poll until extract is complete."""
    print(f"Waiting for extract #{extract_number}...")
    while True:
        status_info = check_status(extract_number)
        status = status_info.get("status")
        print(f"  Status: {status}")

        if status == "completed":
            print("Extract ready for download!")
            return status_info
        elif status in ("failed", "canceled"):
            print(f"Extract {status}!")
            print(json.dumps(status_info, indent=2))
            sys.exit(1)

        time.sleep(poll_interval)


def download_extract(extract_number):
    """Download the completed extract files."""
    status_info = check_status(extract_number)
    download_links = status_info.get("downloadLinks", {})

    if not download_links:
        print("No download links found!")
        return

    for file_type, url_info in download_links.items():
        url = url_info if isinstance(url_info, str) else url_info.get("url", "")
        if not url:
            continue

        filename = url.split("/")[-1]
        filepath = EXTRACT_DIR / filename
        print(f"Downloading {file_type}: {filename}...")

        resp = requests.get(url, headers={"Authorization": IPUMS_API_KEY}, stream=True)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  {pct:.1f}% ({downloaded / 1e6:.1f} MB)", end="", flush=True)
        print(f"\n  Saved to {filepath}")

    return filepath


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download ATUS data from IPUMS")
    parser.add_argument("--submit", action="store_true", help="Submit new extract")
    parser.add_argument("--check", type=int, help="Check status of extract number")
    parser.add_argument("--download", type=int, help="Download completed extract number")
    parser.add_argument("--wait-and-download", type=int, help="Wait for and download extract number")
    args = parser.parse_args()

    if args.submit:
        extract_num = submit_extract()
        print(f"\nNext steps:")
        print(f"  Check status:  python {__file__} --check {extract_num}")
        print(f"  Wait & download: python {__file__} --wait-and-download {extract_num}")

    elif args.check:
        info = check_status(args.check)
        print(json.dumps(info, indent=2))

    elif args.download:
        download_extract(args.download)

    elif args.wait_and_download:
        wait_for_extract(args.wait_and_download)
        download_extract(args.wait_and_download)

    else:
        # Default: submit, wait, download
        extract_num = submit_extract()
        wait_for_extract(extract_num)
        download_extract(extract_num)
