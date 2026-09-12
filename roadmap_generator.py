"""Module 6: turn missing skills into a simple, rule-based learning roadmap."""

from __future__ import annotations

from dataclasses import dataclass

# Short, beginner-friendly learning topic per skill. Falls back to a generic
# "Learn the fundamentals of X" suggestion when a skill isn't listed here.
LEARNING_TOPICS: dict[str, str] = {
    "python": "Python programming fundamentals",
    "sql": "SQL querying and joins",
    "excel": "Excel formulas and pivot tables",
    "pandas": "Data wrangling with pandas",
    "power bi": "Power BI dashboards",
    "data visualization": "Data visualization principles",
    "machine learning": "Core machine learning concepts",
    "scikit-learn": "Building models with scikit-learn",
    "fastapi": "FastAPI basics",
    "docker": "Docker fundamentals",
    "mlflow": "MLflow and experiment tracking",
    "deep learning": "Deep learning foundations",
    "llm": "Large language model concepts",
    "rag": "Retrieval-augmented generation (RAG)",
    "apis": "Consuming and building APIs",
    "pytorch": "PyTorch basics",
    "nlp": "Natural language processing basics",
    "transformers": "Transformer architectures",
    "hugging face": "Hugging Face libraries",
    "spacy": "spaCy for NLP pipelines",
    "nltk": "NLTK for text processing",
    "opencv": "OpenCV image processing",
    "cnn": "Convolutional neural networks",
    "yolo": "Object detection with YOLO",
    "computer vision": "Computer vision fundamentals",
    "image processing": "Digital image processing",
    "flask": "Flask web framework",
    "django": "Django web framework",
    "rest api": "REST API design",
    "git": "Git version control",
    "numpy": "Numerical computing with NumPy",
    "cloud deployment": "Deploying apps to the cloud",
}

WEEK_LABELS = [
    "Week 1",
    "Week 2",
    "Week 3",
    "Week 4",
    "Week 5",
    "Week 6",
]


@dataclass
class RoadmapItem:
    week: str
    topic: str
    skill: str


def _topic_for_skill(skill: str) -> str:
    return LEARNING_TOPICS.get(skill, f"Learn the fundamentals of {skill}")


def generate_roadmap(missing_skills: list[str], skills_per_week: int = 1) -> list[RoadmapItem]:
    """Group missing skills into a week-by-week roadmap, most important first.

    Missing skills are assumed to already be ordered by relevance (e.g. as
    returned by job_matcher). At most len(WEEK_LABELS) weeks are produced;
    remaining skills are grouped into the final week.
    """
    if not missing_skills:
        return []

    roadmap: list[RoadmapItem] = []
    max_weeks = len(WEEK_LABELS)
    chunk_size = max(skills_per_week, 1)

    chunks = [
        missing_skills[i : i + chunk_size] for i in range(0, len(missing_skills), chunk_size)
    ]

    if len(chunks) > max_weeks:
        overflow = chunks[max_weeks - 1 :]
        merged_overflow = [skill for chunk in overflow for skill in chunk]
        chunks = chunks[: max_weeks - 1] + [merged_overflow]

    for week_label, chunk in zip(WEEK_LABELS, chunks):
        for skill in chunk:
            roadmap.append(RoadmapItem(week=week_label, topic=_topic_for_skill(skill), skill=skill))

    return roadmap


def roadmap_to_text(roadmap: list[RoadmapItem]) -> str:
    if not roadmap:
        return "No missing skills detected - great match!"
    lines = []
    current_week = None
    for item in roadmap:
        if item.week != current_week:
            lines.append(f"{item.week}: {item.topic}")
            current_week = item.week
        else:
            lines[-1] += f", {item.topic}"
    return "\n".join(lines)
