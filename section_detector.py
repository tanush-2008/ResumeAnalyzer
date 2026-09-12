"""Optional advanced feature: resume section detection.

Splits a raw resume into Education / Skills / Projects / Experience (and
Summary) blocks using heading heuristics, so the dashboard and the
resume-improvement feedback can reason about each part separately.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SECTION_HEADINGS: dict[str, list[str]] = {
    "Summary": ["summary", "objective", "profile", "about me"],
    "Education": ["education", "academic background", "qualifications"],
    "Skills": ["skills", "technical skills", "core competencies", "technologies"],
    "Projects": ["projects", "personal projects", "academic projects"],
    "Experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "internship",
        "internships",
    ],
    "Certifications": ["certifications", "certificates", "licenses"],
}

_MAX_HEADING_WORDS = 5


@dataclass
class ResumeSections:
    sections: dict[str, str] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)

    def get(self, name: str, default: str = "") -> str:
        return self.sections.get(name, default)


def _match_heading(line: str) -> str | None:
    stripped = line.strip().strip(":").strip()
    if not stripped or len(stripped.split()) > _MAX_HEADING_WORDS:
        return None
    lowered = stripped.lower()
    for canonical, aliases in SECTION_HEADINGS.items():
        for alias in aliases:
            if lowered == alias or (lowered.startswith(alias) and len(lowered) <= len(alias) + 3):
                return canonical
    return None


def detect_sections(raw_text: str) -> ResumeSections:
    """Best-effort heading-based split of a resume into named sections.

    Text before the first recognized heading is kept under "Header" (name,
    contact info, etc). Any resume without recognizable headings simply
    returns the whole text under "Full Resume".
    """
    lines = raw_text.splitlines()
    result = ResumeSections()

    current_name = "Header"
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            if current_name in result.sections:
                result.sections[current_name] += "\n" + text
            else:
                result.sections[current_name] = text
                result.order.append(current_name)

    found_any_heading = False
    for line in lines:
        heading = _match_heading(line)
        if heading:
            found_any_heading = True
            flush()
            buffer = []
            current_name = heading
        else:
            buffer.append(line)
    flush()

    if not found_any_heading:
        cleaned = raw_text.strip()
        return ResumeSections(sections={"Full Resume": cleaned}, order=["Full Resume"])

    return result


_BULLET_RE = re.compile(r"^\s*[-*•●▪]\s*")


def section_bullet_points(section_text: str) -> list[str]:
    """Split a section's text into individual bullet/line items."""
    items = []
    for line in section_text.splitlines():
        line = _BULLET_RE.sub("", line).strip()
        if line:
            items.append(line)
    return items
