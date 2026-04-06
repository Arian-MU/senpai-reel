import streamlit as st
import duckdb
conn = duckdb.connect("reels.duckdb")
df = conn.execute("SELECT * FROM reel_features").df()

st.dataframe(df)