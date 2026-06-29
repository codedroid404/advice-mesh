"""Auto-generated config.py by setup.sh — do not edit manually."""
import os
from dotenv import load_dotenv

# 1. Load the specific environment file
load_dotenv(".private_.env")

# 2. Fetch the variable
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# 2. Fetch the variable
CLAUDE_BASE_URL = os.getenv("CLAUDE_BASE_URL")

# 2. Fetch the variable
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL")


# 3. Validate immediately
if not CLAUDE_API_KEY:
    raise ValueError("❌ ERROR: CLAUDE_API_KEY is missing from .private_.env!")

if not CLAUDE_BASE_URL:
    raise ValueError("❌ ERROR: CLAUDE_BASE_URL is missing from .private_.env!")

# Normalize to the /v1 API root so a bare "https://api.anthropic.com" also works
# (the code builds f"{CLAUDE_BASE_URL}/messages"; without /v1 that 404s).
CLAUDE_BASE_URL = CLAUDE_BASE_URL.rstrip("/")
if not CLAUDE_BASE_URL.endswith("/v1"):
    CLAUDE_BASE_URL = CLAUDE_BASE_URL + "/v1"

if not CLAUDE_MODEL:
    raise ValueError("❌ ERROR: CLAUDE_MODEL is missing from .private_.env!")

# Models selectable in the sidebar dropdown (CLAUDE_MODEL is the default).
MODEL_OPTIONS = {
    "claude-opus-4-8": "Claude Opus 4.8 — most capable",
    "claude-sonnet-4-6": "Claude Sonnet 4.6 — balanced",
    "claude-haiku-4-5": "Claude Haiku 4.5 — fastest & cheapest",
}


if __name__ == "__main__":
    print("✅ Config loaded successfully")
    print("✅  Model: {CLAUDE_MODEL}")
