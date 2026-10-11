"""
pages/2_skills.py
==================
Phase 9 -- Deep Dive: Skills Analysis

Answers the question: Which skills are most valuable in India's job market?

Sections:
    1. Hero header (same as Overview)
    2. Summary KPIs -- total skills tracked, top skill, fastest rising
    3. Top 20 skills ranked bar chart (color = growth outlook)
    4. Rising vs declining skills -- side by side
    5. Skill demand heatmap -- skill vs top role
    6. Skill co-occurrence -- most common skill combinations

Author : India Job Market Visualizer
Phase  : 9 -- Deep Dive Pages
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.components.data_loader import (
    load_jobs, load_skill_stats, get_filter_options, apply_filters
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Skills",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Shared CSS (same tokens as Overview)
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
    background: linear-gradient(135deg, #0d1014 0%, #161922 60%, #0F2A20 100%);
    border-bottom: 0.5px solid rgba(29,158,117,0.3);
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
    background: linear-gradient(135deg, #1D9E75 0%, #0F6E56 100%);
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
}
.hero-title   {font-size: 18px; font-weight: 700; color: #e8e6de; margin: 0; letter-spacing: -0.3px;}
.hero-subtitle{font-size: 11px; color: #5F5E5A; margin: 2px 0 0 0;}
.hero-right   {display: flex; flex-direction: column; align-items: flex-end; gap: 4px;}
.hero-live-badge {
    display: flex; align-items: center; gap: 5px;
    font-size: 11px; color: #5DCAA5;
    background: rgba(29,158,117,0.12);
    border: 0.5px solid rgba(29,158,117,0.3);
    border-radius: 20px; padding: 3px 10px;
}
.hero-live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #5DCAA5; animation: pulse 2s infinite;
}
@keyframes pulse {0%{opacity:1;}50%{opacity:0.3;}100%{opacity:1;}}
.hero-count {font-size: 11px; color: #5F5E5A; white-space: nowrap;}
.kpi-card {
    background: #161922;
    border: 0.5px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 14px 16px;
}
.kpi-label {font-size: 11px; color: #5F5E5A; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.05em;}
.kpi-value {font-size: 28px; font-weight: 600; color: #e8e6de; line-height: 1;}
.kpi-delta-up   {font-size: 11px; color: #5DCAA5; margin-top: 4px;}
.kpi-delta-down {font-size: 11px; color: #F09595; margin-top: 4px;}
.section-label {font-size: 11px; color: #5F5E5A; margin-bottom: 6px; letter-spacing: 0.03em;}
.back-link {font-size: 11px; color: #1D9E75;}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------
C = {
    "very_fast": "#0F6E56", "growing": "#1D9E75",
    "stable": "#BA7517", "slowing": "#993C1D", "declining": "#A32D2D",
}
PLOTLY_CFG = {"displayModeBar": False, "responsive": True}
CHART_BG   = dict(plot_bgcolor="#161922", paper_bgcolor="#161922", font_color="#e8e6de")


def growth_color(score):
    if score > 20:  return C["very_fast"]
    if score > 5:   return C["growing"]
    if score > -5:  return C["stable"]
    if score > -20: return C["slowing"]
    return C["declining"]


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
skill_stats = load_skill_stats()
jobs_df     = load_jobs()
filter_opts = get_filter_options(jobs_df)

# ---------------------------------------------------------------------------
# Sidebar filters
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
    st.markdown("---")
    st.markdown("### Filters")
    sel_city     = st.selectbox("City",       filter_opts["cities"])
    sel_industry = st.selectbox("Industry",   filter_opts["industries"])
    sel_mode     = st.selectbox("Work mode",  filter_opts["work_modes"])
    sel_exp      = st.selectbox("Experience", filter_opts["experience"])

filtered_df = apply_filters(
    jobs_df, city=sel_city, industry=sel_industry,
    work_mode=sel_mode, experience=sel_exp,
)

# Recompute skill stats from filtered data if filters are active
filters_active = (
    sel_city != "All" or sel_industry != "All"
    or sel_mode != "All" or sel_exp != "Any"
)

if filters_active and len(filtered_df) > 0:
    # Re-extract skills from filtered jobs
    skill_rows = []
    for _, row in filtered_df[filtered_df["skills"].notna()].iterrows():
        for sk in str(row["skills"]).split("|"):
            sk = sk.strip()
            if sk:
                skill_rows.append({"skill": sk, "job_id": row["job_id"],
                                   "growth_score": row["growth_score"]})
    if skill_rows:
        sk_df = pd.DataFrame(skill_rows)
        skill_stats = (
            sk_df.groupby("skill")
            .agg(job_count=("job_id","count"), growth_score=("growth_score","mean"))
            .reset_index()
            .sort_values("job_count", ascending=False)
        )

# ===========================================================================
# HERO HEADER
# ===========================================================================
st.markdown(
    '<div class="hero-bar">'
    '<div></div>'  # left spacer (arrow button sits here natively)
    '<div class="hero-brand">'
    '<div class="hero-icon">&#128202;</div>'
    '<div>'
    '<p class="hero-title">Skills Analysis</p>'
    '<p class="hero-subtitle">India Job Market Visualizer &nbsp;&middot;&nbsp; Demand by skill</p>'
    '</div>'
    '</div>'
    '<div class="hero-right">'
    '<div class="hero-live-badge"><div class="hero-live-dot"></div>Live</div>'
    f'<span class="hero-count">{len(skill_stats):,} skills tracked</span>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

# Back link
st.markdown('<a class="back-btn" href="/" target="_self">&#8592; Overview</a>',
            unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)


# ===========================================================================
# KPI STRIP
# ===========================================================================
top_skill    = skill_stats.iloc[0]["skill"] if len(skill_stats) > 0 else "N/A"
top_count    = int(skill_stats.iloc[0]["job_count"]) if len(skill_stats) > 0 else 0
rising       = skill_stats[skill_stats["growth_score"] > 10]
fastest      = rising.sort_values("growth_score", ascending=False).iloc[0]["skill"] \
               if len(rising) > 0 else "N/A"

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Skills tracked</div>'
        f'<div class="kpi-value">{len(skill_stats):,}</div>'
        f'<div class="kpi-delta-up">Extracted from job descriptions</div>'
        f'</div>', unsafe_allow_html=True)
with k2:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Most demanded skill</div>'
        f'<div class="kpi-value" style="font-size:20px;">{top_skill}</div>'
        f'<div class="kpi-delta-up">&#8593; {top_count:,} job postings</div>'
        f'</div>', unsafe_allow_html=True)
with k3:
    growing_count = len(skill_stats[skill_stats["growth_score"] > 5])
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Growing skills</div>'
        f'<div class="kpi-value">{growing_count}</div>'
        f'<div class="kpi-delta-up">&#8593; Growth score &gt; 5</div>'
        f'</div>', unsafe_allow_html=True)
with k4:
    declining_count = len(skill_stats[skill_stats["growth_score"] < -5])
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Fastest rising skill</div>'
        f'<div class="kpi-value" style="font-size:20px;">{fastest}</div>'
        f'<div class="kpi-delta-up">&#8593; Highest growth score</div>'
        f'</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ===========================================================================
# TOP 20 SKILLS -- full width ranked bar chart
# ===========================================================================
st.markdown('<div class="section-label">Top 20 skills by demand &nbsp;&middot;&nbsp; color = growth outlook</div>',
            unsafe_allow_html=True)

top20 = skill_stats.head(20).copy()
top20["color"] = top20["growth_score"].apply(growth_color)
top20 = top20.sort_values("job_count", ascending=True)  # ascending so largest is at top

fig_top20 = px.bar(
    top20, x="job_count", y="skill",
    orientation="h",
    color="color",
    color_discrete_map="identity",
    hover_data={"job_count": True, "growth_score": ":.1f", "color": False},
)
fig_top20.update_traces(
    hovertemplate="<b>%{y}</b><br>Jobs: %{x:,}<br>Growth score: %{customdata[1]:.1f}<extra></extra>"
)
fig_top20.update_layout(
    height=480,
    margin=dict(l=0, r=0, t=0, b=0),
    showlegend=False,
    **CHART_BG,
    yaxis=dict(title="", tickfont=dict(size=12)),
    xaxis=dict(title="Job postings", showgrid=True,
               gridcolor="rgba(255,255,255,0.05)", zeroline=False),
)
st.plotly_chart(fig_top20, use_container_width=True, config=PLOTLY_CFG)

# Color legend
leg1, leg2, leg3, leg4, leg5 = st.columns(5)
for col, label, color in zip(
    [leg1, leg2, leg3, leg4, leg5],
    ["Very fast growth", "Growing", "Stable", "Slowing", "Declining"],
    [C["very_fast"], C["growing"], C["stable"], C["slowing"], C["declining"]],
):
    col.markdown(
        f'<div style="display:flex;align-items:center;gap:6px;font-size:11px;color:#888780;">'
        f'<div style="width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0;"></div>'
        f'{label}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)


# ===========================================================================
# RISING vs DECLINING -- side by side
# ===========================================================================
r_col, d_col = st.columns(2)

with r_col:
    st.markdown('<div class="section-label">&#8593; Rising skills &nbsp;&middot;&nbsp; growth score &gt; 5</div>',
                unsafe_allow_html=True)
    rising_df = (
        skill_stats[skill_stats["growth_score"] > 5]
        .sort_values("growth_score", ascending=False)
        .head(12)
        .copy()
    )
    if len(rising_df) > 0:
        fig_rise = px.bar(
            rising_df.sort_values("growth_score", ascending=True),
            x="growth_score", y="skill", orientation="h",
            color_discrete_sequence=[C["growing"]],
        )
        fig_rise.update_layout(
            height=320, margin=dict(l=0,r=0,t=0,b=0),
            showlegend=False, **CHART_BG,
            yaxis=dict(title=""),
            xaxis=dict(title="Growth score", showgrid=True,
                       gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        )
        st.plotly_chart(fig_rise, use_container_width=True, config=PLOTLY_CFG)
    else:
        st.info("No rising skills in current filter.")

with d_col:
    st.markdown('<div class="section-label">&#8595; Slowing skills &nbsp;&middot;&nbsp; growth score &lt; -5</div>',
                unsafe_allow_html=True)
    declining_df = (
        skill_stats[skill_stats["growth_score"] < -5]
        .sort_values("growth_score", ascending=True)
        .head(12)
        .copy()
    )
    if len(declining_df) > 0:
        fig_dec = px.bar(
            declining_df.sort_values("growth_score", ascending=False),
            x="growth_score", y="skill", orientation="h",
            color_discrete_sequence=[C["slowing"]],
        )
        fig_dec.update_layout(
            height=320, margin=dict(l=0,r=0,t=0,b=0),
            showlegend=False, **CHART_BG,
            yaxis=dict(title=""),
            xaxis=dict(title="Growth score", showgrid=True,
                       gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        )
        st.plotly_chart(fig_dec, use_container_width=True, config=PLOTLY_CFG)
    else:
        st.info("No declining skills in current filter.")

st.markdown("<br>", unsafe_allow_html=True)


# ===========================================================================
# SKILL x ROLE HEATMAP
# ===========================================================================
st.markdown('<div class="section-label">Skill demand by role &nbsp;&middot;&nbsp; which skills appear in which roles</div>',
            unsafe_allow_html=True)

# Build skill x role matrix from jobs data
top_skills_list = skill_stats.head(15)["skill"].tolist()
top_roles_list  = (
    jobs_df["job_title_canonical"]
    .value_counts()
    .head(10)
    .index.tolist()
)
# Exclude "Other"
top_roles_list = [r for r in top_roles_list if r != "Other"][:10]

matrix_rows = []
for role in top_roles_list:
    role_jobs = jobs_df[jobs_df["job_title_canonical"] == role]
    for skill in top_skills_list:
        count = role_jobs["skills"].str.contains(
            skill, case=False, na=False
        ).sum()
        matrix_rows.append({"role": role, "skill": skill, "count": int(count)})

matrix_df = pd.DataFrame(matrix_rows)

if len(matrix_df) > 0 and matrix_df["count"].sum() > 0:
    pivot = matrix_df.pivot(index="skill", columns="role", values="count").fillna(0)
    fig_heat = px.imshow(
        pivot,
        color_continuous_scale=[
            [0.0, "#161922"],
            [0.3, "#0F6E56"],
            [1.0, "#5DCAA5"],
        ],
        aspect="auto",
    )
    fig_heat.update_layout(
        height=420,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#161922",
        font_color="#e8e6de",
        coloraxis_showscale=False,
        xaxis=dict(tickangle=-35, tickfont=dict(size=10)),
        yaxis=dict(tickfont=dict(size=11)),
    )
    fig_heat.update_traces(
        hovertemplate="Skill: <b>%{y}</b><br>Role: <b>%{x}</b><br>Count: %{z}<extra></extra>"
    )
    st.plotly_chart(fig_heat, use_container_width=True, config=PLOTLY_CFG)
else:
    st.info("Not enough skill-role overlap data for the current filter.") 