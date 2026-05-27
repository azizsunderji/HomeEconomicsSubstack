"""Poll extract #122 and download when ready."""
import time, requests, json, sys
from pathlib import Path

API_KEY = "59cba10d8a5da536fc06b59d2762e4c5859b48dbb5215e13b449ba09"
EXTRACT = sys.argv[1] if len(sys.argv) > 1 else "122"
BASE = "https://api.ipums.org"
HDRS = {"Authorization": API_KEY}
DATA = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity/data")

for attempt in range(80):
    time.sleep(15)
    r = requests.get(f"{BASE}/extracts/{EXTRACT}?collection=nhgis&version=2", headers=HDRS, timeout=30)
    s = r.json()
    print(f"  attempt {attempt}: status={s.get('status')}")
    if s.get("status") == "completed":
        print("Download URLs:")
        for k, v in s.get("downloadLinks", {}).items():
            print(f"  {k}: {v.get('url')}")
        # Download table data
        td = s["downloadLinks"]["tableData"]["url"]
        zip_name = td.split("/")[-1]
        out_path = DATA / zip_name
        with requests.get(td, headers=HDRS, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
        print(f"Wrote {out_path}")
        break
    if s.get("status") in ("failed", "canceled"):
        print(f"FAILED: {json.dumps(s, indent=2)}")
        break
