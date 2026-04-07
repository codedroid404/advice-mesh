# AdviceMesh — Claude Code Project Guide

## Project Overview
AdviceMesh is a multipage Streamlit app for job seekers who use Reddit to prepare for interviews. It scrapes Reddit activity, finds relevant subreddits, tracks replies, and uses Claude to analyze advice authenticity.

## Architecture

```
app.py                          # Home page — scrape + overview + inline analysis
pages/
  0_Settings.py                 # API key + connectivity test
  1_Posts.py                    # Posts table
  2_Comments.py                 # Comments table
  3_Where_to_Post.py            # Post distribution + discovery
  4_Replies_&_Analysis.py       # Replies + batch analysis + chat
src/
  config.py                     # Settings loader (JSON or .env)
  scraper.py                    # Reddit JSON API scraping
  finder.py                     # Subreddit metadata + cross-check
  replies.py                    # Reply fetcher with automod filtering
  analyzer.py                   # Claude API — comment analysis + sub filtering
  discovery.py                  # Auto-discover subreddits with Claude
  posting.py                    # Posting log persistence
  post_content.py               # Post formatting per subreddit
  subreddit_config.py           # Candidate subs + domain config
  usage_tracker.py              # API token/cost tracking
  shared.py                     # Shared sidebar + helpers
  logger.py                     # Colored terminal logging
test/                           # pytest unit + integration tests
data/                           # Runtime JSON files (gitignored)
```

## Key Patterns

### Session State
- `st.session_state["scraped"]` gates all pages — check with `require_scrape()` from `shared.py`
- Widget keys (e.g. `key="interview_stage"`) auto-manage their own session state — never set them manually after widget creation
- Clear `analyzed_df` and `chat_history` on new scrape

### Caching
- `@st.cache_data(ttl=300)` on `scrape_user()` and `fetch_sub_metadata()`
- Do NOT cache functions with Streamlit callbacks (`on_status` params)

### Progress
- Use `st.status()` for multi-step pipelines (scrape, analysis)
- Use `st.progress()` inside `st.status()` for per-item progress
- Use `st.spinner()` for quick single-step operations

### API Calls
- All Claude calls go through `src/analyzer.py` or `src/discovery.py`
- Always call `track_usage(response_json, model=MODEL)` after successful API calls
- Rate limit Reddit calls with 2s sleep between requests

## Commands

```bash
streamlit run app.py              # Run the app
pytest                            # Run all tests
pytest -m "not integration"       # Unit tests only
pytest -m integration -v -s       # Integration tests (hits APIs)
source setup.sh                   # Regenerate config + install deps
```

## Testing
- 74 tests total (64 unit + 10 integration)
- Integration tests marked with `@pytest.mark.integration`
- Integration tests skip gracefully on no API credits
- Tests use `sys.path.insert` to find `src/` modules
- File I/O tests use `tmp_path` and `monkeypatch` fixtures

## Config
- Primary: `data/settings.json` (set via Settings page)
- Fallback: `.private_.env` (loaded by `python-dotenv`)
- Required vars: `CLAUDE_API_KEY`, `CLAUDE_BASE_URL`, `CLAUDE_MODEL`
