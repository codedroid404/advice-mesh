"""
Reddit MCP server — exposes the Playwright browser scraper as MCP tools so an AI
agent (Claude Desktop, Cursor, Windsurf) can pull live public Reddit data.

Backend: src/reddit_browser.py (anonymous headless-Chromium HTML scraping — the
only path that still works in 2026: no API keys, no login, no proxies).

Run locally (stdio transport):
    python reddit_mcp_server.py

Register in Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "reddit": {
          "command": "/Users/sitasanon/src/redditScraper/.venv/bin/python",
          "args": ["/Users/sitasanon/src/redditScraper/reddit_mcp_server.py"]
        }
      }
    }

NOTE: scraping is synchronous/blocking (Playwright sync API). Each tool runs the
scrape in a worker thread so the async MCP loop is never blocked.
"""

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from src import reddit_browser

mcp = FastMCP("Reddit Scraper")


async def _run(fn, *args):
    """Run a blocking scraper fn in a thread and return (rows, err)."""
    return await asyncio.to_thread(fn, *args)


@mcp.tool()
async def get_user_posts(username: str, limit: int = 25) -> str:
    """
    Get a Reddit user's recent submitted posts (live, public data).

    Args:
        username: Reddit username, with or without the 'u/' prefix.
        limit: Max number of posts to return (default 25).

    Returns: JSON list of {subreddit, title, post_url, score, num_comments, post_id}.
    """
    rows, err = await _run(reddit_browser.scrape_user_posts, username, limit)
    if err:
        return f"Error scraping u/{username} posts: {err}"
    return json.dumps(rows, indent=2)


@mcp.tool()
async def get_user_comments(username: str, limit: int = 25) -> str:
    """
    Get a Reddit user's recent comments (live, public data).

    Args:
        username: Reddit username, with or without the 'u/' prefix.
        limit: Max number of comments to return (default 25).

    Returns: JSON list of {subreddit, body, post_title, post_url, comment_id}.
    """
    rows, err = await _run(reddit_browser.scrape_user_comments, username, limit)
    if err:
        return f"Error scraping u/{username} comments: {err}"
    return json.dumps(rows, indent=2)


@mcp.tool()
async def search_reddit(query: str, limit: int = 25) -> str:
    """
    Search Reddit for posts matching a query (live, public data). Use this to
    find threads relevant to a topic (e.g. interview advice for a role).

    Args:
        query: Free-text search query.
        limit: Max number of threads to return (default 25).

    Returns: JSON list of {subreddit, title, post_url, post_id}.
    """
    rows, err = await _run(reddit_browser.search_reddit, query, limit)
    if err:
        return f"Error searching Reddit for {query!r}: {err}"
    return json.dumps(rows, indent=2)


@mcp.tool()
async def get_post_comments(post_url: str, limit: int = 50) -> str:
    """
    Get the top-level comments (replies/advice) on a Reddit post (live, public).

    Args:
        post_url: Full Reddit post URL or permalink.
        limit: Max number of comments to return (default 50).

    Returns: JSON list of {author, body, score, comment_id, permalink}.
    """
    rows, err = await _run(reddit_browser.scrape_post_comments, post_url, limit)
    if err:
        return f"Error fetching comments for {post_url}: {err}"
    return json.dumps(rows, indent=2)


@mcp.tool()
async def get_subreddit_posts(subreddit: str, limit: int = 25) -> str:
    """
    Get recent posts from a public subreddit (live, public data).

    Args:
        subreddit: Subreddit name, with or without the 'r/' prefix.
        limit: Max number of posts to return (default 25).

    Returns: JSON list of {subreddit, title, post_url, score, num_comments, author, post_id}.
    """
    rows, err = await _run(reddit_browser.scrape_subreddit_posts, subreddit, limit)
    if err:
        return f"Error scraping r/{subreddit}: {err}"
    return json.dumps(rows, indent=2)


if __name__ == "__main__":
    mcp.run()
