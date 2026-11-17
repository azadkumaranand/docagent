"""Tests for the cleaners and validators, using patterns from real failures."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from docagent.schema import Receipt  # noqa: E402
from docagent.tools import check_total, clean, clean_company, clean_date, validate  # noqa: E402


def test_clean_company_drops_registration_number():
    assert clean_company("GARDENIA BAKERIES (KL) SDN BHD (139386 X)") == "GARDENIA BAKERIES (KL) SDN BHD"
    assert clean_company("99 SPEED MART S/B (519537-X)") == "99 SPEED MART S/B"
    assert clean_company("COSWAY (M) SDN BHD (50118-A)") == "COSWAY (M) SDN BHD"  # keeps "(M)"


def test_clean_date_drops_time():
    assert clean_date("20-06-2018 13:11:45") == "20-06-2018"
    assert clean_date("03/07/2018 5:22:43 PM") == "03/07/2018"
    assert clean_date("19 APR 2018 10:02") == "19 APR 2018"


def test_clean_total_drops_currency():
    assert clean(Receipt(total="RM8.50")).total == "8.50"


CASH_RECEIPT = """TOTAL AMT INCL. GST @ 6% :
12.00
TOTAL AMT PAYABLE :
12.00
PAID AMOUNT :
20.00
CHANGE :
8.00"""


def test_total_equal_to_cash_paid_is_flagged():
    issues = check_total("20.00", CASH_RECEIPT)
    assert issues and "12.00" in issues[0]


def test_correct_total_passes():
    assert check_total("12.00", CASH_RECEIPT) == []


def test_total_equal_to_change_is_flagged():
    text = "TOTAL INCL. GST@6%\nRM 23.00\nCASH\nRM 50.00\nCHANGE\nRM 27.00"
    issues = check_total("27.00", text)
    assert issues and "23.00" in issues[0]


def test_ambiguous_double_cash_is_not_flagged():
    # 20 paid, 10 change, 10 total -> can't tell, so stay silent (no false alarm)
    assert check_total("10.00", "TOTAL\n10.00\nCASH\n20.00\nCHANGE\n10.00") == []


def test_total_not_on_receipt_is_flagged():
    assert "does not appear" in check_total("99.99", CASH_RECEIPT)[0]


def test_validate_flags_bad_date_and_empty_company():
    issues = validate(Receipt(company="", date="yesterday", total="12.00"), CASH_RECEIPT)
    assert any("company" in i for i in issues) and any("date" in i for i in issues)
