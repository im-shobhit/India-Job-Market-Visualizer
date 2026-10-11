"""
pages/2_career_advisor.py
==========================
Phase 10 -- AI Career Advisor

Personalised career intelligence tool.
User enters their skills and gets:
    1. Top matched roles (cosine similarity against role skill profiles)
    2. Salary estimate for each matched role
    3. Skill gap analysis -- what they have vs what the role needs
    4. Market demand context -- how many openings exist

No external API needed. Runs entirely on the clean.csv data using
scikit-learn's cosine similarity on TF-IDF skill vectors.

Author : India Job Market Visualizer
Phase  : 10 -- AI Features
"""

import re
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.components.data_loader import load_jobs, load_role_stats

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Career Advisor",
    page_icon="robot",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
#MainMenu {visibility: hidden !important;}
footer    {visibility: hidden !important;}
header    {visibility: hidden !important;}
.stDeployButton {display: none !important;}
.stApp {background-color: #0f1117;}
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 1rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100% !important;
}
.hero-bar {
    background: linear-gradient(135deg, #0d1014 0%, #161922 60%, #1A1030 100%);
    border-bottom: 0.5px solid rgba(83,74,183,0.4);
    padding: 0 28px;
    height: 64px;
    width: calc(100% + 4rem);
    margin: 0 -2rem 1.5rem -2rem;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    align-items: center;
    box-sizing: border-box;
}
.hero-brand {display: flex; align-items: center; justify-content: center; gap: 12px;}
.hero-icon {
    width: 36px; height: 36px; flex-shrink: 0;
    background: linear-gradient(135deg, #534AB7 0%, #3C3489 100%);
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
}
.hero-title   {font-size: 18px; font-weight: 700; color: #e8e6de; margin: 0;}
.hero-subtitle{font-size: 11px; color: #5F5E5A; margin: 2px 0 0 0;}
.hero-right   {display: flex; flex-direction: column; align-items: flex-end; gap: 4px;}
.ai-badge {
    display: flex; align-items: center; gap: 5px;
    font-size: 11px; color: #AFA9EC;
    background: rgba(83,74,183,0.15);
    border: 0.5px solid rgba(83,74,183,0.4);
    border-radius: 20px; padding: 3px 10px;
}
.hero-count {font-size: 11px; color: #5F5E5A;}
.back-btn {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 12px; font-weight: 500; color: #1D9E75;
    background: rgba(29,158,117,0.1);
    border: 0.5px solid rgba(29,158,117,0.3);
    border-radius: 6px; padding: 6px 14px;
    text-decoration: none; margin-bottom: 16px;
}
.match-card {
    background: #161922;
    border: 0.5px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 10px;
    transition: border-color 0.2s;
}
.match-card:hover {border-color: rgba(83,74,183,0.4);}
.match-rank {
    font-size: 10px; color: #5F5E5A;
    text-transform: uppercase; letter-spacing: 0.06em;
    margin-bottom: 3px;
}
.match-title {font-size: 16px; font-weight: 600; color: #e8e6de; margin: 0 0 6px 0;}
.match-score {
    display: inline-block;
    font-size: 11px; color: #AFA9EC;
    background: rgba(83,74,183,0.15);
    border: 0.5px solid rgba(83,74,183,0.3);
    border-radius: 20px; padding: 2px 8px;
    margin-bottom: 8px;
}
.match-meta {display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 10px;}
.meta-item {font-size: 11px; color: #888780;}
.meta-val  {font-size: 11px; color: #e8e6de; font-weight: 500;}
.skill-tag {
    display: inline-block;
    font-size: 10px; padding: 2px 8px; border-radius: 4px;
    margin: 2px 3px 2px 0;
}
.skill-have {background: rgba(29,158,117,0.15); color: #5DCAA5; border: 0.5px solid rgba(29,158,117,0.3);}
.skill-miss {background: rgba(163,45,45,0.15); color: #F09595; border: 0.5px solid rgba(163,45,45,0.3);}
.gap-label {font-size: 11px; color: #5F5E5A; margin: 6px 0 4px 0;}
.section-label {font-size: 11px; color: #5F5E5A; margin-bottom: 6px; letter-spacing: 0.03em;}
.tip-box {
    background: rgba(83,74,183,0.08);
    border: 0.5px solid rgba(83,74,183,0.25);
    border-radius: 8px; padding: 10px 14px;
    font-size: 11px; color: #888780; line-height: 1.6;
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------
C = {
    "very_fast": "#0F6E56", "growing": "#1D9E75",
    "stable": "#BA7517",   "slowing": "#993C1D", "declining": "#A32D2D",
}
PLOTLY_CFG = {"displayModeBar": False, "responsive": True}
CHART_BG   = dict(plot_bgcolor="#161922", paper_bgcolor="#161922", font_color="#e8e6de")


def growth_color(score):
    if score > 20:  return C["very_fast"]
    if score > 5:   return C["growing"]
    if score > -5:  return C["stable"]
    if score > -20: return C["slowing"]
    return C["declining"]


def growth_label(score):
    if score > 20:  return "Very fast growth"
    if score > 5:   return "Growing"
    if score > -5:  return "Stable"
    if score > -20: return "Slowing"
    return "Declining"


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        '<div style="padding:8px 0 12px 0;">'
        '<p style="font-size:10px;color:#5F5E5A;text-transform:uppercase;'
        'letter-spacing:0.1em;padding:0 8px;margin-bottom:6px;">Navigation</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.page_link("app.py",                    label="Overview",       icon="🏠")
    st.page_link("pages/1_skills.py",         label="Skills",         icon="📊")
    st.page_link("pages/2_career_advisor.py", label="Career Advisor", icon="🤖")


# ===========================================================================
# LOAD DATA
# ===========================================================================
@st.cache_data
def build_role_skill_matrix():
    """
    Build a role -> skills string mapping for TF-IDF vectorization.
    Each role gets a document of its most common skills.
    Used for cosine similarity matching against the user's skill input.
    """
    role_stats = load_role_stats()
    jobs_df    = load_jobs()

    role_docs = {}
    for _, row in role_stats.iterrows():
        role = row["job_title_canonical"]
        if role == "Other":
            continue
        # Get all skills for this role from jobs
        role_jobs = jobs_df[jobs_df["job_title_canonical"] == role]
        all_skills = []
        for skills_str in role_jobs["skills"].dropna():
            all_skills.extend([s.strip().lower() for s in str(skills_str).split("|") if s.strip()])
        if all_skills:
            role_docs[role] = " ".join(all_skills)

    return role_docs, role_stats


@st.cache_data
def get_role_metadata():
    """Return role stats as a dict keyed by canonical title."""
    role_stats = load_role_stats()
    return role_stats.set_index("job_title_canonical").to_dict(orient="index")


role_docs, role_stats_df = build_role_skill_matrix()
role_meta = get_role_metadata()


def match_roles(user_skills_raw: str, top_n: int = 5) -> list[dict]:
    """
    Match user's skills to canonical job roles using TF-IDF cosine similarity.

    Parameters
    ----------
    user_skills_raw : comma-separated skill string from the user
    top_n           : number of top matches to return

    Returns
    -------
    List of dicts with role, score, metadata, and skill gap analysis
    """
    if not user_skills_raw.strip():
        return []

    # Parse and clean user skills
    user_skills = [
        s.strip().lower()
        for s in re.split(r"[,;\n]+", user_skills_raw)
        if s.strip()
    ]
    user_doc = " ".join(user_skills)

    if not user_doc:
        return []

    # Build corpus: all role documents + user document
    role_names  = list(role_docs.keys())
    corpus      = [role_docs[r] for r in role_names] + [user_doc]

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(min_df=1, ngram_range=(1, 2))
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        return []

    # Cosine similarity between user (last row) and all roles
    user_vec   = tfidf_matrix[-1]
    role_vecs  = tfidf_matrix[:-1]
    scores     = cosine_similarity(user_vec, role_vecs)[0]

    # Get top N matches
    top_indices = np.argsort(scores)[::-1][:top_n]

    results = []
    for idx in top_indices:
        role  = role_names[idx]
        score = float(scores[idx])

        if score < 0.01:   # skip zero-similarity matches
            continue

        meta = role_meta.get(role, {})

        # Skill gap analysis
        # Get top skills required by this role
        top_skills_str  = meta.get("top_skills", "") or ""
        required_skills = [s.strip().lower() for s in top_skills_str.split("|") if s.strip()]

        user_skill_set  = set(user_skills)
        have_skills     = [s for s in required_skills if s in user_skill_set]
        missing_skills  = [s for s in required_skills if s not in user_skill_set]

        match_pct = len(have_skills) / len(required_skills) * 100 if required_skills else 0

        results.append({
            "role"            : role,
            "similarity"      : round(score * 100, 1),
            "job_count"       : int(meta.get("job_count", 0)),
            "salary_median"   : meta.get("salary_median"),
            "growth_score"    : float(meta.get("growth_score", 0) or 0),
            "education_mode"  : meta.get("education_mode", "Any"),
            "exp_min_avg"     : meta.get("exp_min_avg"),
            "exp_max_avg"     : meta.get("exp_max_avg"),
            "required_skills" : required_skills,
            "have_skills"     : have_skills,
            "missing_skills"  : missing_skills,
            "skill_match_pct" : round(match_pct, 0),
        })

    return results


# ===========================================================================
# HERO HEADER
# ===========================================================================
st.markdown(
    '<div class="hero-bar">'
    '<div></div>'
    '<div class="hero-brand">'
    '<div class="hero-icon">&#129302;</div>'
    '<div>'
    '<p class="hero-title">AI Career Advisor</p>'
    '<p class="hero-subtitle">India Job Market Visualizer &nbsp;&middot;&nbsp; Personalised role matching</p>'
    '</div>'
    '</div>'
    '<div class="hero-right">'
    '<div class="ai-badge">&#129302; AI-powered</div>'
    f'<span class="hero-count">{len(role_docs)} roles analysed</span>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown('<a class="back-btn" href="/" target="_self">&#8592; Overview</a>',
            unsafe_allow_html=True)


# ===========================================================================
# INPUT SECTION
# ===========================================================================
st.markdown('<div class="section-label">Enter your skills to get personalised role matches</div>',
            unsafe_allow_html=True)

st.markdown(
    '<div class="tip-box">'
    '&#128161; <strong>How it works:</strong> Enter the skills you have, separated by commas. '
    'The advisor uses TF-IDF cosine similarity to match your skills against the skill profiles '
    'of every role in our dataset. You get the top 5 most compatible roles, with salary estimates, '
    'market demand, and a skill gap analysis for each.'
    '</div>',
    unsafe_allow_html=True,
)

col_input, col_btn = st.columns([4, 1])

with col_input:
    user_input = st.text_input(
        label="Your skills",
        placeholder="e.g. Python, SQL, Excel, Data Analysis, Power BI",
        label_visibility="collapsed",
    )

with col_btn:
    analyse_btn = st.button("Analyse ↗", type="primary", use_container_width=True)

# Quick-select skill presets
st.markdown('<div class="section-label" style="margin-top:8px;">Quick presets</div>',
            unsafe_allow_html=True)

p1, p2, p3, p4, p5 = st.columns(5)
presets = {
    "Data Analyst"   : "Python, SQL, Excel, Power BI, Tableau, Data Analysis",
    "Software Eng."  : "Java, Python, JavaScript, Git, REST API, Agile",
    "ML Engineer"    : "Python, Machine Learning, TensorFlow, SQL, Deep Learning",
    "Finance"        : "Excel, Tally, Accounting, Finance, SAP, MS Office",
    "HR / Recruiter" : "Communication, HR, Recruitment, Excel, Leadership",
}
for col, (label, skills) in zip([p1, p2, p3, p4, p5], presets.items()):
    if col.button(label, use_container_width=True):
        user_input = skills
        analyse_btn = True


# ===========================================================================
# RESULTS
# ===========================================================================
if analyse_btn and user_input:
    with st.spinner("Analysing your skills against the market..."):
        matches = match_roles(user_input, top_n=5)

    if not matches:
        st.warning("No strong matches found. Try adding more specific skills.")
    else:
        # Parse user skills for display
        user_skills_list = [s.strip().title() for s in re.split(r"[,;\n]+", user_input) if s.strip()]

        st.markdown("<br>", unsafe_allow_html=True)

        # Summary header
        st.markdown(
            f'<div class="section-label">Top {len(matches)} role matches '
            f'for: <span style="color:#e8e6de;">{", ".join(user_skills_list[:5])}'
            f'{"..." if len(user_skills_list) > 5 else ""}</span></div>',
            unsafe_allow_html=True,
        )

        # ---------------------------------------------------------------
        # Match score bar chart -- visual summary
        # ---------------------------------------------------------------
        match_df = pd.DataFrame([
            {
                "role"  : m["role"],
                "score" : m["similarity"],
                "color" : growth_color(m["growth_score"]),
            }
            for m in matches
        ]).sort_values("score", ascending=True)

        fig_match = px.bar(
            match_df, x="score", y="role", orientation="h",
            color="color", color_discrete_map="identity",
        )
        fig_match.update_layout(
            height=200, margin=dict(l=0,r=0,t=0,b=0),
            showlegend=False, **CHART_BG,
            xaxis=dict(title="Match score (%)", showgrid=True,
                       gridcolor="rgba(255,255,255,0.05)", zeroline=False),
            yaxis=dict(title=""),
        )
        fig_match.update_traces(
            hovertemplate="<b>%{y}</b><br>Match: %{x:.1f}%<extra></extra>"
        )
        st.plotly_chart(fig_match, use_container_width=True, config=PLOTLY_CFG)

        # ---------------------------------------------------------------
        # Detailed match cards
        # ---------------------------------------------------------------
        for i, m in enumerate(matches):
            rank_labels = ["Best match", "2nd match", "3rd match", "4th match", "5th match"]
            rank = rank_labels[i] if i < len(rank_labels) else f"#{i+1} match"

            salary_str = (
                f"&#8377; {m['salary_median']:.1f} LPA"
                if m["salary_median"] and not pd.isna(m["salary_median"])
                else "Not disclosed"
            )

            exp_str = "Any"
            if m["exp_min_avg"] and not pd.isna(m["exp_min_avg"]):
                lo = round(m["exp_min_avg"])
                hi = round(m["exp_max_avg"]) if m["exp_max_avg"] and not pd.isna(m["exp_max_avg"]) else lo
                exp_str = f"{lo}–{hi} years"

            g_color = growth_color(m["growth_score"])
            g_label = growth_label(m["growth_score"])

            # Skills you have
            have_tags = "".join(
                f'<span class="skill-tag skill-have">&#10003; {s.title()}</span>'
                for s in m["have_skills"]
            ) or '<span style="font-size:11px;color:#5F5E5A;">None matched</span>'

            # Skills you are missing
            miss_tags = "".join(
                f'<span class="skill-tag skill-miss">+ {s.title()}</span>'
                for s in m["missing_skills"]
            ) or '<span style="font-size:11px;color:#5DCAA5;">You have all key skills!</span>'

            st.markdown(f"""
            <div class="match-card">
                <div class="match-rank">{rank}</div>
                <p class="match-title">{m['role']}</p>
                <span class="match-score">&#128269; {m['similarity']:.1f}% skill match</span>
                <div class="match-meta">
                    <div>
                        <span class="meta-item">Salary &nbsp;</span>
                        <span class="meta-val">{salary_str}</span>
                    </div>
                    <div>
                        <span class="meta-item">Open jobs &nbsp;</span>
                        <span class="meta-val">{m['job_count']:,}</span>
                    </div>
                    <div>
                        <span class="meta-item">Experience &nbsp;</span>
                        <span class="meta-val">{exp_str}</span>
                    </div>
                    <div>
                        <span class="meta-item">Education &nbsp;</span>
                        <span class="meta-val">{m['education_mode']}</span>
                    </div>
                    <div>
                        <span class="meta-item">Market trend &nbsp;</span>
                        <span class="meta-val" style="color:{g_color};">{g_label}</span>
                    </div>
                </div>
                <div class="gap-label">&#10003; Skills you have</div>
                <div>{have_tags}</div>
                <div class="gap-label">+ Skills to learn</div>
                <div>{miss_tags}</div>
            </div>
            """, unsafe_allow_html=True)

        # ---------------------------------------------------------------
        # Skill gap summary chart
        # ---------------------------------------------------------------
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-label">Skill gap summary across all matched roles</div>',
                    unsafe_allow_html=True)

        all_missing = {}
        for m in matches:
            for sk in m["missing_skills"]:
                all_missing[sk] = all_missing.get(sk, 0) + 1

        if all_missing:
            gap_df = (
                pd.DataFrame(list(all_missing.items()), columns=["skill", "roles_needing"])
                .sort_values("roles_needing", ascending=False)
                .head(10)
            )
            fig_gap = px.bar(
                gap_df.sort_values("roles_needing", ascending=True),
                x="roles_needing", y="skill", orientation="h",
                color_discrete_sequence=[C["slowing"]],
            )
            fig_gap.update_layout(
                height=280, margin=dict(l=0,r=0,t=0,b=0),
                showlegend=False, **CHART_BG,
                xaxis=dict(title="Number of matched roles needing this skill",
                           tickvals=list(range(1, len(matches)+1)),
                           showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False),
                yaxis=dict(title=""),
            )
            st.plotly_chart(fig_gap, use_container_width=True, config=PLOTLY_CFG)
            st.markdown(
                '<div style="font-size:11px;color:#5F5E5A;margin-top:4px;">'
                'The longer the bar, the more your matched roles need this skill. '
                'Prioritise learning the top skills on this list.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.success("Your skills cover all requirements across your top matches.")

elif analyse_btn and not user_input:
    st.warning("Please enter at least one skill before analysing.")

else:
    # Default state -- show a prompt
    st.markdown(
        '<div style="text-align:center;padding:40px 0;color:#5F5E5A;font-size:13px;">'
        '&#128202; Enter your skills above and click Analyse, '
        'or use one of the quick presets to get started.'
        '</div>',
        unsafe_allow_html=True,
    )
