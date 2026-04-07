"""
Reddit Scraper — fetches a user's full post and comment history via Reddit's public JSON API.

Usage:
    from scraper import scrape_user
    posts_df, comments_df = scrape_user("poppinlavish")
"""

import time
import requests
import pandas as pd
import streamlit as st
from src.logger import get_logger

log = get_logger("scraper")

USER_AGENT = "CommunityScraperBot/1.0"


def _fetch_listing(username, kind="submitted", on_status=None):
    """
    Fetch all items from a user's submitted posts or comments.
    Returns a list of raw Reddit 'data' dicts.
    """
    url = f"https://www.reddit.com/user/{username}/{kind}.json"
    headers = {"User-Agent": USER_AGENT}
    items = []
    after = None
    page = 0

    while True:
        params = {"limit": 100, "raw_json": 1}
        if after:
            params["after"] = after

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10)

            if resp.status_code == 429:
                log.warning("Rate limited — waiting 60s...")
                if on_status:
                    on_status("Rate limited — waiting 60s...")
                time.sleep(60)
                continue

            if resp.status_code == 404:
                log.error(f"User not found: u/{username}")
                return None

            if resp.status_code != 200:
                log.error(f"HTTP {resp.status_code} fetching {kind}")
                return None

            data = resp.json().get("data", {})
            children = data.get("children", [])
            if not children:
                break

            for child in children:
                items.append(child["data"])

            page += 1
            if on_status:
                on_status(f"Fetching {kind}... page {page} ({len(items)} items)")

            after = data.get("after")
            if not after:
                break

            time.sleep(2)

        except Exception as e:
            log.error(f"Request failed: {e}")
            return None

    log.info(f"Fetched {len(items)} {kind} for u/{username}")
    return items


def _posts_to_df(items):
    """Convert raw post data to a DataFrame with relevant columns."""
    rows = []
    for item in items:
        rows.append({
            "subreddit": item.get("subreddit", "unknown"),
            "title": item.get("title", ""),
            "post_url": f"https://reddit.com{item.get('permalink', '')}",
            "score": item.get("score", 0),
            "num_comments": item.get("num_comments", 0),
            "created_utc": item.get("created_utc", 0),
            "post_id": item.get("id", ""),
        })
    return pd.DataFrame(rows)


def _comments_to_df(items):
    """Convert raw comment data to a DataFrame with relevant columns."""
    rows = []
    for item in items:
        rows.append({
            "subreddit": item.get("subreddit", "unknown"),
            "body": item.get("body", ""),
            "post_title": item.get("link_title", ""),
            "post_url": f"https://reddit.com{item.get('permalink', '')}",
            "score": item.get("score", 0),
            "created_utc": item.get("created_utc", 0),
            "comment_id": item.get("id", ""),
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300, show_spinner=False)
def scrape_user(username, on_status=None):
    """
    Scrape a Reddit user's full history.

    Args:
        username: Reddit username (without u/ prefix)
        on_status: Optional callback for progress updates, e.g. on_status("Fetching posts... page 2")

    Returns:
        (posts_df, comments_df) — two DataFrames, or (None, None) on failure
    """
    username = username.strip().lstrip("u/").lstrip("/")

    log.info(f"Scraping u/{username}...")

    post_items = _fetch_listing(username, "submitted", on_status)
    if post_items is None:
        return None, None

    comment_items = _fetch_listing(username, "comments", on_status)
    if comment_items is None:
        return None, None

    posts_df = _posts_to_df(post_items) if post_items else pd.DataFrame()
    comments_df = _comments_to_df(comment_items) if comment_items else pd.DataFrame()

    log.info(f"Done: {len(posts_df)} posts, {len(comments_df)} comments")
    return posts_df, comments_df


def summarize_subreddits(posts_df, comments_df):
    """
    Build a summary DataFrame of subreddits with post/comment counts.
    Used for the overview display in the app.
    """
    subs = {}

    if not posts_df.empty:
        for sub, count in posts_df["subreddit"].value_counts().items():
            subs.setdefault(sub, {"posts": 0, "comments": 0})
            subs[sub]["posts"] = count

    if not comments_df.empty:
        for sub, count in comments_df["subreddit"].value_counts().items():
            subs.setdefault(sub, {"posts": 0, "comments": 0})
            subs[sub]["comments"] = count

    rows = []
    for sub, counts in subs.items():
        rows.append({
            "Subreddit": f"r/{sub}",
            "Posts": counts["posts"],
            "Comments": counts["comments"],
            "Total": counts["posts"] + counts["comments"],
        })

    if not rows:
        return pd.DataFrame(columns=["Subreddit", "Posts", "Comments", "Total"])

    df = pd.DataFrame(rows).sort_values("Total", ascending=False).reset_index(drop=True)
    df.index += 1
    return df
