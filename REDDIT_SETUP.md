# Reddit Interview Post Manager — Build Plan

## Overview

A Streamlit app that helps the user find, post to, and monitor the best subreddits for their Shield AI interview question. It scrapes the user's Reddit history, cross-references relevant subreddits, auto-posts to unposted ones, tracks replies, and uses an LLM to analyze comment authenticity.

---

## Context (from conversation history)

- **User:** u/poppinlavish
- **Goal:** Preparing for Shield AI Senior Applications Engineer, Autonomy (Hivemind Catalyst team) — final round C++ code pair on HackerRank
- **Problem:** Posts keep getting removed (karma thresholds, missing tags, automod rules)
- **Post title:** `[Advice] Shield AI - Final Round C++ Code Pair Interview Tips?`
- **Post body:** (see Appendix A)
- **Relevant subreddits identified so far:** r/cscareerquestions, r/leetcode, r/defenseindustry, r/embedded, r/interviews (blocked by karma)

---

## Features

### 1. Scrape User's Reddit History

- Fetch all posts and comments for a given username via Reddit's public JSON API (`/user/{username}/submitted.json`, `/user/{username}/comments.json`)
- Paginate with `after` cursor, respect rate limits (2s delay)
- Store results in a DataFrame: `subreddit`, `post_title`, `post_url`, `type` (post/comment), `created_utc`, `score`, `num_comments`
- Display in Streamlit: metrics cards, bar chart of top communities, full sortable table, CSV download

### 2. Find Best Subreddits for the Post

- Maintain a curated list of candidate subreddits relevant to the topic:

```python
CANDIDATE_SUBS = [
    # Career / interviews
    "cscareerquestions",
    "interviews",
    "leetcode",
    "codinginterview",
    "ExperiencedDevs",
    # Defense / aerospace
    "defenseindustry",
    "AerospaceEngineering",
    "defense",
    # C++ / embedded / robotics
    "cpp",
    "embedded",
    "robotics",
    "ROS",
    # General engineering
    "AskEngineers",
    "engineering",
    # Job hunting
    "jobs",
    "careerguidance",
    "resumes",
    # Autonomy / AI
    "artificial",
    "MachineLearning",
    "autonomousVehicles",
]
```

- For each candidate sub, fetch subreddit metadata via `/r/{sub}/about.json`:
  - `subscribers` count
  - `public_description`
  - Posting rules (if available)
  - Whether the sub requires flair/tags
- Score/rank subs by relevance (keyword match to post topic) and reach (subscriber count)
- Display ranked list in Streamlit with relevance score, subscriber count, and any known posting rules

### 3. Cross-Check: Already Posted vs. Not Yet Posted

- Compare the user's post history (from Step 1) against the candidate list (from Step 2)
- Produce two lists:
  - **Already posted:** subreddit, post title, post URL, date, score, number of replies
  - **Not yet posted:** subreddit, subscriber count, relevance score, known posting rules/gotchas
- Display both lists in Streamlit with clear visual separation

### 4. Auto-Post to Subreddits (requires Reddit API auth)

> **Important:** This feature requires OAuth2 authentication via Reddit's API (not the public JSON endpoints). The user must create a Reddit app at https://www.reddit.com/prefs/apps and provide credentials.

#### 4a. Setup

- Use PRAW (Python Reddit API Wrapper): `pip install praw`
- Credentials needed (store in `.env` or Streamlit secrets):
  - `REDDIT_CLIENT_ID`
  - `REDDIT_CLIENT_SECRET`
  - `REDDIT_USERNAME`
  - `REDDIT_PASSWORD`
  - `REDDIT_USER_AGENT`

#### 4b. Posting Logic

```python
import praw

reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    username=username,
    password=password,
    user_agent=user_agent,
)

def post_to_subreddit(sub_name, title, body, flair=None):
    subreddit = reddit.subreddit(sub_name)
    submission = subreddit.submit(title=title, selftext=body, flair_id=flair)
    return submission.url
```

#### 4c. Safety Features

- **Preview mode (default):** Show what would be posted without actually posting
- **Rate limiting:** Wait 10 minutes between posts to avoid Reddit spam filters
- **Tag/flair handling:** Per-subreddit title tag map (e.g., r/interviews requires `[Advice]`)
- **Karma check:** Warn if the user's karma is below common thresholds
- **Confirmation:** Require user to click "Confirm Post" for each subreddit
- **Post log:** Record all posts (subreddit, URL, timestamp, status) to a local JSON file

#### 4d. Per-Subreddit Config

```python
SUB_CONFIG = {
    "interviews": {"tag": "[Advice]", "min_karma": 50},
    "cscareerquestions": {"tag": None, "min_karma": 0},
    "leetcode": {"tag": None, "min_karma": 0},
    "defenseindustry": {"tag": None, "min_karma": 0},
    "embedded": {"tag": None, "min_karma": 0},
    "cpp": {"tag": None, "min_karma": 0},
    # Add more as discovered
}
```

### 5. Track Replies on Existing Posts

- For each post the user has made (from Step 1), fetch comments via `/comments/{post_id}.json`
- Extract: `author`, `body`, `score`, `created_utc`, `permalink`
- Display in Streamlit grouped by post, sorted by score
- Highlight new replies since last check (store last check timestamp locally)

### 6. LLM-Powered Comment Analysis

- For each reply collected in Step 5, send to an LLM for analysis
- Use the Anthropic API (user has access):

```python
import anthropic

client = anthropic.Anthropic(api_key=api_key)

def analyze_comment(comment_body, post_context):
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{
            "role": "user",
            "content": f"""Analyze this Reddit comment replying to a post about preparing for a Shield AI C++ code pair interview.

Post context: Preparing for Senior Applications Engineer, Autonomy role. Final round C++ code pair on HackerRank.

Comment:
\"\"\"{comment_body}\"\"\"

Provide:
1. **Authenticity score** (1-10): Does this seem like genuine advice or a disguised product plug/ad?
2. **Signals:** What makes it seem genuine or promotional?
3. **Actionable advice extracted:** List any concrete prep tips worth following.
4. **Products mentioned:** Flag any tools/products mentioned and whether the mention feels organic or forced.
5. **Overall verdict:** Genuine / Likely promotional / Mixed"""
        }]
    )
    return message.content[0].text
```

- Display analysis in Streamlit with color-coded authenticity scores:
  - 8-10: Green (genuine)
  - 5-7: Yellow (mixed/uncertain)
  - 1-4: Red (likely promotional)

---

## Tech Stack

| Component | Tool |
|---|---|
| UI | Streamlit |
| Reddit scraping (public) | `requests` + Reddit JSON API |
| Reddit posting (auth) | `praw` |
| LLM analysis | Anthropic API (`anthropic` SDK) |
| Data | `pandas` |
| Config | `.env` file or Streamlit secrets |
| Storage | Local JSON files for post log + reply cache |

## Dependencies

```
streamlit
requests
pandas
praw
anthropic
python-dotenv
```

---

## File Structure

```
reddit_shield_ai_tool/
├── app.py                  # Main Streamlit app
├── scraper.py              # Reddit scraping (public JSON API)
├── poster.py               # Reddit posting (PRAW / OAuth)
├── analyzer.py             # LLM comment analysis (Anthropic API)
├── config.py               # Subreddit configs, candidate list, constants
├── post_content.py         # Post title and body templates
├── .env                    # Reddit + Anthropic API credentials
├── data/
│   ├── post_log.json       # Record of all posts made
│   └── reply_cache.json    # Cached replies + analysis
└── requirements.txt
```

---

## Streamlit App Layout

```
┌─────────────────────────────────────────────┐
│  Reddit Interview Post Manager              │
│  ─────────────────────────────────────────── │
│  [Username input]  [🚀 Scrape]              │
├─────────────────────────────────────────────┤
│  Tab 1: My Reddit History                   │
│    - Metrics: communities, posts, comments  │
│    - Bar chart top 15 subs                  │
│    - Full table + CSV download              │
├─────────────────────────────────────────────┤
│  Tab 2: Best Subreddits to Post             │
│    - Ranked list with relevance + reach     │
│    - ✅ Already posted  │  ❌ Not yet posted │
│    - Post button per sub (preview mode)     │
├─────────────────────────────────────────────┤
│  Tab 3: Post & Track                        │
│    - Post preview with per-sub tag handling │
│    - [Confirm & Post] buttons               │
│    - Post log table                         │
├─────────────────────────────────────────────┤
│  Tab 4: Replies & Analysis                  │
│    - Replies grouped by post                │
│    - LLM analysis per comment               │
│    - Authenticity score with color coding   │
│    - Actionable advice summary              │
└─────────────────────────────────────────────┘
```

---

## Appendix A: Post Content

**Title:** `[Advice] Shield AI - Final Round C++ Code Pair Interview Tips?`

**Body:**

Interviewing for Senior Applications Engineer, Autonomy (Hivemind Catalyst team) at Shield AI. I've passed the recruiter screen and hiring manager interview, and now have the final round — a C++ code pair on HackerRank with a team engineer.

The earlier technical round had relatively straightforward C++ questions (vector iteration, removing elements from an array). Has anyone done the final code pair stage? What level of difficulty should I expect — LC easy/medium/hard? Any particular topics I should focus on?

I have two weeks to prep. Any advice appreciated.

---

## Implementation Order

1. **Phase 1:** Scraper (public API) — already built, enhance with post URL tracking
2. **Phase 2:** Candidate subreddit finder + cross-check logic
3. **Phase 3:** Reply fetcher for existing posts
4. **Phase 4:** LLM comment analyzer integration
5. **Phase 5:** Auto-poster with PRAW (requires user to set up Reddit OAuth app)
6. **Phase 6:** Polish UI, add post log persistence, error handling

---

## Setup Instructions for User

1. `pip install -r requirements.txt`
2. Create a Reddit app at https://www.reddit.com/prefs/apps (select "script" type)
3. Get an Anthropic API key from https://console.anthropic.com
4. Create `.env` file:

```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=poppinlavish
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=ShieldAIInterviewBot/1.0
ANTHROPIC_API_KEY=your_api_key
```

5. Run: `streamlit run app.py`