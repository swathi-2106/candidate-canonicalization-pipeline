import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
from src.models import CandidateProfile, FieldWithProvenance, Provenance, SourceType, Confidence
from src.projection.projection_engine import ProjectionEngine


def make_field(value, confidence=Confidence.HIGH):
    return FieldWithProvenance(
        value=value, confidence=confidence,
        provenance=Provenance(source_type=SourceType.CSV, source_file="test", original_value=value),
    )


def sample_profile():
    return CandidateProfile(
        profile_id=str(uuid.uuid4()),
        name=make_field("Jane Doe"),
        email=make_field("jane@example.com"),
        skills=[make_field("Python"), make_field("Django")],
        experience=[],
        education=[],
        source_files=["test.csv"],
        current_company=make_field("Google"),
        years_of_experience=make_field(7),
        job_titles=[],
        certifications=[],
        total_confidence=0.9,
    )


def test_default_projection():
    engine = ProjectionEngine()
    result = engine.project(sample_profile())
    assert result["name"] == "Jane Doe"
    assert result["email"] == "jane@example.com"
    assert result["skills"] == ["Python", "Django"]
    assert result["current_company"] == "Google"


def test_custom_projection_renaming():
    spec = {
        "fields": [
            {"source": "name.value", "target": "full_name"},
            {"source": "email.value", "target": "contact_email"},
        ],
        "include_confidence": False,
        "missing_value_policy": "null",
    }
    engine = ProjectionEngine(spec=spec)
    result = engine.project(sample_profile())
    assert result == {"full_name": "Jane Doe", "contact_email": "jane@example.com"}


def test_projection_missing_value_policy_omit():
    spec = {
        "fields": [
            {"source": "current_company.value", "target": "company"},
            {"source": "contact.linkedin.value", "target": "linkedin"},
        ],
        "missing_value_policy": "omit",
        "include_confidence": False,
    }
    engine = ProjectionEngine(spec=spec)
    result = engine.project(sample_profile())
    assert "company" in result
    assert "linkedin" not in result


def test_projection_missing_value_policy_error():
    spec = {
        "fields": [{"source": "contact.linkedin.value", "target": "linkedin"}],
        "missing_value_policy": "error",
    }
    engine = ProjectionEngine(spec=spec)
    try:
        engine.project(sample_profile())
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_projection_include_confidence():
    spec = {
        "fields": [{"source": "name.value", "target": "name"}],
        "include_confidence": True,
        "missing_value_policy": "null",
    }
    engine = ProjectionEngine(spec=spec)
    result = engine.project(sample_profile())
    assert result["name"] == "Jane Doe"
    assert result["name_confidence"] == "HIGH"
