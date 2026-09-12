"""Optional advanced feature: feedback-based improvement of the skill dictionary.

Lets a user flag a skill that should have been detected but wasn't. Flags are
appended to a review queue CSV rather than the live dictionary, so a human
curator can vet each suggestion before it affects matching for everyone.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

SUGGESTIONS_PATH = os.path.join("data", "skill_dictionary_suggestions.csv")
FIELDNAMES = ["suggested_skill", "suggested_category", "submitted_at"]


def suggest_skill(skill: str, category: str = "Uncategorized") -> None:
    """Queue a candidate skill for human review; ignored if blank."""
    skill = skill.strip().lower()
    if not skill:
        return

    file_exists = os.path.exists(SUGGESTIONS_PATH)
    os.makedirs(os.path.dirname(SUGGESTIONS_PATH), exist_ok=True)
    with open(SUGGESTIONS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "suggested_skill": skill,
                "suggested_category": category.strip() or "Uncategorized",
                "submitted_at": datetime.now(timezone.utc).isoformat(),
            }
        )


def load_suggestions() -> list[dict]:
    if not os.path.exists(SUGGESTIONS_PATH):
        return []
    with open(SUGGESTIONS_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def promote_suggestion(skill: str, category: str, dictionary_path: str = os.path.join("data", "skill_dictionary.csv")) -> None:
    """Human-curator helper: append an approved suggestion into the live dictionary."""
    with open(dictionary_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([skill.strip().lower(), category.strip()])
