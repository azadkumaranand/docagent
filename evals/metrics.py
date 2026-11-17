"""How we decide if an extracted field is correct.

Plain string equality is too strict ("9.00" vs "RM 9.00", "25/12/2018" vs
"25-12-2018"), and that would make the numbers meaningless. So each field
type gets its own normaliser, and we report two scores:

- exact : equal after normalisation  (the headline number)
- fuzzy : >= 90% character similarity (company/address only), to see how
          many "wrong" answers are near-misses like a missing comma
"""
import re
from datetime import datetime
from difflib import SequenceMatcher

DATE_FORMATS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%d.%m.%y",
                "%Y-%m-%d", "%Y/%m/%d", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%d-%b-%Y", "%d %b %y"]


def norm_text(s: str) -> str:
    s = s.upper()
    s = re.sub(r"[^\w\s]", " ", s)  # drop punctuation
    return re.sub(r"\s+", " ", s).strip()


def norm_date(s: str) -> str:
    s = s.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return norm_text(s)  # unparseable -> fall back to text compare


def norm_total(s: str) -> str:
    s = s.replace(",", "")
    m = re.search(r"-?\d+(\.\d+)?", s)
    return f"{float(m.group()):.2f}" if m else ""


NORMALISERS = {"company": norm_text, "address": norm_text, "date": norm_date, "total": norm_total}


def field_match(field: str, pred: str, gold: str) -> tuple[bool, bool]:
    """Return (exact_match, fuzzy_match) for one field."""
    n = NORMALISERS[field]
    p, g = n(pred or ""), n(gold or "")
    exact = p == g
    if field in ("company", "address"):
        fuzzy = exact or (bool(p) and SequenceMatcher(None, p, g).ratio() >= 0.9)
    else:
        fuzzy = exact
    return exact, fuzzy
