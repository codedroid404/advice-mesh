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
    """Show a message and stop if no Reddit search has been run yet."""
    if not st.session_state.get("searched"):
        st.info(
            "No data yet. Go to the **Home** page, upload a JD, and search Reddit first.",
            icon="👈",
        )
        st.stop()


def get_active_model():
    """Return the model selected in the sidebar (falls back to the config default)."""
    return st.session_state.get("model", config.CLAUDE_MODEL)


def render_sidebar():
    """Render the shared sidebar across all pages."""
    import os
    _logo = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "logo.svg")
    if os.path.exists(_logo):
        st.logo(_logo, size="large")
    with st.sidebar:
        st.header("🕸️ AdviceMesh")

        with st.container(border=True):
            st.subheader("Model", anchor=False)
            _ids = list(config.MODEL_OPTIONS.keys())
            # Default to Haiku — cheapest/fastest for bulk reply analysis.
            _default = "claude-haiku-4-5" if "claude-haiku-4-5" in _ids else (
                config.CLAUDE_MODEL if config.CLAUDE_MODEL in _ids else _ids[0]
            )
            st.selectbox(
                "Claude model",
                _ids,
                index=_ids.index(_default),
                format_func=lambda i: config.MODEL_OPTIONS.get(i, i),
                key="model",
                label_visibility="collapsed",
            )

        with st.container(border=True):
            st.subheader("Appearance", anchor=False)
            _themes = {
                "Indigo (light)":  {"bg": "#eef0f6", "sec": "#e3e6f0", "text": "#24293a", "accent": "#5b6cf0"},
                "Slate (light)":   {"bg": "#eef1f5", "sec": "#e1e5ed", "text": "#1f2430", "accent": "#475569"},
                "Emerald (light)": {"bg": "#ecf2ef", "sec": "#dce9e3", "text": "#1f2a26", "accent": "#0f9d6b"},
                "Rose (light)":    {"bg": "#f5eef1", "sec": "#ecdfe5", "text": "#2a1f24", "accent": "#e11d48"},
                "Midnight (dark)": {"bg": "#0f1117", "sec": "#171a23", "text": "#e6e9f2", "accent": "#818cf8"},
                "Carbon (dark)":   {"bg": "#101418", "sec": "#181d25", "text": "#e3e8ef", "accent": "#22d3ee"},
            }
            _t = _themes[st.selectbox(
                "Theme", list(_themes), key="accent", label_visibility="collapsed"
            )]

        # Full-palette runtime theme override (background + sidebar + text + accent).
        _bg, _sec, _text, _accent = _t["bg"], _t["sec"], _t["text"], _t["accent"]
        st.markdown(
            f"""<style>
            .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"],
            [data-testid="stBottomBlockContainer"] {{ background-color: {_bg} !important; }}
            [data-testid="stSidebar"] {{ background-color: {_sec} !important; }}
            .stApp, .stMarkdown, p, span, label, li, h1, h2, h3, h4,
            [data-testid="stMetricValue"], [data-testid="stMetricLabel"],
            [data-testid="stWidgetLabel"] {{ color: {_text} !important; }}
            .stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div {{
                background-color: {_sec} !important; color: {_text} !important;
                border: 1px solid rgba(128,128,128,0.35) !important; border-radius: 8px !important;
            }}
            /* make sidebar bordered containers (Model, API Usage, Data) visible —
               they already have a faint border; just recolor it to the accent. */
            [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
                border-color: {_accent}66 !important;
            }}
            :root {{ --primary-color: {_accent} !important; }}
            .stButton button[kind="primary"], button[data-testid="stBaseButton-primary"],
            button[data-testid="baseButton-primary"], .stDownloadButton button[kind="primary"] {{
                background-color: {_accent} !important; border-color: {_accent} !important; color: #fff !important;
            }}
            .stTabs button[aria-selected="true"] {{ color: {_accent} !important; }}
            .stTabs [data-baseweb="tab-highlight"] {{ background-color: {_accent} !important; }}
            a, .stMarkdown a {{ color: {_accent} !important; }}
            [data-testid="stSlider"] [role="slider"] {{ background-color: {_accent} !important; }}
            [data-testid="stSlider"] [data-baseweb="slider"] > div > div {{ background: {_accent} !important; }}
            [data-testid="stProgress"] > div > div > div > div {{ background-color: {_accent} !important; }}
            </style>""",
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            st.subheader("API Usage", anchor=False)
            total_usage = get_total_usage(model=get_active_model())
            session_usage = get_session_usage()

            u1, u2 = st.columns(2)
            cost = total_usage.get('cost_usd', total_usage.get('cost', 0.0))
            u1.metric("Cost", f"${cost:.4f}")
            u2.metric("Calls", total_usage['requests'])
            st.caption(f"{total_usage['input_tokens']:,} in / {total_usage['output_tokens']:,} out tokens")
            if session_usage['requests'] > 0:
                session_cost = session_usage.get('cost_usd', session_usage.get('cost', 0.0))
                st.caption(f"Session: {session_usage['requests']} calls | ${session_cost:.4f}")

            # Audit trail — last few AI calls (model · tokens · time).
            with st.expander("🧾 Audit log"):
                _path = os.path.join(DATA_DIR, "api_usage.jsonl")
                if os.path.exists(_path):
                    with open(_path, encoding="utf-8") as _fh:
                        _lines = _fh.readlines()[-8:]
                    for _ln in reversed(_lines):
                        try:
                            _r = json.loads(_ln)
                            _ts = str(_r.get("timestamp", ""))[11:19]
                            st.caption(
                                f"{_ts} · `{_r.get('model', '?')}` · "
                                f"{_r.get('input_tokens', 0)}→{_r.get('output_tokens', 0)} tok"
                            )
                        except (ValueError, KeyError):
                            pass
                else:
                    st.caption("No AI calls yet.")

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
