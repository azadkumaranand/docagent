"""Download SROIE receipts and build a fixed test set.

SROIE (ICDAR 2019) = ~1000 real scanned receipts. For each receipt it gives:
  - a .csv/.txt file (data/box): one OCR text box per line ->  x1,y1,x2,y2,x3,y3,x4,y4,TEXT
  - a .json file (data/key): the correct answers ->  {company, address, date, total}

Output: data/sroie/test.jsonl  (one receipt per line: id, ocr_text, labels)

Why a FIXED test set (seed 42)?
Every experiment (baseline, agent v1, agent v2...) must run on the SAME
receipts, otherwise the accuracy numbers are not comparable.

Usage:  python data/download_sroie.py --n 100
"""
import argparse
import json
import random
import subprocess
from pathlib import Path

REPO = "https://github.com/zzzDavid/ICDAR-2019-SROIE.git"
ROOT = Path(__file__).parent
RAW = ROOT / "raw_sroie"
OUT = ROOT / "sroie"
KEYS = {"company", "address", "date", "total"}


def ocr_lines_to_text(txt_path: Path) -> str:
    """Turn OCR boxes into reading-order text (top-to-bottom, then left-to-right)."""
    boxes = []
    for line in txt_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split(",", 8)  # 8 coordinates, then the text (which may contain commas)
        if len(parts) < 9:
            continue
        try:
            x1, y1 = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        boxes.append((y1, x1, parts[8].strip()))
    boxes.sort()
    return "\n".join(text for _, _, text in boxes)


def main(n: int) -> None:
    if not RAW.exists():
        subprocess.run(["git", "clone", "--depth", "1", REPO, str(RAW)], check=True)

    # Find every answer JSON, then the OCR box file (.csv or .txt) with the same file name.
    txt_by_id = {}
    for ext in ("*.txt", "*.csv"):
        for p in RAW.rglob(ext):
            if "box" in p.parts or p.stem not in txt_by_id:
                txt_by_id[p.stem] = p
    records = []
    for jp in RAW.rglob("*.json"):
        try:
            labels = json.loads(jp.read_text(encoding="utf-8", errors="ignore"))
        except json.JSONDecodeError:
            continue
        if not isinstance(labels, dict) or not KEYS.issubset(labels):
            continue
        txt = txt_by_id.get(jp.stem)
        if txt is None:
            continue
        records.append({"id": jp.stem, "ocr_text": ocr_lines_to_text(txt),
                        "labels": {k: str(labels[k]) for k in KEYS}})

    records.sort(key=lambda r: r["id"])
    random.Random(42).shuffle(records)
    test = records[:n]

    OUT.mkdir(exist_ok=True)
    with open(OUT / "test.jsonl", "w", encoding="utf-8") as f:
        for r in test:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Found {len(records)} labelled receipts -> wrote {len(test)} to {OUT/'test.jsonl'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="test set size")
    main(ap.parse_args().n)
