"""
Shared helpers for the multipage Streamlit app.
Handles session state checks, persistence, and caching.
"""

import json
import os
import streamlit as st
from datetime import datetime, timezone

from src import config
from src.usage_tracker import get_session_usage, get_total_usage

DATA_DIR = "data"
ANALYSIS_CACHE = os.path.join(DATA_DIR, "analysis_cache.json")


def require_scrape():
    """Show a message and stop if no data has been scraped yet."""
    if not st.session_state.get("scraped"):
        st.info("No data yet. Go to the **Home** page and scrape a Reddit user first.", icon="👈")
        st.stop()


def render_sidebar():
    """Render the shared sidebar across all pages."""
    with st.sidebar:
        st.header("🕸️ AdviceMesh")

        with st.container(border=True):
            st.subheader("Model", anchor=False)
            st.code(config.CLAUDE_MODEL, language=None)
            st.caption(config.CLAUDE_BASE_URL)

        with st.container(border=True):
            st.subheader("API Usage", anchor=False)
            total_usage = get_total_usage(model=config.CLAUDE_MODEL)
            session_usage = get_session_usage()

            u1, u2 = st.columns(2)
            cost = total_usage.get('cost_usd', total_usage.get('cost', 0.0))
            u1.metric("Cost", f"${cost:.4f}")
            u2.metric("Calls", total_usage['requests'])
            st.caption(f"{total_usage['input_tokens']:,} in / {total_usage['output_tokens']:,} out tokens")
            if session_usage['requests'] > 0:
                session_cost = session_usage.get('cost_usd', session_usage.get('cost', 0.0))
                st.caption(f"Session: {session_usage['requests']} calls | ${session_cost:.4f}")

        with st.container(border=True):
            st.subheader("Data", anchor=False)
            if st.button("🗑️ Clear cached data", width="stretch"):
                # Clear session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                # Clear data files
                import glob
                for f in glob.glob(os.path.join(DATA_DIR, "*.json")):
                    os.remove(f)
                st.toast("All cached data cleared!")
                st.rerun()

        st.caption("Built with Streamlit + Claude API")


def save_analysis(username, analyzed_records):
    os.makedirs(DATA_DIR, exist_ok=True)
    cache = load_analysis_cache()
    cache[username] = analyzed_records
    with open(ANALYSIS_CACHE, "w") as f:
        json.dump(cache, f, indent=2, default=str)


def load_analysis_cache():
    if os.path.exists(ANALYSIS_CACHE):
        with open(ANALYSIS_CACHE, "r") as f:
            return json.load(f)
    return {}


def save_qa(uname, question, answer, num_replies):
    qa_file = os.path.join(DATA_DIR, "qa_log.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    qa_log = []
    if os.path.exists(qa_file):
        with open(qa_file, "r") as f:
            qa_log = json.load(f)
    qa_log.append({
        "username": uname,
        "question": question,
        "answer": answer,
        "num_replies": num_replies,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    with open(qa_file, "w") as f:
        json.dump(qa_log, f, indent=2)
