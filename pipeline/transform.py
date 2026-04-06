import duckdb
import json
from datetime import datetime

DB_PATH = "reels.duckdb"

def init_db():
    conn = duckdb.connect(DB_PATH)

    # Profiles table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        profile TEXT,
        scraped_at TIMESTAMP,
        total_reels INTEGER
    )
    """)

    # Reels table (expanded + fixed)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS reels (
        reel_id TEXT PRIMARY KEY,
        profile TEXT,
        shortcode TEXT,
        caption TEXT,
        likes INTEGER,
        views INTEGER,
        video_play_count INTEGER,
        comments_count INTEGER,
        video_url TEXT,
        audio_url TEXT,
        thumbnail_url TEXT,
        display_url TEXT,
        all_images JSON,
        timestamp TIMESTAMP,
        location_name TEXT,
        location_id TEXT,
        duration DOUBLE,
        is_pinned BOOLEAN,
        is_sponsored BOOLEAN,
        owner_username TEXT,
        owner_id TEXT,
        raw JSON,
        scraped_at TIMESTAMP
    )
    """)

    # Comments
    conn.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        reel_id TEXT,
        comment_id TEXT,
        parent_id TEXT,
        username TEXT,
        text TEXT,
        likes INTEGER,
        timestamp TIMESTAMP
    )
    """)

    # Tagged users table (enhanced)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS tagged_users (
        reel_id TEXT,
        username TEXT,
        full_name TEXT,
        user_id TEXT,
        profile_pic_url TEXT
    )
    """)

    conn.close()


def fix_timestamp(ts):
    if not ts:
        return None
    # Remove Z and milliseconds
    ts = ts.replace("Z", "")
    if "." in ts:
        ts = ts.split(".")[0]
    return ts.replace("T", " ")


def save_scrape(profile, items):
    conn = duckdb.connect(DB_PATH)

    # Save profile scrape summary
    conn.execute("""
        INSERT INTO profiles VALUES (?, ?, ?)
    """, (profile, datetime.utcnow(), len(items)))

    for item in items:
        reel_id = item.get("id")

        # Insert into reels
        conn.execute("""
            INSERT OR REPLACE INTO reels VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )
        """, (
            reel_id,
            profile,
            item.get("shortCode"),
            item.get("caption"),
            item.get("likesCount"),
            item.get("videoViewCount"),
            item.get("videoPlayCount"),
            item.get("commentsCount"),
            item.get("videoUrl"),
            item.get("audioUrl"),
            item["images"][0] if item.get("images") else None,
            item.get("displayUrl"),
            json.dumps(item.get("images", [])),
            fix_timestamp(item.get("timestamp")),
            item.get("locationName"),
            item.get("locationId"),
            item.get("videoDuration"),
            bool(item.get("isPinned")),
            bool(item.get("isSponsored")),
            item.get("ownerUsername"),
            item.get("ownerId"),
            json.dumps(item),
            datetime.utcnow()
        ))

        # Tagged users
        for u in item.get("taggedUsers", []):
            conn.execute("""
                INSERT INTO tagged_users VALUES (?, ?, ?, ?, ?)
            """, (
                reel_id,
                u.get("username"),
                u.get("full_name"),
                u.get("id"),
                u.get("profile_pic_url")
            ))

        # Comments
        _insert_comments_recursive(conn, reel_id, item.get("latestComments", []))

    conn.close()



def _insert_comments_recursive(conn, reel_id, comments, parent_id=None):
    """Recursively flatten nested comments."""
    for c in comments:
        conn.execute("""
            INSERT INTO comments VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            reel_id,
            c.get("id"),
            parent_id,
            c.get("ownerUsername"),
            c.get("text"),
            c.get("likesCount"),
            fix_timestamp(c.get("timestamp"))
        ))

        # Recurse replies
        if isinstance(c.get("replies"), list):
            _insert_comments_recursive(conn, reel_id, c["replies"], c.get("id"))
