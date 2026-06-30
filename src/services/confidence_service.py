"""Service for calculating field-level and profile-level confidence scores."""
from typing import Any
from src.models import Confidence, SourceType, CandidateProfile, FieldWithProvenance

SOURCE_BASE_WEIGHT = {
    SourceType.CSV: 0.9,
    SourceType.RESUME_PDF: 0.7,
    SourceType.MERGED: 0.85,
    SourceType.DERIVED: 0.5,
    SourceType.UNKNOWN: 0.0,
}


class ConfidenceService:
    """Calculates confidence scores from source type, validation, and agreement."""

    def calculate(self, value: Any, source_type: SourceType, validation_result: bool = True,
                   multiple_sources: bool = False) -> Confidence:
        if value in (None, "", []):
            return Confidence.UNKNOWN

        score = SOURCE_BASE_WEIGHT.get(source_type, 0.5)
        if not validation_result:
            score -= 0.35
        if multiple_sources:
            score += 0.15
        score = max(0.0, min(1.0, score))
        return Confidence.from_numeric(score)

    def calculate_overall(self, profile: CandidateProfile) -> float:
        """Average the numeric confidence of every populated field in the profile."""
        scores = []

        def add(field):
            if field and field.value not in (None, "", []):
                scores.append(field.confidence.numeric)

        add(profile.name)
        add(profile.email)
        if profile.contact:
            add(profile.contact.email)
            add(profile.contact.phone)
            add(profile.contact.linkedin)
            add(profile.contact.address)
        for s in profile.skills:
            add(s)
        for e in profile.experience:
            add(e.company)
            add(e.title)
            add(e.start_date)
            add(e.end_date)
        for ed in profile.education:
            add(ed.institution)
            add(ed.degree)
        add(profile.current_company)
        add(profile.years_of_experience)
        for jt in profile.job_titles:
            add(jt)
        for c in profile.certifications:
            add(c)

        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 4)
