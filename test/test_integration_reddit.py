"""Integration tests for Reddit API endpoints."""

import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from scraper import scrape_user
from finder import fetch_sub_metadata
from replies import fetch_replies
from discovery import search_subreddits


@pytest.mark.integration
def test_scrape_user_valid():
    """Scrape a known public user and verify DataFrame structure."""
    posts_df, comments_df = scrape_user("poppinlavish")

    assert posts_df is not None
    assert comments_df is not None
    assert isinstance(posts_df, pd.DataFrame)
    assert isinstance(comments_df, pd.DataFrame)

    # Verify expected columns exist
    if not posts_df.empty:
        for col in ["subreddit", "title", "post_url", "score", "post_id"]:
            assert col in posts_df.columns, f"Missing column: {col}"

    print(f"\n✅ Scraped {len(posts_df)} posts, {len(comments_df)} comments")


@pytest.mark.integration
def test_scrape_user_not_found():
    """Scraping a nonexistent user should return None."""
    posts_df, comments_df = scrape_user("this_user_definitely_does_not_exist_12345xyz")
    assert posts_df is None
    assert comments_df is None


@pytest.mark.integration
def test_fetch_sub_metadata_single():
    """Fetch metadata for a single known subreddit."""
    df = fetch_sub_metadata(subs=["leetcode"])

    assert len(df) == 1
    assert df.iloc[0]["subreddit"] == "leetcode"
    assert df.iloc[0]["subscribers"] > 0

    print(f"\n✅ r/leetcode has {df.iloc[0]['subscribers']:,} subscribers")


@pytest.mark.integration
def test_fetch_replies_with_posts():
    """Fetch replies for a known post."""
    # First scrape to get real post IDs
    posts_df, _ = scrape_user("poppinlavish")

    if posts_df is None or posts_df.empty:
        pytest.skip("No posts found to fetch replies for")

    # Only fetch for the first post to keep it fast
    single_post = posts_df.head(1)
    replies_df = fetch_replies(single_post)

    assert isinstance(replies_df, pd.DataFrame)
    if not replies_df.empty:
        for col in ["author", "body", "score", "permalink"]:
            assert col in replies_df.columns

    print(f"\n✅ Found {len(replies_df)} replies on first post")


@pytest.mark.integration
def test_search_subreddits():
    """Search for subreddits and verify results."""
    results = search_subreddits("C++ programming", limit=5)

    assert isinstance(results, list)
    assert len(results) > 0
    assert "name" in results[0]
    assert "subscribers" in results[0]

    print(f"\n✅ Found {len(results)} subreddits for 'C++ programming'")
