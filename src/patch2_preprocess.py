"""
src/patch2_preprocess.py
========================
Patch 2 for preprocess.py.

Fixes:
    1. get_canonical_title: fallback now returns "Other" instead of
       cleaned raw title — prevents 15,000+ unique canonical values.

    2. clean_skills: extract skills from job_description using a
       master keyword list instead of the skills_raw field which
       contains industry categories, not skill names.

Run: python src/patch2_preprocess.py
Then: python src/preprocess.py
Then: python src/analysis.py
"""
from pathlib import Path

path = Path("src/preprocess.py")
content = path.read_text(encoding="utf-8")

# -----------------------------------------------------------------------
# PATCH 1: Fix get_canonical_title fallback
# Replace the fallback block that cleans the raw title with "Other"
# -----------------------------------------------------------------------
old_fallback = '''    # No match — clean up the raw title
    # Remove bracketed content like "(2-4 yrs)", special chars
    cleaned = re.sub(r"\\(.*?\\)", "", str(raw))  # remove (...)
    cleaned = re.sub(r"[^a-zA-Z\\s/]", "", cleaned)  # keep letters only
    cleaned = cleaned.strip().title()

    # Cap length for display
    return cleaned[:40] if cleaned else "Other"'''

new_fallback = '''    # No keyword match — return "Other" bucket.
    # This prevents thousands of unique raw titles polluting the treemap.
    # "Other" is a valid treemap category that aggregates misc roles.
    return "Other"'''

if old_fallback in content:
    content = content.replace(old_fallback, new_fallback)
    print("PATCH 1 applied: canonical title fallback now returns Other")
else:
    print("PATCH 1 NOT FOUND - searching for fallback block...")
    if "No match" in content:
        idx = content.find("No match")
        print("Found 'No match' at:", content[idx:idx+300])
    else:
        print("Could not locate fallback block")

# -----------------------------------------------------------------------
# PATCH 2: Replace clean_skills to extract from job_description
# instead of skills_raw which contains industry categories
# -----------------------------------------------------------------------
old_skills = '''def clean_skills(raw: str) -> str:
    """Clean and normalise skills_raw into pipe-separated string."""
    if pd.isna(raw) or not str(raw).strip():
        return ""
    skills = re.split(r"[,;/\\n|]+", str(raw))
    cleaned = []
    seen = set()
    for s in skills:
        s = re.sub(r"\\s+", " ", s.strip()).strip().title()
        if 2 <= len(s) <= 50 and s.lower() not in seen:
            seen.add(s.lower())
            cleaned.append(s)
    return "|".join(cleaned)'''

new_skills = '''# Master list of skills to look for in job descriptions
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
        pattern = r"\\b" + re.escape(skill) + r"\\b"
        if re.search(pattern, text):
            display = skill.strip().title()
            if display.lower() not in seen:
                seen.add(display.lower())
                found.append(display)

    # Fallback: also include anything from skills_raw that looks like
    # a real skill (not just an industry category)
    if not pd.isna(raw):
        raw_parts = re.split(r"[,;|\\n]+", str(raw))
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

    return "|".join(found[:15])  # cap at 15 skills per job'''

if old_skills in content:
    content = content.replace(old_skills, new_skills)
    print("PATCH 2 applied: clean_skills now extracts from job_description")
else:
    print("PATCH 2 NOT FOUND - searching for clean_skills...")
    if "def clean_skills" in content:
        idx = content.find("def clean_skills")
        print("Found clean_skills at:", content[idx:idx+200])
    else:
        print("clean_skills function not found")

# -----------------------------------------------------------------------
# PATCH 3: Update the call to clean_skills in run_cleaning()
# to pass job_description as second argument
# -----------------------------------------------------------------------
old_call = '''    # 6. Skills
    log.info("Cleaning skills...")
    df["skills"] = df["skills_raw"].apply(clean_skills)'''

new_call = '''    # 6. Skills — extract from job_description using keyword matching
    log.info("Cleaning skills...")
    df["skills"] = df.apply(
        lambda row: clean_skills(row["skills_raw"], row["job_description"]),
        axis=1
    )'''

if old_call in content:
    content = content.replace(old_call, new_call)
    print("PATCH 3 applied: clean_skills now receives job_description")
else:
    print("PATCH 3 NOT FOUND - searching for skills call...")
    if "df[\"skills\"] = df[\"skills_raw\"].apply" in content:
        idx = content.find('df["skills"] = df["skills_raw"].apply')
        print("Found at:", content[idx:idx+100])

# -----------------------------------------------------------------------
# PATCH 4: Add city alias for slash-separated variants
# -----------------------------------------------------------------------
old_alias = '''    "vizag"          : "Visakhapatnam",
}'''

new_alias = '''    "vizag"             : "Visakhapatnam",
    # Slash-separated variants found in NDJSON source
    "bengaluru/bangalore" : "Bengaluru",
    "bangalore/bengaluru" : "Bengaluru",
    "delhi/ncr"           : "Delhi NCR",
    "ncr/delhi"           : "Delhi NCR",
    "mumbai/pune"         : "Mumbai",
    "pune/mumbai"         : "Pune",
    "hyderabad/secunderabad" : "Hyderabad",
}'''

if old_alias in content:
    content = content.replace(old_alias, new_alias)
    print("PATCH 4 applied: city aliases updated")
else:
    print("PATCH 4 NOT FOUND")

# Write patched file
path.write_text(content, encoding="utf-8")
print()
print("All patches applied. Now run:")
print("  python src/preprocess.py")
print("  python src/analysis.py")