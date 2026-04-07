"""Unit tests for analyzer parsing functions."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analyzer import parse_score, parse_usefulness, parse_key_tips


# --- parse_score ---

def test_parse_score_valid():
    text = "Authenticity: 8\nSignals: genuine advice"
    assert parse_score(text) == 8


def test_parse_score_with_slash():
    text = "Authenticity: 7/10\nSignals: looks real"
    assert parse_score(text) == 7


def test_parse_score_missing():
    text = "No authenticity line here"
    assert parse_score(text) == 0


def test_parse_score_malformed():
    text = "Authenticity: high\nSignals: unclear"
    assert parse_score(text) == 0


def test_parse_score_zero():
    text = "Authenticity: 0\nSignals: deleted"
    assert parse_score(text) == 0


def test_parse_score_with_extra_whitespace():
    text = "Authenticity:  9 \nSignals: very genuine"
    assert parse_score(text) == 9


# --- parse_usefulness ---

def test_parse_usefulness_valid():
    text = "Authenticity: 8\nUsefulness: 6\nSignals: ok"
    assert parse_usefulness(text) == 6


def test_parse_usefulness_with_slash():
    text = "Usefulness: 9/10"
    assert parse_usefulness(text) == 9


def test_parse_usefulness_missing():
    text = "Authenticity: 8\nSignals: ok"
    assert parse_usefulness(text) == 0


def test_parse_usefulness_malformed():
    text = "Usefulness: very high"
    assert parse_usefulness(text) == 0


# --- parse_key_tips ---

def test_parse_key_tips_multiple():
    text = "Key_Tips: Practice STL containers; Review smart pointers; Do mock interviews"
    result = parse_key_tips(text)
    assert "Practice STL containers" in result
    assert "Review smart pointers" in result
    assert "Do mock interviews" in result


def test_parse_key_tips_none():
    text = "Key_Tips: None"
    assert parse_key_tips(text) == ""


def test_parse_key_tips_missing():
    text = "Authenticity: 8\nSignals: ok"
    assert parse_key_tips(text) == ""


def test_parse_key_tips_single():
    text = "Key_Tips: Focus on data structures"
    assert parse_key_tips(text) == "Focus on data structures"


# --- Full analysis output ---

def test_parse_full_analysis():
    text = """Authenticity: 8
Usefulness: 7
Signals: Genuine first-hand experience
Key_Tips: Practice LC medium; Focus on STL; Review RAII patterns
Products: None
Verdict: Genuine"""

    assert parse_score(text) == 8
    assert parse_usefulness(text) == 7
    tips = parse_key_tips(text)
    assert "Practice LC medium" in tips
    assert "Focus on STL" in tips
