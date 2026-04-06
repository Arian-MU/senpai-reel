import streamlit as st
import json
import duckdb

# Page configuration
st.set_page_config(
    page_title="Senpai Reel — Scraper",
    page_icon="🎥",
    layout="wide"
)

from core.db import init_db, get_posts_stats, get_scrape_history
from collection.scraper import scrape_and_store
from collection.account_list import COMPETITOR_ACCOUNTS, DEFAULT_MAX_ITEMS

# Initialize DB once
init_db()

APIFY_TOKEN = st.secrets["APIFY_TOKEN"]

st.title("🎥 Senpai Reel — Scraper")
st.caption("Scrape competitor Instagram reels and store everything in the database.")

# ── Global stats bar ──────────────────────────────────────────────────────────
stats = get_posts_stats()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Posts in DB", f"{stats['total_posts']:,}")
c2.metric("Creator Accounts", stats['accounts'])
c3.metric("Avg Engagement", f"{stats['avg_engagement']:.2f}%")
c4.metric("Videos Downloaded", stats['downloaded'])

st.markdown("---")

# ── Two modes: single or batch ────────────────────────────────────────────────
tab_single, tab_batch = st.tabs(["Single Account", "Batch Scrape"])

# ── SINGLE ACCOUNT ────────────────────────────────────────────────────────────
with tab_single:
    col1, col2 = st.columns([3, 1])
    with col1:
        username = st.text_input("Instagram Username", placeholder="e.g., resumeworded",
                                  key="single_username")
    with col2:
        max_items = st.number_input("Max reels", min_value=1, max_value=200, value=30,
                                     key="single_max")

    if st.button("🚀 Scrape Account", type="primary", key="btn_single"):
        if not username.strip():
            st.error("Please enter a username.")
        else:
            handle = username.strip().lstrip("@")
            with st.spinner(f"Scraping @{handle}… (10–60 sec)…"):
                result = scrape_and_store(handle, APIFY_TOKEN, max_items)

            if result["status"] == "done":
                st.success(
                    f"✅ @{handle}: {result['reels_found']} reels found, "
                    f"{result['reels_new']} new"
                )
            else:
                st.error(f"❌ @{handle}: {result['error']}")

# ── BATCH SCRAPE ──────────────────────────────────────────────────────────────
with tab_batch:
    st.write("Scrape all competitor accounts from the curated list, or enter custom handles below.")

    default_handles = "\n".join(COMPETITOR_ACCOUNTS[:10])
    handles_input = st.text_area(
        "Accounts to scrape (one per line)",
        value=default_handles,
        height=200,
        help="Paste any Instagram handles, one per line — no @ needed",
    )
    batch_max = st.number_input("Max reels per account", min_value=1, max_value=200,
                                 value=DEFAULT_MAX_ITEMS, key="batch_max")

    if st.button("🚀 Start Batch Scrape", type="primary", key="btn_batch"):
        handles = [h.strip().lstrip("@") for h in handles_input.splitlines() if h.strip()]
        if not handles:
            st.error("No accounts entered.")
        else:
            st.write(f"Scraping **{len(handles)} accounts**…")
            progress = st.progress(0)
            results_placeholder = st.empty()
            results = []

            for i, handle in enumerate(handles):
                results_placeholder.info(f"⏳ Scraping @{handle} ({i+1}/{len(handles)})…")
                result = scrape_and_store(handle, APIFY_TOKEN, batch_max)
                results.append(result)
                progress.progress((i + 1) / len(handles))

            results_placeholder.empty()

            # Summary table
            done = [r for r in results if r["status"] == "done"]
            failed = [r for r in results if r["status"] == "failed"]

            st.success(f"✅ Batch complete: {len(done)} succeeded, {len(failed)} failed")
            st.table([
                {
                    "Account": f"@{r['username']}",
                    "Status": "✅" if r["status"] == "done" else "❌",
                    "Found": r["reels_found"],
                    "New": r["reels_new"],
                    "Error": r["error"] or "",
                }
                for r in results
            ])

# ── Scrape history ────────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📋 Scrape History (last 20 jobs)"):
    history = get_scrape_history()
    if history:
        import pandas as pd
        df = pd.DataFrame(history, columns=[
            "job_id", "username", "started_at", "finished_at",
            "reels_found", "reels_new", "status", "error_msg"
        ])
        df = df.drop(columns=["job_id"]).head(20)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No scrape jobs yet.")
