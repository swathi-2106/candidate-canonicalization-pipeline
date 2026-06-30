"""Detects and merges duplicate candidate profiles (e.g. same candidate
appearing in CSV and resume, or multiple resumes for the same person)."""
import logging
from typing import List, Dict

from src.models import CandidateProfile

logger = logging.getLogger(__name__)


class Deduplicator:
    """Groups profiles by normalized email (primary key) and merges each group."""

    def deduplicate(self, profiles: List[CandidateProfile], merge_engine) -> List[CandidateProfile]:
        groups: Dict[str, List[CandidateProfile]] = {}
        no_email: List[CandidateProfile] = []

        for p in profiles:
            email_val = (p.email.value if p.email else "") or ""
            key = str(email_val).strip().lower()
            if not key:
                no_email.append(p)
                continue
            groups.setdefault(key, []).append(p)

        deduped: List[CandidateProfile] = []
        for key, group in groups.items():
            if len(group) == 1:
                deduped.append(group[0])
                continue
            merged = group[0]
            for other in group[1:]:
                csv_p = merged if merged.origin == "CSV" else (other if other.origin == "CSV" else merged)
                resume_p = merged if merged.origin == "RESUME_PDF" else (other if other.origin == "RESUME_PDF" else other)
                if csv_p is resume_p:
                    # both same origin type; just keep the first, note duplicate
                    merged.merge_notes.append(f"Duplicate profile from {other.source_files} merged (same email).")
                    merged.source_files = list(dict.fromkeys(merged.source_files + other.source_files))
                    continue
                merged = merge_engine.merge(csv_p, resume_p)
            deduped.append(merged)

        deduped.extend(no_email)
        return deduped
