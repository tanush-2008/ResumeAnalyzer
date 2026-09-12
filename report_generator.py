"""Builds the downloadable PDF analysis report shown in the Streamlit dashboard."""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem

from job_matcher import RoleMatch
from roadmap_generator import RoadmapItem


def build_report_pdf(
    target_role: str,
    target_match: RoleMatch,
    ranked_matches: list[RoleMatch],
    roadmap: list[RoadmapItem],
    top_n_recommendations: int = 3,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("AI Resume Analyzer - Analysis Report", styles["Title"]))
    story.append(
        Paragraph(
            datetime.now().strftime("Generated on %Y-%m-%d %H:%M"),
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 16))

    story.append(Paragraph(f"Target Role: {target_role}", styles["Heading2"]))
    story.append(Paragraph(f"Resume Match Score: {target_match.score:.1f}%", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Skills Found:", styles["Heading3"]))
    if target_match.matched_skills:
        story.append(
            ListFlowable(
                [ListItem(Paragraph(s, styles["Normal"])) for s in target_match.matched_skills],
                bulletType="bullet",
            )
        )
    else:
        story.append(Paragraph("None detected.", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Missing Skills:", styles["Heading3"]))
    if target_match.missing_skills:
        story.append(
            ListFlowable(
                [ListItem(Paragraph(s, styles["Normal"])) for s in target_match.missing_skills],
                bulletType="bullet",
            )
        )
    else:
        story.append(Paragraph("None - all required skills found!", styles["Normal"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Recommended Roles:", styles["Heading3"]))
    top_matches = ranked_matches[:top_n_recommendations]
    story.append(
        ListFlowable(
            [
                ListItem(Paragraph(f"{m.role} - {m.score:.1f}%", styles["Normal"]))
                for m in top_matches
            ],
            bulletType="1",
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("Suggested Learning Roadmap:", styles["Heading3"]))
    if roadmap:
        seen_weeks: dict[str, list[str]] = {}
        for item in roadmap:
            seen_weeks.setdefault(item.week, []).append(item.topic)
        for week, topics in seen_weeks.items():
            story.append(Paragraph(f"{week}: {', '.join(topics)}", styles["Normal"]))
    else:
        story.append(Paragraph("No roadmap needed - great match!", styles["Normal"]))

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "Note: This match score is an estimate for guidance only and is not a "
            "recruiter decision. Missing keywords do not always mean missing ability.",
            styles["Italic"],
        )
    )

    doc.build(story)
    return buffer.getvalue()
