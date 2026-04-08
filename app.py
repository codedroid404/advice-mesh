"""
AdviceMesh — Home Page

Scrape a Reddit user and view their activity overview.

Usage:
    streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from src import config
from src.logger import get_logger
from src.scraper import scrape_user, summarize_subreddits
from src.finder import fetch_sub_metadata, cross_check
from src.replies import fetch_replies
from src.posting import get_posted_subs
from src.shared import render_sidebar, load_analysis_cache
from src.subreddit_config import get_all_candidate_subs

log = get_logger("app")


# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="AdviceMesh",
    page_icon="🕸️",
    layout="wide",
)

render_sidebar()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def normalize_username(username: str) -> str:
    """Normalize Reddit username input."""
    if not username:
        return ""
    return username.strip().removeprefix("u/").removeprefix("/").strip()


def read_uploaded_pdf(uploaded_file) -> str:
    """Extract text from an uploaded PDF using PyMuPDF."""
    if not uploaded_file:
        return ""

    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is not installed. Run: pip install pymupdf") from exc

    try:
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception as exc:
        raise RuntimeError(f"Could not read PDF: {exc}") from exc


def clear_analysis_state() -> None:
    """Clear analysis-related cached state when a new scrape starts."""
    for key in ("analyzed_df", "chat_history"):
        st.session_state.pop(key, None)


def save_job_context(job_description: str) -> None:
    """Persist job description into session state. Marks analysis as stale if JD changed."""
    if job_description:
        old_jd = st.session_state.get("job_description", "")
        if old_jd and old_jd != job_description and "analyzed_df" in st.session_state:
            st.session_state["analysis_stale"] = True
        st.session_state["job_description"] = job_description


def render_top_communities(summary_df) -> None:
    """Render top 3 communities."""
    if len(summary_df) < 3:
        return

    st.subheader("Top Communities", anchor=False)
    top3 = summary_df.head(3)
    cols = st.columns(3)

    for col, (_, row) in zip(cols, top3.iterrows()):
        with col:
            with st.container(border=True):
                st.markdown(f"**r/{row['Subreddit']}**")
                st.caption(
                    f"{int(row['Posts'])} posts · "
                    f"{int(row['Comments'])} comments · "
                    f"{int(row['Total'])} total"
                )


def render_overview(summary_df, replies_df, username: str) -> None:
    """Render overview metrics, charts, table, and download."""
    total_posts = int(summary_df["Posts"].sum()) if not summary_df.empty else 0
    total_comments = int(summary_df["Comments"].sum()) if not summary_df.empty else 0
    total_replies = len(replies_df)
    total_communities = len(summary_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Communities", total_communities)
    c2.metric("Posts", total_posts)
    c3.metric("Comments", total_comments)
    c4.metric("Replies", total_replies)

    render_top_communities(summary_df)

    st.subheader("Top 15 Communities", anchor=False)
    with st.container(border=True):
        top = summary_df.head(15).copy()
        if top.empty:
            st.info("No community activity available yet.")
        else:
            st.bar_chart(
                top.set_index("Subreddit")[["Posts", "Comments"]],
                horizontal=True,
            )

    st.subheader("All Communities", anchor=False)
    max_total = int(summary_df["Total"].max()) if not summary_df.empty else 1

    st.dataframe(
        summary_df,
        width="stretch",
        height=400,
        column_config={
            "Subreddit": st.column_config.TextColumn("Subreddit", width="medium"),
            "Posts": st.column_config.NumberColumn("Posts", format="%d"),
            "Comments": st.column_config.NumberColumn("Comments", format="%d"),
            "Total": st.column_config.ProgressColumn(
                "Total",
                min_value=0,
                max_value=max_total,
            ),
        },
    )

    st.download_button(
        label="⬇️ Download CSV",
        data=summary_df.to_csv(index=False),
        file_name=f"{username}_communities.csv",
        mime="text/csv",
        width="content",
    )


def run_scrape_pipeline(username: str) -> None:
    """Run the full Reddit scrape and enrichment pipeline."""
    clear_analysis_state()
    log.info("Starting scrape for u/%s", username)

    with st.status("Scraping Reddit...", expanded=True) as status:
        # Job context
        jd_text = st.session_state.get("job_description", "")
        interview_stage = st.session_state.get("interview_stage", "")

        if jd_text or interview_stage:
            context_parts = []
            if jd_text:
                context_parts.append(f"JD: {len(jd_text):,} chars")
            if interview_stage:
                preview = interview_stage[:50].strip()
                context_parts.append(f"Stage: {preview}..." if preview else "Stage provided")
            st.write(f"✅ Job context loaded ({', '.join(context_parts)})")
        else:
            st.write("ℹ️ No job context provided — analysis will be generic")

        # Step 1: Fetch history
        st.write(f"🔍 Fetching history for u/{username}...")
        posts_df, comments_df = scrape_user(username)

        if posts_df is None:
            log.error("User u/%s not found or profile is private", username)
            st.error(f"User u/{username} not found or profile is private.")
            status.update(label="Scrape failed", state="error")
            return

        if posts_df.empty and comments_df.empty:
            log.warning("No data found for u/%s", username)
            st.warning("No data found. Profile may be private or empty.")
            status.update(label="No data found", state="error")
            return

        st.write(f"✅ Found {len(posts_df)} posts and {len(comments_df)} comments")
        log.info("Fetched %s posts and %s comments", len(posts_df), len(comments_df))

        # Step 2: Filter to relevant subreddits using Claude
        all_subs = list(set(
            list(posts_df["subreddit"].unique()) + list(comments_df["subreddit"].unique())
        ))
        jd = st.session_state.get("job_description", "")
        stage = st.session_state.get("interview_stage", "")

        if jd or stage:
            from src.analyzer import filter_relevant_subs
            st.write(f"🧠 Asking Claude to filter {len(all_subs)} subreddits for relevance...")
            relevant_subs = filter_relevant_subs(all_subs, job_context=jd, interview_stage=stage)
            relevant_lower = {s.lower() for s in relevant_subs}
            posts_df = posts_df[posts_df["subreddit"].str.lower().isin(relevant_lower)].reset_index(drop=True)
            comments_df = comments_df[comments_df["subreddit"].str.lower().isin(relevant_lower)].reset_index(drop=True)
            st.write(f"✅ Kept {len(relevant_subs)}/{len(all_subs)} relevant subreddits")
            log.info("Claude filtered to %s relevant subs", len(relevant_subs))
        else:
            st.write("ℹ️ No job context — showing all communities")

        # Step 3: Build summary
        st.write("📊 Building community summary...")
        summary_df = summarize_subreddits(posts_df, comments_df)
        st.write(f"✅ {len(summary_df)} unique communities")
        log.info("Built summary for %s communities", len(summary_df))

        # Step 3: Candidate metadata
        candidate_subs = get_all_candidate_subs()
        st.write(f"🎯 Checking {len(candidate_subs)} candidate subreddits...")
        candidates_df = fetch_sub_metadata()

        manually_posted = get_posted_subs(username)
        already_df, not_yet_df = cross_check(
            posts_df,
            candidates_df,
            manually_posted=manually_posted,
        )

        st.write(
            f"✅ Already posted in {len(already_df)} candidate subs; "
            f"{len(not_yet_df)} still available"
        )
        log.info(
            "Cross-check complete: %s already posted, %s not yet posted",
            len(already_df),
            len(not_yet_df),
        )

        # Step 4: Replies
        st.write(f"📩 Fetching replies across {len(posts_df)} posts...")
        replies_df = fetch_replies(posts_df)
        st.write(f"✅ Found {len(replies_df)} replies")
        log.info("Fetched %s replies", len(replies_df))

        # Step 5: Save session state
        st.session_state.update(
            {
                "scraped": True,
                "username": username,
                "posts_df": posts_df,
                "comments_df": comments_df,
                "summary_df": summary_df,
                "candidates_df": candidates_df,
                "already_df": already_df,
                "not_yet_df": not_yet_df,
                "replies_df": replies_df,
            }
        )

        cache = load_analysis_cache()
        if username in cache:
            import pandas as pd
            st.session_state["analyzed_df"] = pd.DataFrame(cache[username])
            st.write("✅ Loaded previously saved analysis results")
            log.info("Loaded cached analysis for u/%s", username)

        log.info("Scrape complete for u/%s", username)
        status.update(
            label=(
                f"✅ u/{username}: "
                f"{len(posts_df)} posts, "
                f"{len(comments_df)} comments, "
                f"{len(replies_df)} replies"
            ),
            state="complete",
        )


# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------

st.title("🕸️ AdviceMesh")
st.caption(
    "Scrape Reddit activity, find the best subreddits to post in, "
    "track replies, and analyze advice authenticity."
)


# -----------------------------------------------------------------------------
# Job Context
# -----------------------------------------------------------------------------

st.subheader("Job Context", anchor=False)
st.caption(
    "Upload a job description and describe where you are in the process. "
    "This helps the downstream analysis produce better recommendations."
)

with st.container(border=True):
    jd_col, stage_col = st.columns(2)

    with jd_col:
        uploaded_pdf = st.file_uploader(
            "Upload Job Description (PDF)",
            type=["pdf"],
            key="jd_upload",
        )

        jd_text = ""
        if uploaded_pdf:
            try:
                jd_text = read_uploaded_pdf(uploaded_pdf)
                st.success(f"Loaded: {uploaded_pdf.name} ({len(jd_text):,} chars)")
            except RuntimeError as exc:
                st.error(str(exc))
        else:
            jd_text = st.text_area(
                "Or paste job description",
                placeholder="Paste the job listing text here...",
                height=150,
                key="jd_text_input",
            )

    with stage_col:
        st.text_area(
            "Where are you in the interview process?",
            placeholder=(
                "Example: I passed the phone screen and technical round. "
                "Final round is a live coding session with a senior engineer. "
                "I have 2 weeks to prep."
            ),
            height=200,
            key="interview_stage",
        )

save_job_context(jd_text)


# -----------------------------------------------------------------------------
# Reddit Input
# -----------------------------------------------------------------------------

st.subheader("Reddit Scraper", anchor=False)

with st.container(border=True):
    col1, col2 = st.columns([3, 1], vertical_alignment="bottom")

    with col1:
        username_input = st.text_input(
            "Reddit username",
            value=st.session_state.get("username", ""),
            placeholder="e.g. reddit_user123",
        )

    with col2:
        run = st.button("🚀 Scrape", type="primary", width="stretch")

    st.caption("Tip: Scraping may take 1-2 minutes for active users. Refresh the page to cancel.")

clean_username = normalize_username(username_input)
current_username = st.session_state.get("username")
already_scraped = st.session_state.get("scraped", False)
needs_scrape = run and clean_username and clean_username != current_username

if run and not clean_username:
    st.warning("Please enter a Reddit username.")

if run and clean_username and not needs_scrape and already_scraped:
    log.info("Using cached data for u/%s", current_username)
    st.toast(f"Using cached data for u/{current_username}")

if needs_scrape:
    run_scrape_pipeline(clean_username)


# -----------------------------------------------------------------------------
# Overview
# -----------------------------------------------------------------------------

if not st.session_state.get("scraped"):
    st.info("Enter a Reddit username and click **Scrape** to get started.", icon="👆")
    st.stop()

summary_df = st.session_state["summary_df"]
replies_df = st.session_state["replies_df"]
username = st.session_state["username"]

render_overview(summary_df, replies_df, username)

# --- Quick Analyze from Home ---
if not replies_df.empty and "analyzed_df" not in st.session_state:
    st.divider()
    if st.button("🤖 Analyze All Replies with Claude", type="primary", width="stretch", key="home_analyze_btn"):
        from src.analyzer import analyze_replies_df
        from src.shared import save_analysis

        with st.status(f"Analyzing {len(replies_df)} replies with {config.CLAUDE_MODEL}...", expanded=True) as status:
            progress = st.progress(0, text="Starting...")
            reply_count = len(replies_df)

            def on_status(msg):
                st.write(msg)
                try:
                    parts = msg.split()
                    fraction = parts[2].split("/")
                    current = int(fraction[0])
                    progress.progress(current / reply_count, text=f"Reply {current}/{reply_count}")
                except (IndexError, ValueError):
                    pass

            def on_progress(partial_df):
                st.session_state["analyzed_df"] = partial_df
                save_analysis(username, partial_df.to_dict("records"))

            analyzed_df = analyze_replies_df(
                replies_df,
                on_status=on_status,
                on_progress=on_progress,
                job_context=st.session_state.get("job_description", ""),
                interview_stage=st.session_state.get("interview_stage", ""),
            )
            progress.progress(1.0, text="Complete!")
            status.update(label=f"✅ Analyzed {reply_count} replies", state="complete")

        st.session_state["analyzed_df"] = analyzed_df
        save_analysis(username, analyzed_df.to_dict("records"))
        st.rerun()

elif "analyzed_df" in st.session_state:
    st.divider()

    # Warn if job context changed since last analysis
    if st.session_state.get("analysis_stale"):
        st.warning("Job description changed since last analysis. Re-analyze for updated results.", icon="⚠️")
        if st.button("🔄 Re-analyze with new JD", key="reanalyze_btn"):
            st.session_state.pop("analyzed_df", None)
            st.session_state.pop("analysis_stale", None)
            st.rerun()
    analyzed_df = st.session_state["analyzed_df"]

    if "usefulness_score" not in analyzed_df.columns:
        analyzed_df["usefulness_score"] = 0
    if "key_tips" not in analyzed_df.columns:
        analyzed_df["key_tips"] = ""

    # --- Insights summary ---
    st.subheader("🤖 Analysis Insights", anchor=False)

    auth_scores = analyzed_df["authenticity_score"]
    genuine = int((auth_scores >= 8).sum())
    mixed = int(((auth_scores >= 5) & (auth_scores < 8)).sum())
    suspicious = int((auth_scores < 5).sum())
    avg_useful = analyzed_df["usefulness_score"].mean()

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("🟢 Genuine", genuine)
    s2.metric("🟡 Mixed", mixed)
    s3.metric("🔴 Suspicious", suspicious)
    s4.metric("Avg Usefulness", f"{avg_useful:.1f}/10")

    # --- Top Tips ---
    all_tips = []
    for _, r in analyzed_df.iterrows():
        if r.get("key_tips") and str(r["key_tips"]).lower() != "none":
            for tip in str(r["key_tips"]).split(";"):
                tip = tip.strip()
                if tip:
                    all_tips.append((tip, r["usefulness_score"]))

    if all_tips:
        seen = set()
        unique_tips = []
        for tip, score in sorted(all_tips, key=lambda x: x[1], reverse=True):
            if tip.lower() not in seen:
                seen.add(tip.lower())
                unique_tips.append(tip)

        with st.container(border=True):
            st.subheader(f"💡 Top {min(len(unique_tips), 10)} Tips", anchor=False)
            for i, tip in enumerate(unique_tips[:10], 1):
                st.markdown(f"**{i}.** {tip}")

    # --- Top replies preview ---
    top_replies = analyzed_df.sort_values("usefulness_score", ascending=False).head(5)
    st.subheader("Top Replies", anchor=False)

    for _, row in top_replies.iterrows():
        icon = "🟢" if row["authenticity_score"] >= 8 else ("🟡" if row["authenticity_score"] >= 5 else "🔴")
        with st.expander(f"{icon} u/{row['author']} — auth: {row['authenticity_score']}/10 | useful: {row['usefulness_score']}/10"):
            st.markdown(row['body'][:500])
            if row.get("key_tips") and str(row["key_tips"]).lower() != "none":
                st.info(f"**Tips:** {row['key_tips']}")
            st.link_button("View on Reddit", row['permalink'])

    st.caption("See all results and chat on the **Replies & Analysis** page.")