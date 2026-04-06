import duckdb
import json
from datetime import datetime

DB_PATH = "reels.duckdb"

def init_db():
    conn = duckdb.connect(DB_PATH)

    # Profile summary
    conn.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        profile TEXT,
        scraped_at TIMESTAMP,
        total_reels INTEGER
    )
    """)

    # Raw scrapes (NEW)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS raw_scrapes (
        id INTEGER,
        profile TEXT,
        raw JSON,
        scraped_at TIMESTAMP
    )
    """)

    # Reels table
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

    # Tagged users
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


# --------------------------------------------------------
#  RAW SCRAPE SAVER
# --------------------------------------------------------
def save_raw_scrape(profile, items):
    """Stores the raw JSON array exactly as returned. Skips duplicates by shortCode."""
    conn = duckdb.connect(DB_PATH)

    saved, skipped = 0, 0
    for idx, item in enumerate(items):
        shortcode = item.get("shortCode")

        # Dedup: skip if this shortcode already exists in raw_scrapes
        if shortcode:
            existing = conn.execute(
                "SELECT COUNT(*) FROM raw_scrapes WHERE json_extract_string(raw, '$.shortCode') = ?",
                (shortcode,)
            ).fetchone()[0]
            if existing > 0:
                skipped += 1
                continue

        conn.execute("""
            INSERT INTO raw_scrapes VALUES (?, ?, ?, ?)
        """, (
            idx,
            profile,
            json.dumps(item),
            datetime.utcnow()
        ))
        saved += 1

    conn.close()
    return f"{saved} new, {skipped} already existed"


# --------------------------------------------------------
#  STRUCTURED SCRAPE SAVER
# --------------------------------------------------------
def save_structured_scrape(profile, items):
    """Wrapper matching your old function name."""
    save_scrape(profile, items)


def fix_timestamp(ts):
    if not ts:
        return None
    # Remove Z and milliseconds
    ts = ts.replace("Z", "")
    if "." in ts:
        ts = ts.split(".")[0]
    return ts.replace("T", " ")

# --------------------------------------------------------
#  STRUCTURED LOADER (YOUR ORIGINAL)
# --------------------------------------------------------
def save_scrape(profile, items):
    conn = duckdb.connect(DB_PATH)

    conn.execute("""
        INSERT INTO profiles VALUES (?, ?, ?)
    """, (profile, datetime.utcnow(), len(items)))

    for item in items:
        reel_id = item.get("id")

        conn.execute("""
            INSERT OR REPLACE INTO reels VALUES (
                ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
            )
        """, (
            reel_id,                                    # reel_id
            profile,                                    # profile
            item.get("shortCode"),                      # shortcode
            item.get("caption"),                        # caption
            item.get("likesCount"),                     # likes
            item.get("videoViewCount"),                 # views
            item.get("videoPlayCount"),                 # video_play_count
            item.get("commentsCount"),                  # comments_count
            item.get("videoUrl"),                       # video_url
            item.get("audioUrl"),                       # audio_url
            item["images"][0] if item.get("images") else None,  # thumbnail_url
            item.get("displayUrl"),                     # display_url
            json.dumps(item.get("images", [])),         # all_images
            fix_timestamp(item.get("timestamp")),       # timestamp
            item.get("locationName"),                   # location_name
            item.get("locationId"),                     # location_id
            item.get("videoDuration"),                  # duration
            bool(item.get("isPinned")),                 # is_pinned
            bool(item.get("isSponsored")),              # is_sponsored
            item.get("ownerUsername"),                  # owner_username
            item.get("ownerId"),                        # owner_id
            json.dumps(item),                           # raw
            datetime.utcnow()                           # scraped_at
        ))

        # tagged users
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

        # comments
        _insert_comments_recursive(conn, reel_id, item.get("latestComments", []))

    conn.close()


def _insert_comments_recursive(conn, reel_id, comments, parent_id=None):
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

        if isinstance(c.get("replies"), list):
            _insert_comments_recursive(conn, reel_id, c["replies"], c.get("id"))
