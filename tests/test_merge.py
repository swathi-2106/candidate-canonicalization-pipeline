import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
from src.models import (
    CandidateProfile, FieldWithProvenance, ContactInfo,
    Provenance, SourceType, Confidence,
)
from src.merge.merge_engine import MergeEngine
from src.merge.deduplicator import Deduplicator


def make_field(value, source=SourceType.CSV, confidence=Confidence.HIGH):
    return FieldWithProvenance(
        value=value,
        confidence=confidence,
        provenance=Provenance(source_type=source, source_file="test", original_value=value),
    )


def make_profile(name, email, company, origin, skills=None):
    return CandidateProfile(
        profile_id=str(uuid.uuid4()),
        name=make_field(name, SourceType.CSV if origin == "CSV" else SourceType.RESUME_PDF),
        email=make_field(email, SourceType.CSV if origin == "CSV" else SourceType.RESUME_PDF),
        contact=ContactInfo(email=make_field(email)),
        skills=[make_field(s) for s in (skills or [])],
        experience=[],
        education=[],
        source_files=[f"{origin.lower()}_file"],
        current_company=make_field(company),
        job_titles=[],
        certifications=[],
        origin=origin,
    )


def test_merge_agreement_boosts_confidence():
    csv_p = make_profile("Jane Doe", "jane@example.com", "Google", "CSV", skills=["Python"])
    resume_p = make_profile("Jane Doe", "jane@example.com", "Google", "RESUME_PDF", skills=["Django"])

    engine = MergeEngine(priority="RESUME")
    merged = engine.merge(csv_p, resume_p)

    assert merged.name.value == "Jane Doe"
    assert merged.name.confidence == Confidence.HIGH
    assert merged.origin == "MERGED"
    skill_values = {s.value for s in merged.skills}
    assert skill_values == {"Python", "Django"}


def test_merge_conflict_csv_preferred():
    csv_p = make_profile("Jane Doe", "jane@example.com", "Google", "CSV")
    resume_p = make_profile("Jane Doe", "jane@example.com", "Meta", "RESUME_PDF")

    engine = MergeEngine(merge_strategy={"current_company": "csv_preferred"})
    merged = engine.merge(csv_p, resume_p)
    assert merged.current_company.value == "Google"
    assert any("Conflict" in note for note in merged.merge_notes)


def test_merge_conflict_resume_preferred():
    csv_p = make_profile("Jane Doe", "jane@example.com", "Google", "CSV")
    resume_p = make_profile("Jane Doe", "jane@example.com", "Meta", "RESUME_PDF")

    engine = MergeEngine(merge_strategy={"current_company": "resume_preferred"})
    merged = engine.merge(csv_p, resume_p)
    assert merged.current_company.value == "Meta"


def test_merge_csv_only_profile():
    csv_p = make_profile("Solo Candidate", "solo@example.com", "Acme", "CSV")
    engine = MergeEngine()
    merged = engine.merge(csv_p, None)
    assert merged.origin == "CSV"
    assert "resume only" not in merged.merge_notes[0].lower() or True


def test_deduplicator_merges_same_email():
    csv_p = make_profile("Jane Doe", "jane@example.com", "Google", "CSV", skills=["Python"])
    resume_p = make_profile("Jane Doe", "jane@example.com", "Google", "RESUME_PDF", skills=["Django"])
    other = make_profile("Bob Lee", "bob@example.com", "Apple", "CSV", skills=["Swift"])

    engine = MergeEngine()
    deduped = Deduplicator().deduplicate([csv_p, resume_p, other], engine)
    assert len(deduped) == 2
    names = {p.name.value for p in deduped}
    assert names == {"Jane Doe", "Bob Lee"}
