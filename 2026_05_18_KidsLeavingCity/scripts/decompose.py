"""
Merge PEP + CDC WONDER natality data; compute per-county decomposition of the
under-18 population change from July 1, 2011 to July 1, 2024.

Decomposition identity (per county):

  ΔPop_under18 = Births_to_residents_2012_to_2024
               − Pop_aged_5_to_17(2011)            (aging-out term)
               − Deaths_under18_2012_to_2024       (set to 0 for first pass)
               + Net_migration_under18             (implied as residual)

Note on years: we use 13 calendar years of births (2012-2024) to bridge the
13-year window from July 1, 2011 → July 1, 2024. Births during 2012-2024 are
approximately the new entries to the under-18 cohort during that window.
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
DATA = PROJECT / "data"

PEP_2011 = DATA / "pep_2011.csv"
PEP_2024 = DATA / "pep_2024.csv"
COUNTIES = DATA / "counties_in_scope.csv"
WONDER_BIRTHS = DATA / "wonder_natality_raw.csv"
OUT = DATA / "decomposition.csv"


def load_wonder_births() -> pd.DataFrame:
    """Parse the CDC WONDER natality CSV the user downloaded.

    WONDER's CSV exports include several footer lines starting with '---'
    or '"Notes"', plus blank lines. We just keep the data rows.
    """
    if not WONDER_BIRTHS.exists():
        raise FileNotFoundError(
            f"{WONDER_BIRTHS} not found — user needs to grab the CSV from WONDER first"
        )
    # WONDER CSVs are tab-separated despite the .csv extension; auto-detect
    raw = WONDER_BIRTHS.read_text(errors="replace")
    # Heuristic split
    sep = "\t" if raw.count("\t") > raw.count(",") else ","
    df = pd.read_csv(WONDER_BIRTHS, sep=sep, dtype=str, engine="python",
                     on_bad_lines="skip", comment=None)
    print(f"WONDER raw shape: {df.shape}; cols: {list(df.columns)}")

    # Normalize column names (WONDER uses 'County', 'County Code', 'Year', 'Year Code', 'Births').
    # Only map one Year column to avoid duplicate column names.
    rename = {}
    year_mapped = False
    for c in df.columns:
        cl = c.strip().lower()
        if cl == "county":
            rename[c] = "county_name"
        elif cl in ("county code", "residence county code", "county of residence code"):
            rename[c] = "fips_5"
        elif cl in ("year", "year of birth") and not year_mapped:
            rename[c] = "year"
            year_mapped = True
        elif cl == "year code" and not year_mapped:
            rename[c] = "year"
            year_mapped = True
        elif cl in ("births", "deaths", "count"):
            rename[c] = "births"
        elif cl == "notes":
            rename[c] = "_notes"
    df = df.rename(columns=rename)
    # Drop any leftover unrenamed duplicate columns (e.g., Year Code if Year already mapped)
    df = df.loc[:, ~df.columns.duplicated()]

    # Keep only data rows (drop the "Total", "---" footer notes etc.)
    if "_notes" in df.columns:
        df = df[df["_notes"].isna() | (df["_notes"].astype(str).str.strip() == "")]

    df = df.dropna(subset=["fips_5", "year", "births"])
    df = df[df["year"].astype(str).str.isdigit()]
    df["year"] = df["year"].astype(int)
    df["fips_5"] = df["fips_5"].astype(str).str.zfill(5)
    # 'Births' can be 'Suppressed' or 'Not Available' for tiny cells
    df["births"] = pd.to_numeric(df["births"], errors="coerce")
    print(f"WONDER cleaned shape: {df.shape}")
    print(f"WONDER year range: {df['year'].min()}–{df['year'].max()}")
    return df


def main():
    counties = pd.read_csv(COUNTIES, dtype=str)
    counties["fips_5"] = counties["fips_5"].str.zfill(5)
    pep11 = pd.read_csv(PEP_2011, dtype={"fips_5": str})
    pep24 = pd.read_csv(PEP_2024, dtype={"fips_5": str})
    pep11["fips_5"] = pep11["fips_5"].str.zfill(5)
    pep24["fips_5"] = pep24["fips_5"].str.zfill(5)
    print(f"counties: {len(counties)}, pep11: {len(pep11)}, pep24: {len(pep24)}")

    # Build the base frame
    df = counties[["fips_5", "msa_name_short", "County/County Equivalent",
                   "state_fips", "cbsa_code"]].copy()
    df = df.merge(pep11[["fips_5", "pop_under18", "aged_out_5_17"]], on="fips_5", how="left")
    df = df.merge(pep24[["fips_5", "pop_under18_2024"]], on="fips_5", how="left")
    df["delta_under18"] = df["pop_under18_2024"] - df["pop_under18"]

    # Births: sum 2012-2024
    if WONDER_BIRTHS.exists():
        births_df = load_wonder_births()
        births_window = births_df[
            (births_df["year"] >= 2012) & (births_df["year"] <= 2024)
        ]
        births_sum = (
            births_window.groupby("fips_5")["births"].sum().rename("births_2012_2024")
        )
        df = df.merge(births_sum, left_on="fips_5", right_index=True, how="left")
    else:
        print(f"⚠ {WONDER_BIRTHS} not found; will leave births_2012_2024 blank")
        df["births_2012_2024"] = None

    # Decomposition. Deaths set to 0 for first pass.
    df["deaths_2012_2024"] = 0
    df["net_migration_implied"] = (
        df["delta_under18"]
        - df["births_2012_2024"]
        + df["aged_out_5_17"]
        + df["deaths_2012_2024"]
    )

    # Component shares (each as % of pop_under18(2011))
    base = df["pop_under18"]
    df["delta_pct_of_baseline"] = df["delta_under18"] / base * 100
    df["births_pct_of_baseline"] = df["births_2012_2024"] / base * 100
    df["aging_out_pct_of_baseline"] = -df["aged_out_5_17"] / base * 100
    df["net_mig_pct_of_baseline"] = df["net_migration_implied"] / base * 100

    df.to_csv(OUT, index=False)
    print(f"\nWrote {OUT} ({len(df)} rows)")

    # Sanity check
    missing_pep = df["pop_under18"].isna().sum() + df["pop_under18_2024"].isna().sum()
    missing_births = df["births_2012_2024"].isna().sum()
    print(f"Missing PEP cells: {missing_pep}; missing births: {missing_births}")

    # Preview
    if not df["net_migration_implied"].isna().all():
        print("\nLargest implied net out-migration (top 10):")
        print(
            df.nsmallest(10, "net_migration_implied")[
                ["fips_5", "County/County Equivalent", "msa_name_short",
                 "pop_under18", "pop_under18_2024", "delta_under18",
                 "births_2012_2024", "aged_out_5_17", "net_migration_implied"]
            ].to_string(index=False)
        )
        print("\nLargest implied net in-migration (top 10):")
        print(
            df.nlargest(10, "net_migration_implied")[
                ["fips_5", "County/County Equivalent", "msa_name_short",
                 "pop_under18", "pop_under18_2024", "delta_under18",
                 "births_2012_2024", "aged_out_5_17", "net_migration_implied"]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
