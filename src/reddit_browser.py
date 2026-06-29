"""
Reddit browser scraper (Playwright) — the only path that still works in 2026.

Reddit blocks the anonymous .json API (HTTP 403) and no longer issues OAuth
credentials for personal scripts. But it still serves the HTML website to real
browsers. This module drives a headless Chromium, loads the public HTML pages,
and extracts data from the modern Reddit DOM (`shreddit-post` /
`shreddit-profile-comment` custom elements).

No login, no API keys, no proxies — anonymous, the same data any logged-out
browser sees. Throttle between calls to stay polite (and unblocked).

Empirically verified working for /user/<u>/submitted and /user/<u>/comments even
from flagged datacenter IPs where the .json endpoints 403.
"""

import time
from urllib.parse import quote_plus

from playwright.sync_api import sync_playwright

from src.logger import get_logger

log = get_logger("reddit_browser")

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# polite delay between page loads (seconds). Reddit tolerates real-browser
# traffic; keep this >= a few seconds for personal-volume scraping.
THROTTLE_SECONDS = 4


def _int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _scrape_page(url, extract, settle=4.0, selector=None):
    """
    Load `url` in a headless browser and run `extract(page) -> list`.
    Returns (rows, error_str). error_str is None on success.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            ctx = browser.new_context(user_agent=BROWSER_UA)
            page = ctx.new_page()
            resp = page.goto(url, timeout=30000, wait_until="commit")
            status = resp.status if resp else None
            time.sleep(settle)  # let SPA hydrate / any redirect settle

            html = ""
            try:
                html = page.content()
            except Exception:
                pass
            if "blocked by network security" in html.lower():
                return [], f"blocked by network security (HTTP {status})"

            if selector:
                try:
                    page.wait_for_selector(selector, timeout=10000)
                except Exception:
                    # no elements is not fatal — could be an empty/zero-result page
                    log.warning("selector %s not found on %s", selector, url)

            return extract(page), None
        except Exception as e:  # noqa: BLE001
            return [], str(e)
        finally:
            browser.close()


def scrape_user_posts(username, limit=25):
    """Scrape a user's submitted posts from the HTML profile page."""
    username = username.strip().lstrip("u/").lstrip("/")
    url = f"https://www.reddit.com/user/{username}/submitted/"

    def extract(page):
        rows = []
        for post in page.locator("shreddit-post").all()[:limit]:
            rows.append({
                "subreddit": (post.get_attribute("subreddit-name") or "").strip(),
                "title": (post.get_attribute("post-title") or "").strip(),
                "post_url": "https://reddit.com" + (post.get_attribute("permalink") or ""),
                "score": _int(post.get_attribute("score")),
                "num_comments": _int(post.get_attribute("comment-count")),
                "created_utc": (post.get_attribute("created-timestamp") or ""),
                "post_id": (post.get_attribute("id") or "").strip(),
            })
        return rows

    rows, err = _scrape_page(url, extract, selector="shreddit-post")
    if err:
        log.error("scrape_user_posts(%s) failed: %s", username, err)
    else:
        log.info("scraped %d posts for u/%s", len(rows), username)
    return rows, err


def scrape_user_comments(username, limit=25):
    """Scrape a user's comments from the HTML profile page."""
    username = username.strip().lstrip("u/").lstrip("/")
    url = f"https://www.reddit.com/user/{username}/comments/"

    def extract(page):
        # One JS pass per element: body in `.md`, permalink in href, subreddit +
        # post title from the inner links. Faster and more robust than per-attr.
        raw = page.eval_on_selector_all(
            "shreddit-profile-comment",
            """(els) => els.map(e => {
                const md = e.querySelector('.md, [id$="-comment-rtjson-content"], p');
                const subA = e.querySelector('a[href^="/r/"]');
                const titleA = e.querySelector('a[href*="/comments/"]');
                const href = e.getAttribute('href') || '';
                return {
                    body: md ? md.innerText.trim() : '',
                    permalink: href,
                    comment_id: e.getAttribute('comment-id') || '',
                    subreddit: subA ? (subA.getAttribute('href').split('/')[2] || '') : '',
                    post_title: titleA ? titleA.innerText.trim() : '',
                };
            })""",
        )
        rows = []
        for c in raw[:limit]:
            rows.append({
                "subreddit": c.get("subreddit", ""),
                "body": c.get("body", ""),
                "post_title": c.get("post_title", ""),
                "post_url": "https://reddit.com" + c.get("permalink", ""),
                "score": 0,  # comment score isn't exposed on the profile DOM
                "created_utc": "",
                "comment_id": c.get("comment_id", ""),
            })
        return rows

    rows, err = _scrape_page(url, extract, selector="shreddit-profile-comment")
    if err:
        log.error("scrape_user_comments(%s) failed: %s", username, err)
    else:
        log.info("scraped %d comments for u/%s", len(rows), username)
    return rows, err


def scrape_subreddit_posts(subreddit, limit=25):
    """Scrape recent posts from a public subreddit's HTML page."""
    subreddit = subreddit.strip().lstrip("r/").lstrip("/")
    url = f"https://www.reddit.com/r/{subreddit}/"

    def extract(page):
        rows = []
        for post in page.locator("shreddit-post").all()[:limit]:
            rows.append({
                "subreddit": (post.get_attribute("subreddit-name") or subreddit).strip(),
                "title": (post.get_attribute("post-title") or "").strip(),
                "post_url": "https://reddit.com" + (post.get_attribute("permalink") or ""),
                "score": _int(post.get_attribute("score")),
                "num_comments": _int(post.get_attribute("comment-count")),
                "author": (post.get_attribute("author") or "").strip(),
                "post_id": (post.get_attribute("id") or "").strip(),
            })
        return rows

    rows, err = _scrape_page(url, extract, selector="shreddit-post")
    if err:
        log.error("scrape_subreddit_posts(%s) failed: %s", subreddit, err)
    return rows, err


def search_reddit(query, limit=25):
    """
    Search Reddit posts for a query (live HTML search). This is the entry point
    for the JD-driven flow: derive keywords from the JD, search, then analyze.

    Returns list of {subreddit, title, post_url, post_id}. Search results don't
    expose score/comment-count in the DOM, so those are fetched per-thread later.
    """
    url = f"https://www.reddit.com/search/?q={quote_plus(query)}&type=link"

    def extract(page):
        raw = page.eval_on_selector_all(
            "a[href*='/comments/']",
            "(els) => els.map(a => ({ href: a.getAttribute('href') || '', text: (a.innerText || '').trim() }))",
        )
        seen = set()
        rows = []
        for r in raw:
            href = r["href"]
            parts = href.strip("/").split("/")
            # expect /r/<sub>/comments/<id>/<slug>/
            if len(parts) < 4 or parts[0] != "r" or parts[2] != "comments":
                continue
            pid = parts[3]
            if pid in seen or not r["text"]:
                continue
            seen.add(pid)
            rows.append({
                "subreddit": parts[1],
                "title": r["text"],
                "post_url": "https://reddit.com" + href,
                "post_id": pid,
            })
            if len(rows) >= limit:
                break
        return rows

    rows, err = _scrape_page(url, extract, selector="a[href*='/comments/']", settle=6.0)
    if err:
        log.error("search_reddit(%r) failed: %s", query, err)
    else:
        log.info("search_reddit(%r) -> %d threads", query, len(rows))
    return rows, err


def scrape_post_comments(post_url, limit=50):
    """
    Scrape the top-level comments (the advice/replies) from a post's HTML page.

    Args:
        post_url: full reddit post URL or permalink path.
    Returns list of {author, body, score, comment_id, permalink}.
    """
    if post_url.startswith("/"):
        post_url = "https://reddit.com" + post_url
    if not post_url.startswith("http"):
        post_url = "https://reddit.com/" + post_url.lstrip("/")

    def extract(page):
        raw = page.eval_on_selector_all(
            "shreddit-comment",
            """(els) => els.map(e => {
                const md = e.querySelector('.md, [id$="-comment-rtjson-content"], [slot="comment"], p');
                return {
                    author: e.getAttribute('author') || '',
                    score: e.getAttribute('score') || '',
                    comment_id: e.getAttribute('thingid') || e.getAttribute('comment-id') || '',
                    permalink: e.getAttribute('permalink') || '',
                    body: md ? md.innerText.trim() : '',
                    depth: e.getAttribute('depth') || '0',
                };
            })""",
        )
        rows = []
        # automod / removal noise filter (mirrors replies.py)
        noise = [
            "submission has been automatically removed",
            "does not include one of the required tags",
            "this action was performed automatically",
            "your post has been removed",
        ]
        for c in raw:
            body = c.get("body", "")
            if not body or any(n in body.lower() for n in noise):
                continue
            # top-level comments only (depth 0) keep it focused on direct advice
            if str(c.get("depth", "0")) not in ("0", ""):
                continue
            rows.append({
                "author": c.get("author", "[deleted]"),
                "body": body,
                "score": _int(c.get("score")),
                "comment_id": c.get("comment_id", ""),
                "permalink": "https://reddit.com" + (c.get("permalink", "") or ""),
            })
            if len(rows) >= limit:
                break
        return rows

    rows, err = _scrape_page(post_url, extract, selector="shreddit-comment", settle=5.0)
    if err:
        log.error("scrape_post_comments(%s) failed: %s", post_url, err)
    else:
        log.info("scrape_post_comments -> %d comments from %s", len(rows), post_url)
    return rows, err
