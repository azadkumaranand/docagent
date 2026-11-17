"""Run an extractor over the fixed test set and score it.

Usage:
  python evals/run_eval.py --extractor baseline                   # 100 test receipts
  python evals/run_eval.py --extractor agent --limit 5            # quick smoke test
  python evals/run_eval.py --extractor agent --split holdout      # final, unseen receipts

Writes results/<extractor>.json (per-receipt details, so you can read the
failures) and prints a summary table: accuracy per field, docs fully
correct, average cost and latency per receipt.
"""
import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from evals.metrics import field_match  # noqa: E402
from docagent.schema import FIELDS  # noqa: E402


def load_split(split: str, limit: int | None):
    rows = [json.loads(l) for l in open(ROOT / f"data/sroie/{split}.jsonl", encoding="utf-8")]
    return rows[:limit] if limit else rows


def main(extractor_name: str, limit: int | None, split: str = "test") -> None:
    extractor = importlib.import_module(f"docagent.{extractor_name}")
    rows = load_split(split, limit)
    if not rows:
        sys.exit("Test set is empty. Run: python data/download_sroie.py --n 100")
    details, exact = [], {f: 0 for f in FIELDS}
    fuzzy = {f: 0 for f in FIELDS}
    all_correct = cost = latency = 0.0
    attempts = flagged = accepted = accepted_correct = 0

    for i, row in enumerate(rows, 1):
        out = extractor.extract(row["ocr_text"])
        pred, usage = out[0], out[1]
        meta = out[2] if len(out) > 2 else {"attempts": 1, "needs_review": False}
        per_field = {}
        for f in FIELDS:
            e, z = field_match(f, getattr(pred, f), row["labels"][f])
            exact[f] += e
            fuzzy[f] += z
            per_field[f] = {"pred": getattr(pred, f), "gold": row["labels"][f], "exact": e}
        doc_ok = all(v["exact"] for v in per_field.values())
        all_correct += doc_ok
        cost += usage.cost_usd
        latency += usage.latency_s
        attempts += meta["attempts"]
        if meta["needs_review"]:
            flagged += 1
        else:
            accepted += 1
            accepted_correct += doc_ok
        details.append({"id": row["id"], "fields": per_field, "cost_usd": usage.cost_usd, **meta})
        print(f"[{i}/{len(rows)}] {row['id']} " + " ".join(
            f"{f}:{'ok' if per_field[f]['exact'] else 'X'}" for f in FIELDS))

    n = len(rows)
    summary = {
        "extractor": extractor_name, "n": n,
        "exact_accuracy": {f: round(exact[f] / n, 3) for f in FIELDS},
        "fuzzy_accuracy": {f: round(fuzzy[f] / n, 3) for f in FIELDS},
        "field_accuracy_mean": round(sum(exact.values()) / (n * len(FIELDS)), 3),
        "docs_fully_correct": round(all_correct / n, 3),
        "avg_cost_usd": round(cost / n, 6),
        "avg_latency_s": round(latency / n, 2),
        "avg_llm_calls": round(attempts / n, 2),
        "flagged_for_review": round(flagged / n, 3),
        # of the receipts the system did NOT flag, how many were fully correct?
        "auto_accepted_correct": round(accepted_correct / accepted, 3) if accepted else None,
    }
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    name = extractor_name if split == "test" else f"{extractor_name}_{split}"
    (out / f"{name}.json").write_text(
        json.dumps({"summary": summary, "details": details}, indent=2, ensure_ascii=False))

    print("\n=== SUMMARY:", extractor_name, f"on {split} ({n} receipts) ===")
    for f in FIELDS:
        print(f"  {f:8s} exact {summary['exact_accuracy'][f]:.1%}   fuzzy {summary['fuzzy_accuracy'][f]:.1%}")
    print(f"  mean field accuracy : {summary['field_accuracy_mean']:.1%}")
    print(f"  docs fully correct  : {summary['docs_fully_correct']:.1%}")
    print(f"  avg cost / receipt  : ${summary['avg_cost_usd']:.5f}")
    print(f"  avg latency         : {summary['avg_latency_s']}s")
    print(f"  avg LLM calls       : {summary['avg_llm_calls']}")
    print(f"  flagged for review  : {summary['flagged_for_review']:.1%}")
    if summary["auto_accepted_correct"] is not None:
        print(f"  auto-accepted correct: {summary['auto_accepted_correct']:.1%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--extractor", default="baseline")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--split", default="test", choices=["test", "holdout"])
    a = ap.parse_args()
    main(a.extractor, a.limit, a.split)
