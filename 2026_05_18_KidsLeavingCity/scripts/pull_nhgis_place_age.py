"""
Submit NHGIS API extract for place-level decennial age tables, 1970-2020.

For each decade, the relevant Sex-by-Age table at place geography level.
Then compute under-18 per place for top-50 central cities.

Output: data/nhgis_place_age.csv  (place_fips, place_name, year, under18)
"""
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

API_KEY = "59cba10d8a5da536fc06b59d2762e4c5859b48dbb5215e13b449ba09"
API = "https://api.ipums.org/extracts"

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

# Per-decade dataset + age-table mapping.
# Table codes confirmed via NHGIS metadata for some, best-guess for others.
DATASETS = {
    "1970_Cnt2": ["NT18"],   # Sex by Age (place geog)
    "1980_STF1": ["NT10B"],  # Sex by Age
    "1990_STF1": ["NP12"],   # Sex by Age (single-year for under 18)
    "2000_SF1a": ["NP012B"], # Sex by Age (under 18 broken out)
    "2010_SF1a": ["P12"],    # Sex by Age
    "2020_DHCa": ["P12"],    # Sex by Age (selected categories)
}


def submit():
    body = {
        "description": "Place-level Sex×Age for top-50 1950 SMA central cities, 1970-2020",
        "dataFormat": "csv_no_header",
        "datasets": {
            ds: {"dataTables": tbls, "geogLevels": ["place"]}
            for ds, tbls in DATASETS.items()
        },
    }
    url = f"{API}?collection=nhgis&version=2"
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Authorization": API_KEY, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def status(ext_no):
    url = f"{API}/{ext_no}?collection=nhgis&version=2"
    req = urllib.request.Request(url, headers={"Authorization": API_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def download(url, dst):
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"Authorization": API_KEY})
    with urllib.request.urlopen(req, timeout=900) as r:
        dst.write_bytes(r.read())
    print(f"  wrote {dst.stat().st_size/1e6:.1f}MB -> {dst}")


def main():
    print("Submitting NHGIS place-level extract...")
    try:
        s = submit()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTPError {e.code}: {body[:2000]}")
        raise
    ext_no = s.get("number")
    print(f"  extract # {ext_no}, status: {s.get('status')}")
    (DATA / "nhgis_place_extract.json").write_text(json.dumps(s, indent=2))

    waited = 0
    st = s.get("status")
    while st not in ("completed", "failed"):
        time.sleep(30); waited += 30
        rec = status(ext_no)
        st = rec.get("status")
        print(f"  t+{waited}s — status: {st}")
        if waited > 3600: print("  timeout"); return
    if st != "completed":
        print(f"FAILED with status {st}")
        return

    rec = status(ext_no)
    data_url = (rec.get("downloadLinks") or {}).get("tableData", {}).get("url")
    cb_url = (rec.get("downloadLinks") or {}).get("codebook", {}).get("url")
    if not data_url:
        print("No data URL; full rec:")
        print(json.dumps(rec, indent=2)[:2000])
        return
    raw = DATA / "nhgis_place_raw"
    raw.mkdir(exist_ok=True)
    zip_path = raw / f"nhgis_place_{ext_no}.zip"
    download(data_url, zip_path)
    print("Done — unzip and process next.")


if __name__ == "__main__":
    main()
