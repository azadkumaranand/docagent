"""Re-score saved predictions with the current metrics - no new LLM calls.

Use this after changing evals/metrics.py, so old and new extractors are
always judged by the same ruler (and we don't pay for the API again).

Usage:  python evals/rescore.py --extractor baseline
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from evals.metrics import field_match  # noqa: E402
from docagent.schema import FIELDS  # noqa: E402


def main(name: str) -> None:
    path = ROOT / "results" / f"{name}.json"
    data = json.loads(path.read_text())
    details, summary = data["details"], data["summary"]
    n = len(details)
    exact = {f: 0 for f in FIELDS}
    fuzzy = {f: 0 for f in FIELDS}
    all_correct = 0
    for d in details:
        ok = True
        for f in FIELDS:
            fd = d["fields"][f]
            e, z = field_match(f, fd["pred"], fd["gold"])
            fd["exact"] = e
            exact[f] += e
            fuzzy[f] += z
            ok &= e
        all_correct += ok
    summary["exact_accuracy"] = {f: round(exact[f] / n, 3) for f in FIELDS}
    summary["fuzzy_accuracy"] = {f: round(fuzzy[f] / n, 3) for f in FIELDS}
    summary["field_accuracy_mean"] = round(sum(exact.values()) / (n * len(FIELDS)), 3)
    summary["docs_fully_correct"] = round(all_correct / n, 3)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--extractor", default="baseline")
    main(ap.parse_args().extractor)
