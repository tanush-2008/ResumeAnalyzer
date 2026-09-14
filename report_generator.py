"""Builds the downloadable PDF analysis report shown in the Streamlit dashboard.

Styled to match the dashboard's brand (see styles.py): a colored header/
footer band, a tinted score badge, color-coded skill tables, and a
proportional bar per recommended role instead of plain bullet lists.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Rect

from job_matcher import RoleMatch
from roadmap_generator import RoadmapItem
from styles import BRAND, DANGER, INK, INK_SOFT, SUCCESS, WARNING, score_tier

BRAND_COLOR = colors.HexColor(BRAND)
INK_COLOR = colors.HexColor(INK)
INK_SOFT_COLOR = colors.HexColor(INK_SOFT)
SUCCESS_COLOR = colors.HexColor(SUCCESS)
WARNING_COLOR = colors.HexColor(WARNING)
DANGER_COLOR = colors.HexColor(DANGER)
FOUND_BG = colors.HexColor("#ECFDF5")
MISSING_BG = colors.HexColor("#FEF2F2")
SOFT_BG = colors.HexColor("#F5F3FF")

PAGE_W, PAGE_H = letter
MARGIN = 1.8 * cm


def _tier_color(score: float) -> colors.Color:
    hex_color, _ = score_tier(score)
    return colors.HexColor(hex_color)


def _draw_chrome(canvas, doc) -> None:
    """Header/footer band drawn on every page."""
    canvas.saveState()
    canvas.setFillColor(BRAND_COLOR)
    canvas.rect(0, PAGE_H - 2.1 * cm, PAGE_W, 2.1 * cm, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(MARGIN, PAGE_H - 1.35 * cm, "AI Resume Analyzer")
    canvas.setFont("Helvetica", 9)
    canvas.drawString(MARGIN, PAGE_H - 1.75 * cm, "Resume-to-role match analysis report")

    canvas.setFillColor(INK_SOFT_COLOR)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - MARGIN, 1.1 * cm, f"Page {doc.page}")
    canvas.drawString(MARGIN, 1.1 * cm, "Guidance only - not a hiring decision.")
    canvas.restoreState()


def _score_bar_drawing(score: float, width: float = 6 * cm, height: float = 0.35 * cm) -> Drawing:
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=SOFT_BG, strokeColor=None, rx=height / 2, ry=height / 2))
    fill_w = max(width * min(score, 100) / 100, height)  # keep a visible sliver at 0
    d.add(
        Rect(
            0, 0, fill_w, height, fillColor=_tier_color(score), strokeColor=None,
            rx=height / 2, ry=height / 2,
        )
    )
    return d


def _skills_table(skills: list[str], kind: str) -> Table:
    bg = FOUND_BG if kind == "found" else MISSING_BG
    fg = SUCCESS_COLOR if kind == "found" else DANGER_COLOR
    if not skills:
        placeholder = "None detected." if kind == "found" else "None - all required skills found!"
        t = Table([[placeholder]], colWidths=[16.8 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F5F3FF")),
            ("TEXTCOLOR", (0, 0), (-1, -1), INK_SOFT_COLOR),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        return t

    cols = 3
    rows = [skills[i : i + cols] for i in range(0, len(skills), cols)]
    rows[-1] += [""] * (cols - len(rows[-1]))
    t = Table(rows, colWidths=[5.6 * cm] * cols)
    style = [
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("TEXTCOLOR", (0, 0), (-1, -1), fg),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [bg]),
        ("GRID", (0, 0), (-1, -1), 3, colors.white),
    ]
    t.setStyle(TableStyle(style))
    return t


def build_report_pdf(
    target_role: str,
    target_match: RoleMatch,
    ranked_matches: list[RoleMatch],
    roadmap: list[RoadmapItem],
    top_n_recommendations: int = 3,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=2.6 * cm,
        bottomMargin=1.6 * cm,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
    )
    styles = getSampleStyleSheet()
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=INK_COLOR, spaceBefore=14, spaceAfter=6)
    body = ParagraphStyle("Body", parent=styles["Normal"], textColor=INK_COLOR)
    small = ParagraphStyle("Small", parent=styles["Normal"], textColor=INK_SOFT_COLOR, fontSize=9)

    story = []

    story.append(Paragraph(datetime.now().strftime("Generated on %Y-%m-%d %H:%M"), small))
    story.append(Spacer(1, 8))

    tier_color, tier_label = score_tier(target_match.score)
    score_table = Table(
        [[
            Paragraph(f"<b>Target Role</b><br/>{target_role}", body),
            Paragraph(
                f'<font color="{tier_color}" size="22"><b>{target_match.score:.1f}%</b></font>'
                f'<br/><font color="{tier_color}" size="9">{tier_label}</font>',
                body,
            ),
        ]],
        colWidths=[11 * cm, 5.8 * cm],
    )
    score_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("RIGHTPADDING", (1, 0), (1, 0), 14),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 4))

    story.append(Paragraph("Skills Found", h2))
    story.append(_skills_table(target_match.matched_skills, "found"))

    story.append(Paragraph("Missing Skills", h2))
    story.append(_skills_table(target_match.missing_skills, "missing"))

    story.append(Paragraph("Recommended Roles", h2))
    top_matches = ranked_matches[:top_n_recommendations]
    role_rows = []
    for i, m in enumerate(top_matches, start=1):
        role_rows.append([
            Paragraph(f"<b>#{i}</b>", body),
            Paragraph(m.role, body),
            _score_bar_drawing(m.score),
            Paragraph(f"<b>{m.score:.1f}%</b>", body),
        ])
    role_table = Table(role_rows, colWidths=[1.2 * cm, 6.3 * cm, 6.3 * cm, 3 * cm])
    role_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#E7E3FB")),
    ]))
    story.append(role_table)

    story.append(Paragraph("Suggested Learning Roadmap", h2))
    if roadmap:
        seen_weeks: dict[str, list[str]] = {}
        for item in roadmap:
            seen_weeks.setdefault(item.week, []).append(item.topic)
        roadmap_rows = [
            [Paragraph(f"<b>{week}</b>", body), Paragraph(", ".join(topics), body)]
            for week, topics in seen_weeks.items()
        ]
        roadmap_table = Table(roadmap_rows, colWidths=[2.6 * cm, 14.2 * cm])
        roadmap_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [SOFT_BG, colors.white]),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, 0), (0, -1), BRAND_COLOR),
        ]))
        story.append(roadmap_table)
    else:
        story.append(Paragraph("No roadmap needed - great match!", body))

    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            "This match score is an estimate for guidance only and is not a recruiter "
            "decision. Missing keywords do not always mean missing ability.",
            small,
        )
    )

    doc.build(story, onFirstPage=_draw_chrome, onLaterPages=_draw_chrome)
    return buffer.getvalue()
