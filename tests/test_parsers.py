import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.parsers.csv_parser import CSVParser
from src.parsers.resume_parser import ResumeParser


CSV_CONTENT = """Candidate Name,Email Address,Phone Number,Skills,Current Company
Jane Doe,Jane.Doe@Example.com,(415) 555-0182,"Python, Django",Google
"""

CSV_MISSING_REQUIRED = """Candidate Name,Phone Number
No Email Here,415-555-0000
"""


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "candidates.csv"
    path.write_text(CSV_CONTENT)
    return str(path)


def test_csv_parser_basic(csv_file):
    parser = CSVParser()
    profiles = parser.parse(csv_file)
    assert len(profiles) == 1
    p = profiles[0]
    assert p.name.value == "Jane Doe"
    assert p.email.value == "jane.doe@example.com"  # normalized lowercase
    assert p.current_company.value == "Google"
    assert len(p.skills) == 2
    assert p.origin == "CSV"


def test_csv_parser_missing_required_field_skips_row(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(CSV_MISSING_REQUIRED)
    parser = CSVParser()
    profiles = parser.parse(str(path))
    assert len(profiles) == 0
    assert len(parser.errors) == 1


def test_csv_parser_custom_column_mapping(tmp_path):
    content = "Nom,Courriel\nJean Dupont,jean@example.com\n"
    path = tmp_path / "custom.csv"
    path.write_text(content)
    parser = CSVParser(column_mapping={"Nom": "name", "Courriel": "email"})
    profiles = parser.parse(str(path))
    assert len(profiles) == 1
    assert profiles[0].name.value == "Jean Dupont"


def test_csv_parser_semicolon_delimiter(tmp_path):
    content = "Candidate Name;Email Address\nAna Silva;ana@example.com\n"
    path = tmp_path / "semi.csv"
    path.write_text(content)
    parser = CSVParser()
    profiles = parser.parse(str(path))
    assert len(profiles) == 1
    assert profiles[0].email.value == "ana@example.com"


def test_resume_parser_handles_missing_file_gracefully():
    parser = ResumeParser()
    result = parser.parse("/nonexistent/path/resume.pdf")
    assert result is None
    assert len(parser.errors) == 1
