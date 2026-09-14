"""Design system for the Streamlit dashboard: fonts, color tokens, and one
big CSS block injected once at app start. Keeping every visual constant here
(instead of scattered across app.py) is what makes the dashboard look like
one coherent product instead of a stack of default widgets.
"""

from __future__ import annotations

# Brand palette - a single indigo/violet primary with a teal accent for
# secondary/positive actions, plus semantic colors for score tiers.
BRAND = "#6C5CE7"
BRAND_DARK = "#5445c9"
BRAND_LIGHT = "#A29BFE"
ACCENT = "#00B8A9"
SUCCESS = "#16A34A"
WARNING = "#D97706"
DANGER = "#DC2626"
INK = "#1F2333"
INK_SOFT = "#5B6072"
BORDER = "#E7E3FB"
CARD_BG = "#FFFFFF"
PAGE_BG = "#FAFAFF"
SOFT_BG = "#F5F3FF"

# One accent color per skill category so a category is instantly
# recognizable across the dashboard (badges, section headers, charts).
CATEGORY_COLORS: dict[str, str] = {
    "Programming": "#6C5CE7",
    "Databases": "#0EA5E9",
    "Data Handling": "#00B8A9",
    "Machine Learning": "#F59E0B",
    "NLP": "#EC4899",
    "Computer Vision": "#8B5CF6",
    "Cloud": "#3B82F6",
    "Tools": "#64748B",
}
DEFAULT_CATEGORY_COLOR = "#6C5CE7"


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, DEFAULT_CATEGORY_COLOR)


def score_tier(score: float) -> tuple[str, str]:
    """Returns (color, label) for a match score."""
    if score >= 70:
        return SUCCESS, "Strong match"
    if score >= 45:
        return WARNING, "Partial match"
    return DANGER, "Needs work"


def base_css() -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=Material+Symbols+Rounded&display=swap');

:root {{
    --brand: {BRAND};
    --brand-dark: {BRAND_DARK};
    --brand-light: {BRAND_LIGHT};
    --accent: {ACCENT};
    --success: {SUCCESS};
    --warning: {WARNING};
    --danger: {DANGER};
    --ink: {INK};
    --ink-soft: {INK_SOFT};
    --border: {BORDER};
    --card-bg: {CARD_BG};
    --page-bg: {PAGE_BG};
    --soft-bg: {SOFT_BG};
}}

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

.msymbol {{
    font-family: 'Material Symbols Rounded';
    font-size: 1.15em;
    vertical-align: -0.2em;
    line-height: 1;
}}

/* ---------- Page canvas ---------- */
.stApp {{
    background: var(--page-bg);
}}
.main .block-container {{
    padding-top: 1.4rem;
    max-width: 1180px;
}}
h1, h2, h3, h4 {{
    font-family: 'Plus Jakarta Sans', 'Inter', sans-serif !important;
    color: var(--ink) !important;
    letter-spacing: -0.01em;
}}
p, span, label, div {{ color: var(--ink); }}

/* ---------- Hero banner ---------- */
.hero {{
    background: linear-gradient(120deg, var(--brand) 0%, #8B7CF6 55%, var(--accent) 130%);
    border-radius: 22px;
    padding: 2.1rem 2.4rem;
    margin-bottom: 1.6rem;
    box-shadow: 0 18px 40px -18px rgba(108, 92, 231, 0.55);
    color: white;
}}
.hero h1 {{
    color: white !important;
    font-size: 2rem;
    margin: 0 0 0.35rem 0;
    display: flex;
    align-items: center;
    gap: 0.55rem;
}}
.hero p {{
    color: rgba(255,255,255,0.92) !important;
    font-size: 1.02rem;
    margin: 0;
    max-width: 640px;
}}
.hero-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.35);
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 0.9rem;
    backdrop-filter: blur(4px);
}}

/* ---------- Section headers ---------- */
.section-head {{
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin: 0.2rem 0 0.9rem 0;
}}
.section-head .msymbol {{
    background: var(--soft-bg);
    color: var(--brand);
    border-radius: 10px;
    padding: 0.35rem;
    font-size: 1.3rem;
}}
.section-head h3 {{
    margin: 0 !important;
    font-size: 1.22rem !important;
}}
.section-sub {{
    color: var(--ink-soft);
    font-size: 0.92rem;
    margin: -0.5rem 0 1rem 2.6rem;
}}

/* ---------- Cards ---------- */
.card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.25rem 1.4rem;
    box-shadow: 0 6px 18px -14px rgba(31, 35, 51, 0.25);
}}

/* ---------- Skill badges ---------- */
.badge-group {{ margin-bottom: 0.9rem; }}
.badge-group-label {{
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--ink-soft);
    margin-bottom: 0.4rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}}
.badge-dot {{
    width: 9px; height: 9px; border-radius: 50%;
    display: inline-block;
}}
.skill-badge {{
    display: inline-flex;
    align-items: center;
    padding: 0.28rem 0.72rem;
    border-radius: 999px;
    font-size: 0.83rem;
    font-weight: 600;
    margin: 0 0.35rem 0.35rem 0;
    border: 1px solid transparent;
}}
.skill-badge.found {{ background: #ECFDF5; color: #067A46; border-color: #B7EFD3; }}
.skill-badge.missing {{ background: #FEF2F2; color: #B42318; border-color: #FBD5D5; }}
.skill-badge.neutral {{ background: var(--soft-bg); color: var(--brand-dark); border-color: var(--border); }}

/* ---------- Rank cards (recommended roles) ---------- */
.rank-card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.1rem 1.2rem;
    text-align: left;
    position: relative;
    overflow: hidden;
    height: 100%;
}}
.rank-card.top {{ border-color: var(--brand-light); box-shadow: 0 10px 26px -18px rgba(108,92,231,0.6); }}
.rank-medal {{
    font-size: 1.15rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px; height: 30px;
    border-radius: 50%;
    margin-bottom: 0.5rem;
}}
.rank-role {{ font-weight: 700; font-size: 1.02rem; margin: 0.1rem 0 0.5rem 0; color: var(--ink); }}
.rank-score {{ font-size: 1.6rem; font-weight: 800; font-family: 'Plus Jakarta Sans', sans-serif; }}
.rank-bar-track {{ background: var(--soft-bg); border-radius: 999px; height: 8px; margin-top: 0.55rem; overflow: hidden; }}
.rank-bar-fill {{ height: 100%; border-radius: 999px; }}

/* ---------- Stat chips ---------- */
.chip-row {{ display: flex; gap: 0.7rem; flex-wrap: wrap; margin-bottom: 1rem; }}
.chip {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.65rem 1rem;
    min-width: 140px;
    flex: 1;
}}
.chip .chip-label {{ font-size: 0.76rem; color: var(--ink-soft); font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; }}
.chip .chip-value {{ font-size: 1.3rem; font-weight: 800; font-family: 'Plus Jakarta Sans', sans-serif; color: var(--ink); }}

/* ---------- Roadmap timeline ---------- */
.timeline {{ position: relative; padding-left: 1.6rem; }}
.timeline::before {{
    content: ""; position: absolute; left: 9px; top: 6px; bottom: 6px;
    width: 2px; background: linear-gradient(var(--brand-light), var(--accent));
}}
.timeline-item {{ position: relative; margin-bottom: 1rem; }}
.timeline-dot {{
    position: absolute; left: -1.6rem; top: 0.15rem;
    width: 20px; height: 20px; border-radius: 50%;
    background: var(--brand); color: white; font-size: 0.68rem;
    display: flex; align-items: center; justify-content: center; font-weight: 700;
    box-shadow: 0 0 0 4px var(--soft-bg);
}}
.timeline-card {{
    background: var(--card-bg); border: 1px solid var(--border);
    border-radius: 12px; padding: 0.7rem 1rem;
}}
.timeline-week {{ font-size: 0.75rem; font-weight: 700; color: var(--brand); text-transform: uppercase; letter-spacing: 0.03em; }}
.timeline-topics {{ font-size: 0.93rem; color: var(--ink); margin-top: 0.15rem; }}

/* ---------- How-it-works steps ---------- */
.step-card {{
    background: var(--card-bg); border: 1px dashed var(--border);
    border-radius: 16px; padding: 1.2rem; text-align: left; height: 100%;
}}
.step-num {{
    width: 30px; height: 30px; border-radius: 9px; background: var(--soft-bg);
    color: var(--brand); font-weight: 800; display: flex; align-items: center;
    justify-content: center; margin-bottom: 0.6rem; font-family: 'Plus Jakarta Sans', sans-serif;
}}
.step-title {{ font-weight: 700; margin-bottom: 0.25rem; color: var(--ink); }}
.step-body {{ font-size: 0.88rem; color: var(--ink-soft); }}

/* ---------- Callouts ---------- */
.callout {{
    border-radius: 14px; padding: 0.85rem 1.05rem; font-size: 0.9rem;
    border: 1px solid var(--border); background: var(--soft-bg); color: var(--ink);
    display: flex; gap: 0.6rem; align-items: flex-start;
}}

/* ---------- Streamlit widget polish ---------- */
div[data-testid="stFileUploader"] {{
    border: 1.5px dashed var(--brand-light);
    border-radius: 16px;
    padding: 0.6rem;
    background: var(--soft-bg);
}}
.stButton>button, .stDownloadButton>button {{
    border-radius: 10px;
    font-weight: 600;
    border: 1px solid transparent;
}}
.stButton>button[kind="primary"], .stDownloadButton>button {{
    background: var(--brand);
    color: white;
}}
.stButton>button[kind="primary"]:hover, .stDownloadButton>button:hover {{
    background: var(--brand-dark);
    color: white;
}}
div[data-testid="stMetric"] {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 0.8rem 1rem;
}}
section[data-testid="stSidebar"] {{
    background: var(--soft-bg);
    border-right: 1px solid var(--border);
}}
hr {{ border-color: var(--border) !important; }}
</style>
"""
