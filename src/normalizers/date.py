"""Date parsing and standardization."""
import re
import logging
from datetime import datetime
from typing import Optional

try:
    import dateparser
    HAS_DATEPARSER = True
except ImportError:  # pragma: no cover
    HAS_DATEPARSER = False

logger = logging.getLogger(__name__)

_CURRENT_TOKENS = {"present", "current", "now", "ongoing", "today"}


class DateNormalizer:
    """Parses free-form dates and converts to ISO (YYYY-MM-DD or YYYY-MM)."""

    def normalize(self, date_str: str) -> str:
        """Convert a date string to ISO format. Returns 'PRESENT' for
        ongoing markers and '' if unparseable."""
        if not date_str:
            return ""
        cleaned = str(date_str).strip()
        if cleaned.lower() in _CURRENT_TOKENS:
            return "PRESENT"

        parsed = self._parse(cleaned)
        if parsed is None:
            logger.debug("Could not parse date: %s", cleaned)
            return ""

        # if only month/year were present (no day given explicitly), keep YYYY-MM
        if re.fullmatch(r"[A-Za-z]{3,9}\.?\s+\d{4}", cleaned) or re.fullmatch(r"\d{1,2}/\d{4}", cleaned) or re.fullmatch(r"\d{4}", cleaned):
            return parsed.strftime("%Y-%m")
        return parsed.strftime("%Y-%m-%d")

    def parse_experience_years(self, date_str: str) -> float:
        """Given a 'Start - End' style date range, return years of duration."""
        if not date_str:
            return 0.0
        parts = re.split(r"\s*(?:-|–|to)\s*", str(date_str), maxsplit=1)
        if len(parts) != 2:
            return 0.0
        start_raw, end_raw = parts[0].strip(), parts[1].strip()
        start = self._parse(start_raw)
        end = datetime.now() if end_raw.lower() in _CURRENT_TOKENS else self._parse(end_raw)
        if not start or not end:
            return 0.0
        delta_days = (end - start).days
        return round(max(delta_days, 0) / 365.25, 2)

    @staticmethod
    def _parse(value: str) -> Optional[datetime]:
        if HAS_DATEPARSER:
            result = dateparser.parse(value, settings={"PREFER_DAY_OF_MONTH": "first"})
            if result:
                return result
        # fallback formats
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%B %Y", "%b %Y", "%Y", "%m/%Y"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None
