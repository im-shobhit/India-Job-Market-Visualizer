"""
src/setup_project.py
====================
One-time project bootstrap script.

Run once from your project root:
    python src/setup_project.py

What it does:
    1. Creates all required project folders.
    2. Creates the SQLite database file (data/jobs.db).
    3. Creates all 5 tables with indexes.
    4. Prints a verification report.

No external tools required.
Uses only Python standard library: pathlib, sqlite3, logging.

Author : India Job Market Visualizer
Phase  : 3 — Folder Structure & Database Initialisation
"""

import sqlite3
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup
# Using logging instead of print() so output can be controlled and filtered.
# This is the industry standard for any script that runs unattended.
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Path constants
# Path(__file__) = absolute path to this script (src/setup_project.py)
# .parent        = src/
# .parent.parent = project root
# Using pathlib throughout — handles Windows backslashes automatically.
# ---------------------------------------------------------------------------
ROOT_DIR      = Path(__file__).resolve().parent.parent
DATA_DIR      = ROOT_DIR / "data"
RAW_DIR       = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH       = DATA_DIR / "jobs.db"


# ---------------------------------------------------------------------------
# All folders the project needs
# Add new folders here if the architecture expands.
# ---------------------------------------------------------------------------
REQUIRED_FOLDERS = [
    RAW_DIR,                          # data/raw/
    PROCESSED_DIR,                    # data/processed/
    ROOT_DIR / "notebooks",           # notebooks/
    ROOT_DIR / "src",                 # src/
    ROOT_DIR / "app" / "components",  # app/components/
    ROOT_DIR / "app" / "assets",      # app/assets/
    ROOT_DIR / "pages",               # pages/
    ROOT_DIR / "sql",                 # sql/
    ROOT_DIR / "models",              # models/
]


# ---------------------------------------------------------------------------
# SQLite table definitions
# Stored as Python strings — no external .sql file needed.
# Each string is one complete CREATE TABLE statement.
# ---------------------------------------------------------------------------
TABLES = [

    # Core jobs table — one row per cleaned job posting
    # This is the single source of truth for all dashboard data.
    """
    CREATE TABLE IF NOT EXISTS jobs (
        job_id              TEXT PRIMARY KEY,
        source              TEXT NOT NULL,
        job_title           TEXT,
        job_title_canonical TEXT,
        company             TEXT,
        industry            TEXT,
        employment_type     TEXT,
        work_mode           TEXT,
        city                TEXT,
        state               TEXT,
        salary_min          REAL,
        salary_max          REAL,
        salary_median       REAL,
        experience_min      INTEGER,
        experience_max      INTEGER,
        education           TEXT,
        skills              TEXT,
        job_description     TEXT,
        posted_date         TEXT,
        job_count           INTEGER,
        growth_score        REAL,
        inserted_at         TEXT DEFAULT (datetime('now'))
    )
    """,

    # Pre-computed KPI values — read by the Overview page KPI cards.
    # Computed by analysis.py and stored here so the dashboard
    # never runs heavy aggregations at render time.
    """
    CREATE TABLE IF NOT EXISTS kpi_snapshot (
        snapshot_date       TEXT PRIMARY KEY,
        total_jobs          INTEGER,
        avg_outlook         REAL,
        fast_growing_count  INTEGER,
        declining_count     INTEGER,
        computed_at         TEXT DEFAULT (datetime('now'))
    )
    """,

    # Role-level aggregation — one row per canonical job title.
    # job_count  → treemap rectangle SIZE
    # growth_score → treemap rectangle COLOR
    # This is what the treemap hero visualization reads directly.
    """
    CREATE TABLE IF NOT EXISTS role_stats (
        job_title_canonical TEXT PRIMARY KEY,
        job_count           INTEGER,
        growth_score        REAL,
        salary_median       REAL,
        salary_min_avg      REAL,
        salary_max_avg      REAL,
        top_skills          TEXT,
        education_mode      TEXT,
        exp_min_avg         REAL,
        exp_max_avg         REAL,
        updated_at          TEXT DEFAULT (datetime('now'))
    )
    """,

    # Skill demand — one row per skill.
    # Drives the Skills deep-dive page.
    """
    CREATE TABLE IF NOT EXISTS skill_stats (
        skill               TEXT PRIMARY KEY,
        job_count           INTEGER,
        growth_score        REAL,
        top_roles           TEXT,
        updated_at          TEXT DEFAULT (datetime('now'))
    )
    """,

    # City stats — one row per city.
    # lat/lon fields drive the Plotly India bubble map.
    """
    CREATE TABLE IF NOT EXISTS city_stats (
        city                TEXT PRIMARY KEY,
        state               TEXT,
        job_count           INTEGER,
        growth_score        REAL,
        top_roles           TEXT,
        top_companies       TEXT,
        lat                 REAL,
        lon                 REAL,
        updated_at          TEXT DEFAULT (datetime('now'))
    )
    """,
]


# ---------------------------------------------------------------------------
# Index definitions — one per commonly filtered column.
# Without indexes, every dashboard filter causes a full table scan.
# With indexes, filters on 50,000 rows respond in milliseconds.
# ---------------------------------------------------------------------------
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_city      ON jobs(city)",
    "CREATE INDEX IF NOT EXISTS idx_title     ON jobs(job_title_canonical)",
    "CREATE INDEX IF NOT EXISTS idx_company   ON jobs(company)",
    "CREATE INDEX IF NOT EXISTS idx_industry  ON jobs(industry)",
    "CREATE INDEX IF NOT EXISTS idx_education ON jobs(education)",
    "CREATE INDEX IF NOT EXISTS idx_work_mode ON jobs(work_mode)",
    "CREATE INDEX IF NOT EXISTS idx_date      ON jobs(posted_date)",
]


# ---------------------------------------------------------------------------
# Step 1 — Create all project folders
# ---------------------------------------------------------------------------
def create_folders() -> None:
    """
    Create every required project folder.

    parents=True  → creates intermediate directories (like mkdir -p on Linux)
    exist_ok=True → does not raise an error if the folder already exists

    Safe to run multiple times — will never delete or overwrite existing files.
    """
    log.info("Creating project folders...")
    for folder in REQUIRED_FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
        # Show path relative to project root for cleaner output
        log.info(f"  OK  {folder.relative_to(ROOT_DIR)}")
    log.info("All folders ready.")


# ---------------------------------------------------------------------------
# Step 2 — Initialise the SQLite database
# ---------------------------------------------------------------------------
def init_database() -> None:
    """
    Create the SQLite database file and all tables + indexes.

    sqlite3.connect() creates the .db file automatically if it does not exist.
    This replaces the Linux command: sqlite3 data/jobs.db < sql/create_tables.sql
    No external SQLite installation required.
    """
    log.info(f"Initialising database: {DB_PATH}")

    # connect() creates the file if it does not exist
    conn = sqlite3.connect(DB_PATH)

    # context manager ensures the connection is properly closed
    # even if an error occurs mid-setup
    with conn:
        cursor = conn.cursor()

        # Enable WAL mode — allows concurrent reads while writes happen.
        # Important for Streamlit where multiple users may read simultaneously.
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create tables
        log.info("Creating tables...")
        for statement in TABLES:
            cursor.execute(statement)
            # Extract table name from the SQL string for the log message
            words = statement.split()
            table_name = words[words.index("EXISTS") + 1]
            log.info(f"  OK  {table_name}")

        # Create indexes
        log.info("Creating indexes...")
        for statement in INDEXES:
            cursor.execute(statement)
            # Index name is always the 6th word: CREATE INDEX IF NOT EXISTS <name>
            index_name = statement.split()[5]
            log.info(f"  OK  {index_name}")

    conn.close()
    log.info("Database ready.")


# ---------------------------------------------------------------------------
# Step 3 — Verify by querying the database
# ---------------------------------------------------------------------------
def verify_setup() -> None:
    """
    Connect to the database and list all tables and indexes.
    Prints a clear summary so you can confirm everything worked.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    tables = [row[0] for row in cursor.fetchall()]

    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
    )
    indexes = [row[0] for row in cursor.fetchall()]

    conn.close()

    db_size = DB_PATH.stat().st_size

    print("\n" + "=" * 52)
    print("  SETUP VERIFICATION")
    print("=" * 52)
    print(f"\n  Database : {DB_PATH}")
    print(f"  Size     : {db_size:,} bytes")

    print(f"\n  Tables ({len(tables)}):")
    for t in tables:
        print(f"    OK  {t}")

    print(f"\n  Indexes ({len(indexes)}):")
    for i in indexes:
        print(f"    OK  {i}")

    print(f"\n  Folders:")
    for folder in REQUIRED_FOLDERS:
        status = "OK " if folder.exists() else "MISSING"
        print(f"    {status}  {folder.relative_to(ROOT_DIR)}")

    print("\n" + "=" * 52)
    print("  Phase 3 Step 1 complete.")
    print("  Next: python src/setup_project.py already done.")
    print("  Confirm success and move to Step 2.")
    print("=" * 52 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    log.info("=" * 52)
    log.info("India Job Market Visualizer — Project Setup")
    log.info("=" * 52)

    create_folders()
    init_database()
    verify_setup()


if __name__ == "__main__":
    main()