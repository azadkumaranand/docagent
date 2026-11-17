"""BASELINE: one prompt, one LLM call, no checks.

This is deliberately simple. It is the "before" number that the agent in
Week 2 has to beat. If we skip the baseline we can never prove the agent
is better - we could only claim it.
"""
import json

from .llm import LLMResult, complete
from .schema import Receipt

SYSTEM = (
    "You extract fields from receipt OCR text. "
    "Return ONLY a JSON object with keys: company, address, date, total. "
    "Copy values exactly as printed. total = final amount paid, digits and dot only. "
    "Use an empty string if a field is missing."
)


def extract(ocr_text: str) -> tuple[Receipt, LLMResult]:
    result = complete(SYSTEM, f"Receipt OCR text:\n\n{ocr_text}")
    try:
        data = json.loads(result.text)
        receipt = Receipt(**{k: str(v) for k, v in data.items() if k in Receipt.model_fields})
    except (json.JSONDecodeError, TypeError, ValueError):
        receipt = Receipt()  # a parse failure counts as all fields wrong
    return receipt, result
