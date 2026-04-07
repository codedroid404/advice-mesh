"""Unit tests for data logic — cross_check, summarize_subreddits, get_all_candidate_subs."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from src.scraper import summarize_subreddits
from src.finder import cross_check
from src.subreddit_config import CANDIDATE_SUBS, get_all_candidate_subs


# --- summarize_subreddits ---

def test_summarize_basic():
    posts_df = pd.DataFrame({
        "subreddit": ["leetcode", "leetcode", "cpp"],
    })
    comments_df = pd.DataFrame({
        "subreddit": ["leetcode", "embedded"],
    })
    result = summarize_subreddits(posts_df, comments_df)

    assert len(result) == 3
    # leetcode should be first (2 posts + 1 comment = 3 total)
    top_row = result.iloc[0]
    assert top_row["Subreddit"] == "r/leetcode"
    assert top_row["Posts"] == 2
    assert top_row["Comments"] == 1
    assert top_row["Total"] == 3


def test_summarize_empty():
    posts_df = pd.DataFrame(columns=["subreddit"])
    comments_df = pd.DataFrame(columns=["subreddit"])
    result = summarize_subreddits(posts_df, comments_df)
    assert len(result) == 0


def test_summarize_posts_only():
    posts_df = pd.DataFrame({"subreddit": ["cpp", "cpp"]})
    comments_df = pd.DataFrame(columns=["subreddit"])
    result = summarize_subreddits(posts_df, comments_df)
    assert len(result) == 1
    assert result.iloc[0]["Posts"] == 2
    assert result.iloc[0]["Comments"] == 0


# --- cross_check ---

def test_cross_check_splits_correctly():
    posts_df = pd.DataFrame({
        "subreddit": ["leetcode", "cpp"],
        "title": ["My post", "Another post"],
        "post_url": ["http://a", "http://b"],
        "score": [10, 5],
        "num_comments": [3, 1],
    })
    candidates_df = pd.DataFrame({
        "subreddit": ["leetcode", "cpp", "embedded"],
        "subscribers": [100000, 50000, 30000],
        "description": ["desc1", "desc2", "desc3"],
        "relevance_score": [5, 3, 2],
        "tag": [None, None, None],
        "min_karma": [0, 0, 0],
    })

    already_df, not_yet_df = cross_check(posts_df, candidates_df)

    # leetcode and cpp should be in already_posted
    assert len(already_df) == 2
    # embedded should be in not_yet
    assert len(not_yet_df) == 1
    assert "r/embedded" in not_yet_df["subreddit"].values


def test_cross_check_empty_posts():
    posts_df = pd.DataFrame(columns=["subreddit", "title", "post_url", "score", "num_comments"])
    candidates_df = pd.DataFrame({
        "subreddit": ["leetcode"],
        "subscribers": [100000],
        "description": ["desc"],
        "relevance_score": [5],
        "tag": [None],
        "min_karma": [0],
    })

    already_df, not_yet_df = cross_check(posts_df, candidates_df)
    assert len(already_df) == 0
    assert len(not_yet_df) == 1


def test_cross_check_with_manually_posted():
    posts_df = pd.DataFrame(columns=["subreddit", "title", "post_url", "score", "num_comments"])
    candidates_df = pd.DataFrame({
        "subreddit": ["leetcode", "cpp"],
        "subscribers": [100000, 50000],
        "description": ["desc1", "desc2"],
        "relevance_score": [5, 3],
        "tag": [None, None],
        "min_karma": [0, 0],
    })

    manually_posted = {"leetcode"}
    already_df, not_yet_df = cross_check(posts_df, candidates_df, manually_posted=manually_posted)

    # leetcode should move to already (via manual posting)
    assert len(already_df) == 0  # no post details for manually posted
    assert len(not_yet_df) == 1
    assert "r/cpp" in not_yet_df["subreddit"].values


# --- get_all_candidate_subs ---

def test_candidate_subs_not_empty():
    assert len(CANDIDATE_SUBS) > 0


def test_get_all_includes_base():
    result = get_all_candidate_subs()
    for sub in CANDIDATE_SUBS:
        assert sub in result
