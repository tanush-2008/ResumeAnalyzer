"""Module 7: Streamlit dashboard tying together the whole AI Resume Analyzer
and Job Recommendation System pipeline - including the optional advanced
features (semantic matching, spaCy extraction, custom job descriptions,
LLM feedback, resume sections, login/saved reports, skill-dictionary
feedback) - styled with the design system in styles.py / ui_components.py.
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

import backend_client
import styles
import ui_components as ui
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
from skill_feedback import suggest_skill, load_suggestions, dismiss_suggestion, promote_and_dismiss

st.set_page_config(
    page_title="AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

TOP_N_RECOMMENDATIONS = 3


@st.cache_data
def _load_job_roles_cached():
    return load_job_roles()


@st.cache_data
def _load_skill_dictionary_cached():
    return load_skill_dictionary()


# ---- Cached pipeline stages -------------------------------------------
# Every widget interaction anywhere on the page triggers a full top-to-
# bottom rerun of main(). Without caching, that means re-parsing the PDF,
# re-running skill extraction, and re-computing embeddings/TF-IDF on every
# click - including ones unrelated to the resume (e.g. opening an expander,
# clicking "Generate suggestions"). These wrappers key on the actual inputs
# so a rerun only recomputes a stage when something feeding it changed.


@st.cache_data(show_spinner=False)
def _cached_extract_text(filename: str, file_bytes: bytes) -> str:
    return extract_text(filename, file_bytes)


@st.cache_data(show_spinner=False)
def _cached_extract_skills(resume_text: str, use_spacy: bool):
    skill_df = load_skill_dictionary()
    extractor = extract_skills_spacy if use_spacy else extract_skills
    return extractor(resume_text, skill_df=skill_df)


@st.cache_data(show_spinner=False)
def _cached_rank_roles(resume_text: str, found_skills: list[str], mode: str):
    job_roles_df = load_job_roles()
    return rank_roles(resume_text, found_skills, job_roles_df=job_roles_df, mode=mode)


@st.cache_data(show_spinner=False)
def _cached_rank_custom_jd(resume_text: str, found_skills: list[str], jd_text: str, mode: str):
    skill_df = load_skill_dictionary()
    return rank_custom_job_description(resume_text, found_skills, jd_text, skill_df, mode=mode)


def _init_session_state() -> None:
    st.session_state.setdefault("auth_token", None)
    st.session_state.setdefault("auth_email", None)


# ---------------------------------------------------------------- sidebar --

def render_sidebar() -> dict:
    with st.sidebar:
        st.markdown(f"### {ui.icon('tune')} Settings", unsafe_allow_html=True)

        matching_mode_label = st.radio(
            "Matching approach",
            options=["Beginner (TF-IDF + skill overlap)", "Advanced (+ semantic embeddings)"],
            help="Advanced mode blends in Sentence-Transformers semantic similarity, "
            "on top of TF-IDF and skill overlap.",
        )
        mode = "advanced" if matching_mode_label.startswith("Advanced") else "beginner"

        use_spacy = st.checkbox(
            "Use spaCy for skill extraction",
            value=False,
            help="Uses spaCy's PhraseMatcher instead of plain regex keyword matching.",
        )
        if use_spacy and not spacy_model_available():
            st.warning("spaCy model not installed - falling back to keyword matching.", icon="⚠️")
        if mode == "advanced" and not semantic_model_available():
            st.warning(
                "Sentence-Transformers model unavailable (offline?) - falling back to TF-IDF only.",
                icon="⚠️",
            )

        st.divider()
        render_auth_section()
        render_admin_panel()

    return {"mode": mode, "use_spacy": use_spacy}


def render_admin_panel() -> None:
    """Closes the skill-dictionary feedback loop (Section 13 of the brief):
    a curator can review and promote/dismiss flagged skills from inside the
    app instead of hand-editing data/skill_dictionary_suggestions.csv.
    Disabled unless ADMIN_TOKEN is set in the environment.
    """
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        return

    st.divider()
    with st.expander("Admin: Skill Dictionary Review", icon="🛡️"):
        entered = st.text_input("Admin token", type="password", key="admin_token_input")
        if entered != admin_token:
            if entered:
                st.error("Incorrect admin token.")
            return

        suggestions = load_suggestions()
        if not suggestions:
            st.caption("No pending skill suggestions.")
            return

        for i, row in enumerate(suggestions):
            # Stacked rather than side-by-side columns: the sidebar is too
            # narrow for a 4-column layout to leave room for button labels.
            st.markdown(f"**{row['suggested_skill']}** &nbsp;·&nbsp; {row['suggested_category']}")
            btn_cols = st.columns(2)
            if btn_cols[0].button("Approve", key=f"approve_{i}", use_container_width=True):
                promote_and_dismiss(i)
                _load_skill_dictionary_cached.clear()
                st.toast(f"'{row['suggested_skill']}' added to the live dictionary.", icon="✅")
                st.rerun()
            if btn_cols[1].button("Dismiss", key=f"dismiss_{i}", use_container_width=True):
                dismiss_suggestion(i)
                st.rerun()


def render_auth_section() -> None:
    st.markdown(f"### {ui.icon('account_circle')} Account (optional)", unsafe_allow_html=True)

    if not backend_client.backend_available():
        st.caption(
            "Backend offline - login and saved reports are disabled. "
            "Run the FastAPI backend (see README) to enable them."
        )
        return

    if st.session_state.auth_token:
        st.success(f"Logged in as **{st.session_state.auth_email}**", icon="✅")
        if st.button("Log out", use_container_width=True):
            st.session_state.auth_token = None
            st.session_state.auth_email = None
            st.rerun()
        return

    tab_login, tab_register = st.tabs(["Log in", "Register"])
    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log in", key="login_btn", type="primary", use_container_width=True):
            token, message = backend_client.login(email, password)
            if token:
                st.session_state.auth_token = token
                st.session_state.auth_email = email
                st.toast("Logged in!", icon="✅")
                st.rerun()
            else:
                st.error(message)

    with tab_register:
        reg_email = st.text_input("Email", key="reg_email")
        reg_password = st.text_input(
            "Password (min 8 chars)", type="password", key="reg_password"
        )
        if st.button("Create account", key="register_btn", use_container_width=True):
            ok, message = backend_client.register(reg_email, reg_password)
            (st.success if ok else st.error)(message)


# ------------------------------------------------------------- top sections --

def render_saved_reports() -> None:
    if not st.session_state.auth_token:
        return
    ui.section_header("bookmark", "My Saved Reports")
    reports = backend_client.list_reports(st.session_state.auth_token)
    if not reports:
        st.caption("No saved reports yet - analyze a resume below and save it to your account.")
        return
    for report in reports:
        color, tier = styles.score_tier(report["match_score"])
        with st.container(border=True):
            cols = st.columns([3, 1.4, 1, 1])
            cols[0].markdown(f"**{report['target_role']}**  \n<span style='color:{color};font-weight:700;'>{report['match_score']:.1f}% - {tier}</span>", unsafe_allow_html=True)
            cols[1].caption(report["created_at"][:10])
            if report["has_pdf"]:
                pdf_bytes = backend_client.get_report_pdf(st.session_state.auth_token, report["id"])
                if pdf_bytes:
                    cols[2].download_button(
                        "PDF", data=pdf_bytes, file_name=f"saved_report_{report['id']}.pdf",
                        mime="application/pdf", key=f"dl_{report['id']}", use_container_width=True,
                    )
            if cols[3].button("Delete", key=f"del_{report['id']}", use_container_width=True):
                ok, message = backend_client.delete_report(st.session_state.auth_token, report["id"])
                if ok:
                    st.toast(message, icon="🗑️")
                    st.rerun()
                else:
                    st.error(message)


def render_responsible_ai_note() -> None:
    with st.expander("Responsible use of this tool", icon="ℹ️", expanded=False):
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
    ui.section_header("category", "Extracted Skills", "Grouped by category from the controlled skill dictionary")
    ui.skill_badges_by_category(extraction.by_category)

    with st.expander("Don't see a skill you have? Flag it for review", icon="🛠️"):
        col1, col2, col3 = st.columns([2, 2, 1])
        flagged_skill = col1.text_input("Missing skill", key="flag_skill")
        flagged_category = col2.text_input("Category (optional)", key="flag_category")
        col3.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
        if col3.button("Submit", key="flag_submit", use_container_width=True) and flagged_skill.strip():
            suggest_skill(flagged_skill, flagged_category or "Uncategorized")
            st.toast(f"'{flagged_skill}' queued for dictionary review.", icon="✅")
            # The sidebar's admin panel renders earlier in the script than this
            # button, so without a rerun it would show the pre-submission queue.
            st.rerun()


def render_resume_sections(resume_text: str) -> None:
    with st.expander("Detected Resume Sections", icon="📑", expanded=False):
        sections = detect_sections(resume_text)
        tabs = st.tabs(sections.order)
        for tab, name in zip(tabs, sections.order):
            with tab:
                st.text(sections.get(name)[:3000])


def render_match_and_chart(target_role: str, target_match, ranked_matches, extraction, skill_df) -> None:
    ui.section_header("target", f"Match Score for {target_role}")

    total_categories = skill_df["category"].nunique()
    hit_categories = len(extraction.by_category)
    ui.stat_chips(
        [
            ("Skills found", str(len(target_match.matched_skills))),
            ("Skills missing", str(len(target_match.missing_skills))),
            ("Categories covered", f"{hit_categories}/{total_categories}"),
        ]
    )

    left, right = st.columns([1, 1.2])
    with left:
        st.plotly_chart(ui.score_gauge(target_match.score), use_container_width=True)
        ui.matched_missing_badges(target_match.matched_skills, target_match.missing_skills)

    with right:
        ui.section_header("bar_chart", "Match Score by Role")
        st.plotly_chart(ui.role_bar_chart(ranked_matches), use_container_width=True)


def render_recommendations(ranked_matches) -> None:
    ui.section_header("emoji_events", "Recommended Roles")
    ui.role_rank_cards(ranked_matches[:TOP_N_RECOMMENDATIONS])


def render_roadmap(target_role: str, missing_skills: list[str]):
    ui.section_header("map", f"Suggested Learning Roadmap for {target_role}")
    roadmap = generate_roadmap(missing_skills)
    ui.roadmap_timeline(roadmap)
    return roadmap


def render_resume_feedback(resume_text: str, target_role: str, missing_skills: list[str]) -> None:
    ui.section_header("lightbulb", "Resume Improvement Suggestions")
    if is_llm_configured():
        st.caption("Powered by your configured LLM provider (see .env).")
    else:
        st.caption("Rule-based suggestions (set an API key in .env to enable LLM feedback).")
    if st.button("Generate suggestions", type="primary"):
        with st.spinner("Analyzing resume..."):
            feedback = get_resume_feedback(resume_text, target_role, missing_skills)
        with st.container(border=True):
            st.markdown(feedback.text)
            if feedback.source == "llm":
                st.caption(f"Generated by {feedback.provider} ({feedback.model}).")


def render_save_report(target_role, target_match, report_bytes: bytes) -> None:
    if not st.session_state.auth_token:
        return
    if st.button("Save this report to my account", icon="💾"):
        ok, message = backend_client.save_report(
            st.session_state.auth_token,
            target_role,
            target_match.score,
            target_match.matched_skills,
            target_match.missing_skills,
            pdf_bytes=report_bytes,
        )
        if ok:
            st.toast(message, icon="💾")
        else:
            st.error(message)


def main() -> None:
    _init_session_state()
    ui.inject_base_styles()

    ui.hero(
        "AI Resume Analyzer & Job Recommendation System",
        "Upload your resume to see how well it matches different job roles, "
        "which skills you're missing, and a simple roadmap to close the gap.",
        "NLP-powered - guidance only, never a hiring decision",
    )

    render_responsible_ai_note()

    job_roles_df = _load_job_roles_cached()
    skill_df = _load_skill_dictionary_cached()

    settings = render_sidebar()

    render_saved_reports()
    st.divider()

    col_upload, col_role = st.columns([2, 1])
    with col_upload:
        ui.section_header("upload_file", "Upload Your Resume")
        uploaded_file = st.file_uploader(
            "Upload your resume", type=["pdf", "docx"], label_visibility="collapsed"
        )
    with col_role:
        ui.section_header("target", "Compare Against")
        role_source = st.radio(
            "Compare against",
            options=["Predefined role", "Paste a job description"],
            label_visibility="collapsed",
        )
        if role_source == "Predefined role":
            target_role = st.selectbox("Target role", options=job_roles_df["role"].tolist())
            jd_text = None
        else:
            target_role = "Custom Job Description"
            jd_text = st.text_area("Paste job description text", height=104)

    if uploaded_file is None:
        st.divider()
        ui.how_it_works()
        return

    st.success(f"Uploaded: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)", icon="📄")

    file_bytes = uploaded_file.getvalue()
    try:
        with st.spinner("Extracting resume text..."):
            resume_text = _cached_extract_text(uploaded_file.name, file_bytes)
    except ResumeParseError as exc:
        st.error(str(exc))
        return

    with st.spinner("Identifying skills..."):
        extraction = _cached_extract_skills(resume_text, settings["use_spacy"])

    with st.spinner("Matching against job roles..."):
        if role_source == "Predefined role":
            ranked_matches = _cached_rank_roles(
                resume_text, extraction.found_skills, settings["mode"]
            )
            target_match = get_role_match(target_role, ranked_matches)
        else:
            if not jd_text or not jd_text.strip():
                st.info("Paste a job description above to run the comparison.", icon="✍️")
                return
            target_match = _cached_rank_custom_jd(
                resume_text, extraction.found_skills, jd_text, settings["mode"]
            )
            ranked_matches = [target_match]

    st.divider()
    render_extracted_skills(extraction)
    render_resume_sections(resume_text)
    st.divider()
    render_match_and_chart(target_role, target_match, ranked_matches, extraction, skill_df)
    st.divider()

    if role_source == "Predefined role":
        render_recommendations(ranked_matches)
        st.divider()

    roadmap = render_roadmap(target_role, target_match.missing_skills)
    st.divider()
    render_resume_feedback(resume_text, target_role, target_match.missing_skills)
    st.divider()

    ui.section_header("download", "Download Full Analysis Report")
    report_bytes = build_report_pdf(
        target_role=target_role,
        target_match=target_match,
        ranked_matches=ranked_matches,
        roadmap=roadmap,
        top_n_recommendations=TOP_N_RECOMMENDATIONS,
    )
    dl_col, save_col = st.columns([1, 1])
    with dl_col:
        st.download_button(
            "Download report (PDF)",
            data=report_bytes,
            file_name=f"resume_analysis_{target_role.replace(' ', '_').lower()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with save_col:
        render_save_report(target_role, target_match, report_bytes)


if __name__ == "__main__":
    main()
