"""
Per-county annual decomposition of under-18 change for 22 NYC MSA counties, 2010-2024.

ΔUnder18(y→y+1) = Births(y+1) − AgingOut(y+1) − Deaths_U18(y+1) + NetMig_U18(y+1)
                                                                  └ split into Dom + Intl proportional
                                                                    to PEP county-totals.

Sources:
  Stock under-18 (per panel, used for ΔU18):
    intercensal 2010-2020 (cc-est2020int-agesex) for 2010-2020
    V2024 (v2024-syasex)                          for 2020-2024
  Births by county:
    NCHS WONDER Natality (data/wonder_natality_raw.csv)  2007-2024
    Putnam (36079) is missing from WONDER pull — fill via rate-based estimate later.
  AgingOut18(y+1) approximation:
    = AGE1417 stock at start of year × 0.25 (1 of 4 single-year cohorts ages out)
  Deaths under-18:
    ≈ 40 / 100K × U18 stock (constant approximation; under-18 mortality is very low)
  Migration split:
    NetMig_U18 = ΔU18 − natural_change
    intl_share_county = INTERNATIONALMIG / (INTERNATIONALMIG + DOMESTICMIG) at county-total
    NetMig_U18_intl = NetMig_U18 × intl_share_county   (proportional assumption)
    NetMig_U18_dom  = NetMig_U18 × (1 − intl_share_county)

Output: data/nyc_county_under18_decomposition.csv
"""
import csv
from pathlib import Path

import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"
PEP = DATA / "pep_cache"

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
NYC_FIPS = {st + cf for st, m in NYC_COUNTIES.items() for cf in m}

# Intercensal 2010s YEAR codes: 1=Apr2010, 2-11=Jul2010-2019, 12=Apr2020
IC2010_JUL_YEARS = {2:2010, 3:2011, 4:2012, 5:2013, 6:2014, 7:2015, 8:2016, 9:2017, 10:2018, 11:2019}
# V2024 YEAR codes: 1=Apr2020 Blended Base, 2=Jul2020, ..., 6=Jul2024
V24_JUL_YEARS = {2:2020, 3:2021, 4:2022, 5:2023, 6:2024}


def load_stock_under18_age1417():
    """Returns df with county_fips, year, under18, age1417 — annual July-1, 2010-2024.

    V2024 values are multiplicatively scaled per county to anchor at the intercensal
    April-2020 under-18 value (V2024's "Blended Base" is ~3-6% higher than intercensal,
    so without scaling the 2019→2020 transition would have a spurious upward jump).
    """
    rows = []
    for state in ("34", "36"):
        # Intercensal 2010s
        df = pd.read_csv(PEP / f"cc-est2020int-agesex-{state}.csv",
                         dtype={"STATE": str, "COUNTY": str})
        df = df[df["STATE"] == state]
        df["u18"] = df["UNDER5_TOT"] + df["AGE513_TOT"] + df["AGE1417_TOT"]
        # Get April-2020 anchor per county (year code 12 = Apr 2020 Census)
        apr2020_u18 = df[df["YEAR"] == 12].set_index("COUNTY")["u18"]

        for ycode, year in IC2010_JUL_YEARS.items():
            sub = df[df["YEAR"] == ycode]
            for _, r in sub.iterrows():
                fips = state + r["COUNTY"]
                if fips not in NYC_FIPS:
                    continue
                rows.append({"county_fips": fips, "year": year,
                             "under18": int(r["u18"]), "age1417": int(r["AGE1417_TOT"])})

        # V2024 (single year of age → derive AGE1417), scaled per county
        df2 = pd.read_csv(PEP / f"v2024-syasex-{state}.csv",
                          dtype={"STATE": str, "COUNTY": str})
        df2.columns = [c.replace("﻿", "").strip('"') for c in df2.columns]
        df2 = df2[df2["STATE"] == state]
        # V2024 April-2020 Blended Base per county (year code 1)
        v24_apr2020 = (df2[(df2["YEAR"] == 1) & (df2["AGE"].between(0, 17))]
                       .groupby("COUNTY")["TOT_POP"].sum())

        for ycode, year in V24_JUL_YEARS.items():
            sub = df2[df2["YEAR"] == ycode]
            u18 = (sub[sub["AGE"].between(0, 17)]
                   .groupby("COUNTY")["TOT_POP"].sum())
            age1417 = (sub[sub["AGE"].between(14, 17)]
                       .groupby("COUNTY")["TOT_POP"].sum())
            for cfips in u18.index:
                fips = state + cfips
                if fips not in NYC_FIPS:
                    continue
                # Scale factor for this county
                if cfips in apr2020_u18.index and cfips in v24_apr2020.index:
                    factor = apr2020_u18[cfips] / v24_apr2020[cfips]
                else:
                    factor = 1.0
                rows.append({"county_fips": fips, "year": year,
                             "under18": int(round(u18[cfips] * factor)),
                             "age1417": int(round(age1417[cfips] * factor))})
    return pd.DataFrame(rows)


def load_wonder_births():
    """Returns df county_fips, year, births. Wide format with NYC 22 + some others."""
    rows = []
    with open(DATA / "wonder_natality_raw.csv") as f:
        r = csv.reader(f, delimiter="\t")
        next(r)
        for row in r:
            if len(row) < 6:
                continue
            code = (row[2] or "").strip('"')
            yr = (row[3] or "").strip('"')
            b = row[5] if len(row) > 5 else ""
            if code in NYC_FIPS and yr.isdigit() and b.replace(".", "").isdigit():
                rows.append({"county_fips": code, "year": int(yr),
                             "births": int(float(b))})
    df = pd.DataFrame(rows)
    return df


def estimate_putnam_births(births_df, stock_df):
    """Fill Putnam (36079) births via per-1000 rate from neighboring counties."""
    # Use Westchester (next door, similar profile) crude birth rate
    putnam_existing = births_df[births_df["county_fips"] == "36079"]
    if not putnam_existing.empty:
        return births_df
    # Use NHGIS or PEP for Putnam total pop... fall back to ratio
    # Simpler: Putnam birth rate ≈ 8.5/1000 × total pop. Use under18 stock proxy.
    putnam_u18 = stock_df[stock_df["county_fips"] == "36079"].set_index("year")["under18"]
    # Use national average ~12 births / yr per 100 under-18
    extra = []
    for year, u18 in putnam_u18.items():
        extra.append({"county_fips": "36079", "year": year,
                      "births": int(round(u18 * 0.038))})  # ~38 births / 1000 u18 ≈ 1.7M/45M nationally
    return pd.concat([births_df, pd.DataFrame(extra)], ignore_index=True)


def load_pep_components():
    """Per-county per-year DOMESTICMIG, INTERNATIONALMIG, BIRTHS, DEATHS for 2010-2024."""
    rows = []
    # Dedupe at 2020 boundary: use 2020 from V2024 file, not from 2010-2020 file
    for f, year_start, year_end in [
        ("co-est2020-alldata.csv", 2010, 2019),
        ("co-est2024-alldata.csv", 2020, 2024),
    ]:
        df = pd.read_csv(PEP / f, dtype={"STATE": str, "COUNTY": str}, encoding="latin-1")
        df["STATE"] = df["STATE"].astype(str).str.zfill(2)
        df["COUNTY"] = df["COUNTY"].astype(str).str.zfill(3)
        df["fips"] = df["STATE"] + df["COUNTY"]
        df = df[df["fips"].isin(NYC_FIPS)]
        # The "year" in PEP estimates files refers to interval ending July 1 of that year
        for year in range(year_start, year_end + 1):
            for _, r in df.iterrows():
                rows.append({
                    "county_fips": r["fips"], "year": year,
                    "births_pep": int(r.get(f"BIRTHS{year}", 0) or 0),
                    "deaths_pep": int(r.get(f"DEATHS{year}", 0) or 0),
                    "intl_mig": int(r.get(f"INTERNATIONALMIG{year}", 0) or 0),
                    "dom_mig": int(r.get(f"DOMESTICMIG{year}", 0) or 0),
                })
    return pd.DataFrame(rows)


def main():
    stock = load_stock_under18_age1417()
    print(f"Stock rows: {len(stock)} ({stock['county_fips'].nunique()} counties × {stock['year'].nunique()} years)")

    births = load_wonder_births()
    print(f"WONDER births rows before Putnam fill: {len(births)} ({births['county_fips'].nunique()} counties)")
    births = estimate_putnam_births(births, stock)
    print(f"WONDER births rows after Putnam fill: {len(births)} ({births['county_fips'].nunique()} counties)")

    comp = load_pep_components()
    print(f"PEP component rows: {len(comp)}")

    # Merge stock + births + components
    df = (stock.merge(births, on=["county_fips", "year"], how="left")
                .merge(comp, on=["county_fips", "year"], how="left"))

    # Sort and compute ΔU18 per county
    df = df.sort_values(["county_fips", "year"]).reset_index(drop=True)
    df["u18_next"] = df.groupby("county_fips")["under18"].shift(-1)
    df["delta_u18"] = df["u18_next"] - df["under18"]

    # AgingOut for year y (= turning 18 during y→y+1) approximated as
    # AGE1417 at start of year × 0.25 (one of four cohorts in 14-17 ages out per yr)
    df["aging_out"] = (df["age1417"] * 0.25).round()

    # Deaths under-18 ≈ 40/100k × U18 stock (constant approximation)
    df["deaths_u18"] = (df["under18"] * 0.0004).round()

    # For each interval (year y → y+1), births occur in calendar year y+1
    df["births_yp1"] = df.groupby("county_fips")["births"].shift(-1)

    # Natural change = Births(y+1) − AgingOut(y+1) − Deaths_U18(y+1)
    df["natural_change"] = df["births_yp1"] - df["aging_out"] - df["deaths_u18"]

    # Net migration U18 = residual
    df["net_mig_u18"] = df["delta_u18"] - df["natural_change"]

    # Split U18 net migration into intl + dom.
    # Method: estimate intl_u18 directly as intl_total × U18_AGE_SHARE_INTL (national ACS
    # gives ~20% of international migrants to the US are under 18). Domestic absorbs the
    # residual. Cleaner than proportional sign-flipping when intl and dom have opposite signs.
    U18_AGE_SHARE_INTL = 0.20
    df["intl_mig_yp1"] = df.groupby("county_fips")["intl_mig"].shift(-1)
    df["dom_mig_yp1"] = df.groupby("county_fips")["dom_mig"].shift(-1)
    df["net_mig_u18_intl"] = df["intl_mig_yp1"] * U18_AGE_SHARE_INTL
    df["net_mig_u18_dom"] = df["net_mig_u18"] - df["net_mig_u18_intl"]

    # Drop last year per county (no next-year delta)
    out = df.dropna(subset=["delta_u18"]).copy()

    # Round
    for col in ["aging_out", "deaths_u18", "births_yp1", "natural_change",
                "net_mig_u18", "net_mig_u18_intl", "net_mig_u18_dom"]:
        out[col] = out[col].round().astype("Int64")
    out["delta_u18"] = out["delta_u18"].astype(int)

    out = out[["county_fips", "year",
               "under18", "u18_next", "delta_u18",
               "births_yp1", "aging_out", "deaths_u18", "natural_change",
               "net_mig_u18", "net_mig_u18_dom", "net_mig_u18_intl",
               "intl_mig_yp1", "dom_mig_yp1"]]
    out.columns = ["county_fips", "interval_start",
                   "u18_start", "u18_end", "delta_u18",
                   "births", "aging_out", "deaths_u18", "natural_change",
                   "net_mig_u18", "net_mig_u18_dom", "net_mig_u18_intl",
                   "pep_intl_total", "pep_dom_total"]

    out_path = DATA / "nyc_county_under18_decomposition.csv"
    out.to_csv(out_path, index=False)
    print(f"\nWrote {len(out)} rows → {out_path}")

    # Quick check: NYC 5b sum for 2011→2012
    boros = {"36005", "36047", "36061", "36081", "36085"}
    s = out[out["county_fips"].isin(boros) & (out["interval_start"] == 2011)]
    print("\nNYC 5-borough decomposition for 2011→2012 (validation):")
    print(s[["county_fips", "delta_u18", "births", "aging_out", "natural_change",
             "net_mig_u18", "net_mig_u18_dom", "net_mig_u18_intl"]].to_string(index=False))
    print(f"Sum delta:    {s['delta_u18'].sum():+,}")
    print(f"Sum natural:  {s['natural_change'].sum():+,}")
    print(f"Sum net mig:  {s['net_mig_u18'].sum():+,}")


if __name__ == "__main__":
    main()
