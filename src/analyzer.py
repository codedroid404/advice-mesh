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

def _build_prompt(comment_body, job_context="", interview_stage=""):
    """Build the analysis prompt with optional job context."""
    context_section = ""
    if job_context or interview_stage:
        parts = []
        if job_context:
            parts.append(f"Job description:\n{job_context[:2000]}")
        if interview_stage:
            parts.append(f"Interview stage: {interview_stage}")
        context_section = f"\n{chr(10).join(parts)}\n"

    return f"""Analyze this Reddit comment replying to an interview preparation post.
{context_section}
Comment:
\"\"\"{comment_body}\"\"\"

Respond in this exact format (do not deviate):

Authenticity: [score 1-10]
Usefulness: [score 1-10]
Signals: [what makes it genuine or promotional]
Key_Tips: [semicolon-separated concrete prep tips extracted from the comment, or "None"]
Products: [tools/products mentioned and if organic or forced, or "None"]
Verdict: [Genuine / Likely promotional / Mixed]"""


def analyze_comment(comment_body, job_context="", interview_stage=""):
    """
    Send a single comment to Claude for analysis.
    Returns the analysis text, or an error string on failure.
    """
    url = f"{CLAUDE_BASE_URL}/messages"
    prompt = _build_prompt(comment_body, job_context, interview_stage)

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 500,
        "messages": [{"role": "user", "content": prompt}],
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


def filter_relevant_subs(subreddits, job_context="", interview_stage=""):
    """
    Use Claude to filter a list of subreddits to only those relevant to the job/interview context.
    Returns a list of relevant subreddit names.
    Falls back to returning all subs if Claude fails or no context is provided.
    """
    if not subreddits:
        return []

    # If no context, return all — can't filter without knowing what's relevant
    if not job_context and not interview_stage:
        log.info("No job context — skipping LLM filter, returning all subs")
        return list(subreddits)

    context = ""
    if job_context:
        context += f"Job description:\n{job_context[:1500]}\n\n"
    if interview_stage:
        context += f"Interview stage: {interview_stage}\n\n"

    sub_list = ", ".join(subreddits)

    prompt = f"""{context}Here is a list of subreddits a user has posted or commented in:
{sub_list}

Return ONLY the subreddit names that are relevant to this job search or interview preparation.
Include career, technical, interview, job hunting, and industry-specific subreddits.
Exclude completely unrelated ones (skincare, gaming, hobbies, etc).

Respond with just the subreddit names separated by commas, nothing else."""

    url = f"{CLAUDE_BASE_URL}/messages"
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        log.info(f"Asking Claude to filter {len(subreddits)} subreddits...")
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=15)

        if resp.status_code != 200:
            log.warning(f"Claude filter failed: {resp.status_code} — returning all subs")
            return list(subreddits)

        data = resp.json()
        track_usage(data, model=CLAUDE_MODEL)
        response_text = data["content"][0]["text"]

        # Parse comma-separated subreddit names
        relevant = [s.strip().removeprefix("r/") for s in response_text.split(",") if s.strip()]
        # Only keep subs that were in the original list (case-insensitive)
        original_lower = {s.lower(): s for s in subreddits}
        filtered = [original_lower[r.lower()] for r in relevant if r.lower() in original_lower]

        log.info(f"Claude kept {len(filtered)}/{len(subreddits)} subreddits as relevant")
        return filtered if filtered else list(subreddits)

    except Exception as e:
        log.warning(f"Claude filter error: {e} — returning all subs")
        return list(subreddits)


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


def analyze_replies_df(replies_df, on_status=None, job_context="", interview_stage=""):
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
        analysis = analyze_comment(body, job_context=job_context, interview_stage=interview_stage)

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
