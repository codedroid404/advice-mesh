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

if not CLAUDE_MODEL:
    raise ValueError("❌ ERROR: CLAUDE_MODEL is missing from .private_.env!")


if __name__ == "__main__":
    print("✅ Config loaded successfully")
    print("✅  Model: {CLAUDE_MODEL}")
