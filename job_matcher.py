"""Module 4 & 5: load job-role requirements and rank them against a resume.

Beginner approach from the project brief: TF-IDF vectorization + cosine
similarity between the resume text and each job role's required-skills text,
blended with plain skill overlap for an interpretable final score.

Advanced approach (optional): Sentence-Transformers embeddings + cosine
similarity add a semantic-matching signal on top of TF-IDF, so a resume that
describes a skill in different words than the job listing still scores well.

Also supports matching against an arbitrary pasted/uploaded job description
instead of only the predefined role dataset (another optional advanced
feature from the brief).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from text_cleaner import normalize_for_matching

DEFAULT_JOB_ROLES_PATH = os.path.join("data", "job_roles.csv")
SEMANTIC_MODEL_NAME = "all-MiniLM-L6-v2"

# Score blend weights. "beginner" matches the project brief's baseline
# approach exactly (TF-IDF + skill overlap only). "advanced" folds in a
# semantic-embedding signal, reducing the weight of raw skill overlap.
WEIGHTS = {
    "beginner": {"tfidf": 0.5, "semantic": 0.0, "overlap": 0.5},
    "advanced": {"tfidf": 0.3, "semantic": 0.4, "overlap": 0.3},
}


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


@lru_cache(maxsize=1)
def _load_semantic_model():
    """Lazily load the Sentence-Transformers model. Returns None if unavailable."""
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(SEMANTIC_MODEL_NAME)
    except Exception:  # noqa: BLE001 - missing package or offline first-run download
        return None


def semantic_model_available() -> bool:
    return _load_semantic_model() is not None


def _tfidf_similarities(resume_doc: str, role_docs: list[str]) -> list[float]:
    corpus = [resume_doc] + role_docs
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)
    return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten().tolist()


def _semantic_similarities(resume_doc: str, role_docs: list[str]) -> list[float] | None:
    model = _load_semantic_model()
    if model is None:
        return None
    embeddings = model.encode([resume_doc] + role_docs, normalize_embeddings=True)
    resume_vec = embeddings[0:1]
    role_vecs = embeddings[1:]
    return cosine_similarity(resume_vec, role_vecs).flatten().tolist()


def _rank_against_texts(
    resume_text: str,
    resume_skills: list[str],
    roles: list[tuple[str, list[str], str]],
    mode: str = "beginner",
) -> list[RoleMatch]:
    """Shared scoring core.

    roles: list of (role_name, required_skills, similarity_text) tuples,
    where similarity_text is what gets compared to the resume (usually the
    joined required skills, or full job-description text for a custom JD).
    """
    weights = WEIGHTS.get(mode, WEIGHTS["beginner"])
    resume_doc = normalize_for_matching(resume_text)
    role_docs = [normalize_for_matching(text) for _, _, text in roles]

    tfidf_scores = _tfidf_similarities(resume_doc, role_docs)
    semantic_scores = _semantic_similarities(resume_doc, role_docs) if weights["semantic"] else None
    if semantic_scores is None:
        semantic_scores = [0.0] * len(roles)
        # If semantic matching was requested but unavailable, fall back to
        # redistributing its weight onto TF-IDF so scores stay meaningful.
        if weights["semantic"]:
            weights = {**weights, "tfidf": weights["tfidf"] + weights["semantic"], "semantic": 0.0}

    resume_skill_set = set(resume_skills)
    results: list[RoleMatch] = []
    for (role_name, required, _), tfidf_score, semantic_score in zip(
        roles, tfidf_scores, semantic_scores
    ):
        overlap = _skill_overlap_score(resume_skill_set, required)
        blended = (
            weights["tfidf"] * tfidf_score
            + weights["semantic"] * semantic_score
            + weights["overlap"] * overlap
        )
        matched = sorted(resume_skill_set.intersection(required))
        missing = sorted(set(required) - resume_skill_set)
        results.append(
            RoleMatch(
                role=role_name,
                score=round(blended * 100, 1),
                required_skills=required,
                matched_skills=matched,
                missing_skills=missing,
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results


def rank_roles(
    resume_text: str,
    resume_skills: list[str],
    job_roles_df: pd.DataFrame | None = None,
    job_roles_path: str = DEFAULT_JOB_ROLES_PATH,
    mode: str = "beginner",
) -> list[RoleMatch]:
    """Rank every job role in the dataset against the candidate's resume."""
    if job_roles_df is None:
        job_roles_df = load_job_roles(job_roles_path)

    roles = [
        (row["role"], row["required_skills"], " ".join(row["required_skills"]))
        for _, row in job_roles_df.iterrows()
    ]
    return _rank_against_texts(resume_text, resume_skills, roles, mode=mode)


def rank_custom_job_description(
    resume_text: str,
    resume_skills: list[str],
    jd_text: str,
    skill_df: pd.DataFrame,
    role_name: str = "Custom Job Description",
    mode: str = "beginner",
) -> RoleMatch:
    """Match a resume against an arbitrary pasted/uploaded job description.

    Required skills are auto-derived by running the same skill extractor
    used on resumes over the job-description text.
    """
    from skill_extractor import extract_skills  # local import avoids a cycle

    jd_skills = extract_skills(jd_text, skill_df=skill_df).found_skills
    roles = [(role_name, jd_skills, jd_text)]
    return _rank_against_texts(resume_text, resume_skills, roles, mode=mode)[0]


def get_role_match(role_name: str, ranked_matches: list[RoleMatch]) -> RoleMatch | None:
    for match in ranked_matches:
        if match.role == role_name:
            return match
    return None
