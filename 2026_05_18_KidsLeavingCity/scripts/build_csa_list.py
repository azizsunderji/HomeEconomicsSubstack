"""
Build a CSA-based county list for the 10 biggest metros.
CSAs include adjacent commute-belt MSAs — e.g., LA CSA adds Riverside,
San Bernardino, Ventura.
"""
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

TARGET_CSAS = {
    "408": "New York-Newark, NY-NJ-CT-PA",
    "348": "Los Angeles-Long Beach, CA",
    "176": "Chicago-Naperville, IL-IN-WI",
    "206": "Dallas-Fort Worth, TX-OK",
    "288": "Houston-Pasadena, TX",
    "122": "Atlanta--Athens-Clarke County--Sandy Springs, GA-AL",
    "548": "Washington-Baltimore-Arlington, DC-MD-VA-WV-PA",
    "428": "Philadelphia-Reading-Camden, PA-NJ-DE-MD",
    "370": "Miami-Port St. Lucie-Fort Lauderdale, FL",
    "429": "Phoenix-Mesa, AZ",
}

INNER_BY_CSA = {  # central / "urban core" counties per CSA
    "408": [(36, 5), (36, 47), (36, 61), (36, 81), (36, 85)],  # 5 NYC boroughs
    "348": [(6, 37)],                                            # LA County
    "176": [(17, 31)],                                           # Cook County
    "206": [(48, 113), (48, 439)],                               # Dallas + Tarrant
    "288": [(48, 201)],                                          # Harris
    "122": [(13, 121), (13, 89)],                                # Fulton + DeKalb
    "548": [(11, 1), (51, 13), (51, 510), (24, 510)],            # DC + Arlington + Alexandria + Baltimore city
    "428": [(42, 101)],                                          # Philadelphia
    "370": [(12, 86)],                                           # Miami-Dade
    "429": [(4, 13)],                                            # Maricopa
}


def short_name(title: str) -> str:
    return title.split(",")[0].split("--")[0].split("-")[0].strip()


def main():
    raw = pd.read_excel(DATA / "omb_msa_delineation.xlsx", sheet_name=0, header=None)
    header_idx = None
    for i, row in raw.iterrows():
        if any("CBSA Code" == str(c).strip() for c in row.values):
            header_idx = i
            break
    df = pd.read_excel(DATA / "omb_msa_delineation.xlsx", sheet_name=0, header=header_idx)
    df["CSA Code"] = df["CSA Code"].astype(str).str.split(".").str[0]

    out = df[df["CSA Code"].isin(TARGET_CSAS.keys())].copy()
    out["state_fips"] = out["FIPS State Code"].astype(int).astype(str).str.zfill(2)
    out["county_fips"] = out["FIPS County Code"].astype(int).astype(str).str.zfill(3)
    out["fips_5"] = out["state_fips"] + out["county_fips"]
    out["csa_short"] = out["CSA Code"].map(lambda c: short_name(TARGET_CSAS[c]))
    inner_set = {f"{s:02d}{c:03d}" for codes in INNER_BY_CSA.values() for s, c in codes}
    out["is_inner"] = out["fips_5"].isin(inner_set)

    keep = ["CSA Code", "csa_short", "CSA Title", "County/County Equivalent",
            "State Name", "state_fips", "county_fips", "fips_5", "is_inner"]
    keep = [c for c in keep if c in out.columns]
    out = out[keep].rename(columns={"CSA Code": "csa_code"})
    out.to_csv(DATA / "csa_counties.csv", index=False)
    print(f"Wrote {len(out)} counties → csa_counties.csv")
    by_csa = out.groupby("csa_short").size().sort_values(ascending=False)
    print(by_csa.to_string())

    # States touched
    states = sorted(out["state_fips"].unique())
    print(f"\nStates touched: {len(states)} — {', '.join(states)}")


if __name__ == "__main__":
    main()
