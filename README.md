# India Job Market Visualizer

A portfolio-grade labor market intelligence platform that visualises the Indian job market using publicly collected data from Naukri.com. Built with Python, Streamlit, Plotly, and scikit-learn.

**Live demo:** [Deploy link will go here after Streamlit Cloud deployment]

---

## What It Does

The platform answers the questions every job seeker, student, and recruiter in India asks:

- Which roles are growing or declining?
- Which cities have the highest hiring demand?
- Which skills are most valuable right now?
- What salary can I expect for my role?
- Which roles match my current skill set?

---

## Screenshots

### Overview Page
The landing page gives a complete market snapshot in under 10 seconds.

- 4 KPI cards — total jobs, average outlook, fast-growing roles, declining roles
- Outlook distribution bar — market health at a glance
- Interactive treemap — every role sized by job count, colored by growth rate
- Snapshot charts — top skills, cities, and salary ranges

### Skills Analysis Page
Deep-dive into skill demand across the Indian job market.

- Top 20 skills ranked by job postings
- Rising vs declining skills
- Skill × role heatmap

### AI Career Advisor
Personalised career intelligence powered by TF-IDF cosine similarity.

- Enter your skills → get top 5 matched roles
- Salary estimate, market demand, and experience requirements per role
- Skill gap analysis — what you have vs what each role needs
- Priority upskilling chart — which skills to learn next

---

## Tech Stack

| Layer | Technology |
|---|---|
| Dashboard | Streamlit 1.45 |
| Visualizations | Plotly 6.1 |
| Data processing | Pandas 2.2, NumPy 2.2 |
| ML matching | scikit-learn 1.6 (TF-IDF, cosine similarity) |
| Database | SQLite (Python built-in sqlite3) |
| Language | Python 3.13 |
| Deployment | Streamlit Cloud |

---

## Project Architecture

```
India-Job-Market-Visualizer/
├── app.py                        # Entry point + Overview page
├── pages/
│   ├── 1_skills.py               # Skills deep-dive page
│   └── 2_career_advisor.py       # AI Career Advisor page
├── src/
│   ├── scraper.py                # Data ingestion from CSV sources
│   ├── preprocess.py             # ETL cleaning pipeline
│   ├── analysis.py               # Aggregations → SQLite tables
│   └── fix_canonical.py          # Canonical title normalisation
├── app/
│   └── components/
│       └── data_loader.py        # Cached data loading layer
├── data/
│   ├── raw/                      # Raw Kaggle CSVs (gitignored)
│   └── processed/                # Cleaned CSV (gitignored)
├── .streamlit/
│   └── config.toml               # Dark theme + page settings
└── requirements.txt
```

**Data flow:**
```
Kaggle CSVs → scraper.py → staging.csv → preprocess.py → clean.csv → analysis.py → jobs.db → Dashboard
```

---

## Data Pipeline

### Sources
- **Naukri.com CSV** — 22,000 job postings (PromptCloud via Kaggle)
- **Naukri.com NDJSON** — 4,879 job postings with geographic data

**Total:** 26,862 deduplicated job postings after ingestion

### Cleaning operations (`src/preprocess.py`)
- Salary normalisation — parses raw strings like `"1,50,000 - 2,25,000 P.A"` to LPA floats
- City canonicalisation — 15+ spelling variants → single canonical name
- Job title standardisation — 200+ raw title patterns → 38 canonical role categories
- Education normalisation — UG/PG structured format → 5 standard levels
- Skill extraction — TF-IDF keyword matching against 82-skill master list

### Database (`data/jobs.db`)
Five pre-computed SQLite tables power the dashboard:

| Table | Rows | Purpose |
|---|---|---|
| `jobs` | 26,862 | Full cleaned dataset |
| `role_stats` | 38 | Treemap data (job_count, growth_score) |
| `skill_stats` | 82 | Skills page data |
| `city_stats` | 137 | Cities data with lat/lon |
| `kpi_snapshot` | 1 | Overview KPI cards |

---

## AI Career Advisor

The Career Advisor uses **TF-IDF cosine similarity** to match user skills against role profiles.

**How it works:**
1. Each canonical role is represented as a document of its most common skill keywords
2. The user's input skills form a query document
3. `TfidfVectorizer` converts all documents to TF-IDF vectors
4. `cosine_similarity` scores the user query against every role vector
5. Top 5 highest-scoring roles are returned with skill gap analysis

This is the same technique used in production job recommendation systems at scale.

---

## Setup Instructions

### Prerequisites
- Python 3.9+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/India-Job-Market-Visualizer.git
cd India-Job-Market-Visualizer

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Data Setup

```bash
# Run project setup (creates folders and SQLite DB)
python src/setup_project.py

# Download datasets from Kaggle and place in data/raw/
# Dataset 1: kaggle.com/PromptCloudHQ/jobs-on-naukricom → india_jobs_naukri_01.csv
# Dataset 2: kaggle.com/promptcloud/naukri-job-listing-dataset → india_jobs_naukri_02.csv

# Run the full data pipeline
python src/scraper.py       # Ingest raw data → staging.csv
python src/preprocess.py    # Clean data → clean.csv
python src/analysis.py      # Aggregate → SQLite tables
```

### Run the Dashboard

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Key Engineering Decisions

**SQLite over PostgreSQL** — Zero-configuration, ships as a single file, works identically on Streamlit Cloud without any server setup. The right choice for a portfolio project that needs to be deployable in one click.

**Pre-computed aggregations** — The dashboard reads from five pre-computed SQLite tables, never from the raw 26,862-row dataset at render time. This makes every page load instantaneous regardless of filter state.

**`@st.cache_data` throughout** — Every data loading function is cached. Filter interactions never trigger database reads — they operate on the in-memory cached DataFrame.

**Hub and spoke architecture** — The Overview page tells the market story. Deep-dive pages allow investigation. The AI Advisor enables personalisation. Three distinct user journeys in one platform.

**Salary nulls handled gracefully** — 84% of Indian job postings on Naukri.com omit salary. Rather than imputing or hiding these, the dashboard shows "Not disclosed" — which is what Naukri itself does, and is more credible than invented data.

---

## Resume Bullet Points

```
• Built a full-stack labor market intelligence platform analysing 26,862 Indian
  job postings using Python, Streamlit, Plotly, and SQLite

• Engineered a multi-source ETL pipeline (scraping, cleaning, normalisation,
  aggregation) processing Naukri.com data into 5 pre-computed SQLite tables

• Implemented TF-IDF cosine similarity career matching algorithm using
  scikit-learn, enabling personalised role recommendations with skill gap analysis

• Designed an interactive dark-theme dashboard with Plotly treemap, KPI cards,
  and cross-filtered charts, deployed live on Streamlit Cloud

• Resolved 15+ real-world data quality issues including Indian salary format
  parsing, city name canonicalisation, and UG/PG education format normalisation
```

---

## What I Learned

- End-to-end data engineering: from messy real-world CSVs to a production-ready database
- How to design data pipelines that fail gracefully and log informatively
- Why pre-aggregation matters more than query optimisation for dashboard performance
- How TF-IDF cosine similarity works and why it's effective for skill matching
- The difference between building something that works and something that looks like a real product

---

## Acknowledgements

- Data sourced from PromptCloud's Naukri.com scrapes via Kaggle (public dataset)
- Inspired by the US Job Market Visualizer concept
- Built as a portfolio project to demonstrate full-stack data engineering capability

---

*Built by Shobhit · B.Tech Computer Science · 2026*
