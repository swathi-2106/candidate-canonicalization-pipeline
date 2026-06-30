"""Low-level reusable format validators (distinct from the pipeline Validator
service, which validates whole CandidateProfile objects)."""
import re

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def is_valid_email_format(email: str) -> bool:
    return bool(email and EMAIL_RE.match(email.strip()))


def is_nonempty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_plausible_year(value) -> bool:
    try:
        year = int(value)
        return 1950 <= year <= 2100
    except (TypeError, ValueError):
        return False
