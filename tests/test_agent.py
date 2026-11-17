"""Agent loop tests with a FAKE LLM - no API key, no cost, fully repeatable.

run_loop() follows exactly the same edges as the LangGraph graph, so the
node + routing logic is tested even without LangGraph installed. If
LangGraph IS installed, the real compiled graph is tested too.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from docagent import agent  # noqa: E402
from docagent.llm import LLMResult  # noqa: E402

OCR = """BOOK TA .K (TAMAN DAYA) SDN BHD (789417-W)
NO.53 55,57 & 59, JALAN SAGU 18,
DATE: 25/12/2018 13:02:11
TOTAL AMT PAYABLE :
12.00
PAID AMOUNT :
20.00
CHANGE :
8.00"""

WRONG = {"company": "BOOK TA .K (TAMAN DAYA) SDN BHD (789417-W)", "address": "NO.53 55,57 & 59, JALAN SAGU 18,",
         "date": "25/12/2018 13:02:11", "total": "20.00"}
RIGHT = {**WRONG, "total": "12.00"}


class FakeLLM:
    """Returns the given answers in order and records every prompt it saw."""
    def __init__(self, *answers):
        self.answers, self.prompts = list(answers), []

    def __call__(self, system, user):
        self.prompts.append(user)
        return LLMResult(json.dumps(self.answers.pop(0)), 100, 20, 0.5)


def run_loop(llm):
    state = {"ocr_text": OCR, "attempts": 0, "needs_review": False}
    while True:
        state |= agent.extract_node(state, llm)
        state |= agent.clean_node(state)
        state |= agent.validate_node(state)
        nxt = agent.route(state)
        if nxt == "done":
            return state
        if nxt == "review":
            return state | agent.review_node(state)


def test_retry_with_feedback_fixes_total():
    llm = FakeLLM(WRONG, RIGHT)
    final = run_loop(llm)
    assert final["receipt"]["total"] == "12.00"
    assert final["attempts"] == 2 and not final["needs_review"]
    assert "FAILED" in llm.prompts[1] and "8.00" in llm.prompts[1]   # feedback was specific
    assert final["receipt"]["company"] == "BOOK TA .K (TAMAN DAYA) SDN BHD"  # cleaner ran
    assert final["receipt"]["date"] == "25/12/2018"
    assert final["input_tokens"] == 200                               # usage is summed


def test_gives_up_after_max_retries_and_flags_for_review():
    final = run_loop(FakeLLM(WRONG, WRONG, WRONG))
    assert final["attempts"] == agent.MAX_RETRIES + 1
    assert final["needs_review"] is True


def test_correct_first_time_makes_one_call():
    final = run_loop(FakeLLM(RIGHT))
    assert final["attempts"] == 1 and final["issues"] == []


def test_real_langgraph_graph_matches_loop():
    pytest.importorskip("langgraph")
    graph = agent.build_graph(llm=FakeLLM(WRONG, RIGHT))
    final = graph.invoke({"ocr_text": OCR, "attempts": 0, "needs_review": False})
    assert final["receipt"]["total"] == "12.00" and final["attempts"] == 2
