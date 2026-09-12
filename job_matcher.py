"""Module 4 & 5: load job-role requirements and rank them against a resume.

Beginner approach from the project brief: TF-IDF vectorization + cosine
similarity between the resume text and each job role's required-skills text,
blended with plain skill overlap for an interpretable final score.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from text_cleaner import normalize_for_matching

DEFAULT_JOB_ROLES_PATH = os.path.join("data", "job_roles.csv")

# Weight given to TF-IDF/cosine textual similarity vs. exact skill overlap
# when computing the final blended match score.
SIMILARITY_WEIGHT = 0.5
OVERLAP_WEIGHT = 0.5


@dataclass
class RoleMatch:
    role: str
    score: float
    required_skills: list[str]
    matched_skills: list[str]
    missing_skills: list[str]


def load_job_roles(path: str = DEFAULT_JOB_ROLES_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["required_skills"] = df["required_skills"].apply(
        lambda s: [skill.strip().lower() for skill in str(s).split(";") if skill.strip()]
    )
    return df


def _skill_overlap_score(resume_skills: set[str], required: list[str]) -> float:
    if not required:
        return 0.0
    matched = resume_skills.intersection(required)
    return len(matched) / len(required)


def rank_roles(
    resume_text: str,
    resume_skills: list[str],
    job_roles_df: pd.DataFrame | None = None,
    job_roles_path: str = DEFAULT_JOB_ROLES_PATH,
) -> list[RoleMatch]:
    """Rank every job role in the dataset against the candidate's resume."""
    if job_roles_df is None:
        job_roles_df = load_job_roles(job_roles_path)

    resume_doc = normalize_for_matching(resume_text)
    role_docs = [
        normalize_for_matching(" ".join(skills)) for skills in job_roles_df["required_skills"]
    ]

    corpus = [resume_doc] + role_docs
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    resume_skill_set = set(resume_skills)
    results: list[RoleMatch] = []
    for (_, row), similarity in zip(job_roles_df.iterrows(), similarities):
        required = row["required_skills"]
        overlap = _skill_overlap_score(resume_skill_set, required)
        blended = (SIMILARITY_WEIGHT * similarity) + (OVERLAP_WEIGHT * overlap)
        matched = sorted(resume_skill_set.intersection(required))
        missing = sorted(set(required) - resume_skill_set)
        results.append(
            RoleMatch(
                role=row["role"],
                score=round(blended * 100, 1),
                required_skills=required,
                matched_skills=matched,
                missing_skills=missing,
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results


def get_role_match(role_name: str, ranked_matches: list[RoleMatch]) -> RoleMatch | None:
    for match in ranked_matches:
        if match.role == role_name:
            return match
    return None
