# DESIGN.md — design decisions and engineering log

Why DocAgent is built the way it is, and what broke along the way.

---

## 1. Evaluation harness + baseline

### The big idea
You can't improve what you don't measure. Before building any agent, we build the **ruler** (the eval) and take the **"before" photo** (the baseline). Week 2's agent is only interesting if it beats this number on the *same* receipts.

### Files and the decision behind each

**`schema.py` — the output contract**
- One Pydantic `Receipt` model with 4 string fields.
- *Why:* every part of the system (baseline, agent, API, evals) shares one definition of a valid answer. If the LLM returns junk, Pydantic raises an error instead of letting bad data flow downstream.
- *Why strings, not `date`/`float` types?* We want to see exactly what the model produced, then normalise in the scorer. Converting too early hides errors.

**`llm.py` — provider wrapper**
- `complete(system, user)` returns `LLMResult(text, input_tokens, output_tokens, latency_s)` plus a computed `cost_usd`.
- *Why wrap?* (1) switch OpenAI ↔ Anthropic with one env variable; (2) every call reports cost and speed, so the eval can show the *trade-off*: the agent will be more accurate but cost more — by how much?
- `temperature=0` → the most deterministic output, so re-running the eval gives (nearly) the same numbers.
- OpenAI `response_format={"type": "json_object"}` → the API guarantees syntactically valid JSON (not that the *values* are right — that's what the agent's validation tools are for).

**`baseline.py` — the "before"**
- One system prompt, one call, parse JSON, done. No retries, no checks.
- A parse failure becomes an empty `Receipt` (all fields wrong). *Why:* honest scoring — failures must count.

**`data/download_sroie.py` — the test set**
- Clones the SROIE dataset, pairs each answer `.json` with its OCR `.txt` by file name.
- OCR boxes come as `x1,y1,...,x4,y4,TEXT`; we sort by `(y, x)` → reading order, top to bottom then left to right.
- `split(",", 8)` → the text itself can contain commas ("NO.53 55,57 & 59"), so we split only on the first 8.
- Fixed shuffle with `seed 42`, take 100 → **every experiment runs on identical receipts**. Changing the test set between runs is the most common way people fool themselves.

**`evals/metrics.py` — the ruler**
- Naive `pred == gold` is too strict: `"RM 9.00"` vs `"9.00"`, `"25-12-2018"` vs `"25/12/2018"` would count as wrong, making the number meaningless.
- So each field has a normaliser: company/address → uppercase, drop punctuation, collapse spaces; date → parse many formats into `YYYY-MM-DD`; total → first number, 2 decimals.
- Two scores: **exact** (after normalising — the headline number) and **fuzzy** (≥ 90% similar, company/address only) to show how many errors are near-misses.

**`evals/run_eval.py` — the runner**
- Loads any extractor by name (`--extractor baseline`), so the agent plugs in later with zero changes to the eval.
- Reports per-field accuracy, **docs fully correct** (all 4 fields right — what a business actually cares about), average cost and latency.
- Saves every prediction to `results/<name>.json` → you can open it and *read the failures*. Error analysis drives what the agent's tools should check.

**`tests/test_metrics.py`** — tests for the scorer itself. If the ruler is wrong, every number is wrong.

### Bug log — "Found 0 labelled receipts"
- **Symptom:** the loader found 0 receipts and the eval then crashed with `ZeroDivisionError`.
- **Root cause:** The loader assumed the OCR box files were `.txt`; in this dataset they are `data/box/*.csv` (same line format, different extension). The answers are `data/key/*.json`.
- **Fix:** match box files by both extensions, prefer the `box/` folder, and make the eval exit with a clear message on an empty test set instead of dividing by zero.
- **Lesson (good interview story):** validate your data assumptions first — print counts after every loading step. A silent "0 rows" upstream turns into a confusing crash downstream.
- The fixed 100-receipt `test.jsonl` is now committed, so results are reproducible without re-downloading.
