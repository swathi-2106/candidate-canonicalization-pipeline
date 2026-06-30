"""Merges CSV-sourced and Resume-sourced profiles into one canonical profile."""
import logging
from typing import Dict, List, Optional, Any

from src.models import (
    CandidateProfile, FieldWithProvenance, ContactInfo,
    Provenance, SourceType, Confidence,
)

logger = logging.getLogger(__name__)

DEFAULT_STRATEGY = {
    "name": "csv_preferred",
    "email": "csv_preferred",
    "phone": "csv_preferred",
    "skills": "union",
    "current_company": "csv_preferred",
    "years_of_experience": "longest",
    "job_titles": "union",
    "certifications": "union",
    "experience": "union",
    "education": "union",
}


class MergeEngine:
    """Merges a CSV profile and a Resume profile into a single canonical profile.

    priority: "CSV" or "RESUME" - which source wins on unspecified/tied fields.
    merge_strategy: per-field override, e.g. {"name": "resume_preferred", "skills": "union"}.
    Supported per-field strategies: csv_preferred, resume_preferred, longest, union, csv_only, resume_only.
    """

    def __init__(self, priority: str = "RESUME", merge_strategy: Optional[Dict[str, str]] = None):
        self.priority = priority.upper()
        self.strategy = dict(DEFAULT_STRATEGY)
        if merge_strategy:
            self.strategy.update(merge_strategy)

    def merge(self, csv_profile: Optional[CandidateProfile], resume_profile: Optional[CandidateProfile]) -> CandidateProfile:
        """Merge two profiles. Either may be None (e.g. resume-only or CSV-only candidate)."""
        notes: List[str] = []

        if csv_profile is None and resume_profile is None:
            raise ValueError("At least one of csv_profile or resume_profile must be provided")
        if csv_profile is None:
            notes.append("No matching CSV record found; profile built from resume only.")
            resume_profile.merge_notes = notes
            resume_profile.origin = "RESUME_PDF"
            return resume_profile
        if resume_profile is None:
            notes.append("No matching resume found; profile built from CSV only.")
            csv_profile.merge_notes = notes
            csv_profile.origin = "CSV"
            return csv_profile

        name = self._merge_field(csv_profile.name, resume_profile.name, self.strategy.get("name", "csv_preferred"), notes, "name")
        email = self._merge_field(csv_profile.email, resume_profile.email, self.strategy.get("email", "csv_preferred"), notes, "email")

        contact = self._merge_contact(csv_profile.contact, resume_profile.contact, notes)
        skills = self._merge_list_field(csv_profile.skills, resume_profile.skills, self.strategy.get("skills", "union"), notes, "skills")
        job_titles = self._merge_list_field(csv_profile.job_titles, resume_profile.job_titles, self.strategy.get("job_titles", "union"), notes, "job_titles")
        certifications = self._merge_list_field(csv_profile.certifications, resume_profile.certifications, self.strategy.get("certifications", "union"), notes, "certifications")

        experience = resume_profile.experience or csv_profile.experience
        if resume_profile.experience and csv_profile.experience:
            notes.append("Experience entries taken from resume (richer source); CSV experience discarded.")
        education = resume_profile.education or csv_profile.education

        current_company = self._merge_field(
            csv_profile.current_company, resume_profile.current_company,
            self.strategy.get("current_company", "csv_preferred"), notes, "current_company",
        )
        years_of_experience = self._merge_field(
            csv_profile.years_of_experience, resume_profile.years_of_experience,
            self.strategy.get("years_of_experience", "longest"), notes, "years_of_experience",
        )

        merged_profile = CandidateProfile(
            profile_id=csv_profile.profile_id,
            name=name,
            email=email,
            contact=contact,
            skills=skills,
            experience=experience,
            education=education,
            source_files=list(dict.fromkeys(csv_profile.source_files + resume_profile.source_files)),
            total_confidence=0.0,
            merge_notes=notes,
            current_company=current_company,
            years_of_experience=years_of_experience,
            job_titles=job_titles,
            certifications=certifications,
            origin="MERGED",
        )
        return merged_profile

    def _merge_field(self, csv_field: Optional[FieldWithProvenance], resume_field: Optional[FieldWithProvenance],
                      strategy: str, notes: List[str], field_name: str) -> Optional[FieldWithProvenance]:
        if strategy == "csv_only":
            return csv_field
        if strategy == "resume_only":
            return resume_field
        if not csv_field or csv_field.value in (None, ""):
            return resume_field
        if not resume_field or resume_field.value in (None, ""):
            return csv_field

        if csv_field.value == resume_field.value:
            # Agreement across sources boosts confidence
            merged_conf = Confidence.HIGH
            if csv_field.confidence != merged_conf or resume_field.confidence != merged_conf:
                notes.append(f"'{field_name}' agreed across CSV and resume; confidence boosted to HIGH.")
            prov = Provenance(source_type=SourceType.MERGED, source_file="merged",
                               original_value=[csv_field.value, resume_field.value],
                               transformation="agreement_merge")
            return FieldWithProvenance(value=csv_field.value, confidence=merged_conf, provenance=prov)

        winner, loser, winner_label = self._resolve_conflict(csv_field, resume_field, strategy)
        notes.append(f"Conflict on '{field_name}': CSV='{csv_field.value}' vs Resume='{resume_field.value}' -> chose {winner_label} value.")
        prov = Provenance(source_type=SourceType.MERGED, source_file="merged",
                           original_value=[csv_field.value, resume_field.value],
                           transformation=f"conflict_resolution:{strategy}")
        # Conflict slightly lowers confidence relative to the winning field's own confidence
        conf = Confidence.MEDIUM if winner.confidence == Confidence.HIGH else winner.confidence
        return FieldWithProvenance(value=winner.value, confidence=conf, provenance=prov)

    def _resolve_conflict(self, csv_field: FieldWithProvenance, resume_field: FieldWithProvenance, strategy: str):
        if strategy == "resume_preferred":
            return resume_field, csv_field, "resume"
        if strategy == "longest":
            if isinstance(csv_field.value, (int, float)) and isinstance(resume_field.value, (int, float)):
                return (csv_field, resume_field, "csv") if csv_field.value >= resume_field.value else (resume_field, csv_field, "resume")
            csv_len = len(str(csv_field.value))
            res_len = len(str(resume_field.value))
            return (csv_field, resume_field, "csv") if csv_len >= res_len else (resume_field, csv_field, "resume")
        # default csv_preferred
        return csv_field, resume_field, "csv"

    def _merge_contact(self, csv_contact: Optional[ContactInfo], resume_contact: Optional[ContactInfo], notes: List[str]) -> ContactInfo:
        if not csv_contact:
            return resume_contact or ContactInfo()
        if not resume_contact:
            return csv_contact

        return ContactInfo(
            email=self._merge_field(csv_contact.email, resume_contact.email, self.strategy.get("email", "csv_preferred"), notes, "contact.email"),
            phone=self._merge_field(csv_contact.phone, resume_contact.phone, self.strategy.get("phone", "csv_preferred"), notes, "contact.phone"),
            linkedin=self._merge_field(csv_contact.linkedin, resume_contact.linkedin, "resume_preferred", notes, "contact.linkedin"),
            address=self._merge_field(csv_contact.address, resume_contact.address, "csv_preferred", notes, "contact.address"),
        )

    def _merge_list_field(self, csv_list: List[FieldWithProvenance], resume_list: List[FieldWithProvenance],
                           strategy: str, notes: List[str], field_name: str) -> List[FieldWithProvenance]:
        if strategy == "csv_only":
            return csv_list
        if strategy == "resume_only":
            return resume_list
        # union (default): dedupe by lowercase value, prefer higher confidence on collision
        merged: Dict[str, FieldWithProvenance] = {}
        for f in (csv_list or []) + (resume_list or []):
            key = str(f.value).strip().lower()
            if not key:
                continue
            if key not in merged or f.confidence.numeric > merged[key].confidence.numeric:
                merged[key] = f
        if csv_list and resume_list:
            notes.append(f"'{field_name}' unioned from CSV ({len(csv_list)}) and resume ({len(resume_list)}) -> {len(merged)} unique.")
        return list(merged.values())

    def _detect_duplicates(self, profiles: List[CandidateProfile]) -> List[CandidateProfile]:
        """Detect candidate profiles referring to the same person (same normalized
        email) and merge them together, returning a deduplicated list."""
        from src.merge.deduplicator import Deduplicator
        return Deduplicator().deduplicate(profiles, self)
