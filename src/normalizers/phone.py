"""Phone number normalization using libphonenumber (phonenumbers package)."""
import logging

try:
    import phonenumbers
    from phonenumbers import NumberParseException
    HAS_PHONENUMBERS = True
except ImportError:  # pragma: no cover
    HAS_PHONENUMBERS = False

logger = logging.getLogger(__name__)


class PhoneNormalizer:
    """Normalizes phone numbers to E.164 international format."""

    def normalize(self, phone: str, country_code: str = "US") -> str:
        """Return normalized phone number in E.164 format, or the cleaned
        original string if it cannot be parsed."""
        if not phone or not str(phone).strip():
            return ""
        raw = str(phone).strip()

        if not HAS_PHONENUMBERS:
            return self._fallback_clean(raw)

        try:
            parsed = phonenumbers.parse(raw, country_code)
            if phonenumbers.is_valid_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            return self._fallback_clean(raw)
        except NumberParseException:
            logger.debug("Could not parse phone number: %s", raw)
            return self._fallback_clean(raw)

    def is_valid(self, phone: str, country_code: str = "US") -> bool:
        if not phone:
            return False
        if not HAS_PHONENUMBERS:
            digits = "".join(c for c in phone if c.isdigit())
            return 7 <= len(digits) <= 15
        try:
            parsed = phonenumbers.parse(phone, country_code)
            return phonenumbers.is_valid_number(parsed)
        except NumberParseException:
            return False

    @staticmethod
    def _fallback_clean(raw: str) -> str:
        digits = "".join(c for c in raw if c.isdigit() or c == "+")
        return digits
