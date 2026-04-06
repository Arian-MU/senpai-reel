"""
Phase 6 — Analytics queries.

All analytics queries are in one place so the Streamlit page stays thin.
"""

from __future__ import annotations

import pandas as pd

from core.db import get_connection


def get_creator_leaderboard(limit: int = 20) -> pd.DataFrame:
    conn = get_connection()
    try:
        return conn.execute(
            f"""
            SELECT
                ca.username,
                COUNT(p.post_id)           AS total_posts,
                ROUND(AVG(p.engagement_rate), 2) AS avg_engagement,
                MAX(p.engagement_rate)     AS max_engagement,
                SUM(p.views)               AS total_views,
                SUM(p.likes)               AS total_likes,
                ROUND(AVG(p.duration_sec), 0) AS avg_duration_sec
            FROM posts p
            JOIN creator_accounts ca ON p.account_id = ca.account_id
            GROUP BY ca.username
            ORDER BY avg_engagement DESC
            LIMIT {limit}
            """
        ).df()
    finally:
        conn.close()


def get_topic_distribution() -> pd.DataFrame:
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT topic, COUNT(*) AS unit_count
            FROM message_units
            GROUP BY topic
            ORDER BY unit_count DESC
            """
        ).df()
    finally:
        conn.close()


def get_content_gap_matrix() -> pd.DataFrame:
    """Returns a pivot table: topic (rows) × content_type (cols) = unit count."""
    conn = get_connection()
    try:
        df = conn.execute(
            """
            SELECT topic, content_type, COUNT(*) AS cnt
            FROM message_units
            GROUP BY topic, content_type
            """
        ).df()
    finally:
        conn.close()

    if df.empty:
        return df
    pivot = df.pivot(index="topic", columns="content_type", values="cnt").fillna(0).astype(int)
    return pivot


def get_top_posts(topic: str = "All", limit: int = 20) -> pd.DataFrame:
    conn = get_connection()
    try:
        where = "" if topic == "All" else f"WHERE mu.topic = '{topic}'"
        return conn.execute(
            f"""
            SELECT DISTINCT
                p.post_id,
                ca.username,
                p.caption,
                p.likes,
                p.views,
                ROUND(p.engagement_rate, 2) AS engagement_rate,
                p.duration_sec,
                CAST(p.posted_at AS TEXT) AS posted_at,
                p.video_url,
                p.hashtags
            FROM posts p
            JOIN creator_accounts ca ON p.account_id = ca.account_id
            {'LEFT JOIN message_units mu ON p.post_id = mu.post_id ' + where if topic != 'All' else ''}
            ORDER BY p.engagement_rate DESC NULLS LAST
            LIMIT {limit}
            """
        ).df()
    finally:
        conn.close()


def get_hashtag_intelligence(limit: int = 30) -> pd.DataFrame:
    """Most-used hashtags across all posts."""
    conn = get_connection()
    try:
        df = conn.execute(
            "SELECT hashtags FROM posts WHERE hashtags IS NOT NULL"
        ).df()
    finally:
        conn.close()

    if df.empty:
        return pd.DataFrame(columns=["hashtag", "count"])

    from collections import Counter
    counter: Counter = Counter()
    for tags in df["hashtags"]:
        if tags:
            for tag in tags:
                if tag:
                    counter[tag.lower().strip("#")] += 1

    top = counter.most_common(limit)
    return pd.DataFrame(top, columns=["hashtag", "count"])


def get_posting_cadence() -> pd.DataFrame:
    """Posts per week per creator."""
    conn = get_connection()
    try:
        return conn.execute(
            """
            SELECT
                ca.username,
                DATE_TRUNC('week', p.posted_at) AS week,
                COUNT(*) AS posts
            FROM posts p
            JOIN creator_accounts ca ON p.account_id = ca.account_id
            WHERE p.posted_at IS NOT NULL
            GROUP BY ca.username, week
            ORDER BY week DESC, posts DESC
            """
        ).df()
    finally:
        conn.close()
