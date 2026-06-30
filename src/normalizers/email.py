"""Email validation and normalization."""
import re
import logging

try:
    from email_validator import validate_email, EmailNotValidError
    HAS_EMAIL_VALIDATOR = True
except ImportError:  # pragma: no cover
    HAS_EMAIL_VALIDATOR = False

logger = logging.getLogger(__name__)

_EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


class EmailNormalizer:
    """Validates and normalizes email addresses."""

    def normalize(self, email: str) -> str:
        """Lowercase and trim an email address."""
        if not email:
            return ""
        return str(email).strip().lower()

    def validate(self, email: str) -> bool:
        """Validate an email's format."""
        if not email:
            return False
        cleaned = str(email).strip()
        if HAS_EMAIL_VALIDATOR:
            try:
                validate_email(cleaned, check_deliverability=False)
                return True
            except EmailNotValidError:
                return False
        return bool(_EMAIL_REGEX.match(cleaned))
