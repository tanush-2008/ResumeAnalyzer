"""Module 3: identify job-related skills inside cleaned resume text.

Beginner approach: a controlled skill dictionary (data/skill_dictionary.csv)
matched with simple keyword / phrase regex matching and word boundaries.

Advanced approach (optional): spaCy's PhraseMatcher over the same
dictionary, which is more robust to whitespace/casing variation and lines
up with the project brief's "spaCy entity and phrase extraction" option.
Symbol-heavy skills (c++, c#, .net) always fall back to the regex matcher
since spaCy's tokenizer splits on those symbols.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache

import pandas as pd

from text_cleaner import clean_text

DEFAULT_SKILL_DICTIONARY_PATH = os.path.join("data", "skill_dictionary.csv")
SPACY_MODEL_NAME = "en_core_web_sm"


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


# Skills containing symbols that spaCy's tokenizer would otherwise split apart
# (e.g. "c++" -> "c", "+", "+"). These are always resolved with the regex
# matcher above and merged into the spaCy result.
_SYMBOL_SKILL_RE = re.compile(r"[^a-z0-9\s]")


@lru_cache(maxsize=1)
def _load_spacy_model():
    """Lazily load the spaCy pipeline. Returns None if the model isn't installed."""
    import spacy

    try:
        return spacy.load(SPACY_MODEL_NAME, disable=["ner", "lemmatizer"])
    except OSError:
        return None


def spacy_model_available() -> bool:
    return _load_spacy_model() is not None


def extract_skills_spacy(
    resume_text: str,
    skill_df: pd.DataFrame | None = None,
    dictionary_path: str = DEFAULT_SKILL_DICTIONARY_PATH,
) -> SkillExtractionResult:
    """Advanced extraction using spaCy's PhraseMatcher over the skill dictionary.

    Falls back to the plain regex extractor if the spaCy model isn't
    installed, so callers never have to special-case availability.
    """
    nlp = _load_spacy_model()
    if nlp is None:
        return extract_skills(resume_text, skill_df=skill_df, dictionary_path=dictionary_path)

    from spacy.matcher import PhraseMatcher

    if skill_df is None:
        skill_df = load_skill_dictionary(dictionary_path)

    cleaned = clean_text(resume_text)
    doc = nlp(cleaned)

    plain_skills = skill_df[~skill_df["skill"].str.contains(_SYMBOL_SKILL_RE)]
    symbol_skills = skill_df[skill_df["skill"].str.contains(_SYMBOL_SKILL_RE)]

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    skill_to_category = dict(zip(plain_skills["skill"], plain_skills["category"]))
    patterns = [nlp.make_doc(skill) for skill in skill_to_category]
    if patterns:
        matcher.add("SKILLS", patterns)

    found_skills: list[str] = []
    by_category: dict[str, list[str]] = {}

    for match_id, start, end in matcher(doc):
        skill_text = doc[start:end].text.strip()
        category = skill_to_category.get(skill_text)
        if category and skill_text not in found_skills:
            found_skills.append(skill_text)
            by_category.setdefault(category, []).append(skill_text)

    # Symbol-based skills (c++, c#, .net) via regex, merged in.
    for _, row in symbol_skills.iterrows():
        skill, category = row["skill"], row["category"]
        if _skill_pattern(skill).search(cleaned) and skill not in found_skills:
            found_skills.append(skill)
            by_category.setdefault(category, []).append(skill)

    return SkillExtractionResult(found_skills=found_skills, by_category=by_category)
