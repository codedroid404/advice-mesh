#!/bin/zsh
# Setup for AdviceMesh.  SOURCE this script (do not execute it):
#   source setup.sh
#
# Creates a .venv, installs Python deps + the Playwright Chromium browser
# (required by the scraper), activates the venv, and checks your env file.
#
# NOTE: src/config.py is hand-maintained — this script does NOT generate it.

# --- Guard: must be sourced, not executed ---
if [[ "${ZSH_EVAL_CONTEXT}" != *:file ]]; then
    echo "Error: source this script — 'source setup.sh' (do not run it directly)."
    exit 1
fi

# --- Guard: project root ---
if [[ ! -f "app.py" && ! -d ".git" ]]; then
    echo "Error: run this from the project root (app.py / .git not found)."
    return 1
fi

# --- Logging ---
info()  { print -P "%F{green}[✓]%f $1"; }
warn()  { print -P "%F{yellow}[!]%f $1"; }
error() { print -P "%F{red}[✗]%f $1"; }

VENV_DIR=".venv"
ENV_FILE=".private_.env"

# --- Preflight ---
if ! command -v python3 &>/dev/null; then
    error "python3 not found on PATH (need Python 3.11+)."
    return 1
fi

# --- Deactivate any active venv to avoid conflicts ---
if [[ -n "$VIRTUAL_ENV" ]]; then
    warn "Deactivating current venv: ${VIRTUAL_ENV:t}"
    deactivate 2>/dev/null
fi

# --- Create + activate venv ---
if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment ($VENV_DIR)..."
    python3 -m venv "$VENV_DIR" || { error "venv creation failed."; return 1; }
fi
source "$VENV_DIR/bin/activate" || { error "could not activate $VENV_DIR."; return 1; }
info "Virtual environment activated ($(python3 --version))."

# --- Install Python dependencies ---
info "Installing Python dependencies..."
python -m pip install -q --upgrade pip
if ! python -m pip install -q \
        streamlit requests pandas python-dotenv pymupdf playwright "mcp[cli]"; then
    error "pip install failed."
    return 1
fi
info "Python dependencies installed."

# --- Install the Playwright browser (the scraper drives headless Chromium) ---
info "Installing Playwright Chromium (one-time, ~150MB)..."
python -m playwright install chromium

# --- Check secrets (we do NOT generate config.py — it's hand-maintained) ---
if [[ ! -f "$ENV_FILE" ]]; then
    warn "$ENV_FILE not found. Create it with at least:"
    print "    CLAUDE_API_KEY=sk-ant-..."
    print "    CLAUDE_MODEL=claude-haiku-4-5"
    print "    CLAUDE_BASE_URL=https://api.anthropic.com/v1"
elif ! grep -qE "^CLAUDE_API_KEY=.+" "$ENV_FILE"; then
    warn "CLAUDE_API_KEY is missing/empty in $ENV_FILE — set it before running."
else
    info "$ENV_FILE found with CLAUDE_API_KEY."
fi

echo ""
info "Setup complete. Run:  streamlit run app.py"
