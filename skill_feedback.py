"""Optional advanced feature: feedback-based improvement of the skill dictionary.

Lets a user flag a skill that should have been detected but wasn't. Flags are
appended to a review queue CSV rather than the live dictionary, so a human
curator can vet each suggestion before it affects matching for everyone. The
curator can review and promote/dismiss suggestions either by editing the CSV
directly, or from the in-app admin panel (see app.py's render_admin_panel).
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone

SUGGESTIONS_PATH = os.path.join("data", "skill_dictionary_suggestions.csv")
DICTIONARY_PATH = os.path.join("data", "skill_dictionary.csv")
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


def _write_suggestions(rows: list[dict]) -> None:
    with open(SUGGESTIONS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def dismiss_suggestion(index: int) -> None:
    """Remove one queued suggestion (by its position in load_suggestions()) without promoting it."""
    rows = load_suggestions()
    if 0 <= index < len(rows):
        del rows[index]
        _write_suggestions(rows)


def promote_suggestion(
    skill: str, category: str, dictionary_path: str = DICTIONARY_PATH
) -> None:
    """Human-curator helper: append an approved suggestion into the live dictionary."""
    with open(dictionary_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([skill.strip().lower(), category.strip()])


def promote_and_dismiss(index: int, dictionary_path: str = DICTIONARY_PATH) -> None:
    """Promote a queued suggestion into the live dictionary, then remove it from the queue."""
    rows = load_suggestions()
    if not (0 <= index < len(rows)):
        return
    row = rows[index]
    promote_suggestion(row["suggested_skill"], row["suggested_category"], dictionary_path)
    dismiss_suggestion(index)
