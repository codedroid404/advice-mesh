# AdviceMesh

A multipage Streamlit app that scrapes Reddit activity, finds the best subreddits to post in, tracks replies, and analyzes advice authenticity using Claude.

## What it does

1. **Scrape** a Reddit user's post and comment history
2. **Find** relevant subreddits to cross-post your question
3. **Track** replies across all your posts
4. **Analyze** each reply for authenticity and usefulness with Claude
5. **Chat** with Claude about the collective advice you've received
6. **Discover** new subreddits automatically with AI-powered relevance scoring

## Pages

| Page | Description |
|------|-------------|
| Home | Scrape a user, view community overview with charts |
| Posts | Browse all scraped posts with clickable links |
| Comments | Browse all scraped comments |
| Where to Post | See already posted vs not yet posted, preview/copy posts per subreddit, discover new subs |
| Replies | View replies, quick-analyze individual ones, chat with Claude about all advice |
| Analysis | Batch analyze all replies, filter/sort by authenticity and usefulness, export CSV |

## Setup

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/)
- An [Anthropic API key](https://console.anthropic.com/)

### Install

```bash
# Clone the repo
git clone https://github.com/codedroid404/advice-mesh.git
cd advice-mesh

# Run the setup script (creates venv, installs deps, generates config)
source setup.sh
```

### Configure

Create a `.private_.env` file in the project root (see `.env.example`):

```
CLAUDE_API_KEY=your_anthropic_api_key_here
CLAUDE_BASE_URL=https://api.anthropic.com/v1
CLAUDE_MODEL=claude-sonnet-4-6
```

Then regenerate config:

```bash
source setup.sh
```

### Run

```bash
streamlit run app.py
```

## Testing

```bash
# Run all tests
pytest

# Unit tests only
pytest -m "not integration"

# Integration tests only (hits Reddit + Claude APIs)
pytest -m integration -v -s
```

**52 tests** — 43 unit tests + 9 integration tests covering parsing, formatting, data logic, file I/O, Reddit API, and Claude API.

## Project Structure

```
advice-mesh/
├── app.py                  # Home page — scrape + overview
├── pages/
│   ├── 1_Posts.py          # Posts table
│   ├── 2_Comments.py       # Comments table
│   ├── 3_Where_to_Post.py  # Post distribution + discovery
│   ├── 4_Replies.py        # Replies + chat with Claude
│   └── 5_Analysis.py       # Batch analysis + filters
├── scraper.py              # Reddit user history scraping
├── finder.py               # Subreddit metadata + cross-check
├── replies.py              # Reply fetcher with automod filtering
├── analyzer.py             # Claude-powered comment analysis
├── discovery.py            # Auto-discover new subreddits
├── posting.py              # Posting log persistence
├── post_content.py         # Post title/body templates
├── subreddit_config.py     # Candidate subreddits + config
├── usage_tracker.py        # API token/cost tracking
├── shared.py               # Shared UI helpers
├── logger.py               # Colored terminal logging
├── config.py               # Auto-generated env var loader
├── setup.sh                # Environment setup script
├── test/                   # Unit + integration tests
└── data/                   # Runtime data (gitignored)
    ├── analysis_cache.json
    ├── api_usage.json
    ├── posting_log.json
    ├── discovered_subs.json
    └── qa_log.json
```

## Tech Stack

- **UI:** Streamlit (multipage app)
- **Reddit API:** `requests` + Reddit public JSON API
- **LLM:** Anthropic Claude API
- **Data:** pandas
- **Testing:** pytest
- **Config:** python-dotenv + auto-generated config.py

## License

MIT
