import streamlit as st
import requests
import json
import duckdb

# Page configuration
st.set_page_config(
    page_title="Senpai Reel — Scraper",
    page_icon="🎥",
    layout="wide"
)

from core.db import init_db, save_raw_scrape, save_structured_scrape

# Initialize DB once
init_db()

# Load token
APIFY_TOKEN = st.secrets["APIFY_TOKEN"]
ACTOR_ID = "apify~instagram-reel-scraper"

st.title("🎥 Instagram Reel Scraper")
st.caption("Scrape competitor reels and store everything in the database.")

st.info("💡 After scraping, use the **📊 Data Viewer** page in the sidebar to explore your data.")

# Inputs
col1, col2 = st.columns([3, 1])
with col1:
    username = st.text_input("Instagram Username", placeholder="e.g., resumeworded")
with col2:
    max_items = st.number_input("Max reels", min_value=1, max_value=200, value=10)

run = st.button("🚀 Run Scraper", type="primary")


# ---- Scraper Function ----
def run_scraper(username: str, max_items: int):
    url = f"https://api.apify.com/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items?token={APIFY_TOKEN}"

    instagram_url = f"https://www.instagram.com/{username}/"

    payload = {
        "username": [instagram_url],
        "resultsLimit": max_items,
        "skipPinnedPosts": False,
        "includeSharesCount": False
    }

    res = requests.post(url, json=payload)
    res.raise_for_status()
    return res.json()


# ---- Main Button Logic ----
if run:
    if not username:
        st.error("Please enter a username.")
    else:
        with st.spinner(f"Scraping @{username}… this takes ~10–30 seconds…"):
            try:
                data = run_scraper(username, max_items)
            except Exception as e:
                st.error(f"Scraper error: {e}")
                st.stop()

        st.success(f"✅ Scraping complete — {len(data)} reels returned")

        # Save raw (deduplicates by shortCode) + always process structured
        with st.spinner("Saving to database…"):
            result_msg = save_raw_scrape(username, data)
            save_structured_scrape(username, data)

        st.success(f"💾 Saved: {result_msg}")

        # Quick stats
        conn = duckdb.connect("reels.duckdb")
        reel_count = conn.execute(
            "SELECT COUNT(*) FROM reels WHERE profile = ?", (username,)
        ).fetchone()[0]
        comment_count = conn.execute(
            "SELECT COUNT(*) FROM comments c JOIN reels r ON c.reel_id = r.reel_id WHERE r.profile = ?",
            (username,)
        ).fetchone()[0]
        conn.close()

        st.info(f"📈 @{username} in DB: **{reel_count} reels**, **{comment_count} comments**")

        st.download_button(
            label="⬇️ Download JSON",
            data=json.dumps(data, indent=2),
            file_name=f"{username}_reels.json",
            mime="application/json"
        )
