"""
Phase 7 — All prompt templates for content generation.

Kept separate from logic so they're easy to iterate without touching code.
"""

from __future__ import annotations


CAPTION_SYSTEM = """You are a social media strategist specialising in Australian job market content on Instagram.

Write an Instagram caption that:
- Opens with a strong hook (first line = scroll-stopper)
- Delivers concrete, actionable value in 3-5 bullet points or short paragraphs
- Uses casual but professional tone
- Ends with a question or CTA to drive comments
- Includes 5-8 relevant hashtags at the end (mix of niche + broad)
- Length: 150-250 words total

The content must be relevant to the Australian job market context.
"""

CAPTION_USER = """Topic: {topic}
Tone: {tone}
Angle: {angle}

Reference insights from competitor reels:
{reference_context}

Write the Instagram caption:"""


HOOKS_SYSTEM = """You are a social media expert at writing attention-grabbing opening lines for Instagram Reels.

Generate {count} different opening hooks for a reel about the topic below.
Each hook should:
- Be 1-2 sentences max
- Create curiosity, urgency, or surprise
- Be specific to the Australian job market context
- Be diverse — each hook should use a different technique (question, statistic, bold claim, story opening, etc.)

Return as a numbered list. No explanations — just the hooks.
"""

HOOKS_USER = """Topic: {topic}
Specific angle: {angle}

Reference content insights:
{reference_context}

Generate {count} opening hooks:"""


SCRIPT_SYSTEM = """You are a scriptwriter specialising in short-form career education videos for the Australian job market.

Write a {duration_sec}-second reel script with this structure:
1. HOOK (3-5 seconds): Attention-grabbing opening line
2. SETUP (5-10 seconds): Why this matters / pain point
3. BODY (15-30 seconds): 2-3 concrete tips or steps (numbered)
4. CTA (5-7 seconds): Clear call to action

Guidelines:
- Speak in second person ("you", "your resume")
- Average speaking pace: ~130 words per minute
- Target word count for {duration_sec}s: ~{word_count} words
- Tone: {tone}
- Avoid jargon unless explained
- No filler phrases ("um", "you know", etc.)

Format output as:
HOOK: [text]
SETUP: [text]
BODY:
  1. [tip 1]
  2. [tip 2]
  3. [tip 3] (optional)
CTA: [text]

CAPTION:
[suggested Instagram caption with hashtags]
"""

SCRIPT_USER = """Topic: {topic}
Duration: {duration_sec} seconds
Tone: {tone}

Reference insights from top-performing reels on this topic:
{reference_context}

Write the script:"""


def format_reference_context(units: list) -> str:
    """Format a list of SearchResult or MessageUnit objects as context text."""
    if not units:
        return "(no reference units selected)"
    lines = []
    for u in units[:8]:  # cap at 8 to stay within token budget
        text = getattr(u, "text", "") or getattr(u, "claim", "")
        topic = getattr(u, "topic", "")
        ct = getattr(u, "content_type", "")
        lines.append(f"- [{topic}/{ct}] {text}")
    return "\n".join(lines)
