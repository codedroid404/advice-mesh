# Streamlit Guide for AdviceMesh

Reference guide for the Streamlit patterns and components used in this project, based on the [Streamlit Fundamentals](https://docs.streamlit.io/get-started/fundamentals).

---

## Architecture

### Multipage App

AdviceMesh uses Streamlit's [multipage app](https://docs.streamlit.io/develop/concepts/multipage-apps) pattern:

```
app.py              # Home page (entry point)
pages/
  0_Settings.py     # API configuration
  1_Posts.py        # Posts table
  2_Comments.py     # Comments table
  3_Where_to_Post.py  # Post distribution
  4_Replies_&_Analysis.py  # Replies + analysis + chat
```

Run with `streamlit run app.py`. Streamlit auto-discovers pages in the `pages/` directory. Files are sorted by the numeric prefix.

### Session State

[`st.session_state`](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state) persists data across page navigation and reruns.

**Keys used in AdviceMesh:**

| Key | Type | Set by | Purpose |
|-----|------|--------|---------|
| `scraped` | bool | app.py | Gate — pages check this before rendering |
| `username` | str | app.py | Current Reddit username |
| `posts_df` | DataFrame | app.py | Scraped posts |
| `comments_df` | DataFrame | app.py | Scraped comments |
| `summary_df` | DataFrame | app.py | Community summary |
| `already_df` | DataFrame | app.py | Already-posted subreddits |
| `not_yet_df` | DataFrame | app.py | Not-yet-posted subreddits |
| `replies_df` | DataFrame | app.py | Fetched replies |
| `analyzed_df` | DataFrame | page 4 | Analysis results |
| `chat_history` | list | page 4 | Chat conversation |
| `job_description` | str | app.py | Uploaded JD text |
| `interview_stage` | str | widget | Interview stage (auto-managed by widget key) |
| `discovered_df` | DataFrame | page 3 | Discovery results |

**Widget keys:** When a widget uses `key="interview_stage"`, Streamlit auto-manages `st.session_state["interview_stage"]`. Do NOT set it manually after the widget is created — this causes `StreamlitAPIException`.

### Caching

[`@st.cache_data`](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data) caches function return values:

```python
@st.cache_data(ttl=300, show_spinner=False)
def scrape_user(username):
    ...
```

- `ttl=300` — cache expires after 5 minutes
- `show_spinner=False` — we handle our own progress UI
- Used on `scrape_user()` and `fetch_sub_metadata()` to avoid redundant Reddit API calls

---

## UI Components Used

### Layout

| Component | Usage | Docs |
|-----------|-------|------|
| `st.columns()` | Side-by-side layout (metrics, inputs) | [columns](https://docs.streamlit.io/develop/api-reference/layout/st.columns) |
| `st.container(border=True)` | Bordered card groups | [container](https://docs.streamlit.io/develop/api-reference/layout/st.container) |
| `st.expander()` | Collapsible sections (reply details) | [expander](https://docs.streamlit.io/develop/api-reference/layout/st.expander) |
| `st.tabs()` | Tab groups within a page | [tabs](https://docs.streamlit.io/develop/api-reference/layout/st.tabs) |
| `st.sidebar` | Persistent sidebar across pages | [sidebar](https://docs.streamlit.io/develop/api-reference/layout/st.sidebar) |
| `st.divider()` | Visual separator | [divider](https://docs.streamlit.io/develop/api-reference/text/st.divider) |

### Input

| Component | Usage | Docs |
|-----------|-------|------|
| `st.text_input()` | Username, search queries | [text_input](https://docs.streamlit.io/develop/api-reference/widgets/st.text_input) |
| `st.text_area()` | Job description, interview stage | [text_area](https://docs.streamlit.io/develop/api-reference/widgets/st.text_area) |
| `st.file_uploader()` | PDF upload | [file_uploader](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader) |
| `st.button()` | Scrape, analyze, mark-as-posted | [button](https://docs.streamlit.io/develop/api-reference/widgets/st.button) |
| `st.selectbox()` | Reply selector, sort dropdown | [selectbox](https://docs.streamlit.io/develop/api-reference/widgets/st.selectbox) |
| `st.slider()` | Min score filters | [slider](https://docs.streamlit.io/develop/api-reference/widgets/st.slider) |
| `st.multiselect()` | Domain selection | [multiselect](https://docs.streamlit.io/develop/api-reference/widgets/st.multiselect) |
| `st.chat_input()` | Chat with Claude | [chat_input](https://docs.streamlit.io/develop/api-reference/chat/st.chat_input) |

### Data Display

| Component | Usage | Docs |
|-----------|-------|------|
| `st.dataframe()` | Tables with column config | [dataframe](https://docs.streamlit.io/develop/api-reference/data/st.dataframe) |
| `st.metric()` | KPI cards (communities, posts, scores) | [metric](https://docs.streamlit.io/develop/api-reference/data/st.metric) |
| `st.bar_chart()` | Community activity chart | [bar_chart](https://docs.streamlit.io/develop/api-reference/charts/st.bar_chart) |
| `st.column_config` | Typed columns (Link, Progress, Number) | [column_config](https://docs.streamlit.io/develop/api-reference/data/st.column_config) |

### Status & Feedback

| Component | Usage | Docs |
|-----------|-------|------|
| `st.status()` | Multi-step progress (scrape pipeline) | [status](https://docs.streamlit.io/develop/api-reference/status/st.status) |
| `st.progress()` | Per-reply progress bar during analysis | [progress](https://docs.streamlit.io/develop/api-reference/status/st.progress) |
| `st.spinner()` | Quick single-step loading | [spinner](https://docs.streamlit.io/develop/api-reference/status/st.spinner) |
| `st.toast()` | Non-blocking notifications | [toast](https://docs.streamlit.io/develop/api-reference/status/st.toast) |
| `st.success/error/warning/info()` | Status messages | [status elements](https://docs.streamlit.io/develop/api-reference/status) |
| `st.stop()` | Halt page rendering (guard pattern) | [stop](https://docs.streamlit.io/develop/api-reference/execution-flow/st.stop) |
| `st.rerun()` | Force full page rerun | [rerun](https://docs.streamlit.io/develop/api-reference/execution-flow/st.rerun) |

### Chat

| Component | Usage | Docs |
|-----------|-------|------|
| `st.chat_message()` | Render user/assistant messages | [chat_message](https://docs.streamlit.io/develop/api-reference/chat/st.chat_message) |
| `st.chat_input()` | Text input anchored to bottom | [chat_input](https://docs.streamlit.io/develop/api-reference/chat/st.chat_input) |

---

## Patterns

### Guard Pattern
Pages that need scraped data use `require_scrape()` from `shared.py`:
```python
def require_scrape():
    if not st.session_state.get("scraped"):
        st.info("Go to Home page and scrape first.", icon="👈")
        st.stop()
```

### Form Pattern
Use `st.form()` when you want to batch inputs before submitting (prevents reruns on each keystroke):
```python
with st.form("search_form"):
    query = st.text_input("Search")
    submitted = st.form_submit_button("Go")
if submitted:
    ...
```

### Status Pipeline Pattern
For multi-step operations, use `st.status()` with step-by-step `st.write()`:
```python
with st.status("Processing...", expanded=True) as status:
    st.write("Step 1...")
    # do work
    st.write("✅ Step 1 complete")
    st.write("Step 2...")
    # do work
    status.update(label="Done!", state="complete")
```

### Progress Inside Status
For granular progress within a step:
```python
with st.status("Analyzing...", expanded=True) as status:
    bar = st.progress(0)
    for i, item in enumerate(items):
        process(item)
        bar.progress((i + 1) / len(items))
    status.update(label="Complete", state="complete")
```

---

## Tips

- **`st.rerun()`** — use sparingly, only when session state changes need to reflect immediately (e.g., after mark-as-posted)
- **Widget keys** — always assign `key=` for widgets whose values you read from `session_state` on other pages
- **`use_container_width=True`** — makes buttons and dataframes stretch to full width
- **`anchor=False`** on `st.subheader()` — removes the anchor link icon for cleaner headers
- **`st.stop()`** — use as a guard to prevent rendering below a condition check
- **`horizontal=True`** on `st.bar_chart()` — better for long labels like subreddit names
