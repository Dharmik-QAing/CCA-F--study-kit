# CCA-F personal study kit

Local study tools for the **Claude Certified Architect – Foundations** exam.

This is a personal kit. It is **not** affiliated with Anthropic. Do not put official or confidential exam-guide files in this repository.

## What to open

**[study-book.html](study-book.html)** — interactive textbook: 30 tasks, study tools (how to answer, principles, decision pairs, trap radar, drill), full chapters, labs.

Open the file in a browser. Progress, notes, and drill misses stay in that browser only.

## Rebuild the book

The page is generated from `exam-preparation-guide.md`.

```bash
py -3 _build_study_book.py
```

Requires Python 3. Then refresh `study-book.html`.

## Files in this repo

| File | Why it is here |
|------|----------------|
| `study-book.html` | The study app you use |
| `_build_study_book.py` | Regenerates the HTML |
| `exam-preparation-guide.md` | Source chapters for the builder (community guide) |

Keep `EXAM_GUIDE.md` (official guide) **outside git**, next to this folder or in the original clone. It is listed in `.gitignore` on purpose.

## Sources

The knowledge base is built from the [official exam guide](https://anthropic-partners.skilljar.com/claude-certified-architect-foundations-certification) as a key source, plus the community guide credited below.

## Attribution

`exam-preparation-guide.md` is from the community guide [daronyondem/claude-architect-exam-guide](https://github.com/daronyondem/claude-architect-exam-guide), licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The study book is a personal rearrangement of that teaching material plus original study tools.
