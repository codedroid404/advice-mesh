"""Comments page — view all scraped comments."""

import streamlit as st
from shared import require_scrape, render_sidebar

st.set_page_config(page_title="Comments", page_icon="💬", layout="wide")
render_sidebar()
require_scrape()

comments_df = st.session_state["comments_df"]

st.title("💬 Comments")
st.caption(f"{len(comments_df)} comments across {comments_df['subreddit'].nunique()} subreddits")

if comments_df.empty:
    st.info("No comments found.")
else:
    st.dataframe(
        comments_df,
        use_container_width=True,
        height=600,
        column_config={
            "subreddit": st.column_config.TextColumn("Subreddit", width="small"),
            "body": st.column_config.TextColumn("Comment", width="large"),
            "post_title": st.column_config.TextColumn("Post Title", width="medium"),
            "post_url": st.column_config.LinkColumn("URL", display_text="Open"),
            "score": st.column_config.NumberColumn("Score", format="%d"),
            "created_utc": st.column_config.NumberColumn("Created (UTC)", format="%d"),
            "comment_id": st.column_config.TextColumn("ID", width="small"),
        },
    )
