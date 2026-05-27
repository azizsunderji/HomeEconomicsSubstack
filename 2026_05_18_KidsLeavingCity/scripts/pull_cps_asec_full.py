"""
Submit and download a comprehensive CPS ASEC extract from IPUMS API.

Variables include WHYMOVE (reason for move), full geography (current + 1 year ago),
demographics, income, household composition.

Output: saves to data lake at
  /Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC/cps_asec_full.parquet

Usage: python3 pull_cps_asec_full.py
       Submits the extract, polls for completion, downloads, converts to parquet.

API: https://developer.ipums.org/docs/v2/apiprogram/
"""
from __future__ import annotations
import os
import json
import time
import gzip
import io
import urllib.request
import urllib.error
from pathlib import Path

IPUMS_KEY = "59cba10d8a5da536fc06b59d2762e4c5859b48dbb5215e13b449ba09"
API = "https://api.ipums.org/extracts"
COLLECTION = "cps"
VERSION = "2"

DATA_LAKE = Path("/Users/azizsunderji/Dropbox/Home Economics/Data/CPS_ASEC")
DATA_LAKE.mkdir(parents=True, exist_ok=True)

PROJECT_DATA = Path(
    "/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity/data"
)

VARIABLES = [
    # ID / weights
    "YEAR", "MONTH", "SERIAL", "PERNUM", "CPSID", "CPSIDP",
    "ASECWT", "ASECWTH", "ASECFLAG",
    # Geography (current) — CPS has STATEFIP, COUNTY (where reported), METAREA, METFIPS
    "STATEFIP", "COUNTY", "METAREA", "METFIPS",
    # Geography (1 year ago) — CPS only has state-level
    "MIGSTA1",
    # Migration
    "MIGRATE1", "WHYMOVE",
    # Demographics
    "AGE", "SEX", "RACE", "HISPAN", "MARST", "RELATE",
    # Household
    "NCHILD", "NCHLT5", "FAMSIZE",
    # Socioeconomic
    "EDUC", "EMPSTAT", "OCC", "IND",
    # Income
    "INCTOT", "INCWAGE", "FTOTVAL",
]

# All ASEC samples 1999-2025 (when WHYMOVE has been asked)
SAMPLES = [f"cps{y}_03s" for y in range(1999, 2026)]


def submit_extract():
    body = {
        "description": "Full ASEC pull for kids-leaving-cities and future migration analyses (WHYMOVE + geography)",
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
        resp = json.loads(r.read())
    return resp


def get_extract(extract_number):
    url = f"{API}/{extract_number}?collection={COLLECTION}&version={VERSION}"
    req = urllib.request.Request(url, headers={"Authorization": IPUMS_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def download_to(url, dst):
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"Authorization": IPUMS_KEY})
    with urllib.request.urlopen(req, timeout=600) as r:
        dst.write_bytes(r.read())
    print(f"  wrote {dst.stat().st_size / 1e6:.1f} MB → {dst}")


def main():
    print(f"Submitting CPS ASEC extract — {len(SAMPLES)} samples, {len(VARIABLES)} variables...")
    try:
        sub = submit_extract()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTPError {e.code}: {body[:500]}")
        raise
    ext_no = sub.get("number")
    print(f"  extract # {ext_no}, status = {sub.get('status')}")

    # Poll
    status = sub.get("status")
    waited = 0
    while status not in ("completed", "failed"):
        time.sleep(20)
        waited += 20
        rec = get_extract(ext_no)
        status = rec.get("status")
        print(f"  t+{waited}s — status: {status}")
        if waited > 3600:
            print("  timeout after 1 hour — aborting poll")
            break

    if status != "completed":
        print(f"Extract did not complete (status={status})")
        return

    # Get download URLs
    rec = get_extract(ext_no)
    download_links = rec.get("downloadLinks", {})
    data_url = (download_links.get("data") or {}).get("url")
    ddi_url = (download_links.get("ddiCodebook") or {}).get("url")
    print(f"  data url: {data_url}")
    print(f"  ddi url: {ddi_url}")

    raw_dir = DATA_LAKE / "raw_extracts"
    raw_dir.mkdir(exist_ok=True)
    data_path = raw_dir / f"cps_asec_full_{ext_no}.csv.gz"
    ddi_path = raw_dir / f"cps_asec_full_{ext_no}.xml"

    download_to(data_url, data_path)
    download_to(ddi_url, ddi_path)

    # Convert to parquet
    print("  converting to parquet via duckdb...")
    import duckdb
    out_path = DATA_LAKE / "cps_asec_full.parquet"
    duckdb.query(f"""
        COPY (SELECT * FROM read_csv_auto('{data_path}', compression = 'gzip', sample_size = 100000))
        TO '{out_path}' (FORMAT 'parquet', COMPRESSION 'zstd')
    """)
    print(f"  wrote {out_path}")

    # Write source metadata
    meta = {
        "source": "IPUMS CPS API",
        "extract_number": ext_no,
        "samples": SAMPLES,
        "variables": VARIABLES,
        "pulled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "files": {
            "parquet": str(out_path),
            "raw_csv_gz": str(data_path),
            "ddi_xml": str(ddi_path),
        },
    }
    (DATA_LAKE / "cps_asec_full.source.json").write_text(json.dumps(meta, indent=2))

    # Quick verification
    n = duckdb.query(f"SELECT COUNT(*) AS n FROM '{out_path}'").df()["n"][0]
    print(f"  parquet row count: {n:,}")
    print("\nDone. Data lake now has cps_asec_full.parquet with WHYMOVE.")


if __name__ == "__main__":
    main()
