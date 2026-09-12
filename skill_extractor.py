"""Module 3: identify job-related skills inside cleaned resume text.

Uses a controlled skill dictionary (data/skill_dictionary.csv) and simple
keyword / phrase matching with word boundaries, as suggested by the
project brief's beginner approach.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import pandas as pd

from text_cleaner import clean_text

DEFAULT_SKILL_DICTIONARY_PATH = os.path.join("data", "skill_dictionary.csv")


@dataclass
class SkillExtractionResult:
    found_skills: list[str] = field(default_factory=list)
    by_category: dict[str, list[str]] = field(default_factory=dict)


def load_skill_dictionary(path: str = DEFAULT_SKILL_DICTIONARY_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["skill"] = df["skill"].str.strip().str.lower()
    df["category"] = df["category"].str.strip()
    return df


def _skill_pattern(skill: str) -> re.Pattern:
    """Build a regex that matches a skill as a whole word/phrase.

    Skills containing symbols (c++, c#, .net) are matched literally instead of
    with \\b word boundaries, since those don't fall on word characters.
    """
    escaped = re.escape(skill)
    if re.search(r"[^a-z0-9\s]", skill):
        return re.compile(escaped)
    return re.compile(rf"\b{escaped}\b")


def extract_skills(
    resume_text: str,
    skill_df: pd.DataFrame | None = None,
    dictionary_path: str = DEFAULT_SKILL_DICTIONARY_PATH,
) -> SkillExtractionResult:
    """Search cleaned resume text for every skill in the controlled dictionary."""
    if skill_df is None:
        skill_df = load_skill_dictionary(dictionary_path)

    cleaned = clean_text(resume_text)

    found_skills: list[str] = []
    by_category: dict[str, list[str]] = {}

    for _, row in skill_df.iterrows():
        skill = row["skill"]
        category = row["category"]
        if _skill_pattern(skill).search(cleaned):
            found_skills.append(skill)
            by_category.setdefault(category, []).append(skill)

    return SkillExtractionResult(found_skills=found_skills, by_category=by_category)
