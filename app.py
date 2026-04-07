"""
Reddit Advice Tracker — Home Page
Scrape a Reddit user and view their activity overview.

Usage: streamlit run app.py
"""

import streamlit as st

import config
from logger import get_logger
from scraper import scrape_user, summarize_subreddits
from finder import fetch_sub_metadata, cross_check
from replies import fetch_replies
from posting import get_posted_subs
from shared import render_sidebar, load_analysis_cache

log = get_logger("app")

st.set_page_config(page_title="Reddit Advice Tracker", page_icon="📡", layout="wide")
render_sidebar()

# --- Post filter in sidebar ---
with st.sidebar:
    with st.container(border=True):
        st.subheader("Post Filter", anchor=False)
        st.caption("Only fetch replies on posts matching these keywords.")
        interview_keywords = st.text_area(
            "Keywords (one per line)",
            value="interview\nshield ai\nc++ code pair\nhackerrank\nhiring\nfinal round",
            height=120,
            label_visibility="collapsed",
        )

# --- Header ---
st.title("📡 Reddit Advice Tracker")
st.caption("Track advice from Reddit — find where to post, monitor replies, and analyze authenticity.")

# --- Input ---
with st.container(border=True):
    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")
    with col1:
        username = st.text_input("Reddit username", value="poppinlavish", placeholder="e.g. poppinlavish")
    with col2:
        run = st.button("🚀 Scrape", type="primary", use_container_width=True)

# --- Scrape ---
clean_username = username.strip().lstrip("u/").lstrip("/") if username else ""
needs_scrape = run and clean_username and clean_username != st.session_state.get("username")

if run and clean_username and not needs_scrape and st.session_state.get("scraped"):
    log.info(f"Using cached data for u/{st.session_state['username']}")
    st.toast(f"Using cached data for u/{st.session_state['username']}")

if needs_scrape:
    st.session_state.pop("analyzed_df", None)
    st.session_state.pop("chat_history", None)

    log.info(f"Starting scrape for u/{clean_username}")

    with st.status("Scraping Reddit...", expanded=True) as scrape_status:
        st.write("Fetching user history...")
        log.info("Step 1: Fetching user history...")
        posts_df, comments_df = scrape_user(clean_username)

        if posts_df is None:
            log.error(f"User u/{clean_username} not found or profile is private")
            st.error(f"User u/{clean_username} not found or profile is private.")
            scrape_status.update(label="Scrape failed", state="error")
        elif posts_df.empty and comments_df.empty:
            log.warning(f"No data found for u/{clean_username}")
            st.warning("No data found. Profile may be private or empty.")
            scrape_status.update(label="No data found", state="error")
        else:
            log.info(f"Fetched {len(posts_df)} posts, {len(comments_df)} comments")

            st.write("Building summary...")
            summary_df = summarize_subreddits(posts_df, comments_df)
            log.info(f"Summary: {len(summary_df)} unique communities")

            st.write("Fetching candidate subreddit metadata...")
            log.info("Step 2: Fetching candidate subreddit metadata...")
            candidates_df = fetch_sub_metadata()
            manually_posted = get_posted_subs(clean_username)
            already_df, not_yet_df = cross_check(posts_df, candidates_df, manually_posted=manually_posted)
            log.info(f"Cross-check: {len(already_df)} already posted, {len(not_yet_df)} not yet posted")

            keywords = [kw.strip().lower() for kw in interview_keywords.split("\n") if kw.strip()]
            interview_posts = posts_df[
                posts_df["title"].str.lower().apply(lambda t: any(kw in t for kw in keywords))
            ]
            log.info(f"Step 3: Filtered to {len(interview_posts)} matching posts (from {len(posts_df)} total)")

            st.write(f"Fetching replies on {len(interview_posts)} matching posts...")
            replies_df = fetch_replies(interview_posts)
            log.info(f"Fetched {len(replies_df)} replies")

            st.session_state.update({
                "scraped": True,
                "username": clean_username,
                "posts_df": posts_df,
                "comments_df": comments_df,
                "summary_df": summary_df,
                "candidates_df": candidates_df,
                "already_df": already_df,
                "not_yet_df": not_yet_df,
                "replies_df": replies_df,
            })

            cache = load_analysis_cache()
            if clean_username in cache:
                log.info(f"Loaded cached analysis for u/{clean_username}")
                st.toast("Loaded previously saved analysis results.")

            log.info(f"Scrape complete for u/{clean_username}: {len(posts_df)} posts, {len(comments_df)} comments, {len(replies_df)} replies")
            scrape_status.update(
                label=f"u/{clean_username}: {len(posts_df)} posts, {len(comments_df)} comments, {len(replies_df)} replies",
                state="complete",
            )

# --- Overview ---
if not st.session_state.get("scraped"):
    st.info("Enter a Reddit username and click **Scrape** to get started.", icon="👆")
    st.stop()

summary_df = st.session_state["summary_df"]
posts_df = st.session_state["posts_df"]
comments_df = st.session_state["comments_df"]
replies_df = st.session_state["replies_df"]
uname = st.session_state["username"]

# Metrics
c1, c2, c3, c4 = st.columns(4)
c1.metric("Communities", len(summary_df))
c2.metric("Posts", int(summary_df["Posts"].sum()))
c3.metric("Comments", int(summary_df["Comments"].sum()))
c4.metric("Replies", len(replies_df))

# Chart
st.subheader("Top 15 Communities", anchor=False)
top = summary_df.head(15).copy()
st.bar_chart(top.set_index("Subreddit")[["Posts", "Comments"]])

# Table with column config
st.subheader("All Communities", anchor=False)
st.dataframe(
    summary_df,
    use_container_width=True,
    height=400,
    column_config={
        "Subreddit": st.column_config.TextColumn("Subreddit", width="medium"),
        "Posts": st.column_config.NumberColumn("Posts", format="%d"),
        "Comments": st.column_config.NumberColumn("Comments", format="%d"),
        "Total": st.column_config.ProgressColumn("Total", min_value=0, max_value=int(summary_df["Total"].max()) if not summary_df.empty else 1),
    },
)

st.download_button(
    "⬇️ Download CSV",
    summary_df.to_csv(index=False),
    f"{uname}_communities.csv",
    "text/csv",
)
