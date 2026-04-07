"""
Subreddit discovery — searches Reddit for new relevant subreddits and evaluates them with Claude.

Usage:
    from discovery import discover_and_evaluate
"""

import json
import os
import time
import requests
import pandas as pd
from config import CLAUDE_API_KEY, CLAUDE_BASE_URL, CLAUDE_MODEL
from logger import get_logger
from usage_tracker import track_usage

log = get_logger("discovery")

USER_AGENT = "CommunityScraperBot/1.0"
DATA_DIR = "data"
DISCOVERED_FILE = os.path.join(DATA_DIR, "discovered_subs.json")

CLAUDE_HEADERS = {
    "x-api-key": CLAUDE_API_KEY,
    "anthropic-version": "2023-06-01",
    "Content-Type": "application/json",
}


def search_subreddits(query, limit=25):
    """
    Search Reddit for subreddits matching a query.
    Returns a list of dicts with name, subscribers, description.
    """
    url = "https://www.reddit.com/subreddits/search.json"
    headers = {"User-Agent": USER_AGENT}
    params = {"q": query, "limit": limit, "raw_json": 1}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code == 429:
            log.warning("Rate limited — waiting 60s...")
            time.sleep(60)
            resp = requests.get(url, headers=headers, params=params, timeout=10)

        if resp.status_code != 200:
            log.error(f"Search failed: HTTP {resp.status_code}")
            return []

        children = resp.json().get("data", {}).get("children", [])
        results = []
        for child in children:
            d = child["data"]
            results.append({
                "name": d.get("display_name", ""),
                "subscribers": d.get("subscribers", 0) or 0,
                "description": (d.get("public_description", "") or "")[:200],
            })

        log.info(f"Found {len(results)} subreddits for query: {query}")
        return results

    except Exception as e:
        log.error(f"Search failed: {e}")
        return []


def evaluate_relevance(sub_name, sub_description, post_topic):
    """
    Ask Claude if a subreddit is relevant to the post topic.
    Returns dict with relevant (bool), confidence (int), reason (str).
    """
    url = f"{CLAUDE_BASE_URL}/messages"

    prompt = f"""Given a Reddit post about: "{post_topic}"

Is r/{sub_name} a good subreddit to post this in?
Subreddit description: "{sub_description}"

Respond in this exact format:
Relevant: [Yes or No]
Confidence: [1-10]
Reason: [one sentence explanation]"""

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 150,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        resp = requests.post(url, headers=CLAUDE_HEADERS, json=payload, timeout=15)

        if resp.status_code != 200:
            log.error(f"Claude API error evaluating r/{sub_name}: {resp.status_code}")
            return {"relevant": False, "confidence": 0, "reason": f"API error: {resp.status_code}"}

        data = resp.json()
        track_usage(data, model=CLAUDE_MODEL)
        text = data["content"][0]["text"]

        relevant = False
        confidence = 0
        reason = ""

        for line in text.split("\n"):
            if line.lower().startswith("relevant:"):
                relevant = "yes" in line.lower()
            elif line.lower().startswith("confidence:"):
                try:
                    confidence = int(line.split(":")[1].strip().split("/")[0].split()[0])
                except (ValueError, IndexError):
                    confidence = 0
            elif line.lower().startswith("reason:"):
                reason = line.split(":", 1)[1].strip()

        log.info(f"  r/{sub_name}: relevant={relevant}, confidence={confidence}")
        return {"relevant": relevant, "confidence": confidence, "reason": reason}

    except Exception as e:
        log.error(f"Evaluation failed for r/{sub_name}: {e}")
        return {"relevant": False, "confidence": 0, "reason": str(e)}


def discover_and_evaluate(query, existing_subs, post_topic, on_status=None):
    """
    Search for subreddits and evaluate their relevance with Claude.

    Args:
        query: Search query string
        existing_subs: List of subreddit names already in the candidate list (to exclude)
        post_topic: Description of the post topic for Claude evaluation
        on_status: Optional callback for progress updates

    Returns:
        DataFrame with columns: subreddit, subscribers, description, relevant, confidence, reason
    """
    if on_status:
        on_status(f"Searching Reddit for: {query}...")

    results = search_subreddits(query)

    # Filter out existing subs
    existing_lower = {s.lower() for s in existing_subs}
    new_results = [r for r in results if r["name"].lower() not in existing_lower]

    log.info(f"Found {len(new_results)} new subreddits (filtered {len(results) - len(new_results)} existing)")

    # Also filter out previously rejected subs
    rejected = load_rejected_subs()
    new_results = [r for r in new_results if r["name"].lower() not in rejected]

    rows = []
    for i, sub in enumerate(new_results):
        if on_status:
            on_status(f"Evaluating r/{sub['name']} ({i+1}/{len(new_results)})...")

        eval_result = evaluate_relevance(sub["name"], sub["description"], post_topic)
        rows.append({
            "subreddit": sub["name"],
            "subscribers": sub["subscribers"],
            "description": sub["description"],
            "relevant": eval_result["relevant"],
            "confidence": eval_result["confidence"],
            "reason": eval_result["reason"],
        })
        time.sleep(1)

    df = pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["subreddit", "subscribers", "description", "relevant", "confidence", "reason"]
    )

    if not df.empty:
        df = df.sort_values(["relevant", "confidence"], ascending=[False, False]).reset_index(drop=True)
        df.index += 1

    return df


def load_discovered_subs():
    """Load approved/rejected subs from disk."""
    if os.path.exists(DISCOVERED_FILE):
        with open(DISCOVERED_FILE, "r") as f:
            return json.load(f)
    return {"approved": [], "rejected": []}


def load_rejected_subs():
    """Return set of rejected sub names (lowercase)."""
    data = load_discovered_subs()
    return {s.lower() for s in data.get("rejected", [])}


def save_discovered_subs(approved, rejected):
    """Save approved and rejected subs to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    data = load_discovered_subs()
    # Merge with existing, deduplicate
    existing_approved = set(s.lower() for s in data.get("approved", []))
    existing_rejected = set(s.lower() for s in data.get("rejected", []))

    for s in approved:
        existing_approved.add(s.lower())
        existing_rejected.discard(s.lower())
    for s in rejected:
        existing_rejected.add(s.lower())
        existing_approved.discard(s.lower())

    data["approved"] = sorted(existing_approved)
    data["rejected"] = sorted(existing_rejected)

    with open(DISCOVERED_FILE, "w") as f:
        json.dump(data, f, indent=2)

    log.info(f"Saved discovered subs: {len(data['approved'])} approved, {len(data['rejected'])} rejected")


def get_approved_subs():
    """Return list of approved discovered subreddit names."""
    data = load_discovered_subs()
    return data.get("approved", [])
