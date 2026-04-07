#!/bin/zsh
# Note: do NOT use "set -e" here — this script is sourced,
# so errexit would kill the parent shell on any error.

# Setup script for Python project
#
# Usage: Source this script (don't run it directly)
#   source setup.sh
#   or
#   . setup.sh

# --- Guard: must be sourced, not executed ---
if [[ "${ZSH_EVAL_CONTEXT}" != *:file ]]; then
    echo "Error: This script must be sourced, not executed."
    echo "  Usage: source setup.sh"
    exit 1
fi

# --- Guard: must be in project root ---
if [[ ! -f "pyproject.toml" && ! -d ".git" ]]; then
    echo "Error: Run this from the project root (no pyproject.toml or .git found)."
    return 1
fi

# --- Logging ---
info()  { print -P "%F{green}[✓]%f $1"; }
warn()  { print -P "%F{yellow}[!]%f $1"; }
error() { print -P "%F{red}[✗]%f $1"; }

# --- Configuration ---
VENV_DIR=".venv"
ENV_FILE=".private_.env"
CONFIG_FILE="src/config.py"
TMP_REQUIREMENTS="$(mktemp)"
trap "rm -f '$TMP_REQUIREMENTS'" EXIT INT TERM

# --- Preflight checks ---
local missing=false
for cmd in poetry python3; do
    if ! command -v "$cmd" &>/dev/null; then
        error "$cmd is not found on PATH."
        missing=true
    fi
done
if [[ "$missing" == true ]]; then
    error "Install missing dependencies before continuing."
    return 1
fi

# --- Minimum version checks ---
local poetry_version
poetry_version="$(poetry --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+')"
if [[ "${poetry_version%%.*}" -lt 1 ]]; then
    error "Poetry >= 1.2 required (found $poetry_version)."
    return 1
fi

# --- Deactivate any active venv to avoid conflicts ---
if [[ -n "$VIRTUAL_ENV" ]]; then
    warn "Deactivating current venv: ${VIRTUAL_ENV:t}"
    deactivate
fi

# --- Poetry setup ---
poetry config virtualenvs.in-project true

if [[ ! -f "pyproject.toml" ]]; then
    info "Initializing Poetry project..."
    poetry init --no-interaction
fi

# --- Scan code for imports and sync to Poetry ---
_needs_dep_scan() {
    [[ ! -f "poetry.lock" ]] && return 0
    # Any .py file (excluding .venv) newer than the lockfile?
    [[ -n "$(find . -path "./$VENV_DIR" -prune -o -name '*.py' -newer poetry.lock -print -quit)" ]]
}

if _needs_dep_scan; then
    info "Scanning code for imports..."

    if ! command -v pipreqs &>/dev/null; then
        pip install -q pipreqs 2>/dev/null
    fi

    pipreqs . --force --ignore "$VENV_DIR" --savepath "$TMP_REQUIREMENTS" 2>/dev/null

    # Strip local modules that pipreqs mistakenly resolves from PyPI.
    # Add package names (anchored, one per line) to skip them.
    local -a LOCAL_MODULES=(config utils helpers)
    for mod in "${LOCAL_MODULES[@]}"; do
        sed -i '' "/^${mod}==/d" "$TMP_REQUIREMENTS"
    done

    local dep
    while IFS= read -r dep; do
        [[ -z "$dep" || "$dep" == \#* ]] && continue
        poetry add "$dep" 2>/dev/null || warn "Skipping $dep (already added or invalid)"
    done < "$TMP_REQUIREMENTS"

    # Ensure always-needed deps are present
    local -a REQUIRED_DEPS=(python-dotenv)
    for dep in "${REQUIRED_DEPS[@]}"; do
        poetry add "$dep" 2>/dev/null || true
    done

    poetry lock --no-update
    info "Dependencies synced to Poetry."
else
    info "No code changes detected — skipping dependency scan."
fi

# --- Install into .venv ---
poetry install --no-root
info "Dependencies installed into $VENV_DIR/"

# --- Activate ---
if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    error "Venv activation script not found. Poetry install may have failed."
    return 1
fi
source "$VENV_DIR/bin/activate"
info "Virtual environment activated. ($(python3 --version))"

# --- Generate config.py from env file ---
_generate_config() {
    local env_file="$1" out_file="$2"

    [[ ! -f "$env_file" ]] && { warn "$env_file not found. Skipping $out_file generation."; return 0; }

    info "Generating $out_file from $env_file..."

    # Write header
    cat > "$out_file" <<PYHEADER
"""Auto-generated config.py by setup.sh — do not edit manually."""
import os
from dotenv import load_dotenv

# 1. Load the specific environment file
load_dotenv("$env_file")

PYHEADER

    # 2. Dynamically read all keys from the env file
    local -a keys=()
    local key value
    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        key="${key// /}"
        [[ -z "$key" || "$key" == \#* ]] && continue
        keys+=("$key")
        printf '# 2. Fetch the variable\n' >> "$out_file"
        printf '%s = os.getenv("%s")\n\n' "$key" "$key" >> "$out_file"
    done < "$env_file"

    # 3. Validate all keys
    printf '\n# 3. Validate immediately\n' >> "$out_file"
    for k in "${keys[@]}"; do
        printf 'if not %s:\n' "$k" >> "$out_file"
        printf '    raise ValueError("❌ ERROR: %s is missing from %s!")\n\n' "$k" "$env_file" >> "$out_file"
    done

    # 4. Generate HEADERS if OPENAI_API_KEY exists
    local has_api_key=false
    for k in "${keys[@]}"; do
        [[ "$k" == "OPENAI_API_KEY" ]] && has_api_key=true
    done
    if [[ "$has_api_key" == true ]]; then
        cat >> "$out_file" <<'PYHEADERS'
HEADERS = {
    "Authorization": f"Bearer {OPENAI_API_KEY}",
    "Content-Type": "application/json",
}
PYHEADERS
    fi

    # 5. Main guard
    cat >> "$out_file" <<PYFOOTER

if __name__ == "__main__":
    print("✅ Config loaded successfully")
    print("✅  Model: {CLAUDE_MODEL}")
PYFOOTER

    info "$out_file generated."
}
_generate_config "$ENV_FILE" "$CONFIG_FILE"

echo ""
info "Setup complete! Run 'python config.py' to validate your env vars."