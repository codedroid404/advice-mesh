"""Unit tests for file I/O — posting log and discovery persistence."""

import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import posting
import discovery


# --- posting.py ---

def test_mark_and_get_posted(tmp_path, monkeypatch):
    """Mark a sub as posted, then verify it appears in get_posted_subs."""
    log_file = str(tmp_path / "posting_log.json")
    monkeypatch.setattr(posting, "POSTING_LOG", log_file)
    monkeypatch.setattr(posting, "DATA_DIR", str(tmp_path))

    posting.mark_as_posted("testuser", "leetcode", url="https://reddit.com/r/leetcode/123")
    subs = posting.get_posted_subs("testuser")

    assert "leetcode" in subs


def test_get_posted_empty(tmp_path, monkeypatch):
    """No posting log file — should return empty set."""
    log_file = str(tmp_path / "posting_log.json")
    monkeypatch.setattr(posting, "POSTING_LOG", log_file)

    subs = posting.get_posted_subs("nonexistent")
    assert subs == set()


def test_mark_multiple_subs(tmp_path, monkeypatch):
    """Mark multiple subs and verify all appear."""
    log_file = str(tmp_path / "posting_log.json")
    monkeypatch.setattr(posting, "POSTING_LOG", log_file)
    monkeypatch.setattr(posting, "DATA_DIR", str(tmp_path))

    posting.mark_as_posted("testuser", "leetcode")
    posting.mark_as_posted("testuser", "cpp")
    posting.mark_as_posted("testuser", "embedded")

    subs = posting.get_posted_subs("testuser")
    assert subs == {"leetcode", "cpp", "embedded"}


def test_posting_log_structure(tmp_path, monkeypatch):
    """Verify the JSON structure of the posting log."""
    log_file = str(tmp_path / "posting_log.json")
    monkeypatch.setattr(posting, "POSTING_LOG", log_file)
    monkeypatch.setattr(posting, "DATA_DIR", str(tmp_path))

    posting.mark_as_posted("testuser", "leetcode", url="https://example.com")

    with open(log_file) as f:
        data = json.load(f)

    assert "testuser" in data
    assert "leetcode" in data["testuser"]
    assert data["testuser"]["leetcode"]["url"] == "https://example.com"
    assert "posted_at" in data["testuser"]["leetcode"]


# --- discovery.py ---

def test_save_and_load_discovered(tmp_path, monkeypatch):
    """Save approved/rejected subs and load them back."""
    disc_file = str(tmp_path / "discovered_subs.json")
    monkeypatch.setattr(discovery, "DISCOVERED_FILE", disc_file)
    monkeypatch.setattr(discovery, "DATA_DIR", str(tmp_path))

    discovery.save_discovered_subs(
        approved=["newSub1", "newSub2"],
        rejected=["badSub1"],
    )

    data = discovery.load_discovered_subs()
    assert "newsub1" in data["approved"]
    assert "newsub2" in data["approved"]
    assert "badsub1" in data["rejected"]


def test_load_discovered_no_file(tmp_path, monkeypatch):
    """No file — should return defaults."""
    disc_file = str(tmp_path / "discovered_subs.json")
    monkeypatch.setattr(discovery, "DISCOVERED_FILE", disc_file)

    data = discovery.load_discovered_subs()
    assert data == {"approved": [], "rejected": []}


def test_rejected_subs(tmp_path, monkeypatch):
    """Rejected subs should be returned as a lowercase set."""
    disc_file = str(tmp_path / "discovered_subs.json")
    monkeypatch.setattr(discovery, "DISCOVERED_FILE", disc_file)
    monkeypatch.setattr(discovery, "DATA_DIR", str(tmp_path))

    discovery.save_discovered_subs(approved=[], rejected=["BadSub"])
    rejected = discovery.load_rejected_subs()

    assert "badsub" in rejected


def test_approve_overrides_reject(tmp_path, monkeypatch):
    """Approving a previously rejected sub should remove it from rejected."""
    disc_file = str(tmp_path / "discovered_subs.json")
    monkeypatch.setattr(discovery, "DISCOVERED_FILE", disc_file)
    monkeypatch.setattr(discovery, "DATA_DIR", str(tmp_path))

    discovery.save_discovered_subs(approved=[], rejected=["flipflop"])
    discovery.save_discovered_subs(approved=["flipflop"], rejected=[])

    data = discovery.load_discovered_subs()
    assert "flipflop" in data["approved"]
    assert "flipflop" not in data["rejected"]
