#!/usr/bin/env python3
"""Prose gate: banned characters and ASCII-substituted German in every file
this repository authors.

Two classes, both of which survive review because nobody sees them:

* the em dash (U+2014). The house style writes a hyphen or a comma. It
  arrives by copy-paste and by autocorrect, and once it sits in a comment
  block it is copied into the next repository with that block.
* characters that render as nothing: zero-width space, byte-order mark,
  soft hyphen, and the directional marks. They are legal text, they pass
  every structural check, and they break search and diffs silently.

Deliberately NOT flagged: the ellipsis, the en dash and the no-break space.
They are legitimate typography here, and a gate that fights legitimate
typography gets switched off.

``schema/`` is excluded because it is not authored here: it is a
byte-identical mirror of the pinned learn-content-engine release, held in
place by the drift gate. Its typography is the engine's to fix, and editing
it here would turn the drift gate red for a cosmetic reason.

The second class is the umlaut written as a letter pair: "Abhaengigkeit" for
"Abhängigkeit", "fuer" for "für", "heisst" for "heißt". It is legal text, it
passes every structural check, and a whole lesson set can be authored that way
without a single gate noticing - which is what happened once. It is checked
against a STEM LIST, never against the letter pair: a pattern on "ue" fires on
"value", "true", "queue" and "Sequence", so it would be switched off within a
day.

Code is exempt from the umlaut check, and only from that one. An identifier is
spelled by whoever wrote it: "laeuft" as a variable name is a choice, "laeuft"
in a sentence is a misspelling. In a lesson file that means the code-bearing
fields (``passage``, ``sentence``, ``tokens``, ``code``) and the fenced blocks
inside a theory body; in Markdown it means the fenced blocks.

This file and its test are exempt from the umlaut check too, for the same
reason the banned characters are built from code points: a list of
misspellings has to contain them. ``tests/test_check_prose.py`` asserts the
exemption, so it cannot quietly widen.

Usage:
    python3 scripts/check_prose.py             # gate every tracked file
    python3 scripts/check_prose.py --self-test # prove the gate bites
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

# Built from code points, never from literals: this file has to pass its own
# gate, and a table of the real characters would flag the gate itself.
BANNED = {
    chr(0x2014): "EM DASH (write a hyphen or a comma)",
    chr(0x200B): "ZERO WIDTH SPACE",
    chr(0xFEFF): "BYTE ORDER MARK",
    chr(0x00AD): "SOFT HYPHEN",
    chr(0x200E): "LEFT-TO-RIGHT MARK",
    chr(0x200F): "RIGHT-TO-LEFT MARK",
}

ALLOWED_SAMPLE = "a clean line - hyphen, comma, no-break space" + chr(0x00A0) + ", ellipsis" + chr(0x2026)

EXCLUDED_PREFIXES = ("schema/",)

# German words whose umlaut or sharp s was written as a letter pair. Stems, not
# whole words: German compounds are endless ("Abhaengigkeitsliste"), so a stem
# catches the family. Every entry is a stem that occurs in German and in
# essentially no English word - that is the reason this is a list and not a
# pattern. Add an entry when one slips through; never add a stem that also
# lives inside an English word.
SUBSTITUTED_STEMS = {
    "abhaeng": "abh\u00e4ng",
    "aehnlich": "\u00e4hnlich",
    "aender": "\u00e4nder",
    "aerger": "\u00e4rger",
    "aeusser": "\u00e4u\u00dfer",
    "anhaelt": "anh\u00e4lt",
    "aufloes": "aufl\u00f6s",
    "aufraeum": "aufr\u00e4um",
    "ausfuehr": "ausf\u00fchr",
    "ausgeloest": "ausgel\u00f6st",
    "ausmass": "ausma\u00df",
    "aussen": "au\u00dfen",
    "ausser": "au\u00dfer",
    "behaelt": "beh\u00e4lt",
    "bekaem": "bek\u00e4m",
    "boes": "b\u00f6s",
    "buendel": "b\u00fcndel",
    "dafuer": "daf\u00fcr",
    "darueber": "dar\u00fcber",
    "duerf": "d\u00fcrf",
    "einrueck": "einr\u00fcck",
    "enthaelt": "enth\u00e4lt",
    "enthuell": "enth\u00fcll",
    "ergaenz": "erg\u00e4nz",
    "erklaer": "erkl\u00e4r",
    "faehig": "f\u00e4hig",
    "faell": "f\u00e4ll",
    "faellt": "f\u00e4llt",
    "faeng": "f\u00e4ng",
    "faerb": "f\u00e4rb",
    "fliess": "flie\u00df",
    "fluess": "fl\u00fcss",
    "frueh": "fr\u00fch",
    "fueg": "f\u00fcg",
    "fuehl": "f\u00fchl",
    "fuehr": "f\u00fchr",
    "fuell": "f\u00fcll",
    "fuer": "f\u00fcr",
    "fuess": "f\u00fc\u00df",
    "gaeng": "g\u00e4ng",
    "gemaess": "gem\u00e4\u00df",
    "gewoehn": "gew\u00f6hn",
    "glueck": "gl\u00fcck",
    "groess": "gr\u00f6\u00df",
    "gross": "gro\u00df",
    "gruend": "gr\u00fcnd",
    "gueltig": "g\u00fcltig",
    "haelf": "h\u00e4lf",
    "haelt": "h\u00e4lt",
    "haeng": "h\u00e4ng",
    "haeufig": "h\u00e4ufig",
    "heiss": "hei\u00df",
    "hoech": "h\u00f6ch",
    "hoeh": "h\u00f6h",
    "hoer": "h\u00f6r",
    "itaet": "it\u00e4t",
    "knoepf": "kn\u00f6pf",
    "koenn": "k\u00f6nn",
    "koerper": "k\u00f6rper",
    "kuenftig": "k\u00fcnftig",
    "kuerz": "k\u00fcrz",
    "laedt": "l\u00e4dt",
    "laeng": "l\u00e4ng",
    "laesst": "l\u00e4sst",
    "laeuf": "l\u00e4uf",
    "loes": "l\u00f6s",
    "luege": "l\u00fcge",
    "maessig": "m\u00e4\u00dfig",
    "massnahm": "ma\u00dfnahm",
    "moecht": "m\u00f6cht",
    "moeglich": "m\u00f6glich",
    "muend": "m\u00fcnd",
    "muess": "m\u00fcss",
    "naechst": "n\u00e4chst",
    "naeh": "n\u00e4h",
    "noetig": "n\u00f6tig",
    "nuetz": "n\u00fctz",
    "oberflaech": "oberfl\u00e4ch",
    "oeffn": "\u00f6ffn",
    "prioritaet": "priorit\u00e4t",
    "pruef": "pr\u00fcf",
    "raeum": "r\u00e4um",
    "rueck": "r\u00fcck",
    "saeh": "s\u00e4h",
    "schlaegt": "schl\u00e4gt",
    "schliess": "schlie\u00df",
    "schluessel": "schl\u00fcssel",
    "schoen": "sch\u00f6n",
    "selbsttaetig": "selbstt\u00e4tig",
    "spaeter": "sp\u00e4ter",
    "spuer": "sp\u00fcr",
    "staend": "st\u00e4nd",
    "staetig": "st\u00e4tig",
    "stoess": "st\u00f6\u00df",
    "stoss": "sto\u00df",
    "stueck": "st\u00fcck",
    "stuend": "st\u00fcnd",
    "taeglich": "t\u00e4glich",
    "traeg": "tr\u00e4g",
    "traegt": "tr\u00e4gt",
    "ueber": "\u00fcber",
    "uebrig": "\u00fcbrig",
    "uebrigens": "\u00fcbrigens",
    "uebung": "\u00fcbung",
    "umhuell": "umh\u00fcll",
    "unberuehrt": "unber\u00fchrt",
    "veraender": "ver\u00e4nder",
    "verfuegbar": "verf\u00fcgbar",
    "vollstaend": "vollst\u00e4nd",
    "waehl": "w\u00e4hl",
    "waehr": "w\u00e4hr",
    "waere": "w\u00e4re",
    "waerts": "w\u00e4rts",
    "wuensch": "w\u00fcnsch",
    "wuerd": "w\u00fcrd",
    "zaehl": "z\u00e4hl",
    "zuegig": "z\u00fcgig",
    "zusaetzlich": "zus\u00e4tzlich",
    "zustaendig": "zust\u00e4ndig",
}

# Words a stem cannot reach without claiming an innocent one: "weiss" lives
# inside "Hinweisschilder", so it is matched as a whole word instead. Swiss
# spelling in a German set is the case this exists for.
WHOLE_WORD_SUBSTITUTIONS = {
    "weiss": "wei\u00df",
    "weisst": "wei\u00dft",
    "heisse": "hei\u00dfe",
    "grosse": "gro\u00dfe",
    "grosser": "gro\u00dfer",
    "grosses": "gro\u00dfes",
}

# Words from the languages this content teaches that a German stem would
# otherwise claim. Measured, not guessed: a run over every set in the
# ecosystem produced exactly one family of false positives, the Spanish forms
# around "ser/ir" and "fuerte", all caught by the stem "fuer". A new collision
# belongs here together with the run that found it.
FOREIGN_LOOKALIKES = {
    "fuera",
    "fueras",
    "fueron",
    "fuerte",
    "fuertes",
    "fuerza",
    "fuerzas",
}

# Fields of a lesson file that carry CODE rather than prose. The id fields
# belong here for the same reason as an identifier in a sentence: an id is a
# machine key, the app and the manifest look it up verbatim, and "correcting"
# it silently renames the thing. It also happens to be how a slug stops being
# ASCII without anyone noticing.
CODE_KEYS = {
    # code the learner reads
    "passage",
    "sentence",
    "tokens",
    "code",
    "code_snippet",
    "code_language",
    "expected_output",
    # machine keys: an id is looked up verbatim, so correcting its spelling
    # renames the thing it names - and it is how a slug quietly stops being
    # ASCII.
    "stable_id",
    "id",
    "theory_ref",
    "card_ids",
    "review_lesson_id",
    "variation_of",
    "tags",
    # paths, URLs and enum-ish values: not sentences
    "example_url",
    "audio",
    "image",
    "src",
    "language",
    "media_type",
}


# This gate and its test hold the misspellings on purpose.
UMLAUT_EXEMPT = ("scripts/check_prose.py", "tests/test_check_prose.py")

WORD = re.compile("[A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df]+")


def tracked_files() -> list[str]:
    """Every file git tracks, minus the mirrored artifacts."""
    listing = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.split("\n")
    return [
        path
        for path in listing
        if path and not path.startswith(EXCLUDED_PREFIXES)
    ]


def findings_in(text: str) -> list[tuple[int, str, str]]:
    """(line number, character, reason) for every banned character in ``text``."""
    findings = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        for character, reason in BANNED.items():
            if character in line:
                findings.append((line_number, character, reason))
    return findings


def substituted_words(text: str) -> list[tuple[str, str]]:
    """(word, correct spelling) for every ASCII-substituted German word."""
    findings = []
    for word in WORD.findall(text):
        lowered = word.lower()
        if lowered in FOREIGN_LOOKALIKES or _is_identifier(word):
            continue
        if lowered in WHOLE_WORD_SUBSTITUTIONS:
            suggestion = WHOLE_WORD_SUBSTITUTIONS[lowered]
            if word[:1].isupper():
                suggestion = suggestion[:1].upper() + suggestion[1:]
            findings.append((word, suggestion))
            continue
        suggestion = lowered
        for stem, correct in SUBSTITUTED_STEMS.items():
            # Every matching stem, not just the first: "zurueckhaelt" carries
            # two ("rueck" and "haelt"), and stopping at one leaves half a
            # correction behind - which is exactly how two words survived a
            # full pass over a real set.
            if stem in suggestion:
                suggestion = suggestion.replace(stem, correct)
        if suggestion == lowered:
            continue
        if word[:1].isupper():
            suggestion = suggestion[:1].upper() + suggestion[1:]
        findings.append((word, suggestion))
    return findings


def _is_identifier(word: str) -> bool:
    """True for a camelCase word, which is code even inside a prose field.

    A prompt may name a function it is asking about
    ("fuegeOptimistischHinzu(text)"), and renaming it in prose would make the
    text point at something that does not exist. German never capitalises
    inside a word, so an inner capital next to lower case is a reliable
    marker. An all-caps word is not one: shouted German is still German.
    """
    has_inner_capital = any(character.isupper() for character in word[1:])
    return has_inner_capital and any(character.islower() for character in word)


def prose_segments(path: str, text: str) -> list[tuple[int, str]]:
    """(line number, prose) for the parts of a file the umlaut check applies to.

    A lesson file is walked as JSON so the code-bearing fields drop out; a
    Markdown file keeps everything outside its fenced blocks; anything else is
    prose end to end. Line numbers are best effort for JSON: the line the
    string starts on, looked up once per string.
    """
    if path.endswith(".json"):
        try:
            document = json.loads(text)
        except ValueError:
            return list(enumerate(text.splitlines(), start=1))
        collected: list[str] = []
        _walk_json(document, False, collected)
        lines = text.splitlines()
        segments = []
        for value in collected:
            head = value.splitlines()[0] if value.splitlines() else value
            line_no = next((i for i, line in enumerate(lines, start=1) if head[:60] in line), 0)
            segments.append((line_no, _outside_fences(value)))
        return segments
    if path.endswith(".md"):
        return [(1, _outside_fences(text))]
    return list(enumerate(text.splitlines(), start=1))


def _walk_json(node, in_code: bool, out: list[str]) -> None:
    if isinstance(node, dict):
        # An inline example is prose when it is a sample sentence and code when
        # it declares a language; the field name alone cannot tell them apart.
        example_is_code = bool(node.get("language")) and "content" in node
        for key, value in node.items():
            child_is_code = in_code or key in CODE_KEYS or (example_is_code and key == "content")
            _walk_json(value, child_is_code, out)
    elif isinstance(node, list):
        for value in node:
            _walk_json(value, in_code, out)
    elif isinstance(node, str) and not in_code:
        out.append(node)


def _outside_fences(text: str) -> str:
    """The text with every fenced code block removed."""
    return " ".join(text.split("```")[0::2])


def describe(character: str) -> str:
    return f"U+{ord(character):04X} {unicodedata.name(character, 'UNNAMED')}"


def self_test() -> int:
    """A gate that never fires on a known-bad input is not a gate."""
    for character in BANNED:
        if not findings_in(f"a line with {character} in it"):
            print(f"self-test FAILED: {describe(character)} not detected", file=sys.stderr)
            return 1
    if findings_in(ALLOWED_SAMPLE):
        print("self-test FAILED: a clean line was flagged", file=sys.stderr)
        return 1

    if not substituted_words("Die Abhaengigkeitsliste laeuft"):
        print("self-test FAILED: substituted German not detected", file=sys.stderr)
        return 1
    for clean in ("value true Sequence queue useState", "Die " + SUBSTITUTED_STEMS["abhaeng"] + "igkeit"):
        if substituted_words(clean):
            print(f"self-test FAILED: flagged clean text {clean!r}", file=sys.stderr)
            return 1
    if substituted_words(_outside_fences("prose\n```js\nconst laeuft = true;\n```\nprose")):
        print("self-test FAILED: a fenced code block was scanned", file=sys.stderr)
        return 1

    print(
        f"self-test passed: {len(BANNED)} banned characters and "
        f"{len(SUBSTITUTED_STEMS)} substituted stems detected, clean text untouched"
    )
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()

    files = tracked_files()
    if not files:
        print("check_prose: git tracks no files - wrong directory?", file=sys.stderr)
        return 2

    banned_hits = 0
    umlaut_hits = 0
    for path in files:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for line_number, character, reason in findings_in(text):
            banned_hits += 1
            print(f"{path}:{line_number}: {describe(character)} - {reason}")
        if path in UMLAUT_EXEMPT:
            continue
        for line_number, segment in prose_segments(path, text):
            for word, suggestion in substituted_words(segment):
                umlaut_hits += 1
                print(
                    f"{path}:{line_number}: {word} - German written without its"
                    f" umlaut, correct is {suggestion}"
                )

    if banned_hits or umlaut_hits:
        print(
            f"\nPROSE GATE: {banned_hits} banned character(s) and {umlaut_hits}"
            f" substituted German word(s) in {len(files)} tracked file(s).",
            file=sys.stderr,
        )
        return 1
    print(f"prose gate: {len(files)} tracked file(s) clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
