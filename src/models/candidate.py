"""Canonical candidate profile data models."""
from dataclasses import dataclass, field
from typing import Optional, List, Any
from datetime import datetime

from .provenance import Provenance, SourceType
from .confidence import Confidence


@dataclass
class FieldWithProvenance:
    """A single value plus its confidence and provenance metadata."""
    value: Any
    confidence: Confidence = Confidence.UNKNOWN
    provenance: Optional[Provenance] = None

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "confidence": self.confidence.value if isinstance(self.confidence, Confidence) else self.confidence,
            "provenance": self.provenance.to_dict() if self.provenance else None,
        }

    @classmethod
    def empty(cls, source_file: str = "", source_type: SourceType = SourceType.UNKNOWN) -> "FieldWithProvenance":
        return cls(
            value=None,
            confidence=Confidence.UNKNOWN,
            provenance=Provenance(source_type=source_type, source_file=source_file, original_value=None),
        )


@dataclass
class ContactInfo:
    email: Optional[FieldWithProvenance] = None
    phone: Optional[FieldWithProvenance] = None
    linkedin: Optional[FieldWithProvenance] = None
    address: Optional[FieldWithProvenance] = None

    def to_dict(self) -> dict:
        return {
            "email": self.email.to_dict() if self.email else None,
            "phone": self.phone.to_dict() if self.phone else None,
            "linkedin": self.linkedin.to_dict() if self.linkedin else None,
            "address": self.address.to_dict() if self.address else None,
        }


@dataclass
class Experience:
    company: FieldWithProvenance
    title: FieldWithProvenance
    start_date: Optional[FieldWithProvenance] = None
    end_date: Optional[FieldWithProvenance] = None
    description: Optional[FieldWithProvenance] = None
    current: bool = False

    def to_dict(self) -> dict:
        return {
            "company": self.company.to_dict() if self.company else None,
            "title": self.title.to_dict() if self.title else None,
            "start_date": self.start_date.to_dict() if self.start_date else None,
            "end_date": self.end_date.to_dict() if self.end_date else None,
            "description": self.description.to_dict() if self.description else None,
            "current": self.current,
        }


@dataclass
class Education:
    institution: FieldWithProvenance
    degree: FieldWithProvenance
    field_of_study: Optional[FieldWithProvenance] = None
    graduation_date: Optional[FieldWithProvenance] = None

    def to_dict(self) -> dict:
        return {
            "institution": self.institution.to_dict() if self.institution else None,
            "degree": self.degree.to_dict() if self.degree else None,
            "field_of_study": self.field_of_study.to_dict() if self.field_of_study else None,
            "graduation_date": self.graduation_date.to_dict() if self.graduation_date else None,
        }


@dataclass
class CandidateProfile:
    """Canonical candidate profile - the unified output of the pipeline."""
    profile_id: str
    name: FieldWithProvenance
    email: FieldWithProvenance

    contact: Optional[ContactInfo] = None
    skills: List[FieldWithProvenance] = field(default_factory=list)
    experience: List[Experience] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)

    source_files: List[str] = field(default_factory=list)
    processing_timestamp: datetime = field(default_factory=datetime.now)
    total_confidence: float = 0.0
    merge_notes: List[str] = field(default_factory=list)

    current_company: Optional[FieldWithProvenance] = None
    years_of_experience: Optional[FieldWithProvenance] = None
    job_titles: List[FieldWithProvenance] = field(default_factory=list)
    certifications: List[FieldWithProvenance] = field(default_factory=list)

    # internal: which raw source produced this profile prior to merge ("CSV"/"RESUME_PDF"/"MERGED")
    origin: str = "UNKNOWN"

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "name": self.name.to_dict() if self.name else None,
            "email": self.email.to_dict() if self.email else None,
            "contact": self.contact.to_dict() if self.contact else None,
            "skills": [s.to_dict() for s in self.skills],
            "experience": [e.to_dict() for e in self.experience],
            "education": [e.to_dict() for e in self.education],
            "source_files": self.source_files,
            "processing_timestamp": self.processing_timestamp.isoformat(),
            "total_confidence": round(self.total_confidence, 4),
            "merge_notes": self.merge_notes,
            "current_company": self.current_company.to_dict() if self.current_company else None,
            "years_of_experience": self.years_of_experience.to_dict() if self.years_of_experience else None,
            "job_titles": [j.to_dict() for j in self.job_titles],
            "certifications": [c.to_dict() for c in self.certifications],
            "origin": self.origin,
        }
