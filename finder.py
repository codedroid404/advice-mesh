"""
Subreddit finder — fetches metadata for candidate subs and cross-checks against user history.

Usage:
    from finder import fetch_sub_metadata, cross_check
"""

import time
import requests
import pandas as pd
import streamlit as st
from logger import get_logger
from subreddit_config import CANDIDATE_SUBS, SUB_CONFIG, get_all_candidate_subs

log = get_logger("finder")

USER_AGENT = "CommunityScraperBot/1.0"

# Keywords used to score relevance to the Shield AI interview topic
RELEVANCE_KEYWORDS = [
    "interview", "c++", "cpp", "coding", "leetcode", "hackerrank",
    "career", "job", "engineer", "defense", "autonomous", "robotics",
    "embedded", "aerospace", "shield ai", "hiring", "resume",
]


@st.cache_data(ttl=300, show_spinner=False)
def fetch_sub_metadata(subs=None, on_status=None):
    """
    Fetch metadata for each candidate subreddit via Reddit's public JSON API.

    Returns a DataFrame with: subreddit, subscribers, description, relevance_score, tag, min_karma
    """
    subs = subs or get_all_candidate_subs()
    rows = []

    for i, sub in enumerate(subs):
        if on_status:
            on_status(f"Fetching metadata... r/{sub} ({i+1}/{len(subs)})")

        url = f"https://www.reddit.com/r/{sub}/about.json"
        headers = {"User-Agent": USER_AGENT}

        try:
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 429:
                log.warning("Rate limited — waiting 60s...")
                time.sleep(60)
                resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code != 200:
                log.warning(f"Could not fetch r/{sub}: HTTP {resp.status_code}")
                rows.append({
                    "subreddit": sub,
                    "subscribers": 0,
                    "description": f"Error: HTTP {resp.status_code}",
                    "relevance_score": 0,
                    "tag": SUB_CONFIG.get(sub, {}).get("tag"),
                    "min_karma": SUB_CONFIG.get(sub, {}).get("min_karma", 0),
                })
                time.sleep(2)
                continue

            data = resp.json().get("data", {})
            description = data.get("public_description", "") or data.get("description", "") or ""
            subscribers = data.get("subscribers", 0) or 0

            # Score relevance based on keyword matches in description + display name
            text = f"{sub} {data.get('title', '')} {description}".lower()
            relevance = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text)

            sub_config = SUB_CONFIG.get(sub, {})
            rows.append({
                "subreddit": sub,
                "subscribers": subscribers,
                "description": description[:200],
                "relevance_score": relevance,
                "tag": sub_config.get("tag"),
                "min_karma": sub_config.get("min_karma", 0),
            })

        except Exception as e:
            log.error(f"Failed to fetch r/{sub}: {e}")
            rows.append({
                "subreddit": sub,
                "subscribers": 0,
                "description": f"Error: {e}",
                "relevance_score": 0,
                "tag": SUB_CONFIG.get(sub, {}).get("tag"),
                "min_karma": SUB_CONFIG.get(sub, {}).get("min_karma", 0),
            })

        time.sleep(2)

    df = pd.DataFrame(rows)
    df = df.sort_values(["relevance_score", "subscribers"], ascending=[False, False]).reset_index(drop=True)
    df.index += 1
    log.info(f"Fetched metadata for {len(df)} subreddits")
    return df


def cross_check(posts_df, candidates_df, manually_posted=None):
    """
    Cross-check user's post history against candidate subreddits.

    Args:
        posts_df: DataFrame of user's posts
        candidates_df: DataFrame of candidate subreddits
        manually_posted: Optional set of subreddit names (lowercase) marked as posted via posting log

    Returns:
        already_posted_df — candidates where the user has posted (with post details)
        not_posted_df — candidates where the user hasn't posted yet
    """
    if posts_df.empty:
        posted_subs = set()
    else:
        posted_subs = set(posts_df["subreddit"].str.lower())

    if manually_posted:
        posted_subs = posted_subs | manually_posted

    already = []
    not_yet = []

    for _, row in candidates_df.iterrows():
        sub = row["subreddit"]
        if sub.lower() in posted_subs:
            # Find the user's posts in this sub
            user_posts = posts_df[posts_df["subreddit"].str.lower() == sub.lower()]
            for _, post in user_posts.iterrows():
                already.append({
                    "subreddit": f"r/{sub}",
                    "title": post.get("title", ""),
                    "post_url": post.get("post_url", ""),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                })
        else:
            not_yet.append({
                "subreddit": f"r/{sub}",
                "subscribers": row["subscribers"],
                "relevance_score": row["relevance_score"],
                "tag": row["tag"] or "None",
                "min_karma": row["min_karma"],
            })

    already_df = pd.DataFrame(already) if already else pd.DataFrame(
        columns=["subreddit", "title", "post_url", "score", "num_comments"]
    )
    not_yet_df = pd.DataFrame(not_yet) if not_yet else pd.DataFrame(
        columns=["subreddit", "subscribers", "relevance_score", "tag", "min_karma"]
    )

    not_yet_df = not_yet_df.sort_values(
        ["relevance_score", "subscribers"], ascending=[False, False]
    ).reset_index(drop=True)
    not_yet_df.index += 1

    return already_df, not_yet_df
