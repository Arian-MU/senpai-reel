import streamlit as st
import duckdb
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="Data Viewer", page_icon="📊", layout="wide")
st.title("📊 Instagram Reel Data Viewer")
st.write("Clean table view of all scraped Instagram reel data")

@st.cache_resource
def get_db_connection():
    return duckdb.connect("reels.duckdb")

def load_raw_data(profile_filter=None, limit=100):
    conn = get_db_connection()
    query = "SELECT id, profile, raw, scraped_at FROM raw_scrapes"
    params = []
    
    if profile_filter and profile_filter != 'All':
        query += " WHERE profile = ?"
        params.append(profile_filter)
    
    query += f" ORDER BY scraped_at DESC LIMIT {limit}"
    
    if params:
        return conn.execute(query, params).df()
    else:
        return conn.execute(query).df()

def process_raw_data_for_table(raw_df):
    if raw_df.empty:
        return pd.DataFrame()
    
    processed_rows = []
    for _, row in raw_df.iterrows():
        try:
            raw_json = json.loads(row['raw'])
            likes = raw_json.get('likesCount', 0) or 0
            views = raw_json.get('videoViewCount', 0) or 0
            engagement_rate = (likes / views * 100) if views > 0 else 0
            
            # Extract music info
            music_info = raw_json.get('musicInfo', {}) or {}
            music_text = f"{music_info.get('artist_name', 'Unknown')} - {music_info.get('song_name', 'Unknown')}" if music_info.get('artist_name') or music_info.get('song_name') else 'N/A'
            
            # Extract hashtags and mentions count
            hashtags_count = len(raw_json.get('hashtags', []) or [])
            mentions_count = len(raw_json.get('mentions', []) or [])
            
            processed_row = {
                'Short Code': raw_json.get('shortCode', 'N/A'),
                'Caption Preview': str(raw_json.get('caption', 'No caption') or 'No caption')[:80] + '...' if len(str(raw_json.get('caption', ''))) > 80 else str(raw_json.get('caption', 'No caption') or 'No caption'),
                'Likes': f"{likes:,}",
                'Views': f"{views:,}",
                'Play Count': f"{raw_json.get('videoPlayCount', 0) or 0:,}",
                'Comments': raw_json.get('commentsCount', 0) or 0,
                'Engagement %': f"{engagement_rate:.2f}%",
                'Duration (s)': f"{raw_json.get('videoDuration', 0) or 0:.1f}",
                'Posted': str(raw_json.get('timestamp', 'Unknown'))[:10] if raw_json.get('timestamp') else 'Unknown',
                'Location': raw_json.get('locationName', 'N/A') or 'N/A',
                'Owner': raw_json.get('ownerUsername', 'N/A') or 'N/A',
                'Music': music_text[:50] + '...' if len(music_text) > 50 else music_text,
                'Hashtags': hashtags_count,
                'Mentions': mentions_count,
                'Sponsored': '✓' if raw_json.get('isSponsored') else '✗',
                'Video URL': raw_json.get('videoUrl', 'N/A'),
                'Post URL': raw_json.get('url', 'N/A'),
                'Scraped': row['scraped_at'].strftime('%m/%d %H:%M') if pd.notnull(row['scraped_at']) else 'Unknown'
            }
            processed_rows.append(processed_row)
        except Exception as e:
            processed_rows.append({
                'Short Code': 'ERROR',
                'Caption Preview': f'Failed to parse: {str(e)[:50]}',
                'Likes': '0',
                'Views': '0',
                'Play Count': '0',
                'Comments': 0,
                'Engagement %': '0.00%',
                'Duration (s)': '0.0',
                'Posted': 'Unknown',
                'Location': 'N/A',
                'Owner': 'N/A',
                'Music': 'N/A',
                'Hashtags': 0,
                'Mentions': 0,
                'Sponsored': '✗',
                'Video URL': 'N/A',
                'Post URL': 'N/A',
                'Scraped': 'Unknown'
            })
    return pd.DataFrame(processed_rows)

# Sidebar filters
st.sidebar.header("🔍 Filters")

try:
    conn = get_db_connection()
    profiles_df = conn.execute("SELECT DISTINCT profile FROM raw_scrapes ORDER BY profile").df()
    available_profiles = ['All'] + profiles_df['profile'].tolist() if not profiles_df.empty else ['All']
except:
    available_profiles = ['All']

selected_profile = st.sidebar.selectbox("Select Profile", available_profiles)
limit_options = [50, 100, 200, 500, 1000]
selected_limit = st.sidebar.selectbox("Number of reels to show", limit_options, index=1)

# Load and process data
with st.spinner("Loading data..."):
    raw_data = load_raw_data(selected_profile, selected_limit)
    
    if raw_data.empty:
        st.warning("⚠️ No data found. Please scrape some Instagram reels first!")
        st.stop()

processed_data = process_raw_data_for_table(raw_data)

if not processed_data.empty:
    # Summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Reels", len(processed_data))
    
    with col2:
        likes_values = [int(str(x).replace(',', '')) for x in processed_data['Likes'] if str(x).replace(',', '').isdigit()]
        avg_likes = sum(likes_values) / len(likes_values) if likes_values else 0
        st.metric("Avg Likes", f"{avg_likes:,.0f}")
    
    with col3:
        views_values = [int(str(x).replace(',', '')) for x in processed_data['Views'] if str(x).replace(',', '').isdigit()]
        avg_views = sum(views_values) / len(views_values) if views_values else 0
        st.metric("Avg Views", f"{avg_views:,.0f}")
    
    with col4:
        play_values = [int(str(x).replace(',', '')) for x in processed_data['Play Count'] if str(x).replace(',', '').isdigit()]
        avg_plays = sum(play_values) / len(play_values) if play_values else 0
        st.metric("Avg Plays", f"{avg_plays:,.0f}")
    
    with col5:
        engagement_values = [float(str(x).replace('%', '')) for x in processed_data['Engagement %'] if str(x).replace('%', '').replace('.', '').isdigit()]
        avg_engagement = sum(engagement_values) / len(engagement_values) if engagement_values else 0
        st.metric("Avg Engagement", f"{avg_engagement:.2f}%")
    
    st.markdown("---")
    
    # Search functionality
    search_term = st.text_input("🔍 Search in captions, codes, owners, or music", placeholder="Enter search term...")
    
    if search_term:
        mask = (
            processed_data['Caption Preview'].str.contains(search_term, case=False, na=False) |
            processed_data['Short Code'].str.contains(search_term, case=False, na=False) |
            processed_data['Owner'].str.contains(search_term, case=False, na=False) |
            processed_data['Music'].str.contains(search_term, case=False, na=False) |
            processed_data['Location'].str.contains(search_term, case=False, na=False)
        )
        filtered_data = processed_data[mask]
        st.write(f"Found {len(filtered_data)} reels matching '{search_term}'")
        display_data = filtered_data
    else:
        display_data = processed_data
    
    # Main data table
    st.subheader(f"📊 Reels Data ({len(display_data)} reels)")
    
    # Configure columns for better display
    column_config = {
        "Video URL": st.column_config.LinkColumn(
            "Video URL",
            help="Direct link to the video file",
            display_text="🎥 Video"
        ),
        "Post URL": st.column_config.LinkColumn(
            "Post URL", 
            help="Instagram post URL",
            display_text="📱 Post"
        ),
        "Engagement %": st.column_config.NumberColumn(
            "Engagement %",
            help="Likes/Views ratio as percentage",
            format="%.2f%%"
        ),
        "Duration (s)": st.column_config.NumberColumn(
            "Duration (s)",
            help="Video duration in seconds",
            format="%.1f"
        )
    }
    
    st.dataframe(
        display_data, 
        use_container_width=True, 
        hide_index=True,
        column_config=column_config
    )
    
    # Download options
    st.markdown("---")
    col1, col2 = st.columns(2)
    
    with col1:
        csv = display_data.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"instagram_reels_{selected_profile}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        if st.button("📥 Download Raw JSON", use_container_width=True):
            raw_json_data = []
            for _, row in raw_data.iterrows():
                try:
                    raw_json_data.append(json.loads(row['raw']))
                except:
                    continue
            
            json_str = json.dumps(raw_json_data, indent=2)
            st.download_button(
                label="📥 Click to Download JSON",
                data=json_str,
                file_name=f"instagram_reels_raw_{selected_profile}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json"
            )

else:
    st.error("❌ Failed to process data. Please check your scraped data format.")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("""
💡 **Tips:**
- Use the profile filter to focus on specific accounts
- Search works across captions, codes, owners, music, and locations
- Click on Video URL or Post URL to open links
- Table includes play counts, music info, hashtags/mentions
- Download data as CSV or raw JSON for further analysis
- Data is processed on-the-fly from raw storage
""")
