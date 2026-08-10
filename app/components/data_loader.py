"""
app/components/data_loader.py
==============================
Shared data loading layer for all dashboard pages.

All Streamlit pages import from here — never directly from SQLite or CSV.

Uses @st.cache_data so data loads ONCE per session.
Every filter interaction re-uses the cached data — no repeated DB reads.
This is the single most important performance decision in the app.

Author : India Job Market Visualizer
Phase  : 8 — Dashboard Core
"""

import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

# ---------------------------------------------------------------------------
# Database path — relative to project root
# ---------------------------------------------------------------------------
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "jobs.db"


# ---------------------------------------------------------------------------
# Core loaders — each cached independently
# ---------------------------------------------------------------------------

@st.cache_data
def load_jobs() -> pd.DataFrame:
    """
    Load the full jobs table from SQLite.
    Cached for the entire session — never re-reads from disk on filter change.

    Returns all 26,862 rows. Filtering happens in the page code using
    pandas boolean masks — fast in-memory, no DB round-trips.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM jobs", conn)
    conn.close()
    return df


@st.cache_data
def load_role_stats() -> pd.DataFrame:
    """
    Load pre-computed role aggregations.
    38 rows — one per canonical job title.
    Drives the treemap directly.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT * FROM role_stats ORDER BY job_count DESC",
        conn
    )
    conn.close()
    return df


@st.cache_data
def load_skill_stats() -> pd.DataFrame:
    """
    Load pre-computed skill demand data.
    82 rows — one per skill that appears in 5+ job postings.
    Drives the Skills snapshot and Skills deep-dive page.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT * FROM skill_stats ORDER BY job_count DESC",
        conn
    )
    conn.close()
    return df


@st.cache_data
def load_city_stats() -> pd.DataFrame:
    """
    Load pre-computed city aggregations.
    137 rows — one per city with lat/lon for the bubble map.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        "SELECT * FROM city_stats ORDER BY job_count DESC",
        conn
    )
    conn.close()
    return df


@st.cache_data
def load_kpi() -> dict:
    """
    Load the single KPI snapshot row as a dictionary.
    Powers the 4 KPI cards on the Overview page.
    """
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT * FROM kpi_snapshot").fetchone()
    conn.close()

    if not row:
        return {
            "total_jobs": 0,
            "avg_outlook": 0.0,
            "fast_growing_count": 0,
            "declining_count": 0,
        }

    return {
        "total_jobs"        : row[1],
        "avg_outlook"       : row[2],
        "fast_growing_count": row[3],
        "declining_count"   : row[4],
    }


# ---------------------------------------------------------------------------
# Filter helper — used by every page to apply sidebar/bottom bar filters
# ---------------------------------------------------------------------------

def apply_filters(
    df: pd.DataFrame,
    city: str = "All",
    industry: str = "All",
    work_mode: str = "All",
    experience: str = "Any",
) -> pd.DataFrame:
    """
    Apply dashboard filters to the full jobs DataFrame.

    Called by each page after loading data.
    Returns a filtered DataFrame — never modifies the cached original.

    Parameters
    ----------
    df         : the full jobs DataFrame from load_jobs()
    city       : selected city or "All"
    industry   : selected industry or "All"
    work_mode  : "Remote", "Hybrid", "On-site", or "All"
    experience : "0-2", "2-5", "5-10", "10+" or "Any"
    """
    filtered = df.copy()

    if city != "All":
        filtered = filtered[filtered["city"] == city]

    if industry != "All":
        filtered = filtered[filtered["industry"] == industry]

    if work_mode != "All":
        filtered = filtered[filtered["work_mode"] == work_mode]

    if experience != "Any":
        exp_map = {
            "0-2 years"  : (0, 2),
            "2-5 years"  : (2, 5),
            "5-10 years" : (5, 10),
            "10+ years"  : (10, 99),
        }
        if experience in exp_map:
            lo, hi = exp_map[experience]
            filtered = filtered[
                (filtered["experience_min"] >= lo) &
                (filtered["experience_min"] <= hi)
            ]

    return filtered


def get_filter_options(df: pd.DataFrame) -> dict:
    """
    Extract unique filter values from the jobs DataFrame.
    Used to populate the filter dropdowns.
    """
    cities     = ["All"] + sorted(df["city"].dropna().unique().tolist())
    industries = ["All"] + sorted(df["industry"].dropna().unique().tolist())
    work_modes = ["All", "Remote", "Hybrid", "On-site"]
    experience = ["Any", "0-2 years", "2-5 years", "5-10 years", "10+ years"]

    return {
        "cities"     : cities,
        "industries" : industries,
        "work_modes" : work_modes,
        "experience" : experience,
    }