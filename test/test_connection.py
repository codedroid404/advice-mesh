"""Test Claude (Anthropic) API connectivity and model response."""

"pytest -m integration -v -s"
import sys
import os
import pytest
import requests

# Ensure project root is on the path so config.py is found regardless of how pytest is run
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import CLAUDE_API_KEY, CLAUDE_BASE_URL, CLAUDE_MODEL

HEADERS = {
    "x-api-key": CLAUDE_API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
}


@pytest.mark.integration
def test_claude_connection():
    """Send a lightweight request to the Anthropic API and check for 200."""
    url = f"{CLAUDE_BASE_URL}/messages"

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Say 'hello' and nothing else."}],
    }

    response = requests.post(
        url,
        headers=HEADERS,
        json=payload,
        timeout=15,
    )

    # Skip if no credits
    if response.status_code in (400, 429) and "credit balance" in response.text.lower():
        pytest.skip("No Anthropic credits — add billing at console.anthropic.com/settings/billing")

    # 1. Check status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # 2. Check response structure
    data = response.json()
    assert "content" in data, "Response missing 'content' key"
    assert len(data["content"]) > 0, "No content returned"

    # 3. Check that the model actually replied
    text = data["content"][0]["text"]
    assert len(text) > 0, "Model returned empty response"

    print(f"\n✅ {CLAUDE_MODEL} responded: {text}")
