"""Analysis page — batch analyze replies and explore results."""

import streamlit as st
from src import config
from src.shared import require_scrape, render_sidebar, save_analysis
from src.analyzer import analyze_replies_df

st.set_page_config(page_title="Analysis", page_icon="🤖", layout="wide")
render_sidebar()
require_scrape()

replies_df = st.session_state["replies_df"]
uname = st.session_state["username"]

st.title("🤖 Analysis")

if replies_df.empty:
    st.info("No replies to analyze.")
    st.stop()

# --- Analyze button ---
if st.button("🤖 Analyze All Replies", type="primary", use_container_width=True):
    with st.status(f"Analyzing {len(replies_df)} replies with {config.CLAUDE_MODEL}...", expanded=True) as status:
        analyzed_df = analyze_replies_df(replies_df, on_status=lambda msg: st.write(msg))
        status.update(label=f"Analyzed {len(replies_df)} replies", state="complete")

    st.session_state["analyzed_df"] = analyzed_df
    save_analysis(uname, analyzed_df.to_dict("records"))

if "analyzed_df" not in st.session_state:
    st.info("Click the button above to analyze all replies with Claude.", icon="👆")
    st.stop()

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
        sort_by = st.selectbox("Sort by", ["Usefulness", "Authenticity", "Reddit score"])
    with fc2:
        min_auth = st.slider("Min authenticity", 0, 10, 0)
    with fc3:
        min_useful = st.slider("Min usefulness", 0, 10, 0)

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

# --- Replies ---
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
    use_container_width=True,
)
