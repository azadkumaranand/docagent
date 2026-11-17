# DocAgent

**Agentic document extraction with measured accuracy.** An LLM pipeline that pulls structured fields (company, address, date, total) out of messy scanned receipts — and proves, with a fixed evaluation set, how much an agentic workflow beats a single-prompt baseline.

> Status: **agent implemented** — run it to fill in the results below.

## Why this project

Most LLM demos show an answer. Production teams need to know *how often the answer is right*, what it costs, and what happens when it's wrong. DocAgent is built around that question:

1. **Baseline** – one prompt, one call, no checks.
2. **Agent** – LangGraph workflow: extract → validate with tools (schema, totals, date format) → self-correct → route low-confidence docs to human review.
3. **Evals** – both run on the *same* 100 real receipts (ICDAR-2019 SROIE); field-level accuracy, cost and latency are reported side by side.

## Architecture (target)

```
receipt (OCR text / image)
        │
        ▼
 ┌──────────────┐    ┌─────────────────────────┐
 │ extract node │───▶│ validate node (tools)   │──ok──▶ structured JSON
 └──────────────┘    │ • schema check          │
        ▲            │ • date / total format   │
        │  feedback  │ • total consistency     │
        └────────────┤ retry ≤ 2               │──still failing──▶ human review queue
                     └─────────────────────────┘
```

## Results

100 SROIE receipts, exact match after per-field normalisation. Mean field accuracy for the baseline: **82.8%** — yet only **half** the receipts come out fully correct, i.e. every second document still needs a human.


| Extractor | Company | Address | Date | Total | Docs fully correct | Cost / receipt | Latency |
|---|---|---|---|---|---|---|---|
| Baseline (single prompt, gpt-4o-mini) | 75.0% | 86.0% | 84.0% | 86.0% | **50.0%** | $0.00010 | 1.87 s |
| + deterministic cleaning | _tbd_ | _tbd_ | _tbd_ | _tbd_ | _tbd_ | _tbd_ | _tbd_ |
| Agent (LangGraph: clean + validate + retry) | _tbd_ | _tbd_ | _tbd_ | _tbd_ | _tbd_ | _tbd_ | _tbd_ |

Holdout (100 unseen receipts) results are reported separately to avoid test-set overfitting — see [DESIGN.md](DESIGN.md).

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # add your API key
python data/download_sroie.py --n 100                      # build the fixed test set
python evals/run_eval.py --extractor baseline --limit 5    # smoke test
python evals/run_eval.py --extractor baseline              # full baseline
python evals/run_eval.py --extractor baseline_clean        # + deterministic cleaning
python evals/run_eval.py --extractor agent                 # LangGraph agent
python evals/run_eval.py --extractor agent --split holdout # final score on unseen receipts
pytest -q                                                  # scorer tests
```

## Project layout

```
src/docagent/schema.py     # the output contract (Pydantic)
src/docagent/llm.py        # provider wrapper: text + tokens + latency + cost
src/docagent/baseline.py   # single-prompt extractor (the "before")
src/docagent/tools.py      # deterministic cleaners + validation tools
src/docagent/baseline_clean.py # ablation: baseline + cleaning, no loop
src/docagent/agent.py      # LangGraph agent: extract -> clean -> validate -> retry/review
data/download_sroie.py     # dataset → fixed test + holdout splits (seed 42)
evals/metrics.py           # per-field normalisers + exact / fuzzy matching
evals/run_eval.py          # runs any extractor, writes results/<name>.json
evals/rescore.py           # re-score saved predictions after a metric change (no API cost)
tests/                     # scorer, tools, and agent loop (fake LLM, no API cost)
DESIGN.md                  # design decisions and engineering log
```

## Dataset

[ICDAR 2019 SROIE](https://github.com/zzzDavid/ICDAR-2019-SROIE) — ~1000 real scanned receipts with OCR text boxes and labelled key fields. Public data only; no client or employer documents are used.
