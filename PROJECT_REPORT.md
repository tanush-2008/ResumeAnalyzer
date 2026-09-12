# Project Report: AI Resume Analyzer & Job Recommendation System

## 1. Objective

Build an NLP-based educational tool that tells a student how well their
resume matches a target job role, which skills they're missing, and what
to learn next - without making any hiring or rejection decision itself.

## 2. Approach

The pipeline follows the brief's workflow exactly: upload → extract text →
clean/normalize → extract skills → load job-role requirements → compare →
score → rank → recommend → show gaps → roadmap.

Two matching tiers were implemented:

- **Beginner** (the brief's baseline): keyword/phrase skill matching against
  a controlled dictionary, TF-IDF vectorization, and cosine similarity,
  blended 50/50 with exact skill overlap into one interpretable score.
- **Advanced** (optional, selectable in the UI): spaCy `PhraseMatcher`
  extraction as an alternative to regex, and Sentence-Transformers
  (`all-MiniLM-L6-v2`) semantic-embedding similarity blended into the score
  (30% TF-IDF / 40% semantic / 30% overlap) so paraphrased skill mentions
  still match.

Beyond the dataset of 7 predefined roles, a resume can also be matched
against an arbitrary pasted job description - required skills are derived
by running the same extractor over the JD text.

## 3. Architecture

Streamlit is the primary, standalone UI (`app.py`) - it works with zero
extra setup. An optional FastAPI backend (`backend/`) adds user accounts
and saved reports on top, backed by SQLAlchemy (SQLite by default,
PostgreSQL-compatible via `DATABASE_URL`) with JWT-based auth. The
Streamlit app detects at runtime whether the backend is reachable and
enables/disables login accordingly - the core analysis never depends on it.
See the architecture diagram in [README.md](README.md#architecture--workflow).

## 4. Results

Three anonymized sample resumes were used for validation (see
`tests/test_cases.csv`): all three routed to their expected top role, with
scores of 68.1%, 43.3%, and 72.3% respectively (beginner mode). 16
automated tests cover text cleaning, skill extraction (regex and spaCy),
role ranking (beginner, advanced, and custom-JD), roadmap generation,
resume-section detection, LLM-feedback fallback behavior, and the backend's
auth/report endpoints - all passing.

## 5. Responsible AI

The system deliberately never scores protected attributes (gender, age,
religion, nationality, photo, marital status, disability) - the skill
dictionary and extractors only ever look at technical/job-related terms.
Every score is labeled an estimate in the UI and generated report, not a
hiring decision, and resumes are processed in memory unless a logged-in
user explicitly chooses to save a report.

## 6. Limitations

- Skill detection depends on a manually curated dictionary; skills phrased
  in unusual ways may be missed unless advanced (semantic) matching is
  enabled.
- The job-role dataset is small (7 roles); scores reflect fit against this
  dataset, not the entire job market.
- Scanned/image-only PDFs without a text layer cannot be parsed (no OCR
  step in this pipeline).
- LLM-generated feedback quality depends on the configured provider/model
  and is only as unbiased as the underlying model plus the controlling
  prompt.

## 7. Future Work

Ideas beyond this project's scope: OCR fallback for scanned resumes,
a larger/labelled job-role dataset with supervised ranking, richer resume
parsing (dates, seniority), and a proper admin UI for reviewing
skill-dictionary suggestions (currently queued in
`data/skill_dictionary_suggestions.csv` for manual review).
