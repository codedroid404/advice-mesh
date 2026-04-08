# 📋 Changelog

All notable changes to AdviceMesh are documented here.

---

## [1.1.0] — 2026-04-07

### 🚀 Major Update

**New Features:**
- 📄 PDF job description upload (PyMuPDF) or paste text
- 📝 Interview stage text input for context-aware analysis
- 🧠 Claude-powered subreddit relevance filter (removes unrelated communities from results)
- 📊 Inline analysis insights on home page (metrics, top tips, top replies)
- ⬇️ Download chat responses as markdown files
- 💬 Multi-turn chat with Claude about all replies (with conversation history)
- ⚙️ Settings page for API key configuration and connectivity test
- 🗑️ Clear cached data button in sidebar
- 🖨️ Print-to-PDF support via Streamlit app menu

**UI Improvements:**
- 📩 Consolidated Replies + Analysis into single page with 3 tabs (Replies, Batch Analysis, Chat)
- 📊 Horizontal bar charts for better subreddit name readability
- 🏆 Top 3 communities cards on home page
- 🔍 Step-by-step scrape progress with counts and checkmarks
- 📊 `st.progress` bar inside `st.status` for batch analysis
- 🗂️ `st.column_config` on all dataframes (LinkColumn, ProgressColumn, NumberColumn)
- 🔗 `st.link_button` for Reddit links
- 📋 `st.form` for discovery search and chat input
- 🔔 `st.toast` for non-blocking notifications

**Architecture:**
- 🗂️ Organized `src/` package for all backend modules
- ⚡ `@st.cache_data(ttl=300)` on all API functions (scraper, finder, replies, discovery)
- 💾 Analysis cache restored from disk on re-scrape (no re-analyzing)
- 🔧 Config loads from Settings page (JSON) or `.private_.env`
- 📐 CLAUDE.md + `.claude/rules/streamlit.md` for Claude Code best practices
- 🎓 Streamlit agent skills installed
- 🧪 74 tests (64 unit + 10 integration)

**Bug Fixes:**
- Fixed `use_container_width` deprecation warnings
- Fixed `st.session_state` widget key conflict with `interview_stage`
- Fixed analysis cache not restoring `analyzed_df` to session state
- Fixed `config` import missing on home page analyze button
- Fixed `cost` vs `cost_usd` key mismatch in usage tracker

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
- 🧪 52 tests (43 unit + 9 integration)
- ⚙️ Auto-generated `config.py` via `setup.sh`
- 📦 Poetry for dependency management
- 🔒 Secrets managed via `.private_.env` (gitignored)

**Tech Stack:**
- Streamlit (multipage app)
- Anthropic Claude API (analysis, discovery, chat)
- Reddit public JSON API
- pandas, requests, pytest
