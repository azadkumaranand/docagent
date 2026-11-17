"""ABLATION: baseline + deterministic cleaning, no agent loop.

Comparing baseline -> baseline_clean -> agent shows exactly how much of the
gain comes from plain code and how much from the LLM retry loop. If the
loop adds little, the cheaper version wins.
"""
from . import baseline
from .llm import LLMResult
from .schema import Receipt
from .tools import clean


def extract(ocr_text: str) -> tuple[Receipt, LLMResult]:
    receipt, usage = baseline.extract(ocr_text)
    return clean(receipt), usage
