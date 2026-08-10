"""
pages/1_overview.py
====================
Phase 8 — Dashboard Core: Overview Page

The hub page. Entry point for all users.
Tells the complete Indian job market story in one screen.

Layout (top to bottom):
    1. Page config + dark theme CSS injection
    2. Header bar with title and last-updated
    3. KPI strip — 4 metric cards
    4. Outlook distribution row — 3 compact charts
    5. Treemap hero — full width, interactive
    6. Snapshot row — 3 mini charts with explore links
    7. Bottom filter bar

Author : India Job Market Visualizer
Phase  : 8 — Dashboard Core
"""

import sqlite3
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
# Page configuration — must be the FIRST Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title  = "India Job Market Visualizer",
    page_icon   = "📊",
    layout      = "wide",
    initial_sidebar_state = "collapsed",
)

# ---------------------------------------------------------------------------
# Dark theme CSS — injects custom styles into the Streamlit app
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* Hide Streamlit default header and footer */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Page background */
.stApp {background-color: #0f1117;}

/* Remove default padding */
.block-container {
    padding-top: 1rem;
    padding-bottom: 0rem;
    padding-left: 2rem;
    padding-right: 2rem;
}

/* KPI card styling */
.kpi-card {
    background: #161922;
    border: 0.5px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 14px 16px;
}
.kpi-label {
    font-size: 11px;
    color: #5F5E5A;
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.kpi-value {
    font-size: 28px;
    font-weight: 600;
    color: #e8e6de;
    line-height: 1;
}
.kpi-delta-up   {font-size: 11px; color: #5DCAA5; margin-top: 4px;}
.kpi-delta-down {font-size: 11px; color: #F09595; margin-top: 4px;}
.kpi-delta-neu  {font-size: 11px; color: #FAC775; margin-top: 4px;}

/* Section labels */
.section-label {
    font-size: 11px;
    color: #5F5E5A;
    margin-bottom: 6px;
    letter-spacing: 0.03em;
}

/* Explore link */
.explore-link {
    font-size: 11px;
    color: #1D9E75;
    text-align: right;
}

/* Divider */
.h-rule {
    border: none;
    border-top: 0.5px solid rgba(255,255,255,0.07);
    margin: 8px 0;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Color constants — frozen design system tokens
# ---------------------------------------------------------------------------
COLORS = {
    "very_fast" : "#0F6E56",
    "growing"   : "#1D9E75",
    "stable"    : "#BA7517",
    "slowing"   : "#993C1D",
    "declining" : "#A32D2D",
    "bg_card"   : "#161922",
    "bg_page"   : "#0f1117",
    "text_main" : "#e8e6de",
    "text_muted": "#5F5E5A",
}

PLOTLY_CONFIG = {
    "displayModeBar": False,
    "responsive": True,
}

CHART_BG = dict(
    plot_bgcolor  = "#161922",
    paper_bgcolor = "#161922",
    font_color    = "#e8e6de",
)


def growth_color(score: float) -> str:
    """Map a growth_score to the frozen color token."""
    if score > 20:   return COLORS["very_fast"]
    if score > 5:    return COLORS["growing"]
    if score > -5:   return COLORS["stable"]
    if score > -20:  return COLORS["slowing"]
    return COLORS["declining"]


def growth_label(score: float) -> str:
    if score > 20:  return "Very fast growth"
    if score > 5:   return "Growing"
    if score > -5:  return "Stable"
    if score > -20: return "Slowing"
    return "Declining"


# ===========================================================================
# LOAD DATA
# ===========================================================================
kpi        = load_kpi()
role_stats = load_role_stats()
skill_stats = load_skill_stats()
city_stats  = load_city_stats()
jobs_df     = load_jobs()
filter_opts = get_filter_options(jobs_df)

# ===========================================================================
# SIDEBAR FILTERS (collapsed by default on Overview)
# ===========================================================================
with st.sidebar:
    st.markdown("### Filters")
    sel_city     = st.selectbox("City",       filter_opts["cities"])
    sel_industry = st.selectbox("Industry",   filter_opts["industries"])
    sel_mode     = st.selectbox("Work mode",  filter_opts["work_modes"])
    sel_exp      = st.selectbox("Experience", filter_opts["experience"])

filtered_df = apply_filters(
    jobs_df,
    city=sel_city,
    industry=sel_industry,
    work_mode=sel_mode,
    experience=sel_exp,
)

# Recompute role stats from filtered data if filters are active
if sel_city != "All" or sel_industry != "All" or sel_mode != "All" or sel_exp != "Any":
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
# HEADER
# ===========================================================================
col_title, col_meta = st.columns([3, 1])
with col_title:
    st.markdown(
        "<h2 style='color:#e8e6de;margin:0;font-size:20px;font-weight:600;'>"
        "📊 India Job Market Overview</h2>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<p style='color:#5F5E5A;font-size:12px;margin:2px 0 0 0;'>"
        "Tech &amp; all sectors · Live data from Naukri.com</p>",
        unsafe_allow_html=True
    )
with col_meta:
    st.markdown(
        "<p style='color:#5F5E5A;font-size:11px;text-align:right;margin-top:8px;'>"
        f"Showing {len(filtered_df):,} jobs</p>",
        unsafe_allow_html=True
    )

st.markdown("<hr class='h-rule'>", unsafe_allow_html=True)


# ===========================================================================
# KPI STRIP — 4 cards
# ===========================================================================
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Total active jobs</div>
        <div class='kpi-value'>{kpi['total_jobs']:,}</div>
        <div class='kpi-delta-up'>↑ Full dataset</div>
    </div>""", unsafe_allow_html=True)

with k2:
    outlook = kpi["avg_outlook"]
    delta_class = "kpi-delta-up" if outlook > 0 else "kpi-delta-down"
    delta_text  = "Growing market" if outlook > 0 else "Contracting market"
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Avg. hiring outlook</div>
        <div class='kpi-value'>{outlook:+.1f}</div>
        <div class='{delta_class}'>{delta_text}</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Fast-growing roles</div>
        <div class='kpi-value'>{kpi['fast_growing_count']}</div>
        <div class='kpi-delta-up'>↑ Growth score &gt; 20</div>
    </div>""", unsafe_allow_html=True)

with k4:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Declining roles</div>
        <div class='kpi-value'>{kpi['declining_count']}</div>
        <div class='kpi-delta-down'>↓ Growth score &lt; -5</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ===========================================================================
# OUTLOOK DISTRIBUTION ROW — 3 compact charts
# ===========================================================================
od1, od2, od3 = st.columns(3)

with od1:
    st.markdown("<div class='section-label'>Outlook distribution · all roles</div>",
                unsafe_allow_html=True)
    # Stacked horizontal bar showing growth bucket proportions
    role_stats["color"] = role_stats["growth_score"].apply(growth_color)
    role_stats["label"] = role_stats["growth_score"].apply(growth_label)

    bucket_counts = role_stats.groupby("label")["job_count"].sum().reset_index()
    total = bucket_counts["job_count"].sum()
    bucket_counts["pct"] = (bucket_counts["job_count"] / total * 100).round(1)

    label_order  = ["Very fast growth","Growing","Stable","Slowing","Declining"]
    label_colors = [COLORS["very_fast"], COLORS["growing"], COLORS["stable"],
                    COLORS["slowing"],  COLORS["declining"]]

    fig_dist = go.Figure()
    for lbl, clr in zip(label_order, label_colors):
        row = bucket_counts[bucket_counts["label"] == lbl]
        pct = row["pct"].values[0] if len(row) > 0 else 0
        fig_dist.add_trace(go.Bar(
            x=[pct], y=[""], orientation="h",
            name=lbl, marker_color=clr,
            text=f"{pct:.0f}%", textposition="inside",
            hovertemplate=f"{lbl}: {pct:.1f}%<extra></extra>"
        ))

    fig_dist.update_layout(
        barmode="stack", height=60,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        **CHART_BG,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False),
    )
    st.plotly_chart(fig_dist, use_container_width=True, config=PLOTLY_CONFIG)

with od2:
    st.markdown("<div class='section-label'>Outlook by salary band</div>",
                unsafe_allow_html=True)
    bands = {
        "20+ LPA" : role_stats[role_stats["salary_median"] >= 20]["job_count"].sum(),
        "10–20 LPA": role_stats[(role_stats["salary_median"] >= 10) &
                                (role_stats["salary_median"] < 20)]["job_count"].sum(),
        "5–10 LPA" : role_stats[(role_stats["salary_median"] >= 5) &
                                (role_stats["salary_median"] < 10)]["job_count"].sum(),
        "<5 LPA"   : role_stats[role_stats["salary_median"] < 5]["job_count"].sum(),
    }
    band_df = pd.DataFrame(list(bands.items()), columns=["band","count"])
    fig_sal = px.bar(
        band_df, x="count", y="band", orientation="h",
        color="band",
        color_discrete_map={
            "20+ LPA"  : COLORS["very_fast"],
            "10–20 LPA": COLORS["growing"],
            "5–10 LPA" : COLORS["stable"],
            "<5 LPA"   : COLORS["declining"],
        }
    )
    fig_sal.update_layout(
        height=130, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_sal, use_container_width=True, config=PLOTLY_CONFIG)

with od3:
    st.markdown("<div class='section-label'>Outlook by education level</div>",
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
    edu_df["education"] = pd.Categorical(edu_df["education"],
                                          categories=edu_order, ordered=True)
    edu_df = edu_df.sort_values("education")

    fig_edu = px.bar(
        edu_df, x="count", y="education", orientation="h",
        color_discrete_sequence=[COLORS["growing"]],
    )
    fig_edu.update_layout(
        height=130, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_edu, use_container_width=True, config=PLOTLY_CONFIG)


# ===========================================================================
# TREEMAP HERO — full width
# ===========================================================================
st.markdown("<div class='section-label'>Job roles · rectangle size = openings · "
            "color = growth rate · hover any role for details</div>",
            unsafe_allow_html=True)

# Exclude "Other" from treemap — it's too dominant and not informative
treemap_df = filtered_roles[filtered_roles["job_title_canonical"] != "Other"].copy()

if len(treemap_df) > 0:
    treemap_df["color_val"] = treemap_df["growth_score"]
    treemap_df["hover_label"] = treemap_df.apply(
        lambda r: (
            f"<b>{r['job_title_canonical']}</b><br>"
            f"Jobs: {int(r['job_count']):,}<br>"
            f"Growth: {r['growth_score']:+.1f}"
        ), axis=1
    )

    fig_tree = px.treemap(
        treemap_df,
        path       = ["job_title_canonical"],
        values     = "job_count",
        color      = "color_val",
        color_continuous_scale = [
            [0.0,  COLORS["declining"]],
            [0.25, COLORS["slowing"]],
            [0.5,  COLORS["stable"]],
            [0.75, COLORS["growing"]],
            [1.0,  COLORS["very_fast"]],
        ],
        custom_data = ["hover_label"],
    )
    fig_tree.update_traces(
        hovertemplate="%{customdata[0]}<extra></extra>",
        textfont_size=12,
        marker_line_width=1,
        marker_line_color="#0f1117",
    )
    fig_tree.update_layout(
        height=380,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="#161922",
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_tree, use_container_width=True, config=PLOTLY_CONFIG)
else:
    st.info("No roles match the current filters.")

st.markdown("<br>", unsafe_allow_html=True)


# ===========================================================================
# SNAPSHOT ROW — 3 mini charts with explore links
# ===========================================================================
s1, s2, s3 = st.columns(3)

with s1:
    st.markdown("<div class='section-label'>Top skills by demand</div>",
                unsafe_allow_html=True)
    top_skills = skill_stats.head(8).copy()
    top_skills["color"] = top_skills["growth_score"].apply(growth_color)

    fig_sk = px.bar(
        top_skills, x="job_count", y="skill",
        orientation="h",
        color="color",
        color_discrete_map="identity",
    )
    fig_sk.update_layout(
        height=240, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        yaxis=dict(autorange="reversed", title=""),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    )
    st.plotly_chart(fig_sk, use_container_width=True, config=PLOTLY_CONFIG)
    st.markdown("<div class='explore-link'>→ explore skills page</div>",
                unsafe_allow_html=True)

with s2:
    st.markdown("<div class='section-label'>Hiring demand by city</div>",
                unsafe_allow_html=True)
    top_cities = city_stats.head(8).copy()
    top_cities["color"] = top_cities["growth_score"].apply(growth_color)

    fig_ct = px.bar(
        top_cities, x="job_count", y="city",
        orientation="h",
        color="color",
        color_discrete_map="identity",
    )
    fig_ct.update_layout(
        height=240, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        yaxis=dict(autorange="reversed", title=""),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    )
    st.plotly_chart(fig_ct, use_container_width=True, config=PLOTLY_CONFIG)
    st.markdown("<div class='explore-link'>→ explore cities page</div>",
                unsafe_allow_html=True)

with s3:
    st.markdown("<div class='section-label'>Salary snapshot (median LPA)</div>",
                unsafe_allow_html=True)
    sal_df = (
        role_stats[role_stats["salary_median"].notna()]
        [role_stats["job_title_canonical"] != "Other"]
        .nlargest(8, "salary_median")
        [["job_title_canonical","salary_median","growth_score"]]
        .copy()
    )
    sal_df["color"] = sal_df["growth_score"].apply(growth_color)

    fig_sal2 = px.bar(
        sal_df, x="salary_median", y="job_title_canonical",
        orientation="h",
        color="color",
        color_discrete_map="identity",
    )
    fig_sal2.update_layout(
        height=240, margin=dict(l=0,r=0,t=0,b=0),
        showlegend=False, **CHART_BG,
        yaxis=dict(autorange="reversed", title=""),
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    )
    st.plotly_chart(fig_sal2, use_container_width=True, config=PLOTLY_CONFIG)
    st.markdown("<div class='explore-link'>→ explore salary page</div>",
                unsafe_allow_html=True)