"""
src/scraper.py
==============
Phase 2 — Data Acquisition

Responsibility:
    Load raw CSV files from data/raw/, perform minimal structural validation,
    and save a lightly-normalised staging file to data/processed/staging.csv.

    This is NOT the cleaning layer (that is preprocess.py).
    This file only cares about:
        1. Loading data from multiple sources into one DataFrame.
        2. Renaming columns to match our unified schema.
        3. Adding a `source` tag so we know where each row came from.
        4. Dropping completely empty rows.
        5. Saving the combined staging file.

    All heavy cleaning (salary normalisation, skill extraction, city
    canonicalisation, growth scoring) happens in preprocess.py.

Author  : India Job Market Visualizer
Phase   : 2 — Data Acquisition
"""

import os
import hashlib
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Logging setup
# A senior engineer always logs — not print() — so output can be redirected
# to files, monitoring systems, or suppressed in production.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path constants
# Using pathlib.Path (not os.path.join) — more readable, OS-independent.
# ---------------------------------------------------------------------------
ROOT_DIR     = Path(__file__).resolve().parent.parent  # project root
RAW_DIR      = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
STAGING_PATH  = PROCESSED_DIR / "staging.csv"


# ---------------------------------------------------------------------------
# Column mapping dictionaries
# Each dataset has different column names. We map them to our unified schema.
# Add a new entry here whenever you add a new data source.
# ---------------------------------------------------------------------------

# TimesJobs dataset column mapping
# Raw columns vary — update these keys if your CSV headers differ.
TIMESJOBS_COLUMN_MAP = {
    "jobtitle"         : "job_title",
    "job title"        : "job_title",
    "company"          : "company",
    "company name"     : "company",
    "location"         : "city",
    "city"             : "city",
    "experience"       : "experience_raw",    # raw string e.g. "2-5 yrs"
    "salary"           : "salary_raw",        # raw string e.g. "8-12 LPA"
    "education"        : "education",
    "skills"           : "skills_raw",        # comma or pipe separated
    "job description"  : "job_description",
    "jobdescription"   : "job_description",
    "date"             : "posted_date",
    "posted date"      : "posted_date",
}

# Naukri dataset column mapping
NAUKRI_COLUMN_MAP = {
    "job title"        : "job_title",
    "job_title"        : "job_title",
    "company"          : "company",
    "company_name"     : "company",
    "location"         : "city",
    "experience"       : "experience_raw",
    "salary"           : "salary_raw",
    "education"        : "education",
    "key skills"       : "skills_raw",
    "keyskills"        : "skills_raw",
    "job description"  : "job_description",
    "posted_date"      : "posted_date",
    "industry"         : "industry",
    "functional area"  : "job_function",
    "employment type"  : "employment_type",
}


# ---------------------------------------------------------------------------
# Schema columns
# Every row in the staging DataFrame will have exactly these columns.
# Missing values are filled with pd.NA — never dropped at this stage.
# ---------------------------------------------------------------------------
STAGING_COLUMNS = [
    "job_id",
    "source",
    "job_title",
    "company",
    "city",
    "state",
    "industry",
    "employment_type",
    "work_mode",
    "salary_raw",
    "salary_min",
    "salary_max",
    "salary_median",
    "experience_raw",
    "experience_min",
    "experience_max",
    "education",
    "skills_raw",
    "skills",
    "job_description",
    "posted_date",
    "job_count",
    "growth_score",
    "job_title_canonical",
]


# ---------------------------------------------------------------------------
# Helper: generate a deterministic job_id from row content
# Using MD5 of concatenated key fields — fast and collision-resistant enough
# for a dataset of <1M rows.
# ---------------------------------------------------------------------------
def generate_job_id(row: pd.Series) -> str:
    """
    Create a stable unique ID for a job posting from its key fields.

    Why MD5 and not UUID4?
    UUID4 is random — running the ingestion twice gives different IDs for the
    same row. MD5 of the content gives the same ID every time, which means
    we can safely re-run ingestion without creating duplicate rows.
    """
    raw = f"{row.get('job_title', '')}|{row.get('company', '')}|{row.get('city', '')}|{row.get('posted_date', '')}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]   # 16-char hex string


# ---------------------------------------------------------------------------
# Helper: normalise column names before mapping
# Strips whitespace, lowercases — handles "  Job Title ", "JOB TITLE", etc.
# ---------------------------------------------------------------------------
def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase and strip all column names for robust mapping."""
    df.columns = [c.strip().lower() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Core loader: load one CSV file with source tagging and column mapping
# ---------------------------------------------------------------------------
def load_csv(
    file_path: Path,
    column_map: dict,
    source_name: str,
) -> pd.DataFrame:
    """
    Load a single raw CSV file, apply column renaming, and tag with source.

    Parameters
    ----------
    file_path   : path to the raw CSV file
    column_map  : dict mapping raw column names → unified schema names
    source_name : string tag e.g. "timesjobs", "naukri"

    Returns
    -------
    pd.DataFrame with unified column names and a 'source' column added.
    """
    if not file_path.exists():
        log.warning(f"File not found, skipping: {file_path}")
        return pd.DataFrame()   # return empty — don't crash the pipeline

    log.info(f"Loading {source_name} data from: {file_path.name}")
    df = pd.read_csv(file_path, low_memory=False)
    log.info(f"  Raw shape: {df.shape}")

    # Step 1 — normalise column headers
    df = normalise_columns(df)

    # Step 2 — apply the source-specific column mapping
    # Only rename columns that exist in the file — ignore missing ones
    rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
    df = df.rename(columns=rename_dict)
    log.info(f"  Columns mapped: {list(rename_dict.values())}")

    # Step 3 — add source tag
    df["source"] = source_name

    # Step 4 — drop rows where ALL key fields are empty
    # These are structural empties — blank rows at end of CSV, etc.
    key_cols = ["job_title", "company"]
    key_cols_present = [c for c in key_cols if c in df.columns]
    before = len(df)
    df = df.dropna(subset=key_cols_present, how="all")
    dropped = before - len(df)
    if dropped:
        log.info(f"  Dropped {dropped} fully-empty rows")

    log.info(f"  Loaded {len(df)} rows from {source_name}")
    return df


# ---------------------------------------------------------------------------
# Core function: align any loaded DataFrame to the staging schema
# ---------------------------------------------------------------------------
def align_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add any missing staging columns as pd.NA and drop unexpected extras.

    This ensures that regardless of source, every staging row has the
    exact same 24 columns — making the concat in combine_sources() safe.
    """
    for col in STAGING_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA   # add missing columns as empty

    # Keep only the schema columns — drop source-specific extras
    df = df[STAGING_COLUMNS]
    return df


# ---------------------------------------------------------------------------
# Core function: generate job_id for every row after loading
# ---------------------------------------------------------------------------
def add_job_ids(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate a stable job_id for each row using generate_job_id().

    We do this after all sources are loaded so IDs are consistent
    regardless of which file was processed first.
    """
    df["job_id"] = df.apply(generate_job_id, axis=1)
    return df


# ---------------------------------------------------------------------------
# Core function: combine all sources and deduplicate
# ---------------------------------------------------------------------------
def combine_sources(dataframes: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Concatenate all loaded DataFrames, align to schema, generate IDs,
    and deduplicate on job_id.

    Parameters
    ----------
    dataframes : list of DataFrames from load_csv()

    Returns
    -------
    Single combined and deduplicated DataFrame.
    """
    # Filter out empty DataFrames (from files that didn't exist)
    valid_dfs = [df for df in dataframes if not df.empty]

    if not valid_dfs:
        log.error("No data loaded from any source. Check data/raw/ folder.")
        raise ValueError("No valid data sources found.")

    log.info(f"Combining {len(valid_dfs)} data source(s)...")
    combined = pd.concat(valid_dfs, ignore_index=True)
    log.info(f"Combined shape before dedup: {combined.shape}")

    # Align to schema (adds missing columns, removes extras)
    combined = align_to_schema(combined)

    # Generate stable IDs
    combined = add_job_ids(combined)

    # Deduplicate on job_id — keep first occurrence
    before = len(combined)
    combined = combined.drop_duplicates(subset=["job_id"], keep="first")
    dupes = before - len(combined)
    if dupes:
        log.info(f"Removed {dupes} duplicate rows")

    log.info(f"Final staging shape: {combined.shape}")
    return combined


# ---------------------------------------------------------------------------
# Main entry point: run the full ingestion pipeline
# ---------------------------------------------------------------------------
def run_ingestion() -> pd.DataFrame:
    """
    Discover all raw CSV files, load them, combine, and save to staging.

    File discovery logic:
    - Looks for known filenames in data/raw/
    - Falls back to loading ALL CSVs in data/raw/ with the Naukri mapping
      (most common format) if specific files are not found.

    Returns
    -------
    The final staging DataFrame (also saved to data/processed/staging.csv).
    """
    log.info("=" * 50)
    log.info("Phase 2 — Data Ingestion Pipeline")
    log.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 50)

    # Ensure output directory exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    dataframes = []

    # -----------------------------------------------------------------------
    # Known source files — add new sources here as you find better datasets
    # -----------------------------------------------------------------------
    source_configs = [
        {
            "pattern" : "timesjobs",       # matches any filename containing this
            "map"     : TIMESJOBS_COLUMN_MAP,
            "source"  : "timesjobs",
        },
        {
            "pattern" : "naukri",
            "map"     : NAUKRI_COLUMN_MAP,
            "source"  : "naukri",
        },
        {
            "pattern" : "linkedin",
            "map"     : NAUKRI_COLUMN_MAP,  # LinkedIn format is similar to Naukri
            "source"  : "linkedin",
        },
    ]

    # Find matching files in data/raw/
    matched_files = set()

    for config in source_configs:
        # Find files whose name contains the pattern (case-insensitive)
        matches = list(RAW_DIR.glob(f"*{config['pattern']}*"))
        for file_path in matches:
            if file_path.suffix.lower() == ".csv":
                df = load_csv(file_path, config["map"], config["source"])
                dataframes.append(df)
                matched_files.add(file_path)

    # Fallback: load any remaining CSVs with the Naukri mapping
    # This handles the case where the user downloaded a dataset with a
    # different filename — it still gets ingested rather than silently ignored.
    all_csvs = list(RAW_DIR.glob("*.csv"))
    unmatched = [f for f in all_csvs if f not in matched_files]

    if unmatched:
        log.info(f"Found {len(unmatched)} unmatched CSV(s) — loading with default mapping")
        for file_path in unmatched:
            df = load_csv(file_path, NAUKRI_COLUMN_MAP, source_name="unknown")
            dataframes.append(df)

    # Combine all sources
    staging_df = combine_sources(dataframes)

    # Save to staging
    staging_df.to_csv(STAGING_PATH, index=False)
    log.info(f"Staging file saved → {STAGING_PATH}")
    log.info(f"Rows: {len(staging_df):,}  |  Columns: {len(staging_df.columns)}")
    log.info("Ingestion complete. Next: run preprocess.py")

    return staging_df


# ---------------------------------------------------------------------------
# Quick diagnostics: print a summary of the staging file
# ---------------------------------------------------------------------------
def print_staging_summary(df: pd.DataFrame) -> None:
    """
    Print a human-readable data quality summary after ingestion.
    Tells you immediately which fields need the most cleaning attention.
    """
    print("\n" + "=" * 50)
    print("STAGING DATA SUMMARY")
    print("=" * 50)
    print(f"Total rows : {len(df):,}")
    print(f"Sources    : {df['source'].value_counts().to_dict()}")
    print("\nNull counts per column:")
    null_counts = df.isnull().sum().sort_values(ascending=False)
    for col, count in null_counts.items():
        pct = (count / len(df)) * 100
        bar = "█" * int(pct / 5)
        print(f"  {col:<25} {count:>6,} ({pct:5.1f}%) {bar}")
    print("=" * 50)


# ---------------------------------------------------------------------------
# CLI entry point
# Run directly: python src/scraper.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    staging = run_ingestion()
    print_staging_summary(staging)
