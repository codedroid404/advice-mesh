"""Integration tests for Claude API — requires API credits."""

import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
from src.analyzer import analyze_comment, analyze_replies_df
from src.discovery import evaluate_relevance


def _skip_if_no_credits(response_text):
    """Helper to skip test if Claude returns a billing error."""
    if "credit balance" in response_text.lower():
        pytest.skip("No Anthropic credits")


@pytest.mark.integration
def test_analyze_comment():
    """Analyze a single comment and verify structured output."""
    comment = "I interviewed at Shield AI last year. Focus on STL containers and smart pointers. The LC medium difficulty was spot on."

    result = analyze_comment(comment)

    _skip_if_no_credits(result)

    assert "Authenticity:" in result or "Error:" in result
    if "Error:" not in result:
        assert "Usefulness:" in result
        assert "Key_Tips:" in result
        assert "Verdict:" in result

    print(f"\n✅ Analysis result:\n{result}")


@pytest.mark.integration
def test_analyze_comment_with_job_context():
    """Analyze a comment with job description context."""
    comment = "Focus on system design and data structures. The live coding was LC medium level."

    result = analyze_comment(
        comment,
        job_context="Senior Software Engineer — requires Python, C++, distributed systems experience",
        interview_stage="Final round live coding session",
    )

    _skip_if_no_credits(result)

    assert "Authenticity:" in result or "Error:" in result
    if "Error:" not in result:
        assert "Usefulness:" in result

    print(f"\n✅ Analysis with context:\n{result}")


@pytest.mark.integration
def test_analyze_replies_df():
    """Analyze a small DataFrame of replies."""
    replies_df = pd.DataFrame({
        "body": [
            "Focus on dynamic programming and graph traversal for the final round.",
            "[deleted]",
        ],
        "author": ["helpfuluser", "[deleted]"],
        "score": [15, 0],
        "post_id": ["abc123", "abc123"],
        "post_url": ["http://example.com", "http://example.com"],
        "created_utc": [1700000000, 1700000000],
        "comment_id": ["c1", "c2"],
        "permalink": ["http://reddit.com/c1", "http://reddit.com/c2"],
    })

    result = analyze_replies_df(replies_df)

    # Check if we got a billing error on the first real comment
    if "credit balance" in str(result.iloc[0].get("analysis", "")).lower():
        pytest.skip("No Anthropic credits")

    assert "analysis" in result.columns
    assert "authenticity_score" in result.columns
    assert "usefulness_score" in result.columns
    assert "key_tips" in result.columns

    # Deleted comment should be skipped
    assert result.iloc[1]["authenticity_score"] == 0

    # Real comment should have a score > 0
    assert result.iloc[0]["authenticity_score"] > 0

    print(f"\n✅ Analyzed {len(result)} replies")


@pytest.mark.integration
def test_evaluate_relevance():
    """Evaluate if a subreddit is relevant to the post topic."""
    result = evaluate_relevance(
        sub_name="leetcode",
        sub_description="A community for discussing LeetCode problems and interview prep",
        post_topic="Shield AI C++ code pair interview tips",
    )

    if "credit balance" in result.get("reason", "").lower():
        pytest.skip("No Anthropic credits")

    assert "relevant" in result
    assert "confidence" in result
    assert "reason" in result
    assert isinstance(result["relevant"], bool)
    assert isinstance(result["confidence"], int)

    print(f"\n✅ r/leetcode relevance: {result['relevant']}, confidence: {result['confidence']}/10")
