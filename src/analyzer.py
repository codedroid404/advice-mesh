"""
LLM-powered comment analyzer — sends Reddit replies to Claude for authenticity and usefulness analysis.

Usage:
    from analyzer import analyze_comment, analyze_replies_df
"""

import requests
import pandas as pd
from src.config import CLAUDE_API_KEY, CLAUDE_BASE_URL, CLAUDE_MODEL
from src.logger import get_logger
from src.usage_tracker import track_usage

log = get_logger("analyzer")

HEADERS = {
    "x-api-key": CLAUDE_API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
}

ANALYSIS_PROMPT = """Analyze this Reddit comment replying to a post about preparing for a Shield AI C++ code pair interview.

Post context: Preparing for Senior Applications Engineer, Autonomy role. Final round C++ code pair on HackerRank.

Comment:
\"\"\"{comment}\"\"\"

Respond in this exact format (do not deviate):

Authenticity: [score 1-10]
Usefulness: [score 1-10]
Signals: [what makes it genuine or promotional]
Key_Tips: [semicolon-separated concrete prep tips extracted from the comment, or "None"]
Products: [tools/products mentioned and if organic or forced, or "None"]
Verdict: [Genuine / Likely promotional / Mixed]"""


def analyze_comment(comment_body):
    """
    Send a single comment to Claude for analysis.
    Returns the analysis text, or an error string on failure.
    """
    url = f"{CLAUDE_BASE_URL}/messages"

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 500,
        "messages": [{
            "role": "user",
            "content": ANALYSIS_PROMPT.format(comment=comment_body),
        }],
    }

    try:
        log.debug(f"Sending request to {url} with model {CLAUDE_MODEL}...")
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        log.debug(f"Response status: {resp.status_code}")

        if resp.status_code != 200:
            log.error(f"Claude API error: {resp.status_code} — {resp.text}")
            return f"Error: {resp.status_code}"

        data = resp.json()
        track_usage(data, model=CLAUDE_MODEL)
        return data["content"][0]["text"]

    except Exception as e:
        log.error(f"Analysis failed: {e}")
        return f"Error: {e}"


def _parse_line(analysis_text, prefix):
    """Extract value from a line starting with prefix."""
    for line in analysis_text.split("\n"):
        if line.lower().startswith(prefix.lower()):
            return line.split(":", 1)[1].strip()
    return ""


def parse_score(analysis_text):
    """Extract the authenticity score (1-10) from analysis text."""
    val = _parse_line(analysis_text, "Authenticity:")
    try:
        return int(val.split("/")[0].split()[0])
    except (ValueError, IndexError):
        return 0


def parse_usefulness(analysis_text):
    """Extract the usefulness score (1-10) from analysis text."""
    val = _parse_line(analysis_text, "Usefulness:")
    try:
        return int(val.split("/")[0].split()[0])
    except (ValueError, IndexError):
        return 0


def parse_key_tips(analysis_text):
    """Extract semicolon-separated key tips from analysis text."""
    val = _parse_line(analysis_text, "Key_Tips:")
    if not val or val.lower() == "none":
        return ""
    return val


def analyze_replies_df(replies_df, on_status=None):
    """
    Analyze all replies in a DataFrame using Claude.

    Returns the DataFrame with analysis, authenticity_score, usefulness_score, and key_tips columns.
    """
    if replies_df.empty:
        replies_df["analysis"] = []
        replies_df["authenticity_score"] = []
        replies_df["usefulness_score"] = []
        replies_df["key_tips"] = []
        return replies_df

    log.info(f"Starting analysis of {len(replies_df)} replies using {CLAUDE_MODEL}...")

    analyses = []
    auth_scores = []
    use_scores = []
    tips = []

    for i, (_, row) in enumerate(replies_df.iterrows()):
        body = row["body"]
        author = row.get("author", "unknown")

        if on_status:
            on_status(f"Analyzing reply {i+1}/{len(replies_df)}...")

        if body in ("[deleted]", "[removed]", ""):
            log.debug(f"Skipping deleted/removed comment by {author}")
            analyses.append("Skipped: deleted/removed comment")
            auth_scores.append(0)
            use_scores.append(0)
            tips.append("")
            continue

        log.info(f"Analyzing reply {i+1}/{len(replies_df)} by u/{author}...")
        analysis = analyze_comment(body)

        auth = parse_score(analysis)
        useful = parse_usefulness(analysis)
        key = parse_key_tips(analysis)

        log.info(f"  u/{author} — authenticity: {auth}/10, usefulness: {useful}/10")

        analyses.append(analysis)
        auth_scores.append(auth)
        use_scores.append(useful)
        tips.append(key)

    replies_df = replies_df.copy()
    replies_df["analysis"] = analyses
    replies_df["authenticity_score"] = auth_scores
    replies_df["usefulness_score"] = use_scores
    replies_df["key_tips"] = tips
    return replies_df
