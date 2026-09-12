"""Module 7: Streamlit dashboard tying together the whole AI Resume Analyzer
and Job Recommendation System pipeline - including the optional advanced
features (semantic matching, spaCy extraction, custom job descriptions,
LLM feedback, resume sections, login/saved reports, skill-dictionary
feedback).
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import backend_client
from job_matcher import (
    load_job_roles,
    rank_roles,
    rank_custom_job_description,
    get_role_match,
    semantic_model_available,
)
from llm_feedback import get_resume_feedback, is_llm_configured
from resume_parser import ResumeParseError, extract_text
from roadmap_generator import generate_roadmap
from report_generator import build_report_pdf
from section_detector import detect_sections
from skill_extractor import (
    load_skill_dictionary,
    extract_skills,
    extract_skills_spacy,
    spacy_model_available,
)
from skill_feedback import suggest_skill

st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="wide")

TOP_N_RECOMMENDATIONS = 3


@st.cache_data
def _load_job_roles_cached():
    return load_job_roles()


@st.cache_data
def _load_skill_dictionary_cached():
    return load_skill_dictionary()


def _init_session_state() -> None:
    st.session_state.setdefault("auth_token", None)
    st.session_state.setdefault("auth_email", None)


def render_sidebar(job_roles_df: pd.DataFrame) -> dict:
    st.sidebar.header("⚙️ Settings")

    matching_mode_label = st.sidebar.radio(
        "Matching approach",
        options=["Beginner (TF-IDF + skill overlap)", "Advanced (+ semantic embeddings)"],
        help="Advanced mode blends in Sentence-Transformers semantic similarity, "
        "on top of TF-IDF and skill overlap.",
    )
    mode = "advanced" if matching_mode_label.startswith("Advanced") else "beginner"

    use_spacy = st.sidebar.checkbox(
        "Use spaCy for skill extraction",
        value=False,
        help="Uses spaCy's PhraseMatcher instead of plain regex keyword matching.",
    )
    if use_spacy and not spacy_model_available():
        st.sidebar.warning("spaCy model not installed - falling back to keyword matching.")
    if mode == "advanced" and not semantic_model_available():
        st.sidebar.warning(
            "Sentence-Transformers model unavailable (offline?) - falling back to TF-IDF only."
        )

    st.sidebar.divider()
    render_auth_section()

    return {"mode": mode, "use_spacy": use_spacy}


def render_auth_section() -> None:
    st.sidebar.subheader("👤 Account (optional)")

    if not backend_client.backend_available():
        st.sidebar.caption(
            "Backend offline - login and saved reports are disabled. "
            "Run the FastAPI backend (see README) to enable them."
        )
        return

    if st.session_state.auth_token:
        st.sidebar.success(f"Logged in as {st.session_state.auth_email}")
        if st.sidebar.button("Log out"):
            st.session_state.auth_token = None
            st.session_state.auth_email = None
            st.rerun()
        return

    tab_login, tab_register = st.sidebar.tabs(["Log in", "Register"])
    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in", key="login_btn"):
            token, message = backend_client.login(email, password)
            if token:
                st.session_state.auth_token = token
                st.session_state.auth_email = email
                st.rerun()
            else:
                st.error(message)

    with tab_register:
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input(
            "Password (min 8 chars)", type="password", key="reg_password"
        )
        if st.button("Create account", key="register_btn"):
            ok, message = backend_client.register(reg_email, reg_password)
            (st.success if ok else st.error)(message)


def render_saved_reports() -> None:
    if not st.session_state.auth_token:
        return
    st.subheader("💾 My Saved Reports")
    reports = backend_client.list_reports(st.session_state.auth_token)
    if not reports:
        st.caption("No saved reports yet.")
        return
    for report in reports:
        cols = st.columns([2, 1, 1, 1])
        cols[0].write(f"**{report['target_role']}** - {report['created_at'][:10]}")
        cols[1].write(f"{report['match_score']:.1f}%")
        if report["has_pdf"]:
            pdf_bytes = backend_client.get_report_pdf(st.session_state.auth_token, report["id"])
            if pdf_bytes:
                cols[2].download_button(
                    "PDF",
                    data=pdf_bytes,
                    file_name=f"saved_report_{report['id']}.pdf",
                    mime="application/pdf",
                    key=f"dl_{report['id']}",
                )


def render_responsible_ai_note() -> None:
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
            "and is not stored permanently unless you explicitly save a report."
        )


def render_extracted_skills(extraction) -> None:
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

    with st.expander("🛠️ Don't see a skill you have? Flag it for review"):
        col1, col2, col3 = st.columns([2, 2, 1])
        flagged_skill = col1.text_input("Missing skill", key="flag_skill")
        flagged_category = col2.text_input("Category (optional)", key="flag_category")
        if col3.button("Submit", key="flag_submit") and flagged_skill.strip():
            suggest_skill(flagged_skill, flagged_category or "Uncategorized")
            st.success(f"Thanks! '{flagged_skill}' was queued for dictionary review.")


def render_resume_sections(resume_text: str) -> None:
    with st.expander("📑 Detected Resume Sections", expanded=False):
        sections = detect_sections(resume_text)
        tabs = st.tabs(sections.order)
        for tab, name in zip(tabs, sections.order):
            with tab:
                st.text(sections.get(name)[:3000])


def render_match_and_chart(target_role: str, target_match, ranked_matches) -> None:
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


def render_recommendations(ranked_matches) -> None:
    st.subheader("🏆 Recommended Roles")
    top_matches = ranked_matches[:TOP_N_RECOMMENDATIONS]
    rec_cols = st.columns(len(top_matches))
    for i, (col, match) in enumerate(zip(rec_cols, top_matches), start=1):
        with col:
            st.metric(f"#{i}: {match.role}", f"{match.score:.1f}%")


def render_roadmap(target_role: str, missing_skills: list[str]):
    st.subheader(f"🗺️ Suggested Learning Roadmap for {target_role}")
    roadmap = generate_roadmap(missing_skills)
    if roadmap:
        weeks: dict[str, list[str]] = {}
        for item in roadmap:
            weeks.setdefault(item.week, []).append(item.topic)
        for week, topics in weeks.items():
            st.markdown(f"**{week}:** {', '.join(topics)}")
    else:
        st.success("No missing skills for this role - great match!")
    return roadmap


def render_resume_feedback(resume_text: str, target_role: str, missing_skills: list[str]) -> None:
    st.subheader("💡 Resume Improvement Suggestions")
    if is_llm_configured():
        st.caption("Powered by your configured LLM provider (see .env).")
    else:
        st.caption("Rule-based suggestions (set an API key in .env to enable LLM feedback).")
    if st.button("Generate suggestions"):
        with st.spinner("Analyzing resume..."):
            feedback = get_resume_feedback(resume_text, target_role, missing_skills)
        st.markdown(feedback.text)
        if feedback.source == "llm":
            st.caption(f"Generated by {feedback.provider} ({feedback.model}).")


def render_save_report(target_role, target_match, report_bytes: bytes) -> None:
    if not st.session_state.auth_token:
        return
    if st.button("💾 Save this report to my account"):
        ok, message = backend_client.save_report(
            st.session_state.auth_token,
            target_role,
            target_match.score,
            target_match.matched_skills,
            target_match.missing_skills,
            pdf_bytes=report_bytes,
        )
        (st.success if ok else st.error)(message)


def main() -> None:
    _init_session_state()

    st.title("📄 AI Resume Analyzer & Job Recommendation System")
    st.caption(
        "Upload your resume to see how well it matches different job roles, "
        "which skills you're missing, and a simple roadmap to close the gap."
    )

    render_responsible_ai_note()

    job_roles_df = _load_job_roles_cached()
    skill_df = _load_skill_dictionary_cached()

    settings = render_sidebar(job_roles_df)

    st.divider()
    render_saved_reports()
    st.divider()

    col_upload, col_role = st.columns([2, 1])
    with col_upload:
        uploaded_file = st.file_uploader("Upload your resume", type=["pdf", "docx"])
    with col_role:
        role_source = st.radio(
            "Compare against", options=["Predefined role", "Paste a job description"]
        )
        if role_source == "Predefined role":
            target_role = st.selectbox("Target role", options=job_roles_df["role"].tolist())
            jd_text = None
        else:
            target_role = "Custom Job Description"
            jd_text = st.text_area("Paste job description text", height=120)

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

    extractor = extract_skills_spacy if settings["use_spacy"] else extract_skills
    extraction = extractor(resume_text, skill_df=skill_df)

    if role_source == "Predefined role":
        ranked_matches = rank_roles(
            resume_text, extraction.found_skills, job_roles_df=job_roles_df, mode=settings["mode"]
        )
        target_match = get_role_match(target_role, ranked_matches)
    else:
        if not jd_text or not jd_text.strip():
            st.info("Paste a job description above to run the comparison.")
            return
        target_match = rank_custom_job_description(
            resume_text, extraction.found_skills, jd_text, skill_df, mode=settings["mode"]
        )
        ranked_matches = [target_match]

    st.divider()
    render_extracted_skills(extraction)
    render_resume_sections(resume_text)
    st.divider()
    render_match_and_chart(target_role, target_match, ranked_matches)
    st.divider()

    if role_source == "Predefined role":
        render_recommendations(ranked_matches)
        st.divider()

    roadmap = render_roadmap(target_role, target_match.missing_skills)
    st.divider()
    render_resume_feedback(resume_text, target_role, target_match.missing_skills)
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
    render_save_report(target_role, target_match, report_bytes)


if __name__ == "__main__":
    main()
