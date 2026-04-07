"""Unit tests for subreddit filtering logic."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from src.subreddit_config import CANDIDATE_SUBS


def test_filter_to_candidate_subs():
    """Only posts in candidate subs should remain after filtering."""
    posts_df = pd.DataFrame({
        "subreddit": ["leetcode", "SkincareAddiction", "cscareerquestions", "logisim", "cpp"],
        "title": ["Post 1", "Post 2", "Post 3", "Post 4", "Post 5"],
    })

    candidate_lower = {s.lower() for s in CANDIDATE_SUBS}
    filtered = posts_df[posts_df["subreddit"].str.lower().isin(candidate_lower)]

    assert len(filtered) == 3
    assert set(filtered["subreddit"]) == {"leetcode", "cscareerquestions", "cpp"}


def test_filter_empty_df():
    """Filtering an empty DataFrame should return empty."""
    posts_df = pd.DataFrame(columns=["subreddit", "title"])
    candidate_lower = {s.lower() for s in CANDIDATE_SUBS}
    filtered = posts_df[posts_df["subreddit"].str.lower().isin(candidate_lower)]
    assert len(filtered) == 0


def test_filter_no_matches():
    """If no posts are in candidate subs, result should be empty."""
    posts_df = pd.DataFrame({
        "subreddit": ["SkincareAddiction", "logisim", "htgawm"],
        "title": ["Post 1", "Post 2", "Post 3"],
    })

    candidate_lower = {s.lower() for s in CANDIDATE_SUBS}
    filtered = posts_df[posts_df["subreddit"].str.lower().isin(candidate_lower)]
    assert len(filtered) == 0


def test_filter_case_insensitive():
    """Filter should be case insensitive."""
    posts_df = pd.DataFrame({
        "subreddit": ["LeetCode", "LEETCODE", "Leetcode"],
        "title": ["Post 1", "Post 2", "Post 3"],
    })

    candidate_lower = {s.lower() for s in CANDIDATE_SUBS}
    filtered = posts_df[posts_df["subreddit"].str.lower().isin(candidate_lower)]
    assert len(filtered) == 3
