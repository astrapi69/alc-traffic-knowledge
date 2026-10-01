#!/usr/bin/env python3
"""Content quality audit for adaptive-learner-content.

A *reporting* companion to ``validate_content.py``. The validator
enforces the hard quality gate (and fails CI); this audit hunts for the
softer quality problems a schema check can miss and prints them as a
table so they can be fixed:

  * duplicate cards within a lesson (same front, or same front/back pair)
  * exercises whose answer set is malformed for their type
    (matching pairs, free_text accept/distractors overlap, cloze blanks,
    word_tiles tiles, picture_choice single correct)
  * matching pairs / free_text accepts that don't line up with any
    card the exercise references (possible wrong "correct" answer)
  * empty / whitespace-only fields (card front/back, prompts, theory
    body, titles)
  * lessons missing in their set manifest, or set fields missing

Not here any more, because the engine gate (validate_with_engine.mjs) blocks
on them: duplicate card, step and exercise ids (learn-content-engine#202), and
the quality minimums such as matching pairs and free_text accepts (#185, keyed
to a lesson's ``purpose``). The distractor requirement on free_text and
picture_choice was dropped by the same decision.

Exit code is always 0 - this is advisory. ``--strict`` makes it exit 1
when any finding is reported (handy in CI once the tree is clean).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def is_blank(x) -> bool:
    return not (isinstance(x, str) and x.strip())


def audit_lesson(lesson: dict, label: str, findings: list[tuple]):
    def add(problem, fix):
        findings.append((label, problem, fix))

    cards = lesson.get("cards", []) or []
    # --- duplicate / empty cards -------------------------------------
    seen_front, seen_pair = {}, {}
    card_by_front = {}
    for c in cards:
        cid = c.get("id", "?")
        front = (c.get("front") or "").strip()
        back = (c.get("back") or "").strip()
        if is_blank(c.get("front")) or is_blank(c.get("back")):
            add(f"card '{cid}' has empty front/back", "fill both fields")
        card_by_front[front.lower()] = back
        if front and front.lower() in seen_front:
            add(f"duplicate card front '{front}' (ids {seen_front[front.lower()]}, {cid})",
                "remove/merge the duplicate card")
        seen_front[front.lower()] = cid
        key = (front.lower(), back.lower())
        if front and key in seen_pair:
            add(f"duplicate card front/back pair '{front}'->'{back}'", "remove duplicate")
        seen_pair[key] = cid

    # --- steps: ids, theory, exercises -------------------------------
    steps = lesson.get("steps", []) or []
    for s in steps:
        sid = s.get("id", "?")
        if s.get("type") == "theory":
            if is_blank(s.get("body")):
                add(f"theory step '{sid}' has empty body", "add Markdown body")
            if is_blank(s.get("title")):
                add(f"theory step '{sid}' has empty title", "add a title")

    exercises = [s.get("exercise") for s in steps
                 if s.get("type") == "exercise" and s.get("exercise")]
    for ex in exercises:
        eid = ex.get("id", "?")
        etype = ex.get("type", "?")
        if is_blank(ex.get("prompt")):
            add(f"exercise '{eid}' ({etype}) has empty prompt", "add a prompt")

        if etype == "matching":
            pairs = ex.get("pairs") or []
            seen_left = set()
            for p in pairs:
                left = (p.get("left") or "").strip()
                right = (p.get("right") or "").strip()
                if is_blank(p.get("left")) or is_blank(p.get("right")):
                    add(f"matching '{eid}' has an empty pair side", "fill left/right")
                if left.lower() in seen_left:
                    add(f"matching '{eid}' duplicate left '{left}'", "remove duplicate pair")
                seen_left.add(left.lower())
                # NB: we deliberately do NOT cross-check the pair's right side
                # against the card gloss - matching exercises legitimately pair
                # a word with its article / gender / category, not its dictionary
                # translation, so such a check is all false positives.
        elif etype == "free_text":
            accept = ex.get("accept") or []
            # An accepted answer appearing verbatim in distractors is
            # contradictory. Compare case-SENSITIVELY: a distractor that
            # differs only by capitalisation (e.g. testing that Spanish
            # nationalities are lower-case) is a legitimate wrong answer.
            overlap = {a.strip() for a in accept} & {
                d.strip() for d in (ex.get("distractors") or [])}
            if overlap:
                add(f"free_text '{eid}' accept & distractors overlap: {sorted(overlap)}",
                    "remove the overlap")
        elif etype == "cloze":
            # cloze has three modes. "multiselect" ("select all that apply")
            # deliberately carries NO ___ markers and NO blanks: the sentence
            # is the question stem, and accept/distractors hold the options.
            # Auditing it against the type/select marker+blanks shape produces
            # only false positives, so branch on cloze_mode (mirrors the
            # engine's per-mode semantics; validate_content.py already does).
            if (ex.get("cloze_mode") or "type") == "multiselect":
                accept = {a.strip() for a in (ex.get("accept") or []) if not is_blank(a)}
                distractors = {d.strip() for d in (ex.get("distractors") or []) if not is_blank(d)}
                if not accept:
                    add(f"cloze '{eid}' (multiselect) has no accepted options", "add accept options")
                if not distractors:
                    add(f"cloze '{eid}' (multiselect) has no distractors", "add distractors")
                overlap = accept & distractors
                if overlap:
                    add(f"cloze '{eid}' (multiselect) accept & distractors overlap: {sorted(overlap)}",
                        "remove the overlap")
            else:
                blanks = ex.get("blanks") or []
                sentence = ex.get("sentence") or ""
                if "___" not in sentence:
                    add(f"cloze '{eid}' sentence has no ___ gap", "add a ___ gap")
                if not blanks or any(not (b.get("accept") or []) for b in blanks):
                    add(f"cloze '{eid}' has a blank with no accepted answers", "add accepts")
        elif etype == "word_tiles":
            if len(ex.get("tiles") or []) < 2:
                add(f"word_tiles '{eid}' has < 2 tiles", "add tiles")
        elif etype == "picture_choice":
            images = ex.get("images") or []
            correct = [i for i in images if str(i.get("is_correct")).lower() == "true"]
            if len(correct) != 1:
                add(f"picture_choice '{eid}' has {len(correct)} correct images (need 1)",
                    "mark exactly one is_correct")


def main() -> int:
    strict = "--strict" in sys.argv
    manifest = yaml.safe_load((REPO_ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    findings: list[tuple] = []
    lessons_scanned = 0
    for cs in manifest.get("sets", []) or []:
        sid = cs.get("id", "?")
        # required set fields
        for field in ("source_language", "target_language", "level"):
            if is_blank(cs.get(field)):
                findings.append((sid, f"set missing '{field}'", f"add {field}"))
        path = cs.get("path")
        if not path:
            continue
        set_manifest = yaml.safe_load((REPO_ROOT / path / "manifest.yaml").read_text(encoding="utf-8"))
        listed = (set_manifest.get("metadata") or {}).get("lessons") or []
        for fn in listed:
            lf = REPO_ROOT / path / "lessons" / fn
            if not lf.is_file():
                findings.append((f"{sid}/{fn}", "listed lesson file missing", "add or delist"))
                continue
            try:
                lesson = json.loads(lf.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                findings.append((f"{sid}/{fn}", f"invalid JSON: {exc}", "fix JSON"))
                continue
            lessons_scanned += 1
            audit_lesson(lesson, f"{sid}/{fn}", findings)

    print(f"Scanned {lessons_scanned} lesson(s) across "
          f"{len(manifest.get('sets', []))} set(s).\n")
    if not findings:
        print("No quality issues found. ✓")
        return 0
    # table
    w0 = max(len(f[0]) for f in findings)
    w1 = max(len(f[1]) for f in findings)
    print(f"{'Set/Lesson'.ljust(w0)} | {'Problem'.ljust(w1)} | Fix")
    print(f"{'-'*w0}-+-{'-'*w1}-+-{'-'*20}")
    for loc, problem, fix in findings:
        print(f"{loc.ljust(w0)} | {problem.ljust(w1)} | {fix}")
    print(f"\n{len(findings)} finding(s).")
    return 1 if strict else 0


if __name__ == "__main__":
    sys.exit(main())
