"""Unit tests for automod filtering in replies.py."""

import sys
import os
import json
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from replies import _fetch_post_comments


def _make_reddit_response(comments):
    """Build a fake Reddit /comments/ JSON response."""
    children = []
    for c in comments:
        children.append({
            "kind": "t1",
            "data": {
                "author": c.get("author", "testuser"),
                "body": c["body"],
                "score": c.get("score", 1),
                "created_utc": 1700000000,
                "id": "abc123",
                "permalink": "/r/test/comments/abc123/test/def456",
            },
        })
    return [
        {"data": {}},  # post data (index 0)
        {"data": {"children": children}},  # comments (index 1)
    ]


@patch("replies.requests.get")
def test_filters_automod_removal(mock_get):
    """Automod removal messages should be filtered out."""
    response_data = _make_reddit_response([
        {"body": "Great advice, focus on STL containers!", "author": "helpful_user"},
        {"body": "Your submission has been automatically removed because the title does not include one of the required tags.", "author": "AutoModerator"},
        {"body": "I interviewed there last year, LC medium level.", "author": "another_user"},
    ])

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = response_data
    mock_get.return_value = mock_response

    comments = _fetch_post_comments("test123", "http://example.com")

    assert len(comments) == 2
    authors = [c["author"] for c in comments]
    assert "helpful_user" in authors
    assert "another_user" in authors
    assert "AutoModerator" not in authors


@patch("replies.requests.get")
def test_filters_post_removed_message(mock_get):
    """Other automod removal variants should also be filtered."""
    response_data = _make_reddit_response([
        {"body": "Your post has been removed due to low karma.", "author": "AutoModerator"},
        {"body": "This action was performed automatically by a bot.", "author": "SomeBot"},
        {"body": "Real advice here.", "author": "real_user"},
    ])

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = response_data
    mock_get.return_value = mock_response

    comments = _fetch_post_comments("test456", "http://example.com")

    assert len(comments) == 1
    assert comments[0]["author"] == "real_user"


@patch("replies.requests.get")
def test_keeps_normal_comments(mock_get):
    """Normal comments should pass through the filter."""
    response_data = _make_reddit_response([
        {"body": "Focus on dynamic programming.", "author": "user1"},
        {"body": "Two pointers is key.", "author": "user2"},
    ])

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = response_data
    mock_get.return_value = mock_response

    comments = _fetch_post_comments("test789", "http://example.com")

    assert len(comments) == 2
