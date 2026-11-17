"""Tests for the scorer itself. If the ruler is wrong, every number is wrong."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.metrics import field_match, norm_date, norm_total  # noqa: E402


def test_total_ignores_currency_and_commas():
    assert norm_total("RM 1,234.5") == "1234.50"
    assert field_match("total", "9", "9.00") == (True, True)


def test_date_formats_are_equivalent():
    assert norm_date("25/12/2018") == norm_date("25-12-2018") == "2018-12-25"
    assert field_match("date", "25.12.18", "25/12/2018")[0]


def test_company_ignores_punctuation_and_case():
    assert field_match("company", "book ta.k (taman daya) sdn bhd",
                       "BOOK TA .K (TAMAN DAYA) SDN BHD")[0]


def test_address_fuzzy_catches_near_miss():
    exact, fuzzy = field_match("address", "NO.53 55,57 & 59, JALAN SAGU 18, TAMAN DAYA, 81100 JOHOR BAHRU",
                               "NO.53 55,57 & 59, JALAN SAGU 18, TAMAN DAYA, 81100 JOHOR BAHRU, JOHOR.")
    assert not exact and fuzzy


def test_wrong_value_fails():
    assert field_match("total", "8.00", "9.00") == (False, False)
    assert field_match("company", "", "STARBUCKS") == (False, False)


def test_date_with_brackets_or_compact_format():
    assert norm_date("(06/12/2016)") == "2016-12-06"
    assert norm_date("20180428") == norm_date("2018-04-28") == "2018-04-28"
