"""
Submit IPUMS USA extract — under-18 population by METRO category, 1950-2024.

Decennial 1% / 5% samples 1950-2000 + ACS 1-year 2005-2024 (skipping experimental 2020).
Variables: YEAR, SAMPLE, AGE, METRO, PERWT.
Filter: AGE < 18 (case selection in extract config) to keep download size manageable.

Output: data/ipums_usa_kids_metro.parquet
Codebook + raw csv kept alongside.

API: https://developer.ipums.org/docs/v2/apiprogram/
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

# Decennial long-form samples (smallest available where METRO is defined consistently).
# 1950, 1960: 1% sample. 1970: 1% Form 1 State. 1980/90/2000: 5% samples (no smaller long-form alt).
# ACS 1-year samples 2005-2024, skipping 2020 (experimental, not standard release).
DECENNIAL = ["us1950a", "us1960a", "us1970a", "us1980a", "us1990a", "us2000a"]
ACS_YEARS = [y for y in range(2005, 2025) if y != 2020]
ACS = [f"us{y}a" for y in ACS_YEARS]
SAMPLES = DECENNIAL + ACS

VARIABLES = ["YEAR", "SAMPLE", "AGE", "METRO", "PERWT"]

# Case selection — restrict to under-18 only (massive download size reduction).
CASE_SELECTIONS = {"AGE": {"generalDetailed": "general", "caseSelections": [str(a) for a in range(0, 18)]}}


def submit_extract():
    body = {
        "description": "Under-18 population by METRO (central city / suburb / non-metro), 1950-2024 — for kids-leaving-cities project",
        "dataStructure": {"rectangular": {"on": "P"}},
        "dataFormat": "csv",
        "samples": {s: {} for s in SAMPLES},
        "variables": {
            v: ({"caseSelections": {"general": [str(a) for a in range(0, 18)]}} if v == "AGE" else {})
            for v in VARIABLES
        },
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
    print(f"  wrote {dst.stat().st_size / 1e6:.1f} MB → {dst}")


def main():
    print(f"Submitting IPUMS USA extract — {len(SAMPLES)} samples, {len(VARIABLES)} variables, AGE<18 filter...")
    print(f"  samples: {SAMPLES}")
    try:
        sub = submit_extract()
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTPError {e.code}: {body[:2000]}")
        raise
    ext_no = sub.get("number")
    print(f"  extract # {ext_no}, status = {sub.get('status')}")
    (PROJECT_DATA / "ipums_usa_kids_metro.extract.json").write_text(json.dumps(sub, indent=2))

    # Poll
    status = sub.get("status")
    waited = 0
    while status not in ("completed", "failed"):
        time.sleep(30)
        waited += 30
        rec = get_extract(ext_no)
        status = rec.get("status")
        print(f"  t+{waited}s — status: {status}")
        if waited > 5400:  # 90 min timeout
            print("  timeout after 90 min — aborting poll")
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
    data_path = raw_dir / f"ipums_usa_kids_metro_{ext_no}.csv.gz"
    ddi_path = raw_dir / f"ipums_usa_kids_metro_{ext_no}.xml"

    download_to(data_url, data_path)
    download_to(ddi_url, ddi_path)

    # Convert to parquet
    print("  converting to parquet...")
    import duckdb

    out_path = PROJECT_DATA / "ipums_usa_kids_metro.parquet"
    duckdb.query(
        f"""
        COPY (SELECT * FROM read_csv_auto('{data_path}', compression = 'gzip', sample_size = 100000))
        TO '{out_path}' (FORMAT 'parquet', COMPRESSION 'zstd')
        """
    )
    print(f"  wrote {out_path}")

    n = duckdb.query(f"SELECT COUNT(*) AS n FROM '{out_path}'").df()["n"][0]
    print(f"  parquet row count: {n:,}")

    meta = {
        "source": "IPUMS USA API",
        "extract_number": ext_no,
        "collection": COLLECTION,
        "samples": SAMPLES,
        "variables": VARIABLES,
        "filter": "AGE<18 (case selection)",
        "pulled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "files": {
            "parquet": str(out_path),
            "raw_csv_gz": str(data_path),
            "ddi_xml": str(ddi_path),
        },
    }
    (PROJECT_DATA / "ipums_usa_kids_metro.source.json").write_text(json.dumps(meta, indent=2))
    print("\nDone.")


if __name__ == "__main__":
    main()
