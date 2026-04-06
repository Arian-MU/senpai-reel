"""
Phase 7 — Content generation via GPT-4o.

Uses extracted message units as grounding context for all generated content.
All outputs are saved to the generated_content table with cost tracking.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import requests

from core.db import get_connection
from analysis.prompts import (
    CAPTION_SYSTEM, CAPTION_USER,
    HOOKS_SYSTEM, HOOKS_USER,
    SCRIPT_SYSTEM, SCRIPT_USER,
    format_reference_context,
)

_GPT4O_INPUT_COST = 2.50 / 1_000_000   # $2.50 / 1M input tokens
_GPT4O_OUTPUT_COST = 10.00 / 1_000_000  # $10.00 / 1M output tokens

# Use gpt-4o-mini for lower cost; generation quality is still excellent here
_MODEL = "gpt-4o-mini"
_MINI_INPUT_COST = 0.15 / 1_000_000
_MINI_OUTPUT_COST = 0.60 / 1_000_000


@dataclass
class GeneratedContent:
    gen_id: str
    content_type: str   # caption | hooks | script
    topic: str
    output_text: str
    model: str
    tokens_used: int
    cost_usd: float
    created_at: datetime


def _call_gpt(
    system: str,
    user: str,
    api_key: str,
    model: str = _MODEL,
    stream: bool = False,
    max_tokens: int = 1000,
) -> tuple[str, int, float]:
    """
    Call GPT and return (output_text, tokens_used, cost_usd).
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=60,
    )
    if resp.status_code == 401:
        raise PermissionError("Invalid OpenAI API key")
    resp.raise_for_status()

    data = resp.json()
    usage = data["usage"]
    in_tokens = usage.get("prompt_tokens", 0)
    out_tokens = usage.get("completion_tokens", 0)
    cost = in_tokens * _MINI_INPUT_COST + out_tokens * _MINI_OUTPUT_COST
    text = data["choices"][0]["message"]["content"].strip()
    return text, in_tokens + out_tokens, round(cost, 6)


def generate_caption(
    topic: str,
    angle: str,
    tone: str,
    reference_units: list,
    openai_api_key: str,
) -> GeneratedContent:
    context = format_reference_context(reference_units)
    user_msg = CAPTION_USER.format(topic=topic, tone=tone, angle=angle, reference_context=context)
    text, tokens, cost = _call_gpt(CAPTION_SYSTEM, user_msg, openai_api_key, max_tokens=600)

    result = GeneratedContent(
        gen_id=str(uuid.uuid4()),
        content_type="caption",
        topic=topic,
        output_text=text,
        model=_MODEL,
        tokens_used=tokens,
        cost_usd=cost,
        created_at=datetime.utcnow(),
    )
    _save(result, reference_units)
    return result


def generate_hooks(
    topic: str,
    angle: str,
    reference_units: list,
    openai_api_key: str,
    count: int = 5,
) -> GeneratedContent:
    system = HOOKS_SYSTEM.format(count=count)
    context = format_reference_context(reference_units)
    user_msg = HOOKS_USER.format(topic=topic, angle=angle, reference_context=context, count=count)
    text, tokens, cost = _call_gpt(system, user_msg, openai_api_key, max_tokens=400)

    result = GeneratedContent(
        gen_id=str(uuid.uuid4()),
        content_type="hooks",
        topic=topic,
        output_text=text,
        model=_MODEL,
        tokens_used=tokens,
        cost_usd=cost,
        created_at=datetime.utcnow(),
    )
    _save(result, reference_units)
    return result


def generate_script(
    topic: str,
    duration_sec: int,
    tone: str,
    reference_units: list,
    openai_api_key: str,
) -> GeneratedContent:
    word_count = int(duration_sec / 60 * 130)
    system = SCRIPT_SYSTEM.format(duration_sec=duration_sec, word_count=word_count, tone=tone)
    context = format_reference_context(reference_units)
    user_msg = SCRIPT_USER.format(
        topic=topic, duration_sec=duration_sec, tone=tone, reference_context=context
    )
    text, tokens, cost = _call_gpt(system, user_msg, openai_api_key, max_tokens=800)

    result = GeneratedContent(
        gen_id=str(uuid.uuid4()),
        content_type="script",
        topic=topic,
        output_text=text,
        model=_MODEL,
        tokens_used=tokens,
        cost_usd=cost,
        created_at=datetime.utcnow(),
    )
    _save(result, reference_units)
    return result


def _save(content: GeneratedContent, reference_units: list):
    """Persist generated content to DB."""
    source_ids = [getattr(u, "unit_id", "") for u in reference_units]
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO generated_content
                (gen_id, created_at, topic, content_type, output_text, model,
                 source_units, tokens_used, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                content.gen_id, content.created_at, content.topic, content.content_type,
                content.output_text, content.model, source_ids,
                content.tokens_used, content.cost_usd,
            ],
        )
    finally:
        conn.close()
