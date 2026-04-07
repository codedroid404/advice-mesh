"""
Posting log — tracks which subreddits the user has manually posted to.

Usage:
    from posting import load_posting_log, mark_as_posted, get_posted_subs
"""

import json
import os
from datetime import datetime, timezone
from logger import get_logger

log = get_logger("posting")

DATA_DIR = "data"
POSTING_LOG = os.path.join(DATA_DIR, "posting_log.json")


def load_posting_log():
    """Load the posting log from disk."""
    if os.path.exists(POSTING_LOG):
        with open(POSTING_LOG, "r") as f:
            return json.load(f)
    return {}


def _save_posting_log(data):
    """Write the posting log to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(POSTING_LOG, "w") as f:
        json.dump(data, f, indent=2)


def mark_as_posted(username, subreddit, url=""):
    """Record that a user has posted to a subreddit."""
    data = load_posting_log()
    data.setdefault(username, {})
    data[username][subreddit.lower()] = {
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "url": url,
    }
    _save_posting_log(data)
    log.info(f"Marked u/{username} as posted in r/{subreddit}")


def get_posted_subs(username):
    """Return set of subreddit names (lowercase) the user has posted to."""
    data = load_posting_log()
    return set(data.get(username, {}).keys())
