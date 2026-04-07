"""Posts page — view all scraped posts with rich column config."""

import streamlit as st
from src.shared import require_scrape, render_sidebar

st.set_page_config(page_title="Posts", page_icon="📝", layout="wide")
render_sidebar()
require_scrape()

posts_df = st.session_state["posts_df"]

st.title("📝 Posts")
st.caption(f"{len(posts_df)} posts across {posts_df['subreddit'].nunique()} subreddits")

if posts_df.empty:
    st.info("No posts found.")
else:
    st.dataframe(
        posts_df,
        use_container_width=True,
        height=600,
        column_config={
            "subreddit": st.column_config.TextColumn("Subreddit", width="small"),
            "title": st.column_config.TextColumn("Title", width="large"),
            "post_url": st.column_config.LinkColumn("URL", display_text="Open"),
            "score": st.column_config.NumberColumn("Score", format="%d"),
            "num_comments": st.column_config.NumberColumn("Comments", format="%d"),
            "created_utc": st.column_config.NumberColumn("Created (UTC)", format="%d"),
            "post_id": st.column_config.TextColumn("ID", width="small"),
        },
    )
