"""
src/scraper.py
==============
Phase 4 — Data Acquisition

Reads raw data files from data/raw/, normalises column names
to the unified schema, combines all sources, and writes
data/processed/staging.csv.

Handles two file formats found in our dataset:
    - Standard CSV  (india_jobs_naukri_01.csv)
    - NDJSON        (india_jobs_naukri_02.csv — one JSON per line)

Run from project root:
    python src/scraper.py
"""

import os
import json
import hashlib
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR      = Path(__file__).resolve().parent.parent
RAW_DIR       = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
STAGING_PATH  = PROCESSED_DIR / "staging.csv"

# ---------------------------------------------------------------------------
# Unified schema columns
# Every row in staging.csv will have exactly these columns.
# Missing values are pd.NA — never dropped at this stage.
# ---------------------------------------------------------------------------
SCHEMA = [
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
    "experience_raw",
    "education",
    "skills_raw",
    "job_description",
    "posted_date",
]

# ---------------------------------------------------------------------------
# Column maps — translate raw column names to our unified schema
# ---------------------------------------------------------------------------

# File 1: india_jobs_naukri_01.csv
# Raw columns: company, education, experience, industry, jobdescription,
#              jobid, joblocation_address, jobtitle, numberofpositions,
#              payrate, postdate, site_name, skills, uniq_id
CSV_COLUMN_MAP = {
    "jobtitle"            : "job_title",
    "company"             : "company",
    "joblocation_address" : "city",
    "industry"            : "industry",
    "jobdescription"      : "job_description",
    "payrate"             : "salary_raw",
    "experience"          : "experience_raw",
    "education"           : "education",
    "skills"              : "skills_raw",
    "postdate"            : "posted_date",
    "uniq_id"             : "_source_id",
}

# File 2: india_jobs_naukri_02.csv (NDJSON)
# Raw fields: uniq_id, crawl_timestamp, url, job_title, category,
#             company_name, city, state, country, post_date,
#             job_description
NDJSON_COLUMN_MAP = {
    "job_title"       : "job_title",
    "company_name"    : "company",
    "city"            : "city",
    "state"           : "state",
    "category"        : "industry",
    "job_description" : "job_description",
    "post_date"       : "posted_date",
    "uniq_id"         : "_source_id",
}


# ---------------------------------------------------------------------------
# Helper: generate a stable job_id from row content
# MD5 of key fields — same input always gives same ID.
# This means re-running ingestion never creates duplicate rows.
# ---------------------------------------------------------------------------
def make_job_id(row: pd.Series) -> str:
    raw = (
        str(row.get("job_title", "")) + "|" +
        str(row.get("company", ""))   + "|" +
        str(row.get("city", ""))      + "|" +
        str(row.get("posted_date", ""))
    )
    return hashlib.md5(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Helper: normalise column names
# Strips whitespace and lowercases all headers before mapping.
# Handles "Job Title", "JOB TITLE", "job_title" as the same thing.
# ---------------------------------------------------------------------------
def normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    return df


# ---------------------------------------------------------------------------
# Helper: align DataFrame to unified schema
# Adds missing columns as pd.NA, drops extra source-specific columns.
# ---------------------------------------------------------------------------
def align_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    for col in SCHEMA:
        if col not in df.columns:
            df[col] = pd.NA
    return df[SCHEMA]


# ---------------------------------------------------------------------------
# Loader 1: Standard CSV files
# ---------------------------------------------------------------------------
def load_csv_file(path: Path) -> pd.DataFrame:
    """
    Load a standard CSV file and map columns to unified schema.

    on_bad_lines='skip' — ignores rows where unescaped commas in
    job descriptions cause column count mismatches.
    engine='python'     — more tolerant parser than the default C engine.
    """
    log.info(f"Loading CSV: {path.name}")
    df = pd.read_csv(path, on_bad_lines="skip", engine="python")
    log.info(f"  Raw shape: {df.shape}")

    df = normalise_cols(df)

    # Apply column mapping — only rename columns that exist
    rename = {k: v for k, v in CSV_COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Tag source
    df["source"] = "naukri_csv"

    # Use _source_id as basis for job_id if available
    if "_source_id" in df.columns:
        df = df.drop(columns=["_source_id"])

    log.info(f"  Mapped {len(rename)} columns from {path.name}")
    return df


# ---------------------------------------------------------------------------
# Loader 2: NDJSON files (one JSON object per line)
# ---------------------------------------------------------------------------
def load_ndjson_file(path: Path) -> pd.DataFrame:
    """
    Load a Newline-Delimited JSON file where each line is one JSON record.
    This format is common in web-scraped datasets.

    We read line by line so a single malformed line does not crash the load.
    """
    log.info(f"Loading NDJSON: {path.name}")
    records = []
    errors  = 0

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                errors += 1
                # Skip malformed lines silently
                continue

    log.info(f"  Parsed {len(records):,} records ({errors} bad lines skipped)")

    if not records:
        log.warning(f"  No valid records found in {path.name}")
        return pd.DataFrame()

    df = pd.DataFrame(records)
    log.info(f"  Raw shape: {df.shape}")

    df = normalise_cols(df)

    # Apply column mapping
    rename = {k: v for k, v in NDJSON_COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Tag source
    df["source"] = "naukri_ndjson"

    # Drop source_id helper column
    if "_source_id" in df.columns:
        df = df.drop(columns=["_source_id"])

    log.info(f"  Mapped {len(rename)} columns from {path.name}")
    return df


# ---------------------------------------------------------------------------
# Auto-detect file format and route to correct loader
# ---------------------------------------------------------------------------
def load_file(path: Path) -> pd.DataFrame:
    """
    Detect whether a file is NDJSON or CSV by reading its first byte.
    Routes to the correct loader automatically.
    """
    with open(path, "rb") as f:
        first_byte = f.read(1)

    # NDJSON files start with '{', CSV files start with a letter or quote
    if first_byte == b"{":
        return load_ndjson_file(path)
    else:
        return load_csv_file(path)


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------
def run_ingestion() -> pd.DataFrame:
    """
    Discover all files in data/raw/, load them, combine, deduplicate,
    and save to data/processed/staging.csv.
    """
    log.info("=" * 52)
    log.info("Phase 4 — Data Ingestion Pipeline")
    log.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 52)

    # Ensure output folder exists
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Discover all CSV files in data/raw/
    raw_files = sorted(RAW_DIR.glob("*.csv"))
    if not raw_files:
        log.error("No CSV files found in data/raw/")
        log.error("Place your downloaded Kaggle files there and retry.")
        raise FileNotFoundError("No raw data files found in data/raw/")

    log.info(f"Found {len(raw_files)} file(s) in data/raw/")

    # Load all files
    dataframes = []
    for file_path in raw_files:
        df = load_file(file_path)
        if not df.empty:
            dataframes.append(df)

    if not dataframes:
        raise ValueError("All files failed to load. Check data/raw/ contents.")

    # Combine all sources
    log.info("Combining all sources...")
    combined = pd.concat(dataframes, ignore_index=True)
    log.info(f"Combined shape before processing: {combined.shape}")

    # Align every row to the unified schema
    combined = align_to_schema(combined)

    # Generate stable job IDs
    log.info("Generating job IDs...")
    combined["job_id"] = combined.apply(make_job_id, axis=1)

    # Deduplicate on job_id — keep first occurrence
    before = len(combined)
    combined = combined.drop_duplicates(subset=["job_id"], keep="first")
    dupes = before - len(combined)
    if dupes:
        log.info(f"Removed {dupes:,} duplicate rows")

    # Save staging file
    combined.to_csv(STAGING_PATH, index=False)

    log.info("=" * 52)
    log.info(f"Staging file saved: {STAGING_PATH}")
    log.info(f"Final rows    : {len(combined):,}")
    log.info(f"Final columns : {len(combined.columns)}")
    log.info("=" * 52)

    # Print data quality summary
    print_summary(combined)

    return combined


# ---------------------------------------------------------------------------
# Data quality summary
# ---------------------------------------------------------------------------
def print_summary(df: pd.DataFrame) -> None:
    """Print a readable null-count report after ingestion."""
    print("\n" + "=" * 52)
    print("  STAGING DATA QUALITY SUMMARY")
    print("=" * 52)
    print(f"  Total rows : {len(df):,}")
    print(f"  Sources    : {df['source'].value_counts().to_dict()}")
    print("\n  Null % per column:")
    for col in df.columns:
        null_pct = (df[col].isna().sum() / len(df)) * 100
        bar = "█" * int(null_pct / 5)
        print(f"    {col:<20} {null_pct:5.1f}%  {bar}")
    print("=" * 52)
    print("  Next step: python src/preprocess.py")
    print("=" * 52 + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_ingestion()