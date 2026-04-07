# 📋 Changelog

All notable changes to AdviceMesh are documented here.

---

## [1.0.0] — 2026-04-07

### 🎉 Initial Release

**Core Features:**
- 🔍 Reddit user history scraping (posts + comments) via public JSON API
- 🎯 Candidate subreddit finder with relevance scoring
- ✅ Cross-check: already posted vs not yet posted
- 📩 Reply fetcher with automod message filtering
- 🤖 Claude-powered authenticity + usefulness analysis
- 💬 Chat interface for asking Claude about all replies
- 🔎 Auto-discover new subreddits with AI relevance evaluation
- 📋 Post preview with per-subreddit tag formatting and copy-to-clipboard
- ✅ Mark-as-posted workflow with posting log
- 💰 API usage tracking with cost estimates
- 💾 Persistent storage for analysis, Q&A logs, posting log, and discovered subs

**UI:**
- 📡 Multipage Streamlit app (Home, Posts, Comments, Where to Post, Replies, Analysis)
- 📊 Interactive bar charts and metrics dashboard
- 🔍 Filterable/sortable analysis results
- 💡 Aggregated "Top Tips" extraction
- ⬇️ CSV export for communities and analysis
- 🗂️ Rich column config with clickable links, progress bars, formatted numbers

**Architecture:**
- 🗂️ Organized `src/` package for backend modules
- 🧪 52 tests (43 unit + 9 integration)
- ⚙️ Auto-generated `config.py` via `setup.sh`
- 📦 Poetry for dependency management
- 🔒 Secrets managed via `.private_.env` (gitignored)
- ⚡ `@st.cache_data` caching on Reddit API calls (5 min TTL)

**Tech Stack:**
- Streamlit (multipage app)
- Anthropic Claude API (analysis, discovery, chat)
- Reddit public JSON API
- pandas, requests, pytest
