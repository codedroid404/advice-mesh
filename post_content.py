"""
Post content template and per-subreddit formatting.

Usage:
    from post_content import POST_TITLE, POST_BODY, format_for_subreddit
"""

from subreddit_config import SUB_CONFIG

POST_TITLE = "[Advice] Shield AI - Final Round C++ Code Pair Interview Tips?"

POST_BODY = """\
Interviewing for Senior Applications Engineer, Autonomy (Hivemind Catalyst team) at Shield AI. \
I've passed the recruiter screen and hiring manager interview, and now have the final round — \
a C++ code pair on HackerRank with a team engineer.

The earlier technical round had relatively straightforward C++ questions (vector iteration, \
removing elements from an array). Has anyone done the final code pair stage? What level of \
difficulty should I expect — LC easy/medium/hard? Any particular topics I should focus on?

I have two weeks to prep. Any advice appreciated."""


def format_for_subreddit(sub_name):
    """
    Format the post title and body for a specific subreddit.
    Applies per-sub tags from SUB_CONFIG (e.g. [Advice] for r/interviews).

    Returns:
        (title, body) tuple
    """
    config = SUB_CONFIG.get(sub_name, {})
    tag = config.get("tag")
    title = POST_TITLE

    if tag:
        # If the sub requires a tag and it's not already in the title, prepend it
        if tag not in title:
            title = f"{tag} {title}"
    else:
        # If sub doesn't use tags, strip any existing tag prefix like [Advice]
        if title.startswith("["):
            closing = title.find("]")
            if closing != -1:
                title = title[closing + 1:].strip()

    return title, POST_BODY
