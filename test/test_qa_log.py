"""Unit tests for Q&A log persistence."""

import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _save_qa(qa_file, data_dir, username, question, answer, num_replies):
    """Replicate the Q&A save logic from app.py."""
    os.makedirs(data_dir, exist_ok=True)
    qa_log = []
    if os.path.exists(qa_file):
        with open(qa_file, "r") as f:
            qa_log = json.load(f)
    qa_log.append({
        "username": username,
        "question": question,
        "answer": answer,
        "num_replies": num_replies,
    })
    with open(qa_file, "w") as f:
        json.dump(qa_log, f, indent=2)


def test_qa_log_creates_file(tmp_path):
    """First Q&A should create the file."""
    qa_file = str(tmp_path / "qa_log.json")
    _save_qa(qa_file, str(tmp_path), "testuser", "What topics?", "Focus on STL.", 5)

    assert os.path.exists(qa_file)
    with open(qa_file) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["question"] == "What topics?"
    assert data[0]["answer"] == "Focus on STL."


def test_qa_log_appends(tmp_path):
    """Multiple Q&As should append, not overwrite."""
    qa_file = str(tmp_path / "qa_log.json")
    _save_qa(qa_file, str(tmp_path), "testuser", "Q1?", "A1", 5)
    _save_qa(qa_file, str(tmp_path), "testuser", "Q2?", "A2", 5)

    with open(qa_file) as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]["question"] == "Q1?"
    assert data[1]["question"] == "Q2?"


def test_qa_log_structure(tmp_path):
    """Verify all expected fields are present."""
    qa_file = str(tmp_path / "qa_log.json")
    _save_qa(qa_file, str(tmp_path), "poppinlavish", "Best advice?", "Study STL.", 10)

    with open(qa_file) as f:
        entry = json.load(f)[0]
    assert entry["username"] == "poppinlavish"
    assert entry["num_replies"] == 10
