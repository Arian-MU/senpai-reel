import streamlit as st
import requests
import json

# Page configuration
st.set_page_config(
    page_title="Instagram Reel Scraper",
    page_icon="🎥",
    layout="wide"
)

from core.db import init_db, save_raw_scrape, save_structured_scrape

# Initialize DB once
init_db()

# Load token
APIFY_TOKEN = st.secrets["APIFY_TOKEN"]
ACTOR_ID = "apify~instagram-reel-scraper"

st.title("🎥 Instagram Reel Scraper (Apify-powered)")
st.write("Scrape Instagram reels, save raw JSON, and optionally process them later.")

# Navigation hint
st.info("💡 **Tip**: After scraping data, visit the **📊 Data Viewer** page (in the sidebar) to explore and analyze all your scraped data!")

# Inputs
username = st.text_input("Instagram Username", placeholder="e.g., nomubarsydney")
max_items = st.number_input("Max number of reels", min_value=1, max_value=200, value=10)

run = st.button("Run Scraper")

# ---- Sidebar: RAW View ----
if st.sidebar.button("View RAW scrapes"):
    import duckdb
    conn = duckdb.connect("reels.duckdb")
    df = conn.execute("SELECT * FROM raw_scrapes ORDER BY scraped_at DESC").df()
    st.sidebar.dataframe(df)

if st.sidebar.button("Run Analytics Pipeline"):
    from transform import run_analytics_pipeline
    df = run_analytics_pipeline(username)
    st.sidebar.success("Pipeline complete!")
    st.dataframe(df)


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

    st.write("API Raw Response:")
    st.code(res.text)

    res.raise_for_status()
    return res.json()


# ---- Main Button Logic ----
if run:
    if not username:
        st.error("Please enter a username.")
    else:
        st.info("Running scraper… please wait ~10 seconds…")

        try:
            data = run_scraper(username, max_items)

            st.success("Scraping complete! 🎉")
            st.json(data)

            # Save RAW data first (always)
            raw_id = save_raw_scrape(username, data)
            st.success(f"✅ Raw data saved: {raw_id}")

            # OPTIONAL: Process structured data
            st.write("---")
            st.subheader("📊 Data Processing Options")
            
            if st.checkbox("🔄 Also process structured data (advanced)", value=False, help="This will parse the raw JSON into structured tables for analysis"):
                with st.spinner("Processing structured data..."):
                    save_structured_scrape(username, data)
                st.success("✅ Structured tables updated!")
                
                # Show quick stats
                import duckdb
                conn = duckdb.connect("reels.duckdb")
                reel_count = conn.execute("SELECT COUNT(*) FROM reels WHERE profile = ?", (username,)).fetchone()[0]
                comment_count = conn.execute("SELECT COUNT(*) FROM comments c JOIN reels r ON c.reel_id = r.reel_id WHERE r.profile = ?", (username,)).fetchone()[0]
                tagged_count = conn.execute("SELECT COUNT(*) FROM tagged_users t JOIN reels r ON t.reel_id = r.reel_id WHERE r.profile = ?", (username,)).fetchone()[0]
                conn.close()
                
                st.info(f"📈 Processed: {reel_count} reels, {comment_count} comments, {tagged_count} tagged users")

            # Allow download
            st.download_button(
                label="Download JSON",
                data=json.dumps(data, indent=2),
                file_name=f"{username}_reels.json",
                mime="application/json"
            )

        except Exception as e:
            st.error(f"Error: {e}")
