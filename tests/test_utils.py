from pathlib import Path
from datetime import date, datetime

import pytest

from mudpeter.utils.utils import is_probably_jinja_template, parse_date_or_datetime


def test_detects_simple_jinja_template(tmp_path: Path) -> None:
    template = tmp_path / "template.txt"
    template.write_text("Hello {{ name }}!", encoding="utf-8")

    assert is_probably_jinja_template(template) is True


def test_rejects_plain_text_file(tmp_path: Path) -> None:
    text_file = tmp_path / "plain.txt"
    text_file.write_text("Just some plain text without Jinja syntax.", encoding="utf-8")

    assert is_probably_jinja_template(text_file) is False


def test_rejects_nonexistent_path(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"

    assert is_probably_jinja_template(missing) is False


def test_rejects_invalid_jinja_syntax(tmp_path: Path) -> None:
    bad_template = tmp_path / "bad.txt"
    # Invalid Jinja syntax, e.g. unclosed block
    bad_template.write_text("{% if x %}\nHello\n", encoding="utf-8")

    assert is_probably_jinja_template(bad_template) is False
    
def test_timestamp_from_string() -> None:
    good_string_ts = "2022-01-02 15:01:00"
    bad_string1_ts = "2022-22-01 13:00:00"
    bad_string2 = "2000-01-01 X"
    good_string_date = "2000-01-21"
    bad_string_date = "Xasa"
    
    assert isinstance(parse_date_or_datetime(good_string_ts), datetime)
    assert isinstance(parse_date_or_datetime(good_string_date), date)
    assert parse_date_or_datetime(bad_string1_ts) is None
    assert parse_date_or_datetime(bad_string2) is None
    assert parse_date_or_datetime(bad_string_date) is None