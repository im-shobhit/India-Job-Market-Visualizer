"""
pages/1_overview.py
====================
Phase 8 -- Dashboard Core: Overview Page

The hub page. Entry point for all users.
Tells the complete Indian job market story in one screen.

Layout (top to bottom):
    1. Page config + dark theme CSS injection
    2. Hero header bar with brand, live badge, job count
    3. KPI strip -- 4 metric cards
    4. Outlook distribution row -- 3 compact charts
    5. Treemap hero -- full width, interactive
    6. Snapshot row -- 3 mini charts with explore links
    7. Sidebar filters (collapsed by default)

Author : India Job Market Visualizer
Phase  : 8 -- Dashboard Core
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path
import sys

# Make app/components importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.components.data_loader import (
    load_jobs, load_role_stats, load_skill_stats,
    load_city_stats, load_kpi, apply_filters, get_filter_options
)

# ---------------------------------------------------------------------------
# Page configuration -- must be the FIRST Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="India Job Market Visualizer",
    page_icon="chart_with_upwards_trend",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS -- all plain ASCII, no unicode dashes in comments
# ---------------------------------------------------------------------------
DARK_CSS = """
<style>

/* hide default streamlit chrome */
#MainMenu {visibility: hidden !important;}
footer    {visibility: hidden !important;}
header    {visibility: hidden !important;}
.stDeployButton {display: none !important;}

/* hide the default arrow sidebar toggle completely */
[data-testid="collapsedControl"] {
    display: none !important;
    visibility: hidden !important;
}

/* page background and content area */
.stApp {background-color: #0f1117;}
.block-container {
    padding-top: 0rem !important;
    padding-bottom: 1rem;
    padding-left: 2rem;
    padding-right: 2rem;
    max-width: 100% !important;
}

/* HERO BAR: 3 equal columns - hamburger | centre title | right meta */
.hero-bar {
    background: linear-gradient(135deg, #0d1014 0%, #161922 60%, #0F2A20 100%);
    border-bottom: 0.5px solid rgba(29,158,117,0.3);
    padding: 0 28px;
    height: 64px;
    width: calc(100% + 4rem);
    margin: 0 -2rem 1.5rem -2rem;
    box-sizing: border-box;
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    align-items: center;
}

/* Left col: hamburger button */
.hbg {
    display: flex;
    flex-direction: column;
    gap: 5px;
    cursor: pointer;
    width: 36px;
    height: 36px;
    justify-content: center;
    background: none;
    border: none;
    padding: 0;
    border-radius: 6px;
}
.hbg:hover {background: rgba(255,255,255,0.07);}
.hml {
    width: 20px;
    height: 2px;
    background: #888780;
    border-radius: 2px;
    display: block;
    transition: background 0.15s;
}
.hbg:hover .hml {background: #e8e6de;}

/* Centre col: brand (icon + title + subtitle) - perfectly centred */
.hero-brand {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    text-align: left;
}
.hero-icon {
    width: 36px; height: 36px; flex-shrink: 0;
    background: linear-gradient(135deg, #1D9E75 0%, #0F6E56 100%);
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px;
}
.hero-title {
    font-size: 18px; font-weight: 700; color: #e8e6de;
    letter-spacing: -0.3px; line-height: 1.1; margin: 0;
}
.hero-subtitle {font-size: 11px; color: #5F5E5A; margin: 2px 0 0 0;}

/* Right col: live badge + count - right-aligned */
.hero-right {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    justify-content: center;
    gap: 5px;
}
.hero-live-badge {
    display: flex; align-items: center; gap: 5px;
    font-size: 11px; color: #5DCAA5;
    background: rgba(29,158,117,0.12);
    border: 0.5px solid rgba(29,158,117,0.3);
    border-radius: 20px; padding: 3px 10px;
}
.hero-live-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #5DCAA5;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%   {opacity: 1;}
    50%  {opacity: 0.3;}
    100% {opacity: 1;}
}
.hero-count {font-size: 11px; color: #5F5E5A; white-space: nowrap;}

/* -- Sidebar styling -- */
[data-testid="stSidebar"] {
    background: #0d1014 !important;
    border-right: 0.5px solid rgba(255,255,255,0.07) !important;
}
/* sidebar nav links -- Streamlit 1.45 selectors */
[data-testid="stSidebarNavLink"] span {
    font-size: 13px !important;
    font-weight: 500 !important;
}
div[data-testid="stSidebarNav"] a {
    border-radius: 8px !important;
    padding: 8px 12px !important;
    color: #888780 !important;
}
div[data-testid="stSidebarNav"] a:hover {
    background: rgba(255,255,255,0.06) !important;
    color: #e8e6de !important;
}
div[data-testid="stSidebarNav"] a[aria-current="page"] {
    background: rgba(29,158,117,0.15) !important;
    color: #5DCAA5 !important;
    border-left: 3px solid #1D9E75 !important;
}
.back-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    font-weight: 500;
    color: #1D9E75;
    background: rgba(29,158,117,0.1);
    border: 0.5px solid rgba(29,158,117,0.3);
    border-radius: 6px;
    padding: 6px 14px;
    text-decoration: none;
    margin-bottom: 16px;
    cursor: pointer;
}
.back-btn:hover {
    background: rgba(29,158,117,0.2);
    color: #5DCAA5;
}

/* kpi cards */
.kpi-card {
    background: #161922;
    border: 0.5px solid rgba(255,255,255,0.08);
    border-radius: 8px; padding: 14px 16px;
}
.kpi-label {
    font-size: 11px; color: #5F5E5A; margin-bottom: 4px;
    text-transform: uppercase; letter-spacing: 0.05em;
}
.kpi-value {font-size: 28px; font-weight: 600; color: #e8e6de; line-height: 1;}
.kpi-delta-up   {font-size: 11px; color: #5DCAA5; margin-top: 4px;}
.kpi-delta-down {font-size: 11px; color: #F09595; margin-top: 4px;}
.kpi-delta-neu  {font-size: 11px; color: #FAC775; margin-top: 4px;}

/* section labels */
.section-label {font-size: 11px; color: #5F5E5A; margin-bottom: 6px; letter-spacing: 0.03em;}

/* explore links */
.explore-link {font-size: 11px; color: #1D9E75; text-align: right;}

</style>
"""

st.markdown(DARK_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------
C = {
    "very_fast" : "#0F6E56",
    "growing"   : "#1D9E75",
    "stable"    : "#BA7517",
    "slowing"   : "#993C1D",
    "declining" : "#A32D2D",
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


# ===========================================================================
# LOAD DATA
# ===========================================================================
kpi         = load_kpi()
role_stats  = load_role_stats()
skill_stats = load_skill_stats()
city_stats  = load_city_stats()
jobs_df     = load_jobs()
filter_opts = get_filter_options(jobs_df)

# ===========================================================================
# SIDEBAR FILTERS (collapsed by default)
# ===========================================================================
with st.sidebar:
    # Custom navigation -- replaces auto-generated Streamlit nav
    st.markdown(
        '<div style="padding:8px 0 12px 0;">'
        '<p style="font-size:10px;color:#5F5E5A;text-transform:uppercase;'
        'letter-spacing:0.1em;padding:0 8px;margin-bottom:6px;">Navigation</p>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.page_link("app.py",             label="Overview", icon="🏠")
    st.page_link("pages/1_skills.py",  label="Skills",   icon="📊")
    st.markdown("---")
    st.markdown("### Filters")
    sel_city     = st.selectbox("City",       filter_opts["cities"])
    sel_industry = st.selectbox("Industry",   filter_opts["industries"])
    sel_mode     = st.selectbox("Work mode",  filter_opts["work_modes"])
    sel_exp      = st.selectbox("Experience", filter_opts["experience"])

filtered_df = apply_filters(
    jobs_df,
    city=sel_city, industry=sel_industry,
    work_mode=sel_mode, experience=sel_exp,
)

filters_active = (
    sel_city != "All" or sel_industry != "All"
    or sel_mode != "All" or sel_exp != "Any"
)

if filters_active:
    filtered_roles = (
        filtered_df
        .groupby("job_title_canonical")
        .agg(job_count=("job_id","count"), growth_score=("growth_score","first"))
        .reset_index()
        .sort_values("job_count", ascending=False)
    )
else:
    filtered_roles = role_stats


# ===========================================================================
# HERO HEADER
# ===========================================================================
# The hamburger button uses Streamlit's component HTML trick to
# call the real sidebar toggle button which is hidden beneath.
_hero = (
    '<div class="hero-bar">'

    # Left col: hamburger (onclick finds and clicks the hidden Streamlit toggle)
    '<div></div>'

    # Centre col: icon + title + subtitle (centred by grid)
    '<div class="hero-brand">'
    '<div class="hero-icon">&#128202;</div>'
    '<div>'
    '<p class="hero-title">India Job Market Visualizer</p>'
    '<p class="hero-subtitle">Tech &amp; all sectors &nbsp;&middot;&nbsp; Live data from Naukri.com</p>'
    '</div>'
    '</div>'

    # Right col: live badge stacked above job count
    '<div class="hero-right">'
    '<div class="hero-live-badge"><div class="hero-live-dot"></div>&#11044; Live</div>'
    f'<span class="hero-count">Q2 2025 &nbsp;&middot;&nbsp; {len(filtered_df):,} active jobs</span>'
    '</div>'

    '</div>'
)
st.markdown(_hero, unsafe_allow_html=True)

# restore inner padding for content below the hero bar
st.markdown(
    '<style>.block-container{padding-left:2rem !important;padding-right:2rem !important;}</style>',
    unsafe_allow_html=True,
)

# ===========================================================================
# KPI STRIP
# ===========================================================================
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Total active jobs</div>'
        f'<div class="kpi-value">{kpi["total_jobs"]:,}</div>'
        f'<div class="kpi-delta-up">&#8593; Full dataset</div>'
        f'</div>', unsafe_allow_html=True)

with k2:
    outlook = kpi["avg_outlook"]
    cls  = "kpi-delta-up" if outlook > 0 else "kpi-delta-down"
    txt  = "Growing market" if outlook > 0 else "Contracting market"
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Avg. hiring outlook</div>'
        f'<div class="kpi-value">{outlook:+.1f}</div>'
        f'<div class="{cls}">{txt}</div>'
        f'</div>', unsafe_allow_html=True)

with k3:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Fast-growing roles</div>'
        f'<div class="kpi-value">{kpi["fast_growing_count"]}</div>'
        f'<div class="kpi-delta-up">&#8593; Growth score &gt; 20</div>'
        f'</div>', unsafe_allow_html=True)

with k4:
    st.markdown(
        f'<div class="kpi-card">'
        f'<div class="kpi-label">Declining roles</div>'
        f'<div class="kpi-value">{kpi["declining_count"]}</div>'
        f'<div class="kpi-delta-down">&#8595; Growth score &lt; -5</div>'
        f'</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ===========================================================================
# OUTLOOK DISTRIBUTION ROW
# ===========================================================================
od1, od2, od3 = st.columns(3)

with od1:
    st.markdown('<div class="section-label">Outlook distribution &middot; all roles</div>',
                unsafe_allow_html=True)
    rs = role_stats.copy()
    rs["label"] = rs["growth_score"].apply(growth_label)
    bucket = rs.groupby("label")["job_count"].sum().reset_index()
    total  = bucket["job_count"].sum()
    bucket["pct"] = (bucket["job_count"] / total * 100).round(1)

    label_order  = ["Very fast growth","Growing","Stable","Slowing","Declining"]
    label_colors = [C["very_fast"], C["growing"], C["stable"], C["slowing"], C["declining"]]

    fig_dist = go.Figure()
    for lbl, clr in zip(label_order, label_colors):
        row = bucket[bucket["label"] == lbl]
        pct = row["pct"].values[0] if len(row) > 0 else 0
        fig_dist.add_trace(go.Bar(
            x=[pct], y=[""], orientation="h",
            name=lbl, marker_color=clr,
            text=f"{pct:.0f}%", textposition="inside",
            hovertemplate=f"{lbl}: {pct:.1f}%<extra></extra>",
        ))
    fig_dist.update_layout(
        barmode="stack", height=60,
        margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False),
    )
    st.plotly_chart(fig_dist, use_container_width=True, config=PLOTLY_CFG)

with od2:
    st.markdown('<div class="section-label">Outlook by salary band</div>',
                unsafe_allow_html=True)
    bands = {
        "20+ LPA"  : role_stats[role_stats["salary_median"] >= 20]["job_count"].sum(),
        "10-20 LPA": role_stats[(role_stats["salary_median"] >= 10) &
                                (role_stats["salary_median"] < 20)]["job_count"].sum(),
        "5-10 LPA" : role_stats[(role_stats["salary_median"] >= 5) &
                                (role_stats["salary_median"] < 10)]["job_count"].sum(),
        "<5 LPA"   : role_stats[role_stats["salary_median"] < 5]["job_count"].sum(),
    }
    band_df = pd.DataFrame(list(bands.items()), columns=["band","count"])
    fig_sal = px.bar(
        band_df, x="count", y="band", orientation="h",
        color="band",
        color_discrete_map={
            "20+ LPA"  : C["very_fast"],
            "10-20 LPA": C["growing"],
            "5-10 LPA" : C["stable"],
            "<5 LPA"   : C["declining"],
        },
    )
    fig_sal.update_layout(
        height=130, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_sal, use_container_width=True, config=PLOTLY_CFG)

with od3:
    st.markdown('<div class="section-label">Outlook by education level</div>',
                unsafe_allow_html=True)
    edu_df = (
        jobs_df[jobs_df["education"].isin(
            ["PhD","Master's","Bachelor's","Diploma","Any"]
        )]
        .groupby("education")["job_id"].count()
        .reset_index()
        .rename(columns={"job_id":"count"})
    )
    edu_order = ["PhD","Master's","Bachelor's","Diploma","Any"]
    edu_df["education"] = pd.Categorical(
        edu_df["education"], categories=edu_order, ordered=True
    )
    edu_df = edu_df.sort_values("education")
    fig_edu = px.bar(
        edu_df, x="count", y="education", orientation="h",
        color_discrete_sequence=[C["growing"]],
    )
    fig_edu.update_layout(
        height=130, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_edu, use_container_width=True, config=PLOTLY_CFG)


# ===========================================================================
# TREEMAP HERO
# ===========================================================================
st.markdown('<div class="section-label">Job roles &middot; rectangle size = openings '
            '&middot; color = growth rate &middot; hover any role for details</div>',
            unsafe_allow_html=True)

treemap_df = filtered_roles[filtered_roles["job_title_canonical"] != "Other"].copy()

if len(treemap_df) > 0:
    treemap_df["color_val"] = treemap_df["growth_score"]
    fig_tree = px.treemap(
        treemap_df,
        path   = ["job_title_canonical"],
        values = "job_count",
        color  = "color_val",
        color_continuous_scale=[
            [0.0,  C["declining"]],
            [0.25, C["slowing"]],
            [0.5,  C["stable"]],
            [0.75, C["growing"]],
            [1.0,  C["very_fast"]],
        ],
        hover_data={"job_count": True, "color_val": ":.1f"},
    )
    fig_tree.update_traces(
        textfont_size=12,
        marker_line_width=1,
        marker_line_color="#0f1117",
        hovertemplate="<b>%{label}</b><br>Jobs: %{value:,}<br>Growth score: %{color:.1f}<extra></extra>",
    )
    fig_tree.update_layout(
        height=380,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#161922",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_tree, use_container_width=True, config=PLOTLY_CFG)
else:
    st.info("No roles match the current filters.")

st.markdown("<br>", unsafe_allow_html=True)


# ===========================================================================
# SNAPSHOT ROW
# ===========================================================================
s1, s2, s3 = st.columns(3)

with s1:
    st.markdown('<div class="section-label">Top skills by demand</div>',
                unsafe_allow_html=True)
    top_sk = skill_stats.head(8).copy()
    top_sk["color"] = top_sk["growth_score"].apply(growth_color)
    fig_sk = px.bar(
        top_sk, x="job_count", y="skill", orientation="h",
        color="color", color_discrete_map="identity",
    )
    fig_sk.update_layout(
        height=240, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        yaxis=dict(autorange="reversed", title=""),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    )
    st.plotly_chart(fig_sk, use_container_width=True, config=PLOTLY_CFG)
    st.markdown('<div class="explore-link">explore skills page &rarr;</div>',
                unsafe_allow_html=True)

with s2:
    st.markdown('<div class="section-label">Hiring demand by city</div>',
                unsafe_allow_html=True)
    top_ct = city_stats.head(8).copy()
    top_ct["color"] = top_ct["growth_score"].apply(growth_color)
    fig_ct = px.bar(
        top_ct, x="job_count", y="city", orientation="h",
        color="color", color_discrete_map="identity",
    )
    fig_ct.update_layout(
        height=240, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        yaxis=dict(autorange="reversed", title=""),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    )
    st.plotly_chart(fig_ct, use_container_width=True, config=PLOTLY_CFG)
    st.markdown('<div class="explore-link">explore cities page &rarr;</div>',
                unsafe_allow_html=True)

with s3:
    st.markdown('<div class="section-label">Salary snapshot (median LPA)</div>',
                unsafe_allow_html=True)
    sal_df = (
        role_stats[
            role_stats["salary_median"].notna() &
            (role_stats["job_title_canonical"] != "Other")
        ]
        .nlargest(8, "salary_median")
        [["job_title_canonical","salary_median","growth_score"]]
        .copy()
    )
    sal_df["color"] = sal_df["growth_score"].apply(growth_color)
    fig_sal2 = px.bar(
        sal_df, x="salary_median", y="job_title_canonical",
        orientation="h",
        color="color", color_discrete_map="identity",
    )
    fig_sal2.update_layout(
        height=240, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        yaxis=dict(autorange="reversed", title=""),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    )
    st.plotly_chart(fig_sal2, use_container_width=True, config=PLOTLY_CFG)
    st.markdown('<div class="explore-link">explore salary page &rarr;</div>',
                unsafe_allow_html=True)
