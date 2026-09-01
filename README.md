# alc-traffic-knowledge

[![content validation](https://github.com/astrapi69/alc-traffic-knowledge/actions/workflows/validate-content.yml/badge.svg)](https://github.com/astrapi69/alc-traffic-knowledge/actions/workflows/validate-content.yml)
[![engine on npm](https://img.shields.io/npm/v/learn-content-engine?label=engine%20on%20npm)](https://www.npmjs.com/package/learn-content-engine)

The [Adaptive Learner](https://github.com/astrapi69/adaptive-learner)
content repository for **Verkehrskunde** (traffic knowledge): a Git
repository of plain lesson files that the app loads directly and no
vendor can lock away.

It ships one German-language knowledge set (domain `traffic-knowledge`):
free-form practice questions in the style of the German driving-licence
exam. This repository was created from
[adaptive-learner-content-template](https://github.com/astrapi69/adaptive-learner-content-template),
which provides the schema mirror, validator, CI and authoring tooling
described below.

> **Herkunft:** Dieses Set lag zuvor im Test-/Starter-Repo
> [`adaptive-learner-content-test`](https://github.com/astrapi69/adaptive-learner-content-test)
> und wurde in dieses eigenständige Content-Repo verschoben (siehe
> `adaptive-learner-content#144`).
>
> **Hinweis:** Eigene, frei formulierte Übungsfragen über freie Fakten
> der deutschen StVO: keine amtlichen Prüfungsfragen oder Bilder, kein
> Anspruch auf Prüfungsechtheit.

## Das Set

### `sets/de/fuehrerschein-uebung` (A2, 5 Lektionen, 36 Karten)

Ausschließlich Multiple-Choice (im Schema als cloze select-mode und als
nativer `multiple_choice`-Typ):

| # | Lesson | Titel |
|---|--------|-------|
| 01 | `01-vorfahrt-kreuzungen.json` | Vorfahrt und Kreuzungen |
| 02 | `02-geschwindigkeit-abstand.json` | Geschwindigkeit und Abstand |
| 03 | `03-alkohol-fahrtuechtigkeit.json` | Alkohol, Drogen und Fahrtüchtigkeit |
| 04 | `04-parken-halten-situationen.json` | Parken, Halten und besondere Situationen |
| 05 | `05-rettungsgasse-einsatzfahrzeuge.json` | Rettungsgasse und Einsatzfahrzeuge |

## What's inside

- `manifest.yaml`: the root manifest listing the set.
- `sets/de/fuehrerschein-uebung/`: the lesson set.
- `schema/`: the pinned [`learn-content-engine`](https://github.com/astrapi69/learn-content-engine)
  schema mirror; [`engine-version.txt`](schema/engine-version.txt) holds the
  pinned engine version and is the source of truth. This is what the content
  is validated against, independent of the app.
- `templates/`: starting-point lessons per domain (language / programming / knowledge).
- `scripts/validate_content.py`: the local validator.
- `scripts/generate_exercises.py`: an optional BYOK AI exercise generator.
- `generated/`: staging area for AI drafts (never shipped directly).
- `.github/workflows/`: CI that validates every push/PR against the pinned engine.
- `docs/`: [GETTING-STARTED.md](docs/GETTING-STARTED.md) and a local
  [LESSON-FORMAT.md](docs/LESSON-FORMAT.md). The **canonical, test-validated**
  format reference is the engine's
  [`docs/lesson-format.md`](https://github.com/astrapi69/learn-content-engine/blob/main/docs/lesson-format.md).

## Quick start

You only need `make` and `python3`. The first `make validate` sets up a
local environment for you (no manual `pip`, no virtualenv, no Poetry):

```bash
git clone https://github.com/astrapi69/alc-traffic-knowledge.git
cd alc-traffic-knowledge

# Validate the set. First run creates .venv and installs deps;
# later runs reuse it. Exit 0 == all sets pass.
make validate
```

Before you push, `make lint` runs the same semantic engine gate as CI
(`Engine conformance`): it installs the engine release pinned in
`schema/engine-version.txt` into `node_modules/` (gitignored; needs Node.js
and npm) and checks every lesson and manifest with the engine's rule ids
(`E-CARD-REF` & co.). `make lint-warnings` additionally prints the engine gate's warnings (`W-*`).

No `make` (e.g. Windows without WSL)? Two options: run the validator in a
virtualenv yourself:

```bash
python3 -m venv .venv && . .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 scripts/validate_content.py
```

Or just commit and let the GitHub Actions CI validate (it runs the same
checks). Installing the deps globally with a bare `pip install` fails on
modern Debian/Ubuntu/macOS (PEP 668, "externally-managed-environment");
the virtualenv above is why.

Full walkthrough: [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md).

## Export a set for AI review

`scripts/export_set.py` writes all lessons of ONE set into a single
YAML (or JSON) file so an AI assistant or a human can review the whole
set in one pass (syntax, correctness, consistency across lessons).

**Recommended (via make; reuses the local environment `make validate` set up):**

```bash
make export ARGS="fuehrerschein-uebung"
# -> exports/fuehrerschein-uebung-de-<timestamp>.yaml
```

**Direct (fallback; run it inside the venv from the Quick start):**

```bash
python3 scripts/export_set.py fuehrerschein-uebung
python3 scripts/export_set.py fuehrerschein-uebung --format json --out /tmp/review.json
```

The slug is the set id from the root `manifest.yaml`
(`fuehrerschein-uebung-from-de`) or the folder name of the set path
(`fuehrerschein-uebung`); when the same folder name exists under several
source-language directories, `--lang` (default `de`) picks the
`sets/<lang>/` directory. Non-ASCII characters stay real UTF-8. An
unknown slug aborts with a list of the available sets.

For a large set, `--split-size N` writes multiple self-contained files
of at most N lessons each instead of one huge file, e.g.
`make export ARGS="fuehrerschein-uebung --split-size 2"` (each part
keeps its own `review_instructions` copy, so any one file can be handed
to an AI on its own). Cannot be combined with `--out`.

The export is self-contained: its first field `review_instructions`
holds the complete review prompt from
[`docs/ai-review-prompt-template.md`](docs/ai-review-prompt-template.md)
(read at runtime, not copied into the script). The export file can be
handed to a review AI as-is, without manually prepending a prompt. Edit
the review instructions in that template file and keep the sibling
content repos in sync.

**Read-only snapshot, NOT a re-import format:** nothing reads the
export back. Changes flow only through the individual schema-validated
lesson JSONs under `sets/`. The `exports/` folder is gitignored.

Full usage guide and best practices (incl. the source-chapter workflow):
[`docs/export-set-usage.md`](docs/export-set-usage.md) (English) /
[`docs/export-set-usage.de.md`](docs/export-set-usage.de.md) (Deutsch).

## Export a graded quiz to PDF (school tests)

`scripts/export_quiz_pdf.py` turns a lesson that carries a graded-quiz
exercise (an `ext:*-graded-quiz`: a scored question set, points per
question, optional partial credit on multi-select, an optional
percentage pass threshold) into two print-ready PDFs:

```bash
python3 scripts/export_quiz_pdf.py path/to/graded-quiz.json --out-dir out/
# -> out/<id>-test.pdf      (question paper for students, no answers)
# -> out/<id>-loesung.pdf   (answer sheet for the teacher)
```

The test paper shows the questions with blank checkboxes / answer lines
and the points; the answer sheet shows the correct answers, the points,
a partial-credit note, and the pass threshold. This is a consumer tool -
it renders one presentation of a canonical lesson and does not invoke the
engine, so it is independent of the pinned engine version.

**Caveat (adaptive-learner-content-test#66):** graded-quiz content uses
the `ext:` extension tier, which the content gate (`make lint`) does not
yet accept (it validates core-only and refuses ext lessons). Until that
adoption lands, keep graded-quiz lessons OUTSIDE `sets/` and run the tool
on them directly (a runnable sample lives in
[`tests/fixtures/graded-quiz-sample.json`](tests/fixtures/graded-quiz-sample.json)).

## Generate exercises with AI (optional)

`scripts/generate_exercises.py` turns a topic into a full **language**
lesson with a BYOK model (Anthropic / OpenAI / Gemini) and gates every
draft through the validator before writing it into the `generated/`
staging folder. It is language-focused (target and source differ). For a
**knowledge set** like the one in this repo (material written in the
same language it teaches, source == target), the generator is not the
right tool; hand-author from
[`templates/knowledge/`](templates/knowledge/) instead.

First set your provider key. It is read from the environment (BYOK) and
never committed:

```bash
export ANTHROPIC_API_KEY="sk-..."   # or OPENAI_API_KEY / GEMINI_API_KEY (Gemini also accepts GOOGLE_API_KEY)
```

**Recommended (via make; reuses the local environment `make validate` set up):**

```bash
make generate ARGS="--topic 'Ordering food in a café' --target-lang fr --source-lang en --level A1 --set-id fr-a1"
```

**Direct (fallback; run it inside the venv from the Quick start):**

```bash
python3 scripts/generate_exercises.py \
  --topic "Ordering food in a café" \
  --target-lang fr --source-lang en --level A1 --set-id fr-a1
```

### Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--topic` | (required) | What the lesson is about. |
| `--target-lang` | (required) | The language the learner studies (BCP-47, e.g. `fr`). |
| `--source-lang` | (required) | The explanation language (BCP-47, e.g. `en`). Must differ from the target. |
| `--level` | `A1` | CEFR level. |
| `--count` | `6` | Exercises to request. The effective minimum is **5** (a smaller value is treated as 5, and the quality gate requires at least 5). |
| `--set-id` | `generated-set` | Staging subfolder under `generated/`. |
| `--provider` | `anthropic` | `anthropic` \| `openai` \| `gemini`. Or set `AL_GEN_PROVIDER`. |
| `--model` | provider default | Override the model (`claude-sonnet-4-5` / `gpt-4o` / `gemini-2.5-flash`). |
| `--retries` | `3` | Extra attempts when a draft fails validation before it is discarded. |
| `--out` | `generated` | Staging directory. |

### What happens, and what you still owe

The script pins the exact lesson-schema JSON in the prompt, parses the
model's reply, and runs it through `validate_content.py`. If validation
fails, the errors go back to the model and it retries (up to `--retries`);
a draft that never validates is discarded, not written. A valid draft
lands in `generated/<set-id>/`, never directly in `sets/`.

Two gates remain after generation, neither of them automatic:

1. **Engine semantic gate** (cloze `___` markers equal the blanks,
   `card_ids` integrity, multiselect disjointness). It runs when the
   pinned `learn-content-engine` is installed, otherwise it is deferred to
   CI. The plain validator does not cover it.
2. **Native-speaker review** for a language you do not speak natively. No
   validator catches an unnatural phrasing or a wrong romanization.
   Machine-generated, then human-verified, is the only trustworthy order.

When a draft is good, move it from `generated/` into your set under
`sets/<source>/<target>-<level>/lessons/`, register it in the set
manifest, and re-run `make validate`.

## How it stays current

The content is validated against the **pinned** engine version in
`schema/engine-version.txt` on every push and pull request (structural +
semantic + drift gates in `.github/workflows/`). A green CI means the
content is valid for every consumer of that engine release. When the
engine is bumped, it reaches this repository the same way it reaches the
rest of the chain: a deliberate pin-bump PR that the drift gate guards.

Licensed MIT (see [LICENSE](LICENSE)); the lesson content carries its own
license via each set manifest's `metadata.license`.
