#!/usr/bin/env python3
"""Tests for scripts/audit_content.py.

Focus: the cloze-mode branch. `multiselect` cloze has no ___ markers and
no blanks by design, so the audit must NOT flag it for missing markers /
blanks (issue #1). `type`/`select` cloze keeps the marker+blanks checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import audit_content as ac  # noqa: E402


def _audit(exercise: dict) -> list[str]:
    """Run the audit over a one-exercise lesson; return the problem strings."""
    lesson = {
        "id": "l1",
        "title": "T",
        "steps": [{"id": "s1", "type": "exercise", "exercise": exercise}],
    }
    findings: list[tuple] = []
    ac.audit_lesson(lesson, "<lesson>", findings)
    return [problem for _label, problem, _fix in findings]


def _cloze_findings(exercise: dict) -> list[str]:
    return [p for p in _audit(exercise) if "cloze" in p]


def test_valid_multiselect_is_not_flagged():
    """A correct multiselect (no markers, no blanks) produces no cloze finding."""
    ex = {
        "id": "c1",
        "type": "cloze",
        "cloze_mode": "multiselect",
        "prompt": "Select all that apply.",
        "sentence": "Which of these are prime numbers?",
        "accept": ["2", "3", "5"],
        "distractors": ["4", "6"],
    }
    assert _cloze_findings(ex) == []


def test_multiselect_overlap_is_flagged():
    ex = {
        "id": "c1",
        "type": "cloze",
        "cloze_mode": "multiselect",
        "prompt": "Select all that apply.",
        "sentence": "Which are primes?",
        "accept": ["2", "3"],
        "distractors": ["3", "4"],  # "3" overlaps
    }
    findings = _cloze_findings(ex)
    assert any("overlap" in f for f in findings)


def test_multiselect_without_distractors_is_flagged():
    ex = {
        "id": "c1",
        "type": "cloze",
        "cloze_mode": "multiselect",
        "prompt": "Select all that apply.",
        "sentence": "Which are primes?",
        "accept": ["2", "3"],
        "distractors": [],
    }
    findings = _cloze_findings(ex)
    assert any("no distractors" in f for f in findings)


def test_type_cloze_missing_marker_still_flagged():
    """Regression: the type/select path keeps its marker + blanks checks."""
    ex = {
        "id": "c1",
        "type": "cloze",
        "cloze_mode": "type",
        "prompt": "Fill in.",
        "sentence": "no gap here",  # missing ___
        "blanks": [{"accept": ["x"]}],
    }
    findings = _cloze_findings(ex)
    assert any("no ___ gap" in f for f in findings)


def test_select_cloze_empty_blank_still_flagged():
    ex = {
        "id": "c1",
        "type": "cloze",
        "cloze_mode": "select",
        "prompt": "Choose.",
        "sentence": "a ___ b",
        "blanks": [{"accept": []}],  # empty accept
        "distractors": ["x"],
    }
    findings = _cloze_findings(ex)
    assert any("no accepted answers" in f for f in findings)


def test_default_mode_is_type_marker_checked():
    """No cloze_mode defaults to type, so the marker check applies."""
    ex = {
        "id": "c1",
        "type": "cloze",
        "prompt": "Fill in.",
        "sentence": "no gap",
        "blanks": [{"accept": ["x"]}],
    }
    findings = _cloze_findings(ex)
    assert any("no ___ gap" in f for f in findings)
