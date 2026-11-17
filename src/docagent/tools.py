"""Deterministic cleaners and validation tools used by the agent.

Design rule: use plain code where the rule is certain, use the LLM only
where judgement is needed.
- CLEANERS fix patterns we are sure about (no LLM, free, instant).
- VALIDATORS check an answer against the receipt's own text and return
  human-readable issues. The agent sends those issues back to the LLM as
  feedback, so a retry is targeted instead of blind.
"""
import re
from datetime import datetime

from .schema import Receipt

# ---------------------------------------------------------------- cleaners

# Malaysian company registration numbers: "(139386 X)", "(519537-X)", "(1248446-V)"
_REG_NO = re.compile(r"\s*\(\s*\d{3,8}\s*-?\s*[A-Z]\s*\)")
# A date token: 25/12/2018, 20-06-2018, 5/3/2018, 2018-04-28, 11/03/18, 19 APR 2018, 05-AUG-2017
_DATE_TOKEN = re.compile(r"\d{1,4}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}[ /\-.][A-Za-z]{3}[ /\-.]\d{2,4}")


def clean_company(company: str) -> str:
    """Drop the registration number the model often copies from the header."""
    return _REG_NO.sub("", company).strip()


def clean_date(date: str) -> str:
    """Keep only the date token, e.g. '20-06-2018 13:11:45' -> '20-06-2018'."""
    m = _DATE_TOKEN.search(date)
    return m.group() if m else date.strip()


def clean(receipt: Receipt) -> Receipt:
    return receipt.model_copy(update={
        "company": clean_company(receipt.company),
        "date": clean_date(receipt.date),
        "total": receipt.total.replace("RM", "").replace(",", "").strip(),
    })


# -------------------------------------------------------------- validators

_DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
                 "%Y-%m-%d", "%Y/%m/%d", "%Y%m%d",
                 "%d %b %Y", "%d-%b-%Y", "%d/%b/%Y", "%d %b %y", "%d-%b-%y"]
_AMOUNT = re.compile(r"-?\d+\.\d{2}")
_PAID_LABEL = re.compile(r"\b(CASH|PAID|TENDER(ED)?)\b", re.I)
_CHANGE_LABEL = re.compile(r"\bCHANGE\b", re.I)


def is_valid_date(date: str) -> bool:
    for fmt in _DATE_FORMATS:
        try:
            datetime.strptime(date.strip(), fmt)
            return True
        except ValueError:
            pass
    return False


def _amount_after(lines: list[str], i: int, label: re.Pattern) -> float | None:
    """Amount printed after a label: same line first, else one of the next 2 lines."""
    rest = label.split(lines[i], maxsplit=1)[-1]
    m = _AMOUNT.search(rest)
    if m:
        return float(m.group())
    for nxt in lines[i + 1:i + 3]:
        m = _AMOUNT.search(nxt)
        if m and len(nxt.strip()) <= 14:  # a short line that is basically just the number
            return float(m.group())
    return None


def _amounts_near(ocr_text: str, label: re.Pattern, exclude: re.Pattern | None = None) -> list[float]:
    lines = ocr_text.split("\n")
    out = []
    for i, line in enumerate(lines):
        if label.search(line) and not (exclude and exclude.search(line)):
            v = _amount_after(lines, i, label)
            if v is not None:
                out.append(v)
    return out


def check_total(total: str, ocr_text: str) -> list[str]:
    """Return issues with the total, each one explaining what looks wrong and why."""
    try:
        value = float(total)
    except ValueError:
        return [f"total '{total}' is not a number like 12.50"]

    printed = {float(a) for a in _AMOUNT.findall(ocr_text.replace(",", ""))}
    if value not in printed:
        return [f"total {total} does not appear anywhere on the receipt"]

    issues = []
    paid = _amounts_near(ocr_text, _PAID_LABEL)
    change = [c for c in _amounts_near(ocr_text, _CHANGE_LABEL) if c > 0]

    # Rule A: the model picked the cash the customer handed over.
    # Only when real change was given AND cash - change is printed on the receipt.
    if value in paid:
        for c in change:
            expected = round(value - c, 2)
            if expected > 0 and expected in printed:
                issues.append(
                    f"total {total} equals the cash paid by the customer, not the bill: "
                    f"cash {value:.2f} minus change {c:.2f} = {expected:.2f}")
                break

    # Rule B: the model picked the change given back.
    elif value in change and paid:
        expected = round(max(paid) - value, 2)
        # skip the ambiguous case cash = 2 x total (e.g. 20 paid, 10 change, 10 total)
        if expected > 0 and expected != value and expected in printed:
            issues.append(
                f"total {total} is the change given back, not the bill: "
                f"cash {max(paid):.2f} minus change {value:.2f} = {expected:.2f}")
    return issues


def validate(receipt: Receipt, ocr_text: str) -> list[str]:
    """All issues for one extracted receipt. Empty list = passed every check."""
    issues = []
    if not receipt.company:
        issues.append("company is empty")
    if not is_valid_date(receipt.date):
        issues.append(f"date '{receipt.date}' is not a valid date like 25/12/2018")
    issues += check_total(receipt.total, ocr_text)
    return issues
