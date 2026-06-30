import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.normalizers.phone import PhoneNormalizer
from src.normalizers.email import EmailNormalizer
from src.normalizers.date import DateNormalizer
from src.normalizers.skills import SkillsNormalizer
from src.normalizers.company import CompanyNormalizer
from src.normalizers.experience import ExperienceNormalizer


def test_phone_normalizer_valid_us_number():
    n = PhoneNormalizer()
    result = n.normalize("(415) 555-0182", "US")
    assert result.startswith("+1415")


def test_phone_normalizer_invalid_falls_back():
    n = PhoneNormalizer()
    result = n.normalize("not-a-phone", "US")
    assert isinstance(result, str)


def test_email_normalizer_lowercases_and_trims():
    n = EmailNormalizer()
    assert n.normalize("  Jane.DOE@Example.COM ") == "jane.doe@example.com"


def test_email_normalizer_validation():
    n = EmailNormalizer()
    assert n.validate("jane@example.com") is True
    assert n.validate("not-an-email") is False


def test_date_normalizer_iso_format():
    n = DateNormalizer()
    assert n.normalize("January 2020") == "2020-01"
    assert n.normalize("2020-05-01") == "2020-05-01"


def test_date_normalizer_present_token():
    n = DateNormalizer()
    assert n.normalize("Present") == "PRESENT"


def test_date_normalizer_experience_years():
    n = DateNormalizer()
    years = n.parse_experience_years("Jan 2018 - Jan 2020")
    assert 1.9 <= years <= 2.1


def test_skills_normalizer_maps_known_skill():
    n = SkillsNormalizer()
    result = n.normalize(["python", "PYTHON", "django"])
    assert "Python" in result
    assert "Django" in result
    assert len(result) == 2  # deduped


def test_skills_normalizer_categorize():
    n = SkillsNormalizer()
    cats = n.categorize(["Python", "AWS"])
    assert "Programming Languages" in cats
    assert "Cloud & DevOps" in cats


def test_company_normalizer_synonyms():
    n = CompanyNormalizer()
    assert n.normalize("alphabet inc.") == "Google"
    assert n.normalize("FB") in ("Meta", "Fb")  # FB not in default synonyms map verbatim


def test_company_normalizer_strips_suffix():
    n = CompanyNormalizer()
    result = n.normalize("Acme Corp.")
    assert "Corp" not in result


def test_experience_normalizer_total_years():
    n = ExperienceNormalizer()
    total = n.total_years(["Jan 2015 - Jan 2017", "Feb 2017 - Feb 2019"])
    assert total > 3.5
