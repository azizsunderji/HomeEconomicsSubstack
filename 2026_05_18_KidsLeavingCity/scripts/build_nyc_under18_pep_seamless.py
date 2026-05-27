"""
Build a seamless annual under-18 series for the 22 NYC MSA counties, 1980-2024,
by stacking five PEP / intercensal releases. Per-county correction factors are
LINEARLY INTERPOLATED across each decade so the series passes through the actual
NHGIS Decennial Census anchor at every decade boundary.

Data sources:
  1980s  pe-02-19YY.csv (10 files)  — intercensal 5-year groups; under-15.
         Convert to u18 via per-county u18/u15 ratio that linearly interpolates
         from the 1980 Decennial ratio to the 1990 Decennial ratio.
  1990s  cany9Y.txt / canj9Y.txt    — postcensal cany files have direct under-18.
         Apply per-county correction factor that linearly interpolates from
         (NHGIS_1990/cany90) at y=1990 to (NHGIS_2000/cany99) at y=1999. cany
         is anchored to 1990 Decennial so the y=1990 factor is ≈ 1.0; drift to
         1999 gets corrected smoothly to land on 2000 Decennial.
  2000-2010  co-est00int-alldata    — intercensal 5-year groups. Convert under-15
         to under-18 via per-county ratio interpolated from 2000 to 2010 Decennials.
  2010-2020  cc-est2020int-agesex   — intercensal exact under-18.
  2020-2024  v2024-syasex           — sum 0-17; scaled per county to intercensal
         April-2020 anchor (V2024 Blended Base differs from raw 2020 Census).

NHGIS time-series file nhgis0121_ts_nominal_county.csv provides D08AA (Persons:
Under 18 years) at every Decennial 1970-2010 for every county. We use 1980,
1990, 2000, 2010 as anchors. For 2020 we use the intercensal April-2020 value.
For 1990 under-15 we sum single-year-age cells ET3001-ET3009 from the NHGIS
ds120 (1990 full-detail) county file.

Output: data/nyc_county_under18_pep_seamless.csv
"""
import csv
import re
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
PEP = DATA / "pep_cache"
PRE = PEP / "pre2000"
NHGIS_TS = DATA / "nhgis0121" / "nhgis0121_csv" / "nhgis0121_ts_nominal_county.csv"
NHGIS_1990 = DATA / "nhgis0123" / "nhgis0123_csv" / "nhgis0123_ds120_1990_county.csv"

NYC_COUNTIES = {
    "34": {
        "003": "Bergen", "013": "Essex", "017": "Hudson",
        "019": "Hunterdon", "023": "Middlesex", "025": "Monmouth",
        "027": "Morris", "029": "Ocean", "031": "Passaic",
        "035": "Somerset", "037": "Sussex", "039": "Union",
    },
    "36": {
        "005": "Bronx", "047": "Kings (Brooklyn)", "059": "Nassau",
        "061": "New York (Manhattan)", "079": "Putnam", "081": "Queens",
        "085": "Richmond (Staten Island)", "087": "Rockland",
        "103": "Suffolk", "119": "Westchester",
    },
}
NYC_FIPS_SET = {st + cf for st, m in NYC_COUNTIES.items() for cf in m}

COUNTY_NAME_TO_FIPS_1990s = {
    "Bergen County": "34003", "Essex County": "34013", "Hudson County": "34017",
    "Hunterdon County": "34019", "Middlesex County": "34023", "Monmouth County": "34025",
    "Morris County": "34027", "Ocean County": "34029", "Passaic County": "34031",
    "Somerset County": "34035", "Sussex County": "34037", "Union County": "34039",
    "Bronx County": "36005", "Kings County": "36047", "Nassau County": "36059",
    "New York County": "36061", "Putnam County": "36079", "Queens County": "36081",
    "Richmond County": "36085", "Rockland County": "36087",
    "Suffolk County": "36103", "Westchester County": "36119",
}

IC2000_JULY_YEARS = {2:2000, 3:2001, 4:2002, 5:2003, 6:2004, 7:2005, 8:2006, 9:2007, 10:2008, 11:2009}
IC2010_JULY_YEARS = {2:2010, 3:2011, 4:2012, 5:2013, 6:2014, 7:2015, 8:2016, 9:2017, 10:2018, 11:2019}
V24_JULY_YEARS = {2:2020, 3:2021, 4:2022, 5:2023, 6:2024}


# ---------- Anchor loaders ----------

def load_nhgis_anchors() -> dict:
    """Per-county dict: fips → {1980: u18, 1990: u18, 2000: u18, 2010: u18, 1990_u15: ...}"""
    ts = pd.read_csv(NHGIS_TS, dtype={"STATEFP": str, "COUNTYFP": str})
    ts["fips"] = ts["STATEFP"] + ts["COUNTYFP"]
    ts = ts[ts["fips"].isin(NYC_FIPS_SET)]
    out = {fips: {} for fips in NYC_FIPS_SET}
    for _, r in ts.iterrows():
        out[r["fips"]][int(r["YEAR"])] = {"u18": int(r["D08AA"])}

    # 1990 under-15 from single-year-age 1990 file
    nh90 = pd.read_csv(NHGIS_1990, dtype={"STATEA": str, "COUNTYA": str})
    nh90["fips"] = nh90["STATEA"] + nh90["COUNTYA"]
    nh90 = nh90[nh90["fips"].isin(NYC_FIPS_SET)]
    u15_cols = [f"ET3{str(i).zfill(3)}" for i in range(1, 10)]  # ages 0-14
    nh90["u15_1990"] = nh90[u15_cols].sum(axis=1)
    for _, r in nh90.iterrows():
        out[r["fips"]]["u15_1990"] = int(r["u15_1990"])
    return out


# ---------- Source loaders ----------

def load_1990s_cany_u18() -> pd.DataFrame:
    rows = []
    for st in ("ny", "nj"):
        for yy in range(90, 100):
            year = 1900 + yy
            path = PRE / f"ca{st}{yy:02d}.txt"
            for line in path.read_text(encoding="latin-1").splitlines():
                m = re.match(r"^(.+?County)\s+([\d ]+)$", line.rstrip())
                if not m:
                    continue
                name = m.group(1).strip()
                if name not in COUNTY_NAME_TO_FIPS_1990s:
                    continue
                fips = COUNTY_NAME_TO_FIPS_1990s[name]
                if fips[:2] != ("36" if st == "ny" else "34"):
                    continue
                nums = [int(x) for x in m.group(2).split()]
                if len(nums) < 3:
                    continue
                rows.append({"county_fips": fips, "year": year,
                             "under18": nums[1] + nums[2]})
    return pd.DataFrame(rows)


def load_1980s_pe02_u15() -> pd.DataFrame:
    rows = []
    for year in range(1980, 1990):
        path = PRE / f"pe-02-{year}.csv"
        df = pd.read_csv(path, skiprows=5, dtype={"FIPS State and County Codes": str})
        df = df.rename(columns={"Year of Estimate": "year",
                                "FIPS State and County Codes": "fips"})
        df = df.dropna(subset=["fips"])
        df["fips"] = df["fips"].str.zfill(5)
        df = df[df["fips"].isin(NYC_FIPS_SET)]
        for col in ["Under 5 years", "5 to 9 years", "10 to 14 years"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        u15 = (df.groupby("fips")[["Under 5 years", "5 to 9 years", "10 to 14 years"]]
                 .sum().sum(axis=1).astype(int))
        for fips, val in u15.items():
            rows.append({"county_fips": fips, "year": year, "under15": int(val)})
    return pd.DataFrame(rows)


def load_2000s_u15(state: str) -> pd.DataFrame:
    df = pd.read_csv(PEP / f"co-est00int-alldata-{state}.csv",
                     dtype={"STATE": str, "COUNTY": str}, encoding="latin-1")
    df = df[df["STATE"] == state]
    u15 = (df[df["AGEGRP"].isin([1, 2, 3])]
           .groupby(["STATE", "COUNTY", "YEAR"])["TOT_POP"].sum()
           .reset_index().rename(columns={"TOT_POP": "u15"}))
    return u15


def load_2010s_u18(state: str) -> pd.DataFrame:
    df = pd.read_csv(PEP / f"cc-est2020int-agesex-{state}.csv",
                     dtype={"STATE": str, "COUNTY": str})
    df = df[df["STATE"] == state]
    df["u18"] = df["UNDER5_TOT"] + df["AGE513_TOT"] + df["AGE1417_TOT"]
    return df[["STATE", "COUNTY", "YEAR", "u18"]]


def load_v2024_u18(state: str) -> pd.DataFrame:
    df = pd.read_csv(PEP / f"v2024-syasex-{state}.csv",
                     dtype={"STATE": str, "COUNTY": str})
    df.columns = [c.replace("﻿", "").strip('"') for c in df.columns]
    df = df[df["STATE"] == state]
    u18 = (df[df["AGE"].between(0, 17)]
           .groupby(["STATE", "COUNTY", "YEAR"])["TOT_POP"].sum()
           .reset_index().rename(columns={"TOT_POP": "u18"}))
    return u18


# ---------- Main ----------

def lerp(a, b, t):
    return a + (b - a) * t


def main():
    anchors = load_nhgis_anchors()
    df_1990s_u18 = load_1990s_cany_u18()
    df_1980s_u15 = load_1980s_pe02_u15()
    rows_out = []

    for state, counties in NYC_COUNTIES.items():
        ic_2000s = load_2000s_u15(state)
        ic_2010s = load_2010s_u18(state)
        v24 = load_v2024_u18(state)

        for cfips, cname in counties.items():
            full = state + cfips
            anc = anchors[full]

            # ---- 2010-2020 anchor (April-2020 Decennial = year 12) ----
            u18_apr2020 = ic_2010s[(ic_2010s["COUNTY"] == cfips) &
                                    (ic_2010s["YEAR"] == 12)]["u18"].iloc[0]

            # ---- V2024 scaling (one factor, no interpolation needed) ----
            u18_apr2020_v24 = v24[(v24["COUNTY"] == cfips) &
                                   (v24["YEAR"] == 1)]["u18"].iloc[0]
            factor_v24 = u18_apr2020 / u18_apr2020_v24

            # ---- 2000s u15→u18 ratio, interpolated decennial 2000→2010 ----
            u18_2000_anc = anc[2000]["u18"]
            u18_2010_anc = anc[2010]["u18"]
            u15_apr2000 = ic_2000s[(ic_2000s["COUNTY"] == cfips) &
                                    (ic_2000s["YEAR"] == 1)]["u15"].iloc[0]
            u15_apr2010 = ic_2000s[(ic_2000s["COUNTY"] == cfips) &
                                    (ic_2000s["YEAR"] == 12)]["u15"].iloc[0]
            ratio_2000 = u18_2000_anc / u15_apr2000  # u18/u15 at April 2000
            ratio_2010 = u18_2010_anc / u15_apr2010  # u18/u15 at April 2010

            # ---- 1990s cany correction factor: 1.0 at 1990 → drift_corr at 1999 ----
            cany_1990_raw = df_1990s_u18[(df_1990s_u18["county_fips"] == full) &
                                          (df_1990s_u18["year"] == 1990)]["under18"].iloc[0]
            cany_1999_raw = df_1990s_u18[(df_1990s_u18["county_fips"] == full) &
                                          (df_1990s_u18["year"] == 1999)]["under18"].iloc[0]
            u18_1990_anc = anc[1990]["u18"]
            # Target for 1999: extrapolate decennial 1990→2000 by 9/10 of the way
            target_1999 = u18_1990_anc + (u18_2000_anc - u18_1990_anc) * (9 / 10)
            factor_cany_1990 = u18_1990_anc / cany_1990_raw
            factor_cany_1999 = target_1999 / cany_1999_raw

            # ---- 1980s u15→u18 ratio, interpolated decennial 1980→1990 ----
            u18_1980_anc = anc[1980]["u18"]
            pe02_1980_u15 = df_1980s_u15[(df_1980s_u15["county_fips"] == full) &
                                          (df_1980s_u15["year"] == 1980)]["under15"].iloc[0]
            u15_1990_anc = anc["u15_1990"]
            ratio_1980 = u18_1980_anc / pe02_1980_u15
            ratio_1990 = u18_1990_anc / u15_1990_anc

            # --- Emit 1980-1989 ---
            for yr in range(1980, 1990):
                u15 = df_1980s_u15[(df_1980s_u15["county_fips"] == full) &
                                    (df_1980s_u15["year"] == yr)]["under15"]
                if u15.empty:
                    continue
                t = (yr - 1980) / 10  # 0 at 1980, 1 at 1990
                ratio_y = lerp(ratio_1980, ratio_1990, t)
                est = int(round(u15.iloc[0] * ratio_y))
                rows_out.append({"county_fips": full, "county_name": cname,
                                 "year": yr, "under18": est,
                                 "source": "1980s_pe02_u15interp",
                                 "scale_factor": round(ratio_y, 5)})

            # --- Emit 1990-1999 ---
            for yr in range(1990, 2000):
                raw = df_1990s_u18[(df_1990s_u18["county_fips"] == full) &
                                    (df_1990s_u18["year"] == yr)]["under18"]
                if raw.empty:
                    continue
                t = (yr - 1990) / 9  # 0 at 1990, 1 at 1999
                factor_y = lerp(factor_cany_1990, factor_cany_1999, t)
                est = int(round(raw.iloc[0] * factor_y))
                rows_out.append({"county_fips": full, "county_name": cname,
                                 "year": yr, "under18": est,
                                 "source": "1990s_cany_interp",
                                 "scale_factor": round(factor_y, 5)})

            # --- Emit 2000-2009 ---
            for ycode, yr in IC2000_JULY_YEARS.items():
                u15 = int(ic_2000s[(ic_2000s["COUNTY"] == cfips) &
                                    (ic_2000s["YEAR"] == ycode)]["u15"].iloc[0])
                t = (yr - 2000) / 10  # 0 at 2000, 1 at 2010
                ratio_y = lerp(ratio_2000, ratio_2010, t)
                est = int(round(u15 * ratio_y))
                rows_out.append({"county_fips": full, "county_name": cname,
                                 "year": yr, "under18": est,
                                 "source": "intercensal_2000-2010_u15interp",
                                 "scale_factor": round(ratio_y, 5)})

            # --- Emit 2010-2019 (intercensal direct u18) ---
            for ycode, yr in IC2010_JULY_YEARS.items():
                v = int(ic_2010s[(ic_2010s["COUNTY"] == cfips) &
                                  (ic_2010s["YEAR"] == ycode)]["u18"].iloc[0])
                rows_out.append({"county_fips": full, "county_name": cname,
                                 "year": yr, "under18": v,
                                 "source": "intercensal_2010-2020",
                                 "scale_factor": 1.0})

            # --- Emit 2020-2024 ---
            for ycode, yr in V24_JULY_YEARS.items():
                raw = int(v24[(v24["COUNTY"] == cfips) &
                               (v24["YEAR"] == ycode)]["u18"].iloc[0])
                est = int(round(raw * factor_v24))
                rows_out.append({"county_fips": full, "county_name": cname,
                                 "year": yr, "under18": est,
                                 "source": "v2024_scaled",
                                 "scale_factor": round(factor_v24, 5)})

            print(f"  {full} {cname:24s}: "
                  f"80s ratio {ratio_1980:.3f}→{ratio_1990:.3f}  "
                  f"90s factor {factor_cany_1990:.3f}→{factor_cany_1999:.3f}  "
                  f"00s ratio {ratio_2000:.3f}→{ratio_2010:.3f}  "
                  f"v24 ×{factor_v24:.4f}")

    out_path = DATA / "nyc_county_under18_pep_seamless.csv"
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "county_fips", "county_name", "year", "under18",
            "source", "scale_factor",
        ])
        w.writeheader()
        w.writerows(rows_out)
    print(f"\nWrote {len(rows_out)} rows → {out_path}")


if __name__ == "__main__":
    main()
