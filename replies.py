"""
Reply fetcher — fetches comments on a user's posts via Reddit's public JSON API.

Usage:
    from replies import fetch_replies
    replies_df = fetch_replies(posts_df)
"""

import time
import requests
import pandas as pd
from logger import get_logger

log = get_logger("replies")

USER_AGENT = "CommunityScraperBot/1.0"


def _fetch_post_comments(post_id, post_url, max_depth=1):
    """Fetch top-level comments for a single post."""
    url = f"https://www.reddit.com/comments/{post_id}.json"
    headers = {"User-Agent": USER_AGENT}

    try:
        resp = requests.get(url, headers=headers, params={"raw_json": 1, "limit": 100}, timeout=10)

        if resp.status_code == 429:
            log.warning("Rate limited — waiting 60s...")
            time.sleep(60)
            resp = requests.get(url, headers=headers, params={"raw_json": 1, "limit": 100}, timeout=10)

        if resp.status_code != 200:
            log.warning(f"Could not fetch comments for {post_id}: HTTP {resp.status_code}")
            return []

        data = resp.json()
        if len(data) < 2:
            return []

        comments = []
        children = data[1].get("data", {}).get("children", [])
        # Automod messages to filter out
        automod_phrases = [
            "submission has been automatically removed",
            "does not include one of the required tags",
            "your post has been removed",
            "this action was performed automatically",
        ]

        for child in children:
            if child.get("kind") != "t1":
                continue
            c = child["data"]
            body = c.get("body", "")

            # Skip automod removal notices
            if any(phrase in body.lower() for phrase in automod_phrases):
                log.debug(f"Filtered automod message in {post_id}")
                continue

            comments.append({
                "post_id": post_id,
                "post_url": post_url,
                "author": c.get("author", "[deleted]"),
                "body": c.get("body", ""),
                "score": c.get("score", 0),
                "created_utc": c.get("created_utc", 0),
                "comment_id": c.get("id", ""),
                "permalink": f"https://reddit.com{c.get('permalink', '')}",
            })

        return comments

    except Exception as e:
        log.error(f"Failed to fetch comments for {post_id}: {e}")
        return []


def fetch_replies(posts_df, on_status=None):
    """
    Fetch replies for all posts in the DataFrame.

    Args:
        posts_df: DataFrame with 'post_id' and 'post_url' columns
        on_status: Optional callback for progress updates

    Returns:
        DataFrame of all replies across all posts
    """
    if posts_df.empty:
        return pd.DataFrame(columns=[
            "post_id", "post_url", "author", "body", "score",
            "created_utc", "comment_id", "permalink",
        ])

    all_comments = []

    for i, (_, post) in enumerate(posts_df.iterrows()):
        post_id = post["post_id"]
        post_url = post.get("post_url", "")

        if on_status:
            on_status(f"Fetching replies... {i+1}/{len(posts_df)} (post: {post_id})")

        comments = _fetch_post_comments(post_id, post_url)
        all_comments.extend(comments)

        time.sleep(2)

    df = pd.DataFrame(all_comments)
    if not df.empty:
        df = df.sort_values("score", ascending=False).reset_index(drop=True)
        df.index += 1

    log.info(f"Fetched {len(df)} replies across {len(posts_df)} posts")
    return df
