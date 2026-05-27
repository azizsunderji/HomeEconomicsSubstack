"""
Submit IPUMS USA extract — TOTAL US population by METRO category for 2010, 2020-equivalent, 2023.

We grab three samples:
  - us2010a — ACS 2010 1-yr (for 2010 Census-comparable national tabulation)
  - us2021a — ACS 2021 1-yr (closest non-pandemic-affected proxy near 2020)
  - us2023a — ACS 2023 1-yr (most recent at this run)

Variables: YEAR, SAMPLE, AGE, METRO, PERWT.
No AGE filter — we want all ages.

Output: data/ipums_usa_allages_metro.parquet
"""
from __future__ import annotations
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

IPUMS_KEY = "59cba10d8a5da536fc06b59d2762e4c5859b48dbb5215e13b449ba09"
API = "https://api.ipums.org/extracts"
COLLECTION = "usa"
VERSION = "2"

PROJECT_DATA = Path(
    "/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity/data"
)
PROJECT_DATA.mkdir(parents=True, exist_ok=True)

# Just three ACS samples — total ~3 GB raw but smaller after select few vars
SAMPLES = ["us2010a", "us2021a", "us2023a"]
VARIABLES = ["YEAR", "SAMPLE", "AGE", "METRO", "PERWT"]


def submit_extract():
    body = {
        "description": "Total US pop by METRO (PC/suburb/non-metro) — 2010, 2021, 2023 ACS 1-yr",
        "dataStructure": {"rectangular": {"on": "P"}},
        "dataFormat": "csv",
        "samples": {s: {} for s in SAMPLES},
        "variables": {v: {} for v in VARIABLES},
    }
    url = f"{API}?collection={COLLECTION}&version={VERSION}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": IPUMS_KEY,
            "Content-Type": "application/json",
            "Accept": "*/*",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get_extract(extract_number):
    url = f"{API}/{extract_number}?collection={COLLECTION}&version={VERSION}"
    req = urllib.request.Request(url, headers={"Authorization": IPUMS_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def download_to(url, dst):
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"Authorization": IPUMS_KEY})
    with urllib.request.urlopen(req, timeout=1800) as r:
        dst.write_bytes(r.read())
    print(f"  wrote {dst.stat().st_size / 1e6:.1f} MB -> {dst}")


def main():
    print(f"Submitting IPUMS USA extract...")
    try:
        sub = submit_extract()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTPError {e.code}: {body[:2000]}")
        raise
    ext_no = sub.get("number")
    print(f"  extract # {ext_no}, status = {sub.get('status')}")
    (PROJECT_DATA / "ipums_usa_allages_metro.extract.json").write_text(json.dumps(sub, indent=2))

    status = sub.get("status")
    waited = 0
    while status not in ("completed", "failed"):
        time.sleep(20)
        waited += 20
        rec = get_extract(ext_no)
        status = rec.get("status")
        print(f"  t+{waited}s -- status: {status}", flush=True)
        if waited > 3600:
            print("  timeout 60 min -- aborting poll")
            return

    if status != "completed":
        print(f"Extract did not complete (status={status})")
        return

    rec = get_extract(ext_no)
    download_links = rec.get("downloadLinks", {})
    data_url = (download_links.get("data") or {}).get("url")
    ddi_url = (download_links.get("ddiCodebook") or {}).get("url")

    raw_dir = PROJECT_DATA / "ipums_raw"
    raw_dir.mkdir(exist_ok=True)
    data_path = raw_dir / f"ipums_usa_allages_metro_{ext_no}.csv.gz"
    ddi_path = raw_dir / f"ipums_usa_allages_metro_{ext_no}.xml"

    download_to(data_url, data_path)
    download_to(ddi_url, ddi_path)

    print("  converting to parquet...")
    import duckdb

    out_path = PROJECT_DATA / "ipums_usa_allages_metro.parquet"
    duckdb.query(
        f"""
        COPY (SELECT * FROM read_csv_auto('{data_path}', compression = 'gzip', sample_size = 100000))
        TO '{out_path}' (FORMAT 'parquet', COMPRESSION 'zstd')
        """
    )
    n = duckdb.query(f"SELECT COUNT(*) AS n FROM '{out_path}'").df()["n"][0]
    print(f"  parquet row count: {n:,}")
    print(f"  wrote {out_path}")

    meta = {
        "source": "IPUMS USA API",
        "extract_number": ext_no,
        "samples": SAMPLES,
        "variables": VARIABLES,
        "filter": "none (all ages)",
        "pulled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (PROJECT_DATA / "ipums_usa_allages_metro.source.json").write_text(json.dumps(meta, indent=2))
    print("\nDone.")


if __name__ == "__main__":
    main()
