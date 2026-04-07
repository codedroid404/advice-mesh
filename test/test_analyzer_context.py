"""Unit tests for analyzer prompt building with job context."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.analyzer import _build_prompt


def test_prompt_no_context():
    """Prompt without job context should be generic."""
    prompt = _build_prompt("Great advice!")
    assert "Great advice!" in prompt
    assert "Authenticity:" in prompt
    assert "Job description" not in prompt
    assert "Interview stage" not in prompt


def test_prompt_with_job_description():
    """Prompt should include job description when provided."""
    prompt = _build_prompt("Great advice!", job_context="Senior Software Engineer at Google")
    assert "Senior Software Engineer at Google" in prompt
    assert "Job description" in prompt


def test_prompt_with_interview_stage():
    """Prompt should include interview stage when provided."""
    prompt = _build_prompt("Great advice!", interview_stage="Final round, live coding")
    assert "Final round, live coding" in prompt
    assert "Interview stage" in prompt


def test_prompt_with_both():
    """Prompt should include both job context and interview stage."""
    prompt = _build_prompt(
        "Great advice!",
        job_context="ML Engineer at Tesla",
        interview_stage="Phone screen passed, system design next",
    )
    assert "ML Engineer at Tesla" in prompt
    assert "Phone screen passed" in prompt
    assert "Great advice!" in prompt


def test_prompt_truncates_long_jd():
    """Job description should be truncated to 2000 chars."""
    long_jd = "x" * 5000
    prompt = _build_prompt("comment", job_context=long_jd)
    # The JD in the prompt should be capped at 2000
    assert "x" * 2000 in prompt
    assert "x" * 2001 not in prompt


def test_prompt_always_has_format():
    """All prompts should include the expected response format."""
    for prompt in [
        _build_prompt("test"),
        _build_prompt("test", job_context="SWE role"),
        _build_prompt("test", interview_stage="final round"),
        _build_prompt("test", job_context="SWE", interview_stage="onsite"),
    ]:
        assert "Authenticity:" in prompt
        assert "Usefulness:" in prompt
        assert "Key_Tips:" in prompt
        assert "Verdict:" in prompt
