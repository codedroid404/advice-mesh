"""Unit tests for domain-based subreddit selection."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.subreddit_config import SUB_DOMAINS, CANDIDATE_SUBS, get_subs_for_domains


def test_all_domains_have_subs():
    """Every domain should have at least one subreddit."""
    for domain, subs in SUB_DOMAINS.items():
        assert len(subs) > 0, f"Domain '{domain}' has no subreddits"


def test_candidate_subs_matches_domains():
    """CANDIDATE_SUBS should contain all subs from all domains."""
    all_from_domains = []
    for subs in SUB_DOMAINS.values():
        all_from_domains.extend(subs)
    assert set(CANDIDATE_SUBS) == set(all_from_domains)


def test_get_subs_single_domain():
    """Selecting one domain should return only its subs."""
    defense_subs = get_subs_for_domains(["Defense / Aerospace"])
    assert "defenseindustry" in defense_subs
    assert "leetcode" not in defense_subs


def test_get_subs_multiple_domains():
    """Selecting multiple domains should return merged subs."""
    subs = get_subs_for_domains(["Defense / Aerospace", "FAANG / Big Tech"])
    assert "defenseindustry" in subs
    assert "leetcode" in subs
    assert "embedded" not in subs


def test_get_subs_all_domains():
    """Selecting all domains should return all candidate subs."""
    subs = get_subs_for_domains(list(SUB_DOMAINS.keys()))
    assert set(s.lower() for s in subs) == set(s.lower() for s in CANDIDATE_SUBS)


def test_get_subs_empty():
    """No domains selected should return empty list."""
    subs = get_subs_for_domains([])
    assert subs == []


def test_get_subs_invalid_domain():
    """Invalid domain name should be ignored."""
    subs = get_subs_for_domains(["Nonexistent Domain"])
    assert subs == []


def test_get_subs_no_duplicates():
    """Result should have no duplicate subreddits."""
    subs = get_subs_for_domains(list(SUB_DOMAINS.keys()))
    assert len(subs) == len(set(s.lower() for s in subs))
