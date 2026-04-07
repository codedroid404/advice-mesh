"""
API usage tracker — tracks token usage and estimates cost from Claude API responses.

Usage:
    from usage_tracker import track_usage, get_session_usage, get_total_usage
"""

import json
import os
from datetime import datetime, timezone
from logger import get_logger

log = get_logger("usage")

DATA_DIR = "data"
USAGE_FILE = os.path.join(DATA_DIR, "api_usage.json")

# Claude pricing per million tokens (as of 2025)
PRICING = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
}
DEFAULT_PRICING = {"input": 3.00, "output": 15.00}

# Session-level counters (reset on app restart)
_session_input_tokens = 0
_session_output_tokens = 0
_session_requests = 0


def track_usage(response_json, model=""):
    """
    Track token usage from a Claude API response.
    Call this after every successful API call.
    """
    global _session_input_tokens, _session_output_tokens, _session_requests

    usage = response_json.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)

    _session_input_tokens += input_tokens
    _session_output_tokens += output_tokens
    _session_requests += 1

    # Persist to disk
    _save_usage(input_tokens, output_tokens, model)

    log.debug(f"API call: {input_tokens} in / {output_tokens} out tokens")


def _save_usage(input_tokens, output_tokens, model):
    """Append usage record to disk."""
    os.makedirs(DATA_DIR, exist_ok=True)

    records = []
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "r") as f:
            records = json.load(f)

    records.append({
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    with open(USAGE_FILE, "w") as f:
        json.dump(records, f, indent=2)


def get_session_usage():
    """Return session usage stats."""
    return {
        "input_tokens": _session_input_tokens,
        "output_tokens": _session_output_tokens,
        "requests": _session_requests,
        "cost": _estimate_cost(_session_input_tokens, _session_output_tokens),
    }


def get_total_usage(model=""):
    """Return all-time usage stats from disk."""
    if not os.path.exists(USAGE_FILE):
        return {"input_tokens": 0, "output_tokens": 0, "requests": 0, "cost": 0.0}

    with open(USAGE_FILE, "r") as f:
        records = json.load(f)

    total_in = sum(r["input_tokens"] for r in records)
    total_out = sum(r["output_tokens"] for r in records)

    return {
        "input_tokens": total_in,
        "output_tokens": total_out,
        "requests": len(records),
        "cost": _estimate_cost(total_in, total_out, model),
    }


def _estimate_cost(input_tokens, output_tokens, model=""):
    """Estimate cost in USD based on token counts."""
    pricing = PRICING.get(model, DEFAULT_PRICING)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 4)
