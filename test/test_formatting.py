"""Unit tests for post_content formatting."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from post_content import format_for_subreddit, POST_TITLE, POST_BODY


def test_format_sub_with_tag():
    """r/interviews requires [Advice] — title should keep it."""
    title, body = format_for_subreddit("interviews")
    assert "[Advice]" in title
    assert body == POST_BODY


def test_format_sub_without_tag():
    """r/leetcode has no tag — [Advice] should be stripped from title."""
    title, body = format_for_subreddit("leetcode")
    assert not title.startswith("[")
    assert "Shield AI" in title
    assert body == POST_BODY


def test_format_unknown_sub():
    """Unknown sub should strip the tag like subs without tags."""
    title, body = format_for_subreddit("some_random_sub")
    assert not title.startswith("[")
    assert body == POST_BODY


def test_format_body_unchanged():
    """Body should never be modified."""
    _, body = format_for_subreddit("interviews")
    assert body == POST_BODY
    _, body = format_for_subreddit("cpp")
    assert body == POST_BODY


def test_post_title_not_empty():
    assert len(POST_TITLE) > 0


def test_post_body_not_empty():
    assert len(POST_BODY) > 0
