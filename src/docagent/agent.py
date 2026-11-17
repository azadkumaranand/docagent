"""AGENT: extract -> clean -> validate -> (done | retry with feedback | human review).

    START -> extract -> clean -> validate --(no issues)--------------> END
                ^                    |
                |---(issues, retries left: feedback)---|
                                     |
                                     +--(issues, no retries left)--> review -> END

Why LangGraph?
- The flow has a LOOP (retry) and a BRANCH (done / retry / review).
  LangGraph makes that an explicit graph with a typed shared state,
  instead of nested if/while code, so it is easy to read, draw and extend
  (e.g. add a vision node for images later).
- Each node is a small pure function: state in -> partial state out.
  That keeps every step unit-testable without the graph or the LLM.
"""
import json
from typing import TypedDict

from .baseline import SYSTEM
from .llm import LLMResult, complete
from .schema import Receipt
from .tools import clean, validate

MAX_RETRIES = 2  # caps cost and latency: at most 3 LLM calls per receipt


class State(TypedDict, total=False):
    ocr_text: str
    receipt: dict           # current answer
    issues: list[str]       # problems found by validate
    attempts: int           # LLM calls made so far
    needs_review: bool      # True -> a human must check this receipt
    input_tokens: int
    output_tokens: int
    latency_s: float


# ------------------------------------------------------------------ nodes

def _parse(text: str) -> Receipt:
    try:
        data = json.loads(text)
        return Receipt(**{k: str(v) for k, v in data.items() if k in Receipt.model_fields})
    except (json.JSONDecodeError, TypeError, ValueError):
        return Receipt()


def build_user_message(state: State) -> str:
    """First attempt: just the receipt. Retries: previous answer + exact problems."""
    msg = f"Receipt OCR text:\n\n{state['ocr_text']}"
    if state.get("issues"):
        msg += (
            "\n\nYour previous answer was:\n" + json.dumps(state["receipt"])
            + "\n\nThese checks FAILED:\n- " + "\n- ".join(state["issues"])
            + "\n\nRe-read the receipt and return the corrected JSON. "
              "Keep fields that were not flagged unchanged."
        )
    return msg


def extract_node(state: State, llm=complete) -> State:
    r: LLMResult = llm(SYSTEM, build_user_message(state))
    return {
        "receipt": _parse(r.text).model_dump(),
        "attempts": state.get("attempts", 0) + 1,
        "input_tokens": state.get("input_tokens", 0) + r.input_tokens,
        "output_tokens": state.get("output_tokens", 0) + r.output_tokens,
        "latency_s": state.get("latency_s", 0.0) + r.latency_s,
    }


def clean_node(state: State) -> State:
    return {"receipt": clean(Receipt(**state["receipt"])).model_dump()}


def validate_node(state: State) -> State:
    return {"issues": validate(Receipt(**state["receipt"]), state["ocr_text"])}


def review_node(state: State) -> State:
    return {"needs_review": True}


def route(state: State) -> str:
    if not state["issues"]:
        return "done"
    if state["attempts"] <= MAX_RETRIES:
        return "retry"
    return "review"


# ------------------------------------------------------------------ graph

def build_graph(llm=complete):
    from langgraph.graph import END, START, StateGraph

    g = StateGraph(State)
    g.add_node("extract", lambda s: extract_node(s, llm))
    g.add_node("clean", clean_node)
    g.add_node("validate", validate_node)
    g.add_node("review", review_node)

    g.add_edge(START, "extract")
    g.add_edge("extract", "clean")
    g.add_edge("clean", "validate")
    g.add_conditional_edges("validate", route,
                            {"done": END, "retry": "extract", "review": "review"})
    g.add_edge("review", END)
    return g.compile()


_graph = None


def extract(ocr_text: str) -> tuple[Receipt, LLMResult, dict]:
    """Same interface as baseline.extract, plus a meta dict for the eval."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    final = _graph.invoke({"ocr_text": ocr_text, "attempts": 0, "needs_review": False})
    usage = LLMResult("", final["input_tokens"], final["output_tokens"], final["latency_s"])
    meta = {"attempts": final["attempts"], "needs_review": final["needs_review"],
            "issues": final["issues"]}
    return Receipt(**final["receipt"]), usage, meta
