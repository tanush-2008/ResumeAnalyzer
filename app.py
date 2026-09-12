"""Module 7: Streamlit dashboard tying together the whole AI Resume Analyzer
and Job Recommendation System pipeline.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from job_matcher import load_job_roles, rank_roles, get_role_match
from resume_parser import ResumeParseError, extract_text
from roadmap_generator import generate_roadmap
from report_generator import build_report_pdf
from skill_extractor import load_skill_dictionary, extract_skills

st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="wide")

TOP_N_RECOMMENDATIONS = 3


@st.cache_data
def _load_job_roles_cached():
    return load_job_roles()


@st.cache_data
def _load_skill_dictionary_cached():
    return load_skill_dictionary()


def main() -> None:
    st.title("📄 AI Resume Analyzer & Job Recommendation System")
    st.caption(
        "Upload your resume to see how well it matches different job roles, "
        "which skills you're missing, and a simple roadmap to close the gap."
    )

    with st.expander("ℹ️ Responsible use of this tool", expanded=False):
        st.markdown(
            "- This tool is for **guidance only** - it does not make hiring or "
            "rejection decisions.\n"
            "- It evaluates only job-related **skills, education, projects, and "
            "experience** - never gender, age, religion, nationality, photos, "
            "marital status, or disability.\n"
            "- Match scores are **estimates**, not guarantees. A missing keyword "
            "does not always mean missing ability.\n"
            "- Your uploaded file is processed in memory for this session only "
            "and is not stored permanently."
        )

    job_roles_df = _load_job_roles_cached()
    skill_df = _load_skill_dictionary_cached()

    col_upload, col_role = st.columns([2, 1])
    with col_upload:
        uploaded_file = st.file_uploader("Upload your resume", type=["pdf", "docx"])
    with col_role:
        target_role = st.selectbox("Target role", options=job_roles_df["role"].tolist())

    if uploaded_file is None:
        st.info("Upload a PDF or DOCX resume to get started.")
        return

    st.success(f"Uploaded: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")

    file_bytes = uploaded_file.getvalue()
    try:
        resume_text = extract_text(uploaded_file.name, file_bytes)
    except ResumeParseError as exc:
        st.error(str(exc))
        return

    extraction = extract_skills(resume_text, skill_df=skill_df)
    ranked_matches = rank_roles(resume_text, extraction.found_skills, job_roles_df=job_roles_df)
    target_match = get_role_match(target_role, ranked_matches)

    st.divider()

    st.subheader("🧩 Extracted Skills")
    if extraction.by_category:
        cat_cols = st.columns(min(len(extraction.by_category), 4) or 1)
        for i, (category, skills) in enumerate(extraction.by_category.items()):
            with cat_cols[i % len(cat_cols)]:
                st.markdown(f"**{category}**")
                for skill in skills:
                    st.markdown(f"- {skill}")
    else:
        st.warning("No known skills were detected in this resume.")

    st.divider()

    left, right = st.columns([1, 1])

    with left:
        st.subheader(f"🎯 Match Score for {target_role}")
        st.metric("Resume Match Score", f"{target_match.score:.1f}%")
        st.progress(min(int(target_match.score), 100))

        st.markdown("**Skills Found**")
        st.write(", ".join(target_match.matched_skills) or "None detected.")

        st.markdown("**Missing Skills**")
        st.write(", ".join(target_match.missing_skills) or "None - all required skills found!")

    with right:
        st.subheader("📊 Match Score by Role")
        chart_df = pd.DataFrame(
            {"role": [m.role for m in ranked_matches], "score": [m.score for m in ranked_matches]}
        )
        fig = px.bar(
            chart_df,
            x="score",
            y="role",
            orientation="h",
            range_x=[0, 100],
            labels={"score": "Match Score (%)", "role": "Job Role"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🏆 Recommended Roles")
    top_matches = ranked_matches[:TOP_N_RECOMMENDATIONS]
    rec_cols = st.columns(len(top_matches))
    for i, (col, match) in enumerate(zip(rec_cols, top_matches), start=1):
        with col:
            st.metric(f"#{i}: {match.role}", f"{match.score:.1f}%")

    st.divider()

    st.subheader(f"🗺️ Suggested Learning Roadmap for {target_role}")
    roadmap = generate_roadmap(target_match.missing_skills)
    if roadmap:
        weeks: dict[str, list[str]] = {}
        for item in roadmap:
            weeks.setdefault(item.week, []).append(item.topic)
        for week, topics in weeks.items():
            st.markdown(f"**{week}:** {', '.join(topics)}")
    else:
        st.success("No missing skills for this role - great match!")

    st.divider()

    st.subheader("⬇️ Download Full Analysis Report")
    report_bytes = build_report_pdf(
        target_role=target_role,
        target_match=target_match,
        ranked_matches=ranked_matches,
        roadmap=roadmap,
        top_n_recommendations=TOP_N_RECOMMENDATIONS,
    )
    st.download_button(
        "Download report (PDF)",
        data=report_bytes,
        file_name=f"resume_analysis_{target_role.replace(' ', '_').lower()}.pdf",
        mime="application/pdf",
    )


if __name__ == "__main__":
    main()
