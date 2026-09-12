"""Unit tests covering the core (non-Streamlit) pipeline modules.

Run with: python -m pytest tests/ -v
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_cleaner import clean_text
from skill_extractor import extract_skills, extract_skills_spacy, load_skill_dictionary
from job_matcher import load_job_roles, rank_roles, rank_custom_job_description
from roadmap_generator import generate_roadmap
from section_detector import detect_sections
from llm_feedback import get_resume_feedback, is_llm_configured

SAMPLE_RESUME = """
Jane Doe
Email: jane.doe@example.com | Phone: 555-123-4567

Experience:
Worked with Python, Pandas, SQL and Power BI to analyze sales data.
Built dashboards for data visualization and reporting.

Skills: Python, SQL, Excel, Pandas, Power BI
"""

SKILL_DF = load_skill_dictionary()
JOB_ROLES_DF = load_job_roles()


def test_clean_text_preserves_protected_tokens():
    cleaned = clean_text("Experience with C++, C#, and .NET frameworks.")
    assert "c++" in cleaned
    assert "c#" in cleaned
    assert ".net" in cleaned


def test_clean_text_removes_email_and_phone():
    cleaned = clean_text(SAMPLE_RESUME)
    assert "@" not in cleaned
    assert "555" not in cleaned


def test_extract_skills_finds_expected_skills():
    result = extract_skills(SAMPLE_RESUME, skill_df=SKILL_DF)
    assert "python" in result.found_skills
    assert "sql" in result.found_skills
    assert "power bi" in result.found_skills


def test_extract_skills_does_not_false_positive():
    result = extract_skills("I enjoy hiking and cooking.", skill_df=SKILL_DF)
    assert result.found_skills == []


def test_rank_roles_returns_all_roles_sorted_desc():
    extraction = extract_skills(SAMPLE_RESUME, skill_df=SKILL_DF)
    ranked = rank_roles(SAMPLE_RESUME, extraction.found_skills, job_roles_df=JOB_ROLES_DF)
    assert len(ranked) == len(JOB_ROLES_DF)
    scores = [m.score for m in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_roles_top_role_is_data_analyst():
    extraction = extract_skills(SAMPLE_RESUME, skill_df=SKILL_DF)
    ranked = rank_roles(SAMPLE_RESUME, extraction.found_skills, job_roles_df=JOB_ROLES_DF)
    assert ranked[0].role == "Data Analyst"


def test_generate_roadmap_empty_when_no_missing_skills():
    assert generate_roadmap([]) == []


def test_generate_roadmap_groups_by_week():
    roadmap = generate_roadmap(["docker", "mlflow", "fastapi"], skills_per_week=1)
    weeks = {item.week for item in roadmap}
    assert len(weeks) == 3


def test_extract_skills_spacy_matches_regex_result():
    spacy_result = extract_skills_spacy(SAMPLE_RESUME, skill_df=SKILL_DF)
    regex_result = extract_skills(SAMPLE_RESUME, skill_df=SKILL_DF)
    assert set(spacy_result.found_skills) == set(regex_result.found_skills)


def test_rank_custom_job_description_derives_required_skills():
    extraction = extract_skills(SAMPLE_RESUME, skill_df=SKILL_DF)
    jd_text = "Looking for a candidate skilled in Python, SQL and Power BI."
    match = rank_custom_job_description(
        SAMPLE_RESUME, extraction.found_skills, jd_text, SKILL_DF
    )
    assert match.role == "Custom Job Description"
    assert "python" in match.matched_skills
    assert match.missing_skills == []


def test_detect_sections_splits_known_headings():
    resume = (
        "Jane Doe\n\nEducation\nB.Sc. Computer Science\n\n"
        "Skills\nPython, SQL\n\nProjects\nBuilt a dashboard.\n"
    )
    sections = detect_sections(resume)
    assert "Education" in sections.sections
    assert "Skills" in sections.sections
    assert "Projects" in sections.sections
    assert "B.Sc. Computer Science" in sections.get("Education")


def test_detect_sections_falls_back_to_full_resume():
    sections = detect_sections("Just a single unstructured paragraph with no headings.")
    assert sections.order == ["Full Resume"]


def test_llm_feedback_falls_back_to_rule_based_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    assert is_llm_configured() is False
    feedback = get_resume_feedback(SAMPLE_RESUME, "Data Analyst", ["excel"])
    assert feedback.source == "rule_based"
    assert "excel" in feedback.text.lower()
