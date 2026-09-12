"""Optional advanced feature: LLM-generated resume feedback.

Uses a controlled, responsible-AI-constrained prompt against an
OpenAI-compatible chat completions endpoint. Supports Groq (default),
OpenAI, or any self-hosted/local OpenAI-compatible server (e.g. Ollama,
LM Studio) purely via environment variables - no vendor SDK required.

If no API key is configured, or the request fails for any reason, this
module falls back to deterministic, rule-based feedback so the dashboard
never breaks and never silently calls out to the network without consent
implied by the user having set an API key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()

# Provider presets: base URL + default model. All expose an OpenAI-compatible
# POST {base_url}/chat/completions endpoint.
PROVIDER_PRESETS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.1-8b-instant",
        "api_key_env": "GROQ_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
    "gemini": {
        # Gemini's OpenAI-compatibility layer.
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-1.5-flash",
        "api_key_env": "GEMINI_API_KEY",
    },
    "local": {
        # e.g. Ollama's OpenAI-compatible endpoint, or LM Studio.
        "base_url": os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1"),
        "default_model": os.environ.get("LOCAL_LLM_MODEL", "llama3.1"),
        "api_key_env": None,
    },
}

SYSTEM_PROMPT = """You are a resume-feedback assistant embedded in a student \
educational tool. Follow these rules strictly:
- Comment ONLY on job-related skills, education, projects, and relevant experience.
- NEVER mention or infer gender, age, religion, nationality, ethnicity, photo, \
marital status, disability, or any other protected attribute.
- Do not claim a missing keyword always means missing ability - suggest the \
candidate clarify or add evidence for it instead.
- Be constructive, specific, and concise (max 6 short bullet points).
- State clearly that this is guidance, not a hiring decision.
"""


@dataclass
class FeedbackResult:
    text: str
    source: str  # "llm" or "rule_based"
    provider: str | None = None
    model: str | None = None


def _active_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "groq").lower()


def is_llm_configured(provider: str | None = None) -> bool:
    provider = provider or _active_provider()
    preset = PROVIDER_PRESETS.get(provider)
    if preset is None:
        return False
    if preset["api_key_env"] is None:
        return True  # local providers don't need a key
    return bool(os.environ.get(preset["api_key_env"]))


def _build_user_prompt(resume_text: str, target_role: str, missing_skills: list[str]) -> str:
    missing = ", ".join(missing_skills) if missing_skills else "none"
    trimmed_resume = resume_text[:4000]  # keep prompt bounded
    return (
        f"Target role: {target_role}\n"
        f"Missing skills for this role: {missing}\n\n"
        f"Resume text (truncated):\n{trimmed_resume}\n\n"
        "Give resume improvement feedback following your system instructions."
    )


def _call_llm(resume_text: str, target_role: str, missing_skills: list[str]) -> FeedbackResult:
    provider = _active_provider()
    preset = PROVIDER_PRESETS[provider]
    api_key = os.environ.get(preset["api_key_env"]) if preset["api_key_env"] else "not-required"
    model = os.environ.get("LLM_MODEL", preset["default_model"])

    headers = {"Content-Type": "application/json"}
    if preset["api_key_env"]:
        headers["Authorization"] = f"Bearer {api_key}"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_prompt(resume_text, target_role, missing_skills)},
        ],
        "temperature": 0.4,
        "max_tokens": 400,
    }

    response = requests.post(
        f"{preset['base_url']}/chat/completions",
        json=payload,
        headers=headers,
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()
    return FeedbackResult(text=content, source="llm", provider=provider, model=model)


def _rule_based_feedback(target_role: str, missing_skills: list[str]) -> FeedbackResult:
    lines = [
        f"This is automated guidance for the **{target_role}** role, not a hiring decision.",
    ]
    if missing_skills:
        lines.append(
            "- Add a project or bullet point that demonstrates: "
            + ", ".join(missing_skills[:5])
            + "."
        )
        lines.append(
            "- If you already have this experience, make sure it's named explicitly "
            "on your resume - relevant keywords help both this tool and recruiters find it."
        )
    else:
        lines.append("- Your resume already covers every required skill for this role.")
    lines.append(
        "- Quantify achievements where possible (e.g. \"reduced processing time by 30%\")."
    )
    lines.append("- Keep bullet points action-oriented and specific to the target role.")
    lines.append(
        "- A missing keyword does not always mean missing ability - consider adding "
        "evidence for skills you have but didn't list explicitly."
    )
    return FeedbackResult(text="\n".join(lines), source="rule_based")


def get_resume_feedback(
    resume_text: str, target_role: str, missing_skills: list[str]
) -> FeedbackResult:
    """Return LLM feedback when configured, otherwise a rule-based fallback."""
    if is_llm_configured():
        try:
            return _call_llm(resume_text, target_role, missing_skills)
        except Exception:  # noqa: BLE001 - any network/provider issue -> safe fallback
            return _rule_based_feedback(target_role, missing_skills)
    return _rule_based_feedback(target_role, missing_skills)
