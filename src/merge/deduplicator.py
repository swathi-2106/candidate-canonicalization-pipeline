"""Detects and merges duplicate candidate profiles (e.g. same candidate
appearing in CSV and resume, or multiple resumes for the same person)."""
import logging
from typing import List, Optional, Tuple

from src.models import CandidateProfile

logger = logging.getLogger(__name__)


class Deduplicator:
    """Groups duplicate profiles using email plus lightweight secondary rules."""

    def deduplicate(self, profiles: List[CandidateProfile], merge_engine) -> List[CandidateProfile]:
        groups: List[Tuple[List[CandidateProfile], List[str]]] = []
        for p in profiles:
            matched = False
            for group, reasons in groups:
                reason = self._duplicate_reason(group[0], p)
                if reason:
                    group.append(p)
                    reasons.append(reason)
                    matched = True
                    break
            if not matched:
                groups.append(([p], []))

        deduped: List[CandidateProfile] = []
        for group, reasons in groups:
            if len(group) == 1:
                deduped.append(group[0])
                continue
            merged = group[0]
            for other, reason in zip(group[1:], reasons):
                csv_p = merged if merged.origin == "CSV" else (other if other.origin == "CSV" else merged)
                resume_p = merged if merged.origin == "RESUME_PDF" else (other if other.origin == "RESUME_PDF" else other)
                if csv_p is resume_p:
                    # both same origin type; just keep the first, note duplicate
                    merged.merge_notes.append(f"Duplicate profile from {other.source_files} merged ({reason}).")
                    merged.source_files = list(dict.fromkeys(merged.source_files + other.source_files))
                    continue
                merged = merge_engine.merge(csv_p, resume_p)
                merged.merge_notes.insert(0, f"Duplicate match: {reason}.")
            deduped.append(merged)

        return deduped

    def _duplicate_reason(self, left: CandidateProfile, right: CandidateProfile) -> Optional[str]:
        if self._email(left) and self._email(left) == self._email(right):
            return "same normalized email"
        if self._phone(left) and self._phone(left) == self._phone(right):
            return "same normalized phone number"
        if self._name(left) and self._name(left) == self._name(right):
            if self._company(left) and self._company(left) == self._company(right):
                return "same full name and current company"
            if self._linkedin(left) and self._linkedin(left) == self._linkedin(right):
                return "same full name and LinkedIn URL"
            if self._experience_signature(left) and self._experience_signature(left) == self._experience_signature(right):
                return "same full name and similar experience history"
        return None

    @staticmethod
    def _field_value(field) -> str:
        return str(field.value).strip().lower() if field and field.value else ""

    def _email(self, profile: CandidateProfile) -> str:
        return self._field_value(profile.email)

    def _name(self, profile: CandidateProfile) -> str:
        return " ".join(self._field_value(profile.name).split())

    def _phone(self, profile: CandidateProfile) -> str:
        if not profile.contact:
            return ""
        return self._field_value(profile.contact.phone)

    def _linkedin(self, profile: CandidateProfile) -> str:
        if not profile.contact:
            return ""
        return self._field_value(profile.contact.linkedin).rstrip("/")

    def _company(self, profile: CandidateProfile) -> str:
        return self._field_value(profile.current_company)

    def _experience_signature(self, profile: CandidateProfile) -> str:
        parts = []
        for exp in profile.experience[:3]:
            company = self._field_value(exp.company)
            title = self._field_value(exp.title)
            if company or title:
                parts.append(f"{title}@{company}")
        return "|".join(parts)
