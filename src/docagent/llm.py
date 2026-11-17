"""A tiny wrapper around the LLM provider.

Why wrap the SDK instead of calling it directly everywhere?
1. Swap providers (OpenAI <-> Anthropic) with one env variable, no code changes.
2. Every call returns the same object with text + token usage + latency,
   so the eval can report cost and speed, not just accuracy.
"""
import os
import time
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # optional
    def load_dotenv(): pass

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # "openai" or "anthropic"
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# USD per 1M tokens (input, output). Edit if you change models.
PRICES = {
    "gpt-4o-mini": (0.15, 0.60),
    "claude-haiku-4-5": (1.00, 5.00),
}


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    latency_s: float

    @property
    def cost_usd(self) -> float:
        p_in, p_out = PRICES.get(MODEL, (0.0, 0.0))
        return (self.input_tokens * p_in + self.output_tokens * p_out) / 1_000_000


def complete(system: str, user: str, temperature: float = 0.0) -> LLMResult:
    """Send one system + user message, return the reply with usage stats.

    temperature=0 -> most deterministic answer, which keeps evals repeatable.
    """
    start = time.perf_counter()
    if PROVIDER == "openai":
        from openai import OpenAI

        client = OpenAI()
        r = client.chat.completions.create(
            model=MODEL,
            temperature=temperature,
            response_format={"type": "json_object"},  # forces valid JSON text
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        text = r.choices[0].message.content or ""
        tin, tout = r.usage.prompt_tokens, r.usage.completion_tokens
    elif PROVIDER == "anthropic":
        import anthropic

        client = anthropic.Anthropic()
        r = client.messages.create(
            model=MODEL, max_tokens=512, temperature=temperature, system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in r.content if b.type == "text")
        tin, tout = r.usage.input_tokens, r.usage.output_tokens
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {PROVIDER}")
    return LLMResult(text, tin, tout, time.perf_counter() - start)
