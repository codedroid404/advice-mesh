"""Replies & Analysis — view replies, analyze with Claude, and chat about advice."""

import streamlit as st
import requests as _req

from src import config
from src.shared import require_scrape, render_sidebar, save_qa, save_analysis
from src.analyzer import (
    analyze_comment,
    analyze_replies_df,
    parse_score,
    parse_usefulness,
    parse_key_tips,
)
from src.usage_tracker import track_usage

st.set_page_config(page_title="Replies & Analysis", page_icon="📩", layout="wide")
render_sidebar()
require_scrape()

replies_df = st.session_state["replies_df"]
uname = st.session_state["username"]

st.title("📩 Replies & Analysis")

if replies_df.empty:
    st.info("No replies found. Scrape a user on the Home page first.")
    st.stop()

st.caption(f"{len(replies_df)} replies for u/{uname}")

# =============================================
# TABS
# =============================================
tab_replies, tab_analysis, tab_chat = st.tabs([
    "📩 Replies",
    "🤖 Batch Analysis",
    "💬 Chat",
])

# ==================== TAB 1: Replies ====================
with tab_replies:
    st.dataframe(
        replies_df,
        width="stretch",
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

    selected_label = st.selectbox(
        "Select a reply",
        list(reply_options.keys()),
        key="reply_select",
    )

    if st.button("Analyze this reply", key="quick_analyze_btn", width="stretch"):
        selected = reply_options[selected_label]
        with st.spinner(f"Analyzing u/{selected['author']}..."):
            analysis = analyze_comment(
                selected["body"],
                job_context=st.session_state.get("job_description", ""),
                interview_stage=st.session_state.get("interview_stage", ""),
            )

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

# ==================== TAB 2: Batch Analysis ====================
with tab_analysis:
    if st.button("🤖 Analyze All Replies", type="primary", key="batch_analyze_btn", width="stretch"):
        reply_count = len(replies_df)

        with st.status(f"Analyzing {reply_count} replies with {config.CLAUDE_MODEL}...", expanded=True) as status:
            progress_bar = st.progress(0, text="Starting...")

            def on_analysis_status(msg):
                st.write(msg)
                try:
                    parts = msg.split()
                    fraction = parts[2].split("/")
                    current = int(fraction[0])
                    progress_bar.progress(
                        current / reply_count,
                        text=f"Reply {current}/{reply_count}",
                    )
                except (IndexError, ValueError):
                    pass

            analyzed_df = analyze_replies_df(
                replies_df,
                on_status=on_analysis_status,
                job_context=st.session_state.get("job_description", ""),
                interview_stage=st.session_state.get("interview_stage", ""),
            )

            progress_bar.progress(1.0, text="Complete!")
            status.update(label=f"✅ Analyzed {reply_count} replies", state="complete")

        st.session_state["analyzed_df"] = analyzed_df
        save_analysis(uname, analyzed_df.to_dict("records"))

    if "analyzed_df" not in st.session_state:
        st.info("Click the button above to analyze all replies with Claude.", icon="👆")
    else:
        analyzed_df = st.session_state["analyzed_df"]

        if "usefulness_score" not in analyzed_df.columns:
            analyzed_df["usefulness_score"] = 0
        if "key_tips" not in analyzed_df.columns:
            analyzed_df["key_tips"] = ""

        # --- Summary metrics ---
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

        # --- Filters ---
        with st.container(border=True):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                sort_by = st.selectbox("Sort by", ["Usefulness", "Authenticity", "Reddit score"], key="analysis_sort")
            with fc2:
                min_auth = st.slider("Min authenticity", 0, 10, 0, key="min_auth_slider")
            with fc3:
                min_useful = st.slider("Min usefulness", 0, 10, 0, key="min_useful_slider")

        filtered = analyzed_df[
            (analyzed_df["authenticity_score"] >= min_auth) &
            (analyzed_df["usefulness_score"] >= min_useful)
        ]
        sort_map = {"Usefulness": "usefulness_score", "Authenticity": "authenticity_score", "Reddit score": "score"}
        filtered = filtered.sort_values(sort_map[sort_by], ascending=False)

        # --- Top Tips ---
        all_tips = []
        for _, r in filtered.iterrows():
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
                st.subheader(f"💡 Top {len(unique_tips)} Tips", anchor=False)
                for i, tip in enumerate(unique_tips[:15], 1):
                    st.markdown(f"**{i}.** {tip}")

        # --- Individual replies ---
        st.caption(f"Showing {len(filtered)} of {len(analyzed_df)} replies")

        for _, row in filtered.iterrows():
            icon = "🟢" if row["authenticity_score"] >= 8 else ("🟡" if row["authenticity_score"] >= 5 else "🔴")

            with st.expander(f"{icon} u/{row['author']} — auth: {row['authenticity_score']}/10 | useful: {row['usefulness_score']}/10"):
                st.markdown(row['body'][:500])

                col_r1, col_r2, col_r3 = st.columns(3)
                col_r1.metric("Reddit Score", row['score'])
                col_r2.metric("Authenticity", f"{row['authenticity_score']}/10")
                col_r3.metric("Usefulness", f"{row['usefulness_score']}/10")

                if row.get("key_tips") and str(row["key_tips"]).lower() != "none":
                    st.info(f"**Tips:** {row['key_tips']}")

                with st.expander("Full analysis"):
                    st.markdown(row["analysis"])

                st.link_button("View on Reddit", row['permalink'])

        # --- Export ---
        export_data = filtered[["author", "body", "score", "authenticity_score", "usefulness_score", "key_tips", "permalink"]].copy()
        export_data["body"] = export_data["body"].str[:200]
        st.download_button(
            "⬇️ Export Analysis CSV",
            export_data.to_csv(index=False),
            f"{uname}_analysis.csv",
            "text/csv",
            width="stretch",
            key="export_csv_btn",
        )

# ==================== TAB 3: Chat ====================
with tab_chat:
    st.caption("Chat with Claude about the advice you've received.")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Display chat history with download buttons on assistant messages
    for i, msg in enumerate(st.session_state["chat_history"]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                st.download_button(
                    "⬇️ Download",
                    data=msg["content"],
                    file_name=f"advicemesh_response_{i}.md",
                    mime="text/markdown",
                    key=f"dl_history_{i}",
                )

    # Chat input
    user_question = st.chat_input("Ask about the advice you received...")

    if user_question:
        st.session_state["chat_history"].append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.markdown(user_question)

        # Build context
        reply_context = "\n\n".join(
            f"u/{r['author']} (score: {r['score']}): {r['body'][:500]}"
            for _, r in replies_df.iterrows()
            if r["body"] not in ("[deleted]", "[removed]", "")
        )

        job_desc = st.session_state.get("job_description", "")
        stage = st.session_state.get("interview_stage", "")
        extra = ""
        if job_desc:
            extra += f"\nJob description:\n{job_desc[:2000]}\n"
        if stage:
            extra += f"\nInterview stage: {stage}\n"

        system_context = f"""You are analyzing Reddit replies to an interview preparation post.
{extra}
Here are {len(replies_df)} replies for context:

{reply_context}

Answer questions about these replies. Be specific and reference which users gave relevant advice."""

        # Build messages with context on latest message
        messages = []
        for msg in st.session_state["chat_history"]:
            messages.append(msg)
        if messages:
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

                # Download button for this response
                st.download_button(
                    "⬇️ Download as Markdown",
                    data=f"# {user_question}\n\n{answer}",
                    file_name=f"{user_question[:30].replace(' ', '_')}.md",
                    mime="text/markdown",
                    key=f"dl_{len(st.session_state['chat_history'])}",
                )
            else:
                st.error(f"Claude API error: {resp.status_code}")
