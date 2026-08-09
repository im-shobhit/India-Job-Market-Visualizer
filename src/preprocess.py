"""
src/preprocess.py
=================
Phase 5 — Data Cleaning

Reads data/processed/staging.csv and produces data/processed/clean.csv.

Cleaning operations performed:
    1.  Salary parsing      — convert raw salary strings to numeric LPA
    2.  Experience parsing  — extract min/max years from raw strings
    3.  City normalisation  — standardise city name variants
    4.  Job title canonical — map raw titles to standard role categories
    5.  Education normalise — map degree strings to 5 standard levels
    6.  Skills extraction   — clean and split skill strings into lists
    7.  Date normalisation  — parse posted_date to ISO YYYY-MM-DD
    8.  Industry cleaning   — strip and title-case industry names
    9.  Null handling       — document nulls, never silently drop rows
    10. Growth scoring      — compute synthetic growth_score per role

Run from project root:
    python src/preprocess.py

Author : India Job Market Visualizer
Phase  : 5 — Data Cleaning
"""

import re
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
ROOT_DIR     = Path(__file__).resolve().parent.parent
STAGING_PATH = ROOT_DIR / "data" / "processed" / "staging.csv"
CLEAN_PATH   = ROOT_DIR / "data" / "processed" / "clean.csv"

# ---------------------------------------------------------------------------
# City alias dictionary
# ---------------------------------------------------------------------------
CITY_ALIASES = {
    "bangalore"      : "Bengaluru",
    "bengaluru"      : "Bengaluru",
    "bengalore"      : "Bengaluru",
    "blr"            : "Bengaluru",
    "banglore"       : "Bengaluru",
    "mumbai"         : "Mumbai",
    "bombay"         : "Mumbai",
    "navi mumbai"    : "Mumbai",
    "thane"          : "Mumbai",
    "delhi"          : "Delhi NCR",
    "new delhi"      : "Delhi NCR",
    "delhi ncr"      : "Delhi NCR",
    "noida"          : "Delhi NCR",
    "gurgaon"        : "Delhi NCR",
    "gurugram"       : "Delhi NCR",
    "faridabad"      : "Delhi NCR",
    "ghaziabad"      : "Delhi NCR",
    "hyderabad"      : "Hyderabad",
    "hyd"            : "Hyderabad",
    "secunderabad"   : "Hyderabad",
    "pune"           : "Pune",
    "chennai"        : "Chennai",
    "madras"         : "Chennai",
    "kolkata"        : "Kolkata",
    "calcutta"       : "Kolkata",
    "ahmedabad"      : "Ahmedabad",
    "ahemdabad"      : "Ahmedabad",
    "surat"          : "Surat",
    "jaipur"         : "Jaipur",
    "lucknow"        : "Lucknow",
    "kochi"          : "Kochi",
    "cochin"         : "Kochi",
    "bhubaneswar"    : "Bhubaneswar",
    "coimbatore"     : "Coimbatore",
    "indore"         : "Indore",
    "chandigarh"     : "Chandigarh",
    "nagpur"         : "Nagpur",
    "visakhapatnam"  : "Visakhapatnam",
    "vizag"          : "Visakhapatnam",
    "bengaluru/bangalore" : "Bengaluru",
    "bangalore/bengaluru" : "Bengaluru",
    "delhi/ncr"           : "Delhi NCR",
    "ncr"                 : "Delhi NCR",
    "mumbai/pune"         : "Mumbai",
}

# ---------------------------------------------------------------------------
# Job title canonical mapping
# ---------------------------------------------------------------------------
TITLE_CANONICAL = {
    "data analyst"           : "Data Analyst",
    "data analysis"          : "Data Analyst",
    "business analyst"       : "Business Analyst",
    "data scientist"         : "Data Scientist",
    "data science"           : "Data Scientist",
    "data engineer"          : "Data Engineer",
    "data engineering"       : "Data Engineer",
    "ml engineer"            : "ML Engineer",
    "machine learning"       : "ML Engineer",
    "ai engineer"            : "AI/ML Engineer",
    "artificial intelligence": "AI/ML Engineer",
    "deep learning"          : "AI/ML Engineer",
    "bi developer"           : "BI Developer",
    "business intelligence"  : "BI Developer",
    "power bi"               : "BI Developer",
    "tableau"                : "BI Developer",
    "reporting analyst"      : "BI Developer",
    "software engineer"      : "Software Engineer",
    "software developer"     : "Software Engineer",
    "full stack"             : "Full Stack Developer",
    "frontend"               : "Frontend Developer",
    "front end"              : "Frontend Developer",
    "backend"                : "Backend Developer",
    "back end"               : "Backend Developer",
    "java developer"         : "Java Developer",
    "python developer"       : "Python Developer",
    "react"                  : "Frontend Developer",
    "angular"                : "Frontend Developer",
    "devops"                 : "DevOps Engineer",
    "cloud engineer"         : "Cloud Engineer",
    "site reliability"       : "DevOps Engineer",
    "qa engineer"            : "QA Engineer",
    "quality assurance"      : "QA Engineer",
    "manual testing"         : "Manual Tester",
    "automation testing"     : "Automation Tester",
    "selenium"               : "Automation Tester",
    "database administrator" : "Database Administrator",
    "sql developer"          : "Database Developer",
    "sales executive"        : "Sales Executive",
    "sales manager"          : "Sales Manager",
    "business development"   : "Business Development",
    "marketing"              : "Marketing Executive",
    "digital marketing"      : "Digital Marketing",
    "seo"                    : "Digital Marketing",
    "human resources"        : "HR Executive",
    "hr executive"           : "HR Executive",
    "hr manager"             : "HR Manager",
    "recruiter"              : "Recruiter",
    "talent acquisition"     : "Recruiter",
    "accountant"             : "Accountant",
    "accounts"               : "Accountant",
    "finance"                : "Finance Analyst",
    "financial analyst"      : "Finance Analyst",
    "chartered accountant"   : "Chartered Accountant",
    "operations"             : "Operations Executive",
    "customer support"       : "Customer Support",
    "customer service"       : "Customer Support",
    "bpo"                    : "BPO / Customer Support",
    "call center"            : "BPO / Customer Support",
    "network engineer"       : "Network Engineer",
    "cybersecurity"          : "Cybersecurity Engineer",
    "security analyst"       : "Cybersecurity Engineer",
    "project manager"        : "Project Manager",
    "product manager"        : "Product Manager",
    "scrum master"           : "Project Manager",
}


# ===========================================================================
# CLEANING FUNCTIONS
# ===========================================================================

def parse_salary(raw: str) -> tuple:
    """
    Parse raw Indian salary string → (salary_min, salary_max, salary_median) in LPA.

    Confirmed real patterns from dataset:
        '1,50,000 - 2,25,000 P.A'
        '1,50,000 - 2,50,000 P.A. 20000'       bonus after main salary — ignore
        '3,00,000 - 8,00,000 P.A. 20000 to 80000' bonuses — take first two >= 100000
        '2,25,000 - 3,75,000 P.A. Apart from...'  text noise — handled
        '10000 to 45000'                           plain range, no P.A. marker
        'Not Disclosed by Recruiter'               NaN
    """
    nan = (np.nan, np.nan, np.nan)

    if pd.isna(raw) or not str(raw).strip():
        return nan

    raw_str = str(raw).strip().lower()

    # Not-available patterns
    skip_patterns = [
        "not disclosed", "not mentioned", "not provided", "confidential",
        "negotiable", "as per", "best in", "industry standard", "hike",
        "n/a", "nil", "no salary", "competitive", "company norms",
        "as per company", "best in the industry", "thesis", "fellowship"
    ]
    if any(p in raw_str for p in skip_patterns):
        return nan

    # ------------------------------------------------------------------
    # Case 1: LPA format — "8 - 12 lpa" or "10 lpa"
    # ------------------------------------------------------------------
    lpa_range = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*lpa", raw_str
    )
    if lpa_range:
        lo = float(lpa_range.group(1))
        hi = float(lpa_range.group(2))
        if 0 < lo <= hi <= 100:
            return round(lo, 2), round(hi, 2), round((lo + hi) / 2, 2)

    lpa_single = re.search(r"(\d+(?:\.\d+)?)\s*lpa", raw_str)
    if lpa_single:
        val = float(lpa_single.group(1))
        if 0 < val <= 100:
            return round(val, 2), round(val, 2), round(val, 2)

    # ------------------------------------------------------------------
    # Case 2: Annual rupees with P.A. marker
    # Key insight: main salary figures are always >= 1,00,000 (1 Lakh)
    # Bonus figures like 20000, 9600 are < 1,00,000 — we exclude them
    # by using threshold of 100,000 (1 Lakh) as minimum.
    # This correctly excludes bonus noise while capturing real salaries.
    # ------------------------------------------------------------------
    if "p.a" in raw_str or "per annum" in raw_str or "per year" in raw_str:
        clean = raw_str.replace(",", "")
        all_nums = re.findall(r"\d+", clean)
        # Only numbers >= 100000 (1 Lakh) are real annual salaries
        # Upper cap: 10000000 (1 Crore = 100 LPA)
        salary_nums = [
            float(n) for n in all_nums
            if 80000 <= float(n) <= 10000000
        ]
        if not salary_nums:
            return nan
        lo = round(salary_nums[0] / 100000, 2)
        hi = round(salary_nums[1] / 100000, 2) if len(salary_nums) > 1 else lo
        if lo > hi:
            lo, hi = hi, lo
        if lo <= 0 or hi > 100:
            return nan
        return lo, hi, round((lo + hi) / 2, 2)

    # ------------------------------------------------------------------
    # Case 3: Plain rupee range without P.A. — "10000 to 45000"
    # These are annual rupee amounts without the P.A. marker.
    # Range: 10000 (₹10k/year = very low) to 10000000 (₹1Cr)
    # ------------------------------------------------------------------
    clean = raw_str.replace(",", "")
    plain_range = re.search(r"(\d+)\s*(?:to|-)\s*(\d+)", clean)
    if plain_range:
        n1 = float(plain_range.group(1))
        n2 = float(plain_range.group(2))
        if 10000 <= n1 <= 10000000 and 10000 <= n2 <= 10000000:
            lo = round(min(n1, n2) / 100000, 2)
            hi = round(max(n1, n2) / 100000, 2)
            if 0 < lo and hi <= 100:
                return lo, hi, round((lo + hi) / 2, 2)

    # ------------------------------------------------------------------
    # Case 4: Monthly — "80,000 per month"
    # ------------------------------------------------------------------
    if "month" in raw_str:
        clean = raw_str.replace(",", "")
        all_nums = re.findall(r"\d+", clean)
        monthly = [float(n) for n in all_nums if 3000 <= float(n) <= 500000]
        if not monthly:
            return nan
        lo = round((monthly[0] * 12) / 100000, 2)
        hi = round((monthly[1] * 12) / 100000, 2) if len(monthly) > 1 else lo
        if lo > hi:
            lo, hi = hi, lo
        if lo <= 0 or hi > 100:
            return nan
        return lo, hi, round((lo + hi) / 2, 2)

    return nan


def parse_experience(raw: str) -> tuple:
    """Extract (experience_min, experience_max) in years."""
    nan = (np.nan, np.nan)
    if pd.isna(raw) or not str(raw).strip():
        return nan
    raw = str(raw).strip().lower()
    if "fresher" in raw or "fresh" in raw:
        return 0, 1
    nums = re.findall(r"\d+", raw)
    if not nums:
        return nan
    nums = [int(n) for n in nums if int(n) <= 40]
    if not nums:
        return nan
    return nums[0], nums[-1]


def normalise_city(raw: str) -> str:
    """Map raw city string to canonical name."""
    if pd.isna(raw) or not str(raw).strip():
        return "Unknown"
    raw = str(raw).split("|")[0].split(",")[0].strip()
    return CITY_ALIASES.get(raw.lower().strip(), raw.strip().title())


def get_canonical_title(raw: str) -> str:
    """Map raw job title to canonical role category for treemap."""
    if pd.isna(raw) or not str(raw).strip():
        return "Other"
    raw_lower = str(raw).lower()
    for keyword, canonical in TITLE_CANONICAL.items():
        if keyword in raw_lower:
            return canonical


    return "Other"


def normalise_education(raw: str) -> str:
    """
    Map raw education strings to 5 canonical levels.

    Confirmed format from this dataset:
        'UG: B.Tech/B.E. - Any Specialization PG:M.Tech - Any Specialization'
        'UG: Any Graduate - Any Specialization PG:Any Postgraduate'
        'UG: Any Graduate - Any Specialization PG:Any Postgraduate, MBA/PGDM'
        'UG: B.Tech/B.E. - Any Specialization, Diploma - Any Specialization'

    KEY LOGIC: Parse UG and PG sections separately.
    PG 'Any Postgraduate' alone does NOT mean Master's required.
    Only a specific PG degree (MBA, M.Tech, MCA etc.) means Master's.
    """
    if pd.isna(raw) or not str(raw).strip():
        return "Unknown"

    r = str(raw).lower().strip()

    # --- PhD ---
    if "phd" in r or "ph.d" in r:
        return "PhD"
    if "doctorate" in r:
        after = r.split("doctorate")[-1][:25]
        if "not required" not in after:
            return "PhD"

    # --- Extract PG section content ---
    pg_content = ""
    if "pg:" in r:
        pg_content = r.split("pg:")[-1].strip()
    elif "pg :" in r:
        pg_content = r.split("pg :")[-1].strip()

    # Specific Master's degrees in PG section (not just "any postgraduate")
    specific_masters = [
        "m.tech", "mba", "pgdm", "mca", "msc", "m.sc",
        "m.com", "mcom", "master", "m.e.", "me -"
    ]
    pg_has_specific_masters = any(k in pg_content for k in specific_masters)

    # "any postgraduate" alone is NOT a master's requirement
    pg_is_any_only = (
        "any postgraduate" in pg_content
        and not pg_has_specific_masters
    )

    if pg_has_specific_masters:
        return "Master's"

    # Check for Master's keywords anywhere in full string
    # (outside UG/PG structure)
    full_masters = [
        "m.tech", "mba", "pgdm", "mca", "msc", "m.sc",
        "m.com", "mcom", "master", "post graduate"
    ]
    # NOTE: "postgraduate" deliberately excluded — "any postgraduate" in
    # UG/PG format means the degree is optional, not required.
    # Only fire if NOT preceded by "not required"
    for k in full_masters:
        if k in r:
            idx = r.find(k)
            surrounding = r[max(0, idx-15):idx+len(k)+15]
            if "not required" not in surrounding:
                return "Master's"

    # --- Bachelor's ---
    bachelor_keywords = [
        "b.tech", "b.e.", "/b.e", "be/", "bsc", "b.sc",
        "bca", "bcom", "b.com", "bba", "b.a.", "bachelor",
        "any graduate", "ug:", "b.tech/b.e", "graduate - any",
        "be -", "b.e -"
    ]
    if any(k in r for k in bachelor_keywords):
        return "Bachelor's"

    # --- Diploma ---
    if "diploma" in r or "polytechnic" in r:
        return "Diploma"

    # --- Any ---
    if "any" in r or "graduate" in r:
        return "Any"

    if pg_is_any_only:
        return "Any"

    return "Unknown"

# Master list of skills to look for in job descriptions
SKILL_KEYWORDS = [
    "python", "sql", "excel", "power bi", "tableau", "r ", "scala",
    "java", "javascript", "typescript", "react", "angular", "node.js",
    "aws", "azure", "gcp", "docker", "kubernetes", "linux", "git",
    "machine learning", "deep learning", "nlp", "tensorflow", "pytorch",
    "scikit-learn", "pandas", "numpy", "spark", "hadoop", "hive",
    "kafka", "airflow", "dbt", "snowflake", "redshift", "bigquery",
    "mongodb", "postgresql", "mysql", "oracle", "redis",
    "power apps", "power automate", "looker", "qlik",
    "c++", "c#", ".net", "php", "django", "flask", "fastapi",
    "selenium", "jira", "agile", "scrum", "rest api", "graphql",
    "photoshop", "figma", "tally", "sap", "salesforce", "hubspot",
    "communication", "leadership", "ms office", "google analytics",
]

def clean_skills(raw: str, description: str = "") -> str:
    """
    Extract skills by scanning the job_description for known skill keywords.
    Falls back to cleaning skills_raw if description is empty.

    This approach works better for this dataset where skills_raw contains
    industry categories (ITES, Marketing) rather than specific skills.
    """
    found = []
    seen = set()

    # Primary: scan job description for known skill keywords
    text = str(description).lower() if not pd.isna(description) else ""

    for skill in SKILL_KEYWORDS:
        # Use word boundary check to avoid partial matches
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text):
            display = skill.strip().title()
            if display.lower() not in seen:
                seen.add(display.lower())
                found.append(display)

    # Fallback: also include anything from skills_raw that looks like
    # a real skill (not just an industry category)
    if not pd.isna(raw):
        raw_parts = re.split(r"[,;|\n]+", str(raw))
        for part in raw_parts:
            part = part.strip().title()
            # Only include if it looks like a specific skill (not generic)
            if 2 <= len(part) <= 30 and part.lower() not in seen:
                # Skip obvious industry categories
                skip = ["ites", "it software", "it hardware", "bpo",
                        "accounts", "marketing", "sales", "banking",
                        "finance", "insurance", "pharma", "retail",
                        "telecom", "media", "engineering", "fmcg"]
                if not any(s in part.lower() for s in skip):
                    seen.add(part.lower())
                    found.append(part)

    return "|".join(found[:15])  # cap at 15 skills per job


def normalise_date(raw: str) -> str:
    """Normalise posted_date to ISO YYYY-MM-DD."""
    if pd.isna(raw) or not str(raw).strip():
        return ""
    raw = str(raw).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        return raw[:10]
    for fmt in ["%d-%m-%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y", "%Y/%m/%d"]:
        try:
            return datetime.strptime(raw[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return ""


def compute_growth_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute synthetic growth_score per canonical job title.
    Based on relative job count — normalised to approx -10 to +50 range.
    Drives treemap color: higher = greener.
    """
    counts = df.groupby("job_title_canonical")["job_id"].count().reset_index()
    counts.columns = ["job_title_canonical", "job_count"]
    min_c = counts["job_count"].min()
    max_c = counts["job_count"].max()
    counts["growth_score"] = (
        (counts["job_count"] - min_c) / (max_c - min_c + 1) * 60 - 10
    ).round(1)
    df = df.merge(
        counts[["job_title_canonical", "job_count", "growth_score"]],
        on="job_title_canonical", how="left"
    )
    return df


# ===========================================================================
# MAIN PIPELINE
# ===========================================================================

def run_cleaning() -> pd.DataFrame:
    """Full cleaning pipeline: staging.csv → clean.csv"""
    log.info("=" * 55)
    log.info("Phase 5 — Data Cleaning Pipeline")
    log.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("=" * 55)

    log.info(f"Loading: {STAGING_PATH}")
    df = pd.read_csv(STAGING_PATH, low_memory=False)
    log.info(f"Loaded {len(df):,} rows x {len(df.columns)} columns")

    # 1. Salary
    log.info("Parsing salary...")
    parsed = df["salary_raw"].apply(parse_salary)
    df["salary_min"]    = parsed.apply(lambda x: x[0])
    df["salary_max"]    = parsed.apply(lambda x: x[1])
    df["salary_median"] = parsed.apply(lambda x: x[2])
    n_sal = df["salary_median"].notna().sum()
    log.info(f"  Salary: {n_sal:,}/{len(df):,} ({n_sal/len(df)*100:.1f}%)")

    # 2. Experience
    log.info("Parsing experience...")
    exp = df["experience_raw"].apply(parse_experience)
    df["experience_min"] = exp.apply(lambda x: x[0])
    df["experience_max"] = exp.apply(lambda x: x[1])

    # 3. City
    log.info("Normalising cities...")
    df["city"] = df["city"].apply(normalise_city)

    # 4. Job title canonical
    log.info("Canonicalising job titles...")
    df["job_title_canonical"] = df["job_title"].apply(get_canonical_title)

    # 5. Education
    log.info("Normalising education...")
    df["education"] = df["education"].apply(normalise_education)

    # 6. Skills — extract from job_description using keyword matching
    log.info("Cleaning skills...")
    df["skills"] = df.apply(
        lambda row: clean_skills(row["skills_raw"], row["job_description"]),
        axis=1
    )

    # 7. Dates
    log.info("Normalising dates...")
    df["posted_date"] = df["posted_date"].apply(normalise_date)

    # 8. Industry
    df["industry"] = df["industry"].fillna("Unknown").str.strip().str.title()

    # 9. Defaults
    df["employment_type"] = df["employment_type"].fillna("Full-time")
    df["work_mode"]       = df["work_mode"].fillna("On-site")

    # 10. Growth score
    log.info("Computing growth scores...")
    df = compute_growth_score(df)

    # Save
    df.to_csv(CLEAN_PATH, index=False)
    log.info(f"Saved: {CLEAN_PATH}")

    print_summary(df)
    return df


def print_summary(df: pd.DataFrame) -> None:
    print("\n" + "=" * 55)
    print("  CLEANING SUMMARY")
    print("=" * 55)
    print(f"  Total rows      : {len(df):,}")
    print(f"  Salary coverage : {df['salary_median'].notna().sum():,} "
          f"({df['salary_median'].notna().mean()*100:.1f}%)")
    print(f"  Salary max LPA  : {df['salary_median'].max():.1f}")
    print(f"  Salary median   : {df['salary_median'].median():.2f} LPA")
    print(f"  Exp. coverage   : {df['experience_min'].notna().sum():,} "
          f"({df['experience_min'].notna().mean()*100:.1f}%)")
    print(f"  Cities found    : {df['city'].nunique()}")
    print(f"  Canonical titles: {df['job_title_canonical'].nunique()}")
    print(f"\n  Education distribution:")
    for edu, cnt in df["education"].value_counts().items():
        print(f"    {edu:<15} {cnt:>6,}")
    print(f"\n  Top 10 roles:")
    for role, cnt in df["job_title_canonical"].value_counts().head(10).items():
        print(f"    {role:<35} {cnt:>5,}")
    print(f"\n  Growth score    : {df['growth_score'].min():.1f} to {df['growth_score'].max():.1f}")
    print("=" * 55)
    print("  Next step: python src/analysis.py")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    run_cleaning()