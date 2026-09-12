"""Module 2 (cleaning part): normalize raw resume text for comparison.

Protected technical tokens such as C++, C#, and .NET are preserved by
temporarily swapping them for placeholders before punctuation is stripped.
"""

from __future__ import annotations

import re

# Tokens that contain symbols we must not strip out.
PROTECTED_TOKENS = ["c++", "c#", ".net"]
_PLACEHOLDER_PREFIX = "__protected_token_"


def _placeholder(index: int) -> str:
    return f"{_PLACEHOLDER_PREFIX}{index}__"


def clean_text(raw_text: str) -> str:
    """Lowercase, protect known technical symbols, strip noise, collapse whitespace."""
    text = raw_text.lower()

    protected = {}
    for i, token in enumerate(PROTECTED_TOKENS):
        placeholder = _placeholder(i)
        if token in text:
            protected[placeholder] = token
            text = text.replace(token, placeholder)

    # Remove emails, URLs and phone numbers (not job-relevant, also protects privacy).
    text = re.sub(r"\S+@\S+", " ", text)
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    text = re.sub(r"\+?\d[\d\-\s()]{7,}\d", " ", text)

    # Drop remaining punctuation/symbols except letters, digits, spaces and underscores
    # (underscores are used by our placeholders).
    text = re.sub(r"[^a-z0-9\s_]", " ", text)

    # Collapse repeated whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    for placeholder, token in protected.items():
        text = text.replace(placeholder, token)

    return text


def normalize_for_matching(text: str) -> str:
    """Extra normalization pass used right before TF-IDF vectorization."""
    text = clean_text(text)
    # Merge multi-word skill phrases into single tokens so TF-IDF treats them atomically.
    phrase_map = {
        "power bi": "power_bi",
        "data visualization": "data_visualization",
        "machine learning": "machine_learning",
        "deep learning": "deep_learning",
        "hugging face": "hugging_face",
        "computer vision": "computer_vision",
        "image processing": "image_processing",
        "cloud deployment": "cloud_deployment",
        "rest api": "rest_api",
    }
    for phrase, token in phrase_map.items():
        text = text.replace(phrase, token)
    return text
