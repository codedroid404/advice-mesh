"""Replies page — view replies, quick analysis, and chat with Claude about advice."""

import streamlit as st
import requests as _req

import config
from shared import require_scrape, render_sidebar, save_qa
from analyzer import analyze_comment, parse_score, parse_usefulness, parse_key_tips
from usage_tracker import track_usage

st.set_page_config(page_title="Replies", page_icon="📩", layout="wide")
render_sidebar()
require_scrape()

replies_df = st.session_state["replies_df"]
uname = st.session_state["username"]

st.title("📩 Replies")

if replies_df.empty:
    st.info("No replies found. Try adjusting keywords in the sidebar on the Home page.")
    st.stop()

# --- Replies table ---
st.caption(f"{len(replies_df)} replies on your matching posts")
st.dataframe(
    replies_df,
    use_container_width=True,
    height=350,
    column_config={
        "author": st.column_config.TextColumn("Author", width="small"),
        "body": st.column_config.TextColumn("Comment", width="large"),
        "score": st.column_config.NumberColumn("Score", format="%d"),
        "post_url": st.column_config.LinkColumn("Post", display_text="Open"),
        "permalink": st.column_config.LinkColumn("Link", display_text="Open"),
        "post_id": st.column_config.TextColumn("Post ID", width="small"),
        "created_utc": st.column_config.NumberColumn("Created (UTC)", format="%d"),
        "comment_id": st.column_config.TextColumn("ID", width="small"),
    },
)

# --- Quick Analysis ---
st.subheader("🤖 Quick Analysis", anchor=False)
st.caption("Select a reply and analyze it with Claude.")

reply_options = {}
for _, r in replies_df.iterrows():
    label = f"u/{r['author']} — {r['body'][:80]}..."
    reply_options[label] = r

selected_label = st.selectbox("Select a reply", list(reply_options.keys()), key="reply_select")

if st.button("Analyze this reply", key="quick_analyze_btn", use_container_width=True):
    selected = reply_options[selected_label]
    with st.spinner(f"Analyzing u/{selected['author']}..."):
        analysis = analyze_comment(selected["body"])

    if "credit balance" in analysis.lower():
        st.error("No Anthropic credits.", icon="💳")
    elif analysis.startswith("Error:"):
        st.error(analysis)
    else:
        auth = parse_score(analysis)
        useful = parse_usefulness(analysis)
        tips = parse_key_tips(analysis)
        icon = "🟢" if auth >= 8 else ("🟡" if auth >= 5 else "🔴")

        with st.container(border=True):
            q1, q2 = st.columns(2)
            q1.metric(f"{icon} Authenticity", f"{auth}/10")
            q2.metric("Usefulness", f"{useful}/10")
            if tips and tips.lower() != "none":
                st.info(f"**Tips:** {tips}")

        with st.expander("Full analysis", expanded=True):
            st.markdown(analysis)
        st.link_button("View on Reddit", selected['permalink'])

# --- Chat about replies ---
st.subheader("💬 Ask About All Replies", anchor=False)
st.caption("Chat with Claude about the advice you've received.")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Display chat history
for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
user_question = st.chat_input("Ask about the advice you received...")

if user_question:
    # Add user message to history
    st.session_state["chat_history"].append({"role": "user", "content": user_question})
    with st.chat_message("user"):
        st.markdown(user_question)

    # Build context from replies
    reply_context = "\n\n".join(
        f"u/{r['author']} (score: {r['score']}): {r['body'][:500]}"
        for _, r in replies_df.iterrows()
        if r["body"] not in ("[deleted]", "[removed]", "")
    )

    # Build conversation for Claude (include history for context)
    messages = []
    system_context = f"""You are analyzing Reddit replies about preparing for a Shield AI C++ code pair interview.

Here are {len(replies_df)} replies for context:

{reply_context}

Answer questions about these replies. Be specific and reference which users gave relevant advice."""

    # Add conversation history
    for msg in st.session_state["chat_history"]:
        if msg["role"] == "user" and msg == st.session_state["chat_history"][0]:
            # First user message gets the system context prepended
            messages.append({"role": "user", "content": f"{system_context}\n\nQuestion: {msg['content']}"})
        else:
            messages.append(msg)

    # If this isn't the first message, prepend context to the latest message
    if len(st.session_state["chat_history"]) > 1 and messages:
        messages[-1] = {"role": "user", "content": f"{system_context}\n\nQuestion: {user_question}"}

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            headers = {
                "x-api-key": config.CLAUDE_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            resp = _req.post(
                f"{config.CLAUDE_BASE_URL}/messages",
                headers=headers,
                json={
                    "model": config.CLAUDE_MODEL,
                    "max_tokens": 1000,
                    "messages": messages,
                },
                timeout=30,
            )

        if resp.status_code == 200:
            resp_data = resp.json()
            track_usage(resp_data, model=config.CLAUDE_MODEL)
            answer = resp_data["content"][0]["text"]
            st.markdown(answer)
            st.session_state["chat_history"].append({"role": "assistant", "content": answer})
            save_qa(uname, user_question, answer, len(replies_df))
        else:
            st.error(f"Claude API error: {resp.status_code}")
