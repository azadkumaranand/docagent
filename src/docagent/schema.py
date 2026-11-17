"""The shape of the answer we want from every extractor.

Why a Pydantic model?
- One single definition of "a correct output" that the baseline, the agent,
  the API and the evals all share.
- Pydantic validates types for us, so a malformed LLM answer fails loudly
  instead of silently producing garbage downstream.
"""
from pydantic import BaseModel, Field


class Receipt(BaseModel):
    company: str = Field("", description="Merchant / business name as printed")
    address: str = Field("", description="Merchant address as printed")
    date: str = Field("", description="Transaction date as printed, e.g. 25/12/2018")
    total: str = Field("", description="Final amount paid, digits only, e.g. 9.00")


FIELDS = list(Receipt.model_fields.keys())  # ["company", "address", "date", "total"]
