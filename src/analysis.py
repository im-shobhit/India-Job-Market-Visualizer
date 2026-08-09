"""
src/analysis.py
===============
Phase 6 — ETL Pipeline

Reads data/processed/clean.csv and writes pre-computed aggregations
into all 5 SQLite tables in data/jobs.db.

Tables populated:
    jobs          — the full cleaned job postings
    kpi_snapshot  — top-level KPI numbers for the Overview page cards
    role_stats    — one row per canonical role (drives treemap)
    skill_stats   — one row per skill (drives Skills page)
    city_stats    — one row per city (drives Cities page + map)

Run from project root:
    python src/analysis.py

Author : India Job Market Visualizer
Phase  : 6 — ETL Pipeline
"""

import sqlite3
import logging
import pandas as pd
import numpy as np
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
ROOT_DIR   = Path(__file__).resolve().parent.parent
CLEAN_PATH = ROOT_DIR / "data" / "processed" / "clean.csv"
DB_PATH    = ROOT_DIR / "data" / "jobs.db"

# ---------------------------------------------------------------------------
# City coordinates for the Plotly bubble map
# These are approximate city centre coordinates for major Indian cities.
# ---------------------------------------------------------------------------
CITY_COORDS = {
    "Bengaluru"      : (12.9716,  77.5946),
    "Mumbai"         : (19.0760,  72.8777),
    "Delhi NCR"      : (28.6139,  77.2090),
    "Hyderabad"      : (17.3850,  78.4867),
    "Pune"           : (18.5204,  73.8567),
    "Chennai"        : (13.0827,  80.2707),
    "Kolkata"        : (22.5726,  88.3639),
    "Ahmedabad"      : (23.0225,  72.5714),
    "Surat"          : (21.1702,  72.8311),
    "Jaipur"         : (26.9124,  75.7873),
    "Lucknow"        : (26.8467,  80.9462),
    "Kochi"          : ( 9.9312,  76.2673),
    "Bhubaneswar"    : (20.2961,  85.8245),
    "Coimbatore"     : (11.0168,  76.9558),
    "Indore"         : (22.7196,  75.8577),
    "Chandigarh"     : (30.7333,  76.7794),
    "Nagpur"         : (21.1458,  79.0882),
    "Visakhapatnam"  : (17.6868,  83.2185),
}


# ===========================================================================
# DATABASE HELPERS
# ===========================================================================

def get_connection() -> sqlite3.Connection:
    """Open a connection to jobs.db with WAL mode enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def clear_tables(conn: sqlite3.Connection) -> None:
    """
    Clear all tables before reloading.
    This ensures a clean reload every time analysis.py runs.
    We use DELETE not DROP — preserves table structure and indexes.
    """
    tables = ["jobs", "kpi_snapshot", "role_stats", "skill_stats", "city_stats"]
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.commit()
    log.info("All tables cleared for fresh load")


# ===========================================================================
# LOAD FUNCTIONS — one per table
# ===========================================================================

def load_jobs_table(df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """
    Load the full cleaned dataset into the jobs table.
    Uses pandas to_sql for efficiency — much faster than row-by-row INSERT.
    if_exists='append' because we already cleared the table above.
    """
    log.info("Loading jobs table...")

    # Select only the columns that exist in the jobs table schema
    job_cols = [
        "job_id", "source", "job_title", "job_title_canonical",
        "company", "industry", "employment_type", "work_mode",
        "city", "state", "salary_min", "salary_max", "salary_median",
        "experience_min", "experience_max", "education", "skills",
        "job_description", "posted_date", "job_count", "growth_score"
    ]
    # Only include columns that exist in the DataFrame
    cols_present = [c for c in job_cols if c in df.columns]
    df_jobs = df[cols_present].copy()

    df_jobs.to_sql("jobs", conn, if_exists="append", index=False)
    count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    log.info(f"  jobs table: {count:,} rows loaded")


def compute_kpi_snapshot(df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """
    Compute top-level KPI metrics and write to kpi_snapshot table.

    These numbers power the 4 KPI cards on the Overview page:
        - Total active jobs
        - Average hiring outlook (mean growth_score)
        - Fast-growing roles count (growth_score > 20)
        - Declining roles count (growth_score < -5)
    """
    log.info("Computing KPI snapshot...")

    total_jobs = len(df)

    # Average outlook — mean growth score across all roles
    avg_outlook = round(df["growth_score"].mean(), 1)

    # Count roles by growth category
    role_scores = df.groupby("job_title_canonical")["growth_score"].first()
    fast_growing = int((role_scores > 20).sum())
    declining    = int((role_scores < -5).sum())

    snapshot = {
        "snapshot_date"     : datetime.now().strftime("%Y-%m-%d"),
        "total_jobs"        : total_jobs,
        "avg_outlook"       : avg_outlook,
        "fast_growing_count": fast_growing,
        "declining_count"   : declining,
        "computed_at"       : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    pd.DataFrame([snapshot]).to_sql(
        "kpi_snapshot", conn, if_exists="append", index=False
    )
    log.info(f"  KPI: {total_jobs:,} jobs | outlook {avg_outlook} | "
             f"fast-growing: {fast_growing} | declining: {declining}")


def compute_role_stats(df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """
    Compute one aggregated row per canonical job title.
    This table directly drives the Plotly treemap:
        job_count    → rectangle SIZE
        growth_score → rectangle COLOR
        top_skills   → hover tooltip skills list
    """
    log.info("Computing role stats...")

    role_grp = df.groupby("job_title_canonical")

    stats = role_grp.agg(
        job_count      = ("job_id",        "count"),
        growth_score   = ("growth_score",  "first"),
        salary_median  = ("salary_median", "median"),
        salary_min_avg = ("salary_min",    "mean"),
        salary_max_avg = ("salary_max",    "mean"),
        exp_min_avg    = ("experience_min","mean"),
        exp_max_avg    = ("experience_max","mean"),
    ).reset_index()

    # Most common education level per role
    edu_mode = (
        df[df["education"] != "Unknown"]
        .groupby("job_title_canonical")["education"]
        .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else "Any")
        .reset_index()
        .rename(columns={"education": "education_mode"})
    )
    stats = stats.merge(edu_mode, on="job_title_canonical", how="left")
    stats["education_mode"] = stats["education_mode"].fillna("Any")

    # Top 5 skills per role
    def get_top_skills(group: pd.Series) -> str:
        from collections import Counter
        all_skills = []
        for s in group.dropna():
            all_skills.extend([sk.strip() for sk in str(s).split("|") if sk.strip()])
        top = [skill for skill, _ in Counter(all_skills).most_common(5)]
        return "|".join(top)

    top_skills = (
        df.groupby("job_title_canonical")["skills"]
        .apply(get_top_skills)
        .reset_index()
        .rename(columns={"skills": "top_skills"})
    )
    stats = stats.merge(top_skills, on="job_title_canonical", how="left")

    # Round numeric columns
    for col in ["salary_median", "salary_min_avg", "salary_max_avg",
                "exp_min_avg", "exp_max_avg", "growth_score"]:
        stats[col] = stats[col].round(2)

    stats.to_sql("role_stats", conn, if_exists="append", index=False)
    log.info(f"  role_stats: {len(stats):,} roles")


def compute_skill_stats(df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """
    Compute one aggregated row per skill.
    Drives the Skills deep-dive page: bar chart, rising/declining split.

    Skills are stored as pipe-separated strings in clean.csv.
    We explode them into individual rows for counting.
    """
    log.info("Computing skill stats...")

    # Explode skills — one row per skill per job posting
    skills_exploded = (
        df[["job_id", "job_title_canonical", "skills", "growth_score"]]
        .copy()
        .dropna(subset=["skills"])
    )
    skills_exploded = skills_exploded[skills_exploded["skills"].str.strip() != ""]

    # Split pipe-separated skills and explode
    skills_exploded["skill"] = skills_exploded["skills"].str.split("|")
    skills_exploded = skills_exploded.explode("skill")
    skills_exploded["skill"] = skills_exploded["skill"].str.strip()
    skills_exploded = skills_exploded[skills_exploded["skill"].str.len() > 1]

    # Count and aggregate
    skill_counts = (
        skills_exploded
        .groupby("skill")
        .agg(
            job_count    = ("job_id",        "count"),
            growth_score = ("growth_score",  "mean"),
        )
        .reset_index()
    )

    # Top 3 roles per skill
    def top_roles_for_skill(skill_df: pd.DataFrame) -> str:
        roles = (
            skill_df.groupby("job_title_canonical")["job_id"]
            .count()
            .nlargest(3)
            .index.tolist()
        )
        return "|".join(roles)

    top_roles = (
        skills_exploded
        .groupby("skill")
        .apply(top_roles_for_skill)
        .reset_index()
        .rename(columns={0: "top_roles"})
    )
    skill_counts = skill_counts.merge(top_roles, on="skill", how="left")

    # Filter to meaningful skills — at least 5 job postings
    skill_counts = skill_counts[skill_counts["job_count"] >= 5]
    skill_counts["growth_score"] = skill_counts["growth_score"].round(2)
    skill_counts["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    skill_counts.to_sql("skill_stats", conn, if_exists="append", index=False)
    log.info(f"  skill_stats: {len(skill_counts):,} skills")


def compute_city_stats(df: pd.DataFrame, conn: sqlite3.Connection) -> None:
    """
    Compute one aggregated row per city.
    Drives the Cities page and the India bubble map.
    lat/lon fields are added from CITY_COORDS lookup.
    """
    log.info("Computing city stats...")

    city_grp = df[df["city"] != "Unknown"].groupby("city")

    city_stats = city_grp.agg(
        job_count    = ("job_id",        "count"),
        growth_score = ("growth_score",  "mean"),
    ).reset_index()

    # State lookup from most common value in data
    state_lookup = (
        df[df["state"].notna()]
        .groupby("city")["state"]
        .agg(lambda x: x.mode().iloc[0] if len(x) > 0 else "")
        .reset_index()
    )
    city_stats = city_stats.merge(state_lookup, on="city", how="left")
    city_stats["state"] = city_stats["state"].fillna("")

    # Top 3 roles per city
    def top_roles_for_city(group):
        return (
            group.groupby("job_title_canonical")["job_id"]
            .count().nlargest(3).index.tolist()
        )

    top_roles = (
        df[df["city"] != "Unknown"]
        .groupby("city")
        .apply(top_roles_for_city)
        .reset_index()
        .rename(columns={0: "top_roles_list"})
    )
    top_roles["top_roles"] = top_roles["top_roles_list"].apply(
        lambda x: "|".join(x)
    )
    city_stats = city_stats.merge(
        top_roles[["city", "top_roles"]], on="city", how="left"
    )

    # Top 3 companies per city
    def top_companies_for_city(group):
        return (
            group.groupby("company")["job_id"]
            .count().nlargest(3).index.tolist()
        )

    top_cos = (
        df[df["city"] != "Unknown"]
        .groupby("city")
        .apply(top_companies_for_city)
        .reset_index()
        .rename(columns={0: "top_cos_list"})
    )
    top_cos["top_companies"] = top_cos["top_cos_list"].apply(
        lambda x: "|".join(x)
    )
    city_stats = city_stats.merge(
        top_cos[["city", "top_companies"]], on="city", how="left"
    )

    # Add coordinates from lookup
    city_stats["lat"] = city_stats["city"].map(
        lambda c: CITY_COORDS.get(c, (None, None))[0]
    )
    city_stats["lon"] = city_stats["city"].map(
        lambda c: CITY_COORDS.get(c, (None, None))[1]
    )

    city_stats["growth_score"] = city_stats["growth_score"].round(2)
    city_stats["updated_at"]   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    city_stats.to_sql("city_stats", conn, if_exists="append", index=False)
    log.info(f"  city_stats: {len(city_stats):,} cities")


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run_etl() -> None:
    """Full ETL pipeline: clean.csv → all 5 SQLite tables."""
    log.info("=" * 55)
    log.info("Phase 6 — ETL Pipeline")
    log.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 55)

    # Load clean data
    log.info(f"Loading: {CLEAN_PATH}")
    df = pd.read_csv(CLEAN_PATH, low_memory=False)
    log.info(f"Loaded {len(df):,} rows")

    # Connect to database
    conn = get_connection()

    try:
        # Clear all tables first
        clear_tables(conn)

        # Load and compute all tables
        load_jobs_table(conn=conn, df=df)
        compute_kpi_snapshot(conn=conn, df=df)
        compute_role_stats(conn=conn, df=df)
        compute_skill_stats(conn=conn, df=df)
        compute_city_stats(conn=conn, df=df)

        conn.commit()

    except Exception as e:
        conn.rollback()
        log.error(f"ETL failed: {e}")
        raise
    finally:
        conn.close()

    # Print verification summary
    print_summary()


def print_summary() -> None:
    """Query the database and print a verification report."""
    conn = get_connection()
    print("\n" + "=" * 55)
    print("  ETL VERIFICATION SUMMARY")
    print("=" * 55)

    tables = ["jobs", "kpi_snapshot", "role_stats", "skill_stats", "city_stats"]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<20} {count:>6,} rows")

    print()
    kpi = conn.execute("SELECT * FROM kpi_snapshot").fetchone()
    if kpi:
        print(f"  Total jobs      : {kpi[1]:,}")
        print(f"  Avg outlook     : {kpi[2]}")
        print(f"  Fast-growing    : {kpi[3]}")
        print(f"  Declining       : {kpi[4]}")

    print()
    print("  Top 5 roles by job count:")
    roles = conn.execute(
        "SELECT job_title_canonical, job_count, growth_score "
        "FROM role_stats ORDER BY job_count DESC LIMIT 5"
    ).fetchall()
    for r in roles:
        print(f"    {r[0]:<30} {r[1]:>5} jobs  score: {r[2]}")

    print()
    print("  Top 5 cities:")
    cities = conn.execute(
        "SELECT city, job_count FROM city_stats ORDER BY job_count DESC LIMIT 5"
    ).fetchall()
    for c in cities:
        print(f"    {c[0]:<20} {c[1]:>5} jobs")

    print("=" * 55)
    print("  Next step: python src/analysis.py done")
    print("  Then: streamlit run app/main.py")
    print("=" * 55 + "\n")
    conn.close()


if __name__ == "__main__":
    run_etl()