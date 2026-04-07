"""
API usage tracker — tracks token usage and estimates cost from Claude API responses.

Usage:
    from usage_tracker import track_usage, get_session_usage, get_total_usage

Records are persisted as newline-delimited JSON (JSONL) so each call is a
single append — no read-modify-write race condition.
"""

import json
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TypedDict

from src.logger import get_logger

log = get_logger("usage")

DATA_DIR = "data"
USAGE_FILE = os.path.join(DATA_DIR, "api_usage.jsonl")  # append-only JSONL

# ---------------------------------------------------------------------------
# Pricing table  (USD per million tokens, as of 2025)
# Canonical model IDs only — aliases are resolved via MODEL_ALIASES below.
# ---------------------------------------------------------------------------
PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-20250514":   {"input": 15.00, "cache_write": 18.75, "cache_read": 1.50,  "output": 75.00},
    "claude-sonnet-4-20250514": {"input":  3.00, "cache_write":  3.75, "cache_read": 0.30,  "output": 15.00},
    "claude-haiku-4-5-20251001":{"input":  0.80, "cache_write":  1.00, "cache_read": 0.08,  "output":  4.00},
}
DEFAULT_PRICING: dict[str, float] = {"input": 3.00, "cache_write": 3.75, "cache_read": 0.30, "output": 15.00}

# Short/friendly aliases → canonical model ID
MODEL_ALIASES: dict[str, str] = {
    "claude-opus-4-6":    "claude-opus-4-20250514",
    "claude-sonnet-4-6":  "claude-sonnet-4-20250514",
}


def _canonical(model: str) -> str:
    """Resolve a model alias to its canonical ID."""
    return MODEL_ALIASES.get(model, model)


# ---------------------------------------------------------------------------
# Session state  (reset on process restart)
# ---------------------------------------------------------------------------
@dataclass
class _SessionState:
    input_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    output_tokens: int = 0
    requests: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)


_session = _SessionState()


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------
class UsageStats(TypedDict):
    input_tokens: int
    cache_write_tokens: int
    cache_read_tokens: int
    output_tokens: int
    requests: int
    cost_usd: float


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def track_usage(response_json: dict, model: str = "") -> None:
    """
    Record token usage from a Claude API response object.

    Call this after every successful API call:

        data = response.json()
        track_usage(data, model="claude-sonnet-4-20250514")

    Args:
        response_json: The parsed JSON body returned by the Anthropic API.
        model:         Model ID used for the request (used for cost estimation).
    """
    usage = response_json.get("usage", {})
    inp   = int(usage.get("input_tokens", 0))
    cw    = int(usage.get("cache_creation_input_tokens", 0))
    cr    = int(usage.get("cache_read_input_tokens", 0))
    out   = int(usage.get("output_tokens", 0))
    model = _canonical(model)

    with _session.lock:
        _session.input_tokens       += inp
        _session.cache_write_tokens += cw
        _session.cache_read_tokens  += cr
        _session.output_tokens      += out
        _session.requests           += 1

    _append_record(inp, cw, cr, out, model)
    log.debug("API call: %d in / %d out tokens (model=%s)", inp, out, model or "unknown")


def get_session_usage() -> UsageStats:
    """Return cumulative token usage and cost for the current process session."""
    with _session.lock:
        inp, cw, cr, out, reqs = (
            _session.input_tokens,
            _session.cache_write_tokens,
            _session.cache_read_tokens,
            _session.output_tokens,
            _session.requests,
        )
    return UsageStats(
        input_tokens=inp,
        cache_write_tokens=cw,
        cache_read_tokens=cr,
        output_tokens=out,
        requests=reqs,
        cost_usd=_estimate_cost(inp, cw, cr, out),
    )


def get_total_usage(model: str = "") -> UsageStats:
    """
    Return all-time token usage and cost aggregated from the on-disk log.

    Cost is computed per-record using each record's stored model ID so that
    mixed-model sessions are priced correctly.  If a record has no stored
    model (e.g. older entries), ``model`` is used as a fallback.
    """
    if not os.path.exists(USAGE_FILE):
        return UsageStats(input_tokens=0, cache_write_tokens=0, cache_read_tokens=0,
                          output_tokens=0, requests=0, cost_usd=0.0)

    total_in = total_cw = total_cr = total_out = 0
    total_cost = 0.0
    records_read = 0

    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    log.warning("Skipping malformed record on line %d of %s", lineno, USAGE_FILE)
                    continue

                inp = rec.get("input_tokens", 0)
                cw  = rec.get("cache_write_tokens", 0)
                cr  = rec.get("cache_read_tokens", 0)
                out = rec.get("output_tokens", 0)
                mdl = _canonical(rec.get("model", "") or model)

                total_in  += inp
                total_cw  += cw
                total_cr  += cr
                total_out += out
                total_cost += _estimate_cost(inp, cw, cr, out, mdl)
                records_read += 1

    except OSError as exc:
        log.error("Could not read usage file %s: %s", USAGE_FILE, exc)

    return UsageStats(
        input_tokens=total_in,
        cache_write_tokens=total_cw,
        cache_read_tokens=total_cr,
        output_tokens=total_out,
        requests=records_read,
        cost_usd=round(total_cost, 6),
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _append_record(
    input_tokens: int,
    cache_write_tokens: int,
    cache_read_tokens: int,
    output_tokens: int,
    model: str,
) -> None:
    """Append a single usage record to the JSONL log (one JSON object per line)."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "input_tokens": input_tokens,
        "cache_write_tokens": cache_write_tokens,
        "cache_read_tokens": cache_read_tokens,
        "output_tokens": output_tokens,
    }
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(USAGE_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError as exc:
        # Non-fatal: session counters are still correct; just warn.
        log.warning("Could not persist usage record: %s", exc)


def _estimate_cost(
    input_tokens: int,
    cache_write_tokens: int,
    cache_read_tokens: int,
    output_tokens: int,
    model: str = "",
) -> float:
    """Return estimated cost in USD for the given token counts and model."""
    p = PRICING.get(model, DEFAULT_PRICING)
    cost = (
        (input_tokens       / 1_000_000) * p["input"]
        + (cache_write_tokens / 1_000_000) * p["cache_write"]
        + (cache_read_tokens  / 1_000_000) * p["cache_read"]
        + (output_tokens      / 1_000_000) * p["output"]
    )
    return round(cost, 6)