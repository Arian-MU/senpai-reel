"""
Phase 4 — Jobs-AU Domain Taxonomy.

Defines the canonical topic and content_type values used throughout
extraction, search, and content generation.
"""

from __future__ import annotations
from typing import Optional

# ── Topics ─────────────────────────────────────────────────────────────────────
TOPICS = [
    "ATS",
    "Resume",
    "CoverLetter",
    "Interview",
    "LinkedIn",
    "JobSearch",
    "Salary",
    "CareerChange",
    "Recruiter",
    "Visa",
    "General",   # fallback for content that doesn't fit a specific topic
]

# ── Content Types ──────────────────────────────────────────────────────────────
CONTENT_TYPES = [
    "tip",         # Actionable advice
    "warning",     # Common mistake to avoid
    "stat",        # Statistic or data point
    "myth",        # Debunking a misconception
    "story",       # Personal experience / case study
    "hook",        # Opening hook (first 3 seconds)
    "cta",         # Call to action
    "other",       # Catch-all fallback
]

# ── Descriptions used in GPT system prompt ────────────────────────────────────
TOPIC_DESCRIPTIONS = {
    "ATS": "Applicant Tracking Systems — keywords, resume parsing, rejection",
    "Resume": "Resume writing, formatting, sections, keywords, length",
    "CoverLetter": "Cover letter strategy, structure, personalisation",
    "Interview": "Interview prep, common questions, STAR method, follow-up",
    "LinkedIn": "LinkedIn profile optimisation, networking, InMail, content",
    "JobSearch": "Job search strategy, job boards, cold outreach, referrals",
    "Salary": "Salary negotiation, benchmarks, market rates",
    "CareerChange": "Pivoting industries, upskilling, transferable skills",
    "Recruiter": "Working with recruiters, agency vs in-house, recruiter tips",
    "Visa": "Working visa, sponsorship Australia, 482, 189, 190 visas",
    "General": "Career advice that doesn't fit a specific topic",
}

CONTENT_TYPE_DESCRIPTIONS = {
    "tip": "Actionable advice the viewer can apply immediately",
    "warning": "A common mistake or thing to avoid",
    "stat": "A specific statistic or data point cited",
    "myth": "Debunking a widely-held misconception",
    "story": "A personal experience, case study, or anecdote",
    "hook": "Opening hook or attention-grabbing statement (first 3 seconds)",
    "cta": "Call to action — follow, like, comment, download",
    "other": "Content that doesn't fit the above types",
}


def validate_topic(value: str) -> str:
    """Normalise and validate a topic string. Returns 'General' if unrecognised."""
    for t in TOPICS:
        if t.lower() == value.lower().strip():
            return t
    return "General"


def validate_content_type(value: str) -> str:
    """Normalise and validate a content_type string. Returns 'other' if unrecognised."""
    for ct in CONTENT_TYPES:
        if ct.lower() == value.lower().strip():
            return ct
    return "other"


def topics_for_prompt() -> str:
    """Return a formatted string of topics for GPT system prompts."""
    return "\n".join(f"  - {t}: {TOPIC_DESCRIPTIONS[t]}" for t in TOPICS)


def content_types_for_prompt() -> str:
    """Return a formatted string of content types for GPT system prompts."""
    return "\n".join(f"  - {ct}: {CONTENT_TYPE_DESCRIPTIONS[ct]}" for ct in CONTENT_TYPES)
