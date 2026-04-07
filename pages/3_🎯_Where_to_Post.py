"""Where to Post page — post preview, distribution, and subreddit discovery."""

import streamlit as st
from shared import require_scrape, render_sidebar
from posting import mark_as_posted
from post_content import format_for_subreddit, POST_TITLE
from discovery import discover_and_evaluate, save_discovered_subs
from subreddit_config import get_all_candidate_subs

st.set_page_config(page_title="Where to Post", page_icon="🎯", layout="wide")
render_sidebar()
require_scrape()

already_df = st.session_state["already_df"]
not_yet_df = st.session_state["not_yet_df"]
uname = st.session_state["username"]

st.title("🎯 Where to Post")

# --- Already vs Not Yet ---
col_a, col_b = st.columns(2)
with col_a:
    with st.container(border=True):
        st.subheader(f"✅ Already Posted ({len(already_df)})", anchor=False)
        if not already_df.empty:
            st.dataframe(
                already_df,
                use_container_width=True,
                height=300,
                column_config={
                    "subreddit": st.column_config.TextColumn("Subreddit"),
                    "title": st.column_config.TextColumn("Title", width="large"),
                    "post_url": st.column_config.LinkColumn("URL", display_text="Open"),
                    "score": st.column_config.NumberColumn("Score", format="%d"),
                    "num_comments": st.column_config.NumberColumn("Replies", format="%d"),
                },
            )
        else:
            st.info("No posts in candidate subreddits yet.")

with col_b:
    with st.container(border=True):
        st.subheader(f"❌ Not Yet Posted ({len(not_yet_df)})", anchor=False)
        if not not_yet_df.empty:
            st.dataframe(
                not_yet_df,
                use_container_width=True,
                height=300,
                column_config={
                    "subreddit": st.column_config.TextColumn("Subreddit"),
                    "subscribers": st.column_config.NumberColumn("Subscribers", format="%d"),
                    "relevance_score": st.column_config.ProgressColumn("Relevance", min_value=0, max_value=10),
                    "tag": st.column_config.TextColumn("Tag"),
                    "min_karma": st.column_config.NumberColumn("Min Karma", format="%d"),
                },
            )
        else:
            st.success("Posted in all candidate subreddits!")

# --- Post Preview ---
if not not_yet_df.empty:
    st.subheader("📋 Post Preview & Copy", anchor=False)
    st.caption("Expand a subreddit to preview your post, copy the text, then mark as posted.")

    for _, row in not_yet_df.iterrows():
        sub_name = row["subreddit"].replace("r/", "")
        title, body = format_for_subreddit(sub_name)
        subs_count = f"{row['subscribers']:,}" if row['subscribers'] > 0 else "?"
        tag_info = f"Tag: {row['tag']}" if row["tag"] != "None" else "No tag"

        with st.expander(f"r/{sub_name} — {subs_count} subs | {tag_info} | relevance: {row['relevance_score']}"):
            st.text_input("Title (copy this):", value=title, key=f"title_{sub_name}", disabled=True)
            st.text_area("Body (copy this):", value=body, key=f"body_{sub_name}", height=150, disabled=True)

            mc1, mc2 = st.columns([2, 1], vertical_alignment="bottom")
            with mc1:
                post_url = st.text_input("Post URL (paste after posting)", key=f"url_{sub_name}", placeholder="https://reddit.com/r/...")
            with mc2:
                if st.button("✅ Mark as posted", key=f"mark_{sub_name}", use_container_width=True):
                    mark_as_posted(uname, sub_name, url=post_url)
                    st.toast(f"Marked r/{sub_name} as posted!")
                    st.rerun()

# --- Discovery ---
st.subheader("🔎 Discover New Subreddits", anchor=False)
st.caption("Search Reddit for relevant subreddits. Claude evaluates each one.")

with st.form("discovery_form"):
    search_query = st.text_input("Search query", value="C++ interview coding career defense")
    discover_btn = st.form_submit_button("🔎 Discover", use_container_width=True)

if discover_btn and search_query:
    with st.status("Discovering subreddits...", expanded=True) as disc_status:
        st.write(f"Searching for: {search_query}")
        discovered_df = discover_and_evaluate(
            query=search_query,
            existing_subs=get_all_candidate_subs(),
            post_topic=POST_TITLE,
            on_status=lambda msg: st.write(msg),
        )
        disc_status.update(label=f"Found {len(discovered_df)} new subreddits", state="complete")
    st.session_state["discovered_df"] = discovered_df

if "discovered_df" in st.session_state:
    discovered_df = st.session_state["discovered_df"]
    if discovered_df.empty:
        st.info("No new subreddits found. Try a different search query.")
    else:
        relevant = discovered_df[discovered_df["relevant"]]
        not_relevant = discovered_df[~discovered_df["relevant"]]

        st.success(f"**{len(relevant)} relevant** / {len(not_relevant)} not relevant")
        if not relevant.empty:
            st.dataframe(
                relevant,
                use_container_width=True,
                column_config={
                    "subreddit": st.column_config.TextColumn("Subreddit"),
                    "subscribers": st.column_config.NumberColumn("Subscribers", format="%d"),
                    "description": st.column_config.TextColumn("Description", width="large"),
                    "confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=10),
                    "reason": st.column_config.TextColumn("Reason", width="medium"),
                },
            )
            if st.button("✅ Approve all relevant", use_container_width=True):
                save_discovered_subs(relevant["subreddit"].tolist(), not_relevant["subreddit"].tolist())
                st.toast(f"Saved {len(relevant)} new subreddits!")
                st.session_state.pop("discovered_df", None)
                st.rerun()
