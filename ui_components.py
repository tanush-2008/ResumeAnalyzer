"""Reusable HTML/Plotly render helpers built on top of styles.py.

Keeping these out of app.py means the page-flow logic in app.py stays
readable, while every visual "component" (badge, gauge, rank card, timeline
item) is defined once and reused consistently.
"""

from __future__ import annotations

import html

import plotly.graph_objects as go
import streamlit as st

import styles

_ICON = {
    "Programming": "code",
    "Databases": "database",
    "Data Handling": "table_chart",
    "Machine Learning": "smart_toy",
    "NLP": "chat",
    "Computer Vision": "visibility",
    "Cloud": "cloud",
    "Tools": "build",
}


def inject_base_styles() -> None:
    st.markdown(styles.base_css(), unsafe_allow_html=True)


def icon(name: str) -> str:
    return f'<span class="msymbol">{name}</span>'


def hero(title: str, subtitle: str, badge_text: str) -> None:
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-badge">{icon('auto_awesome')} {html.escape(badge_text)}</div>
            <h1>{icon('description')} {html.escape(title)}</h1>
            <p>{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(icon_name: str, title: str, subtitle: str | None = None) -> None:
    st.markdown(
        f"""
        <div class="section-head">{icon(icon_name)}<h3>{html.escape(title)}</h3></div>
        {f'<div class="section-sub">{html.escape(subtitle)}</div>' if subtitle else ''}
        """,
        unsafe_allow_html=True,
    )


def callout(icon_name: str, text_html: str) -> None:
    st.markdown(
        f'<div class="callout">{icon(icon_name)}<div>{text_html}</div></div>',
        unsafe_allow_html=True,
    )


def skill_badges_by_category(by_category: dict[str, list[str]]) -> None:
    if not by_category:
        callout("info", "No known skills were detected in this resume.")
        return
    for category, skills in by_category.items():
        color = styles.category_color(category)
        cat_icon = _ICON.get(category, "label")
        badges = "".join(
            f'<span class="skill-badge neutral" style="background:{color}18;'
            f'color:{color};border-color:{color}40;">{html.escape(s)}</span>'
            for s in skills
        )
        st.markdown(
            f"""
            <div class="badge-group">
                <div class="badge-group-label">
                    <span class="badge-dot" style="background:{color};"></span>
                    {icon(cat_icon)} {html.escape(category)}
                </div>
                <div>{badges}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def matched_missing_badges(matched: list[str], missing: list[str]) -> None:
    matched_html = "".join(
        f'<span class="skill-badge found">{icon("check_circle")} {html.escape(s)}</span>'
        for s in matched
    ) or '<span class="section-sub" style="margin:0;">None detected.</span>'
    missing_html = "".join(
        f'<span class="skill-badge missing">{icon("cancel")} {html.escape(s)}</span>'
        for s in missing
    ) or '<span class="section-sub" style="margin:0;">None - all required skills found!</span>'
    st.markdown(
        f'<div class="badge-group-label">Skills Found</div><div>{matched_html}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="badge-group-label" style="margin-top:0.8rem;">Missing Skills</div>'
        f"<div>{missing_html}</div>",
        unsafe_allow_html=True,
    )


def score_gauge(score: float, title: str = "Match Score") -> go.Figure:
    color, _ = styles.score_tier(score)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"suffix": "%", "font": {"size": 40, "family": "Plus Jakarta Sans"}},
            title={"text": title, "font": {"size": 14, "color": styles.INK_SOFT}},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": styles.INK_SOFT, "tickwidth": 1},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": styles.SOFT_BG,
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 45], "color": "#FEF2F2"},
                    {"range": [45, 70], "color": "#FFFBEB"},
                    {"range": [70, 100], "color": "#ECFDF5"},
                ],
            },
        )
    )
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter"},
    )
    return fig


def stat_chips(stats: list[tuple[str, str]]) -> None:
    chips = "".join(
        f'<div class="chip"><div class="chip-label">{html.escape(label)}</div>'
        f'<div class="chip-value">{html.escape(str(value))}</div></div>'
        for label, value in stats
    )
    st.markdown(f'<div class="chip-row">{chips}</div>', unsafe_allow_html=True)


_MEDALS = [("#FFD700", "🥇"), ("#C0C0C0", "🥈"), ("#CD7F32", "🥉")]


def role_rank_cards(ranked_matches) -> None:
    cols = st.columns(len(ranked_matches))
    for i, (col, match) in enumerate(zip(cols, ranked_matches)):
        color, _ = styles.score_tier(match.score)
        medal_color, medal_emoji = _MEDALS[i] if i < len(_MEDALS) else ("#94A3B8", str(i + 1))
        with col:
            st.markdown(
                f"""
                <div class="rank-card {'top' if i == 0 else ''}">
                    <div class="rank-medal" style="background:{medal_color}30;">{medal_emoji}</div>
                    <div class="rank-role">{html.escape(match.role)}</div>
                    <div class="rank-score" style="color:{color};">{match.score:.1f}%</div>
                    <div class="rank-bar-track">
                        <div class="rank-bar-fill" style="width:{min(match.score,100)}%;background:{color};"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def roadmap_timeline(roadmap) -> None:
    if not roadmap:
        callout("celebration", "No missing skills for this role - great match!")
        return
    weeks: dict[str, list[str]] = {}
    for item in roadmap:
        weeks.setdefault(item.week, []).append(item.topic)

    items_html = ""
    # Built as compact single-line HTML with no blank lines between items:
    # Streamlit's Markdown pass treats a blank line followed by an indented
    # line as a code block, which would otherwise break items 2+ into raw text.
    for i, (week, topics) in enumerate(weeks.items(), start=1):
        items_html += (
            '<div class="timeline-item">'
            f'<div class="timeline-dot">{i}</div>'
            '<div class="timeline-card">'
            f'<div class="timeline-week">{html.escape(week)}</div>'
            f'<div class="timeline-topics">{html.escape(", ".join(topics))}</div>'
            "</div></div>"
        )
    st.markdown(f'<div class="timeline">{items_html}</div>', unsafe_allow_html=True)


def role_bar_chart(ranked_matches):
    roles = [m.role for m in ranked_matches]
    scores = [m.score for m in ranked_matches]
    bar_colors = [styles.score_tier(s)[0] for s in scores]

    fig = go.Figure(
        go.Bar(
            x=scores,
            y=roles,
            orientation="h",
            marker=dict(color=bar_colors, line=dict(width=0)),
            text=[f"{s:.1f}%" for s in scores],
            textposition="outside",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        height=max(220, 60 * len(roles)),
        margin=dict(l=10, r=30, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter", "color": styles.INK},
        xaxis=dict(range=[0, 105], showgrid=True, gridcolor=styles.BORDER, title="Match Score (%)"),
        yaxis=dict(autorange="reversed", title=""),
        showlegend=False,
    )
    return fig


def how_it_works() -> None:
    steps = [
        ("upload_file", "1. Upload", "Add your resume as a PDF or DOCX file - it's processed in memory only."),
        ("target", "2. Pick a target", "Choose a predefined job role or paste any job description."),
        ("insights", "3. Get insights", "See your match score, missing skills, and a week-by-week roadmap."),
    ]
    cols = st.columns(3)
    for col, (ic, title, body) in zip(cols, steps):
        with col:
            st.markdown(
                f"""
                <div class="step-card">
                    <div class="step-num">{icon(ic)}</div>
                    <div class="step-title">{html.escape(title)}</div>
                    <div class="step-body">{html.escape(body)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
