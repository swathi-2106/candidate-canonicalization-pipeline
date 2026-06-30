"""Company name normalization using a synonyms map."""
import json
import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DEFAULT_SYNONYMS = {
    "google": "Google",
    "alphabet": "Google",
    "alphabet inc.": "Google",
    "meta": "Meta",
    "facebook": "Meta",
    "fb": "Meta",
    "amazon": "Amazon",
    "amazon.com": "Amazon",
    "amazon web services": "Amazon",
    "aws": "Amazon",
    "microsoft": "Microsoft",
    "msft": "Microsoft",
    "apple": "Apple",
    "apple inc.": "Apple",
    "ibm": "IBM",
    "international business machines": "IBM",
}

_SUFFIX_RE = re.compile(r"\b(inc\.?|llc\.?|ltd\.?|corp\.?|corporation|co\.?)\b\.?", re.IGNORECASE)


class CompanyNormalizer:
    """Standardizes company names using a synonyms file plus suffix stripping."""

    def __init__(self, synonyms_file: Optional[str] = None):
        self.synonyms: Dict[str, str] = self._load_synonyms(synonyms_file)

    def _load_synonyms(self, synonyms_file: Optional[str]) -> Dict[str, str]:
        if synonyms_file:
            try:
                with open(synonyms_file, "r", encoding="utf-8") as f:
                    return {k.lower(): v for k, v in json.load(f).items()}
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Failed to load synonyms file %s: %s. Using default.", synonyms_file, e)
        return DEFAULT_SYNONYMS

    def normalize(self, company: str) -> str:
        """Standardize a company name: trim, strip legal suffixes, apply synonyms."""
        if not company:
            return ""
        cleaned = company.strip()
        key = cleaned.lower()
        if key in self.synonyms:
            return self.synonyms[key]

        stripped = _SUFFIX_RE.sub("", cleaned).strip(" ,.")
        stripped_key = stripped.lower()
        if stripped_key in self.synonyms:
            return self.synonyms[stripped_key]

        # Title-case fallback for consistency, but preserve all-caps acronyms (<=4 chars)
        if len(stripped) <= 4 and stripped.isupper():
            return stripped
        return " ".join(w if w.isupper() and len(w) <= 4 else w.capitalize() for w in stripped.split())
