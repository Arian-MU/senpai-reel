import streamlit as st
import duckdb
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="Data Viewer", page_icon="📊", layout="wide")
st.title("📊 Data Viewer")
st.caption("All scraped reels — sorted by engagement rate")


@st.cache_resource
def get_conn():
    return duckdb.connect("reels.duckdb")


# ── Sidebar filters ────────────────────────────────────────────────────────────
st.sidebar.header("🔍 Filters")

conn = get_conn()

# Account filter — prefer posts table, fall back to raw_scrapes
try:
    accounts_df = conn.execute(
        "SELECT DISTINCT account_id as profile FROM posts ORDER BY account_id"
    ).df()
    source = "posts"
except Exception:
    accounts_df = conn.execute(
        "SELECT DISTINCT profile FROM raw_scrapes ORDER BY profile"
    ).df()
    source = "raw_scrapes"

available_accounts = ["All"] + accounts_df.iloc[:, 0].tolist()
selected_account = st.sidebar.selectbox("Account", available_accounts)
selected_limit = st.sidebar.selectbox("Rows to show", [50, 100, 200, 500], index=1)
sort_by = st.sidebar.selectbox("Sort by", ["engagement_rate", "views", "likes", "posted_at"])

st.sidebar.markdown("---")
st.sidebar.caption(f"Data source: `{source}` table")

# ── Load from posts table (canonical) ─────────────────────────────────────────
def load_posts(account_filter, limit, order_by):
    where = "" if account_filter == "All" else f"WHERE account_id = '{account_filter}'"
    order_col = order_by if order_by in ("engagement_rate", "views", "likes", "posted_at") else "engagement_rate"
    try:
        df = conn.execute(f"""
            SELECT
                post_id,
                account_id,
                caption,
                likes,
                views,
                comments_count,
                duration_sec,
                posted_at,
                hashtags,
                mentions,
                engagement_rate,
                video_url,
                thumbnail_url,
                is_pinned,
                is_sponsored,
                download_status
            FROM posts
            {where}
            ORDER BY {order_col} DESC NULLS LAST
            LIMIT {limit}
        """).df()
        return df, "posts"
    except Exception:
        return pd.DataFrame(), "empty"


def load_raw_fallback(account_filter, limit):
    """Fall back to raw_scrapes if posts table is empty."""
    where = "" if account_filter == "All" else f"WHERE profile = '{account_filter}'"
    df = conn.execute(f"""
        SELECT profile, raw, scraped_at FROM raw_scrapes
        {where} ORDER BY scraped_at DESC LIMIT {limit}
    """).df()
    if df.empty:
        return pd.DataFrame()
    rows = []
    for _, row in df.iterrows():
        try:
            r = json.loads(row["raw"])
            likes = r.get("likesCount") or 0
            views = r.get("videoViewCount") or 0
            rows.append({
                "post_id": r.get("shortCode", ""),
                "account_id": row["profile"],
                "caption": str(r.get("caption", "") or "")[:120],
                "likes": likes,
                "views": views,
                "comments_count": r.get("commentsCount") or 0,
                "duration_sec": r.get("videoDuration") or 0,
                "posted_at": r.get("timestamp", "")[:10],
                "engagement_rate": round(likes / views * 100, 2) if views > 0 else 0,
                "video_url": r.get("videoUrl", ""),
                "download_status": "pending",
            })
        except Exception:
            continue
    return pd.DataFrame(rows)


with st.spinner("Loading…"):
    df, source_used = load_posts(selected_account, selected_limit, sort_by)
    if df.empty:
        df = load_raw_fallback(selected_account, selected_limit)
        source_used = "raw_scrapes (fallback)"

if df.empty:
    st.warning("⚠️ No data yet. Go to the **Scraper** page (home) and run a scrape first.")
    st.stop()

# ── Summary metrics ────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Reels shown", len(df))
c2.metric("Avg Likes", f"{df['likes'].mean():,.0f}" if "likes" in df else "—")
c3.metric("Avg Views", f"{df['views'].mean():,.0f}" if "views" in df else "—")
c4.metric("Avg Engagement", f"{df['engagement_rate'].mean():.2f}%" if "engagement_rate" in df else "—")
c5.metric("Source", source_used)

st.markdown("---")

# ── Search ─────────────────────────────────────────────────────────────────────
search = st.text_input("🔍 Search captions or account", placeholder="e.g., ATS, resume, interview")
if search and "caption" in df.columns:
    mask = (
        df["caption"].str.contains(search, case=False, na=False) |
        df["account_id"].str.contains(search, case=False, na=False)
    )
    df = df[mask]
    st.caption(f"{len(df)} results for '{search}'")

# ── Main table ─────────────────────────────────────────────────────────────────
col_cfg = {}
if "video_url" in df.columns:
    col_cfg["video_url"] = st.column_config.LinkColumn("Video", display_text="🎥 Watch")
if "engagement_rate" in df.columns:
    col_cfg["engagement_rate"] = st.column_config.NumberColumn("Engagement %", format="%.2f")
if "duration_sec" in df.columns:
    col_cfg["duration_sec"] = st.column_config.NumberColumn("Duration (s)", format="%.0f")

# Truncate caption for table display
if "caption" in df.columns:
    df["caption"] = df["caption"].str.slice(0, 100)

st.dataframe(df, use_container_width=True, hide_index=True, column_config=col_cfg)

# ── Downloads ─────────────────────────────────────────────────────────────────
st.markdown("---")
dl1, dl2 = st.columns(2)
with dl1:
    st.download_button(
        "📥 Download CSV",
        data=df.to_csv(index=False),
        file_name=f"reels_{selected_account}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with dl2:
    st.download_button(
        "📥 Download JSON",
        data=df.to_json(orient="records", indent=2),
        file_name=f"reels_{selected_account}_{datetime.now().strftime('%Y%m%d')}.json",
        mime="application/json",
        use_container_width=True,
    )

