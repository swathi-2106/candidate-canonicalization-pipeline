import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.merge.deduplicator import Deduplicator
from src.merge.merge_engine import MergeEngine
from src.models import CandidateProfile, ContactInfo, FieldWithProvenance, Provenance, SourceType, Confidence
from src.normalizers.experience import ExperienceNormalizer
from src.pipeline.config import PipelineConfig
from src.pipeline.orchestrator import PipelineOrchestrator


def make_field(value, source=SourceType.CSV):
    return FieldWithProvenance(
        value=value,
        confidence=Confidence.HIGH,
        provenance=Provenance(source_type=source, source_file="test", original_value=value),
    )


def make_profile(name, email="", phone="", company="", linkedin="", origin="CSV"):
    contact = ContactInfo(
        email=make_field(email),
        phone=make_field(phone) if phone else None,
        linkedin=make_field(linkedin) if linkedin else None,
    )
    return CandidateProfile(
        profile_id=name.lower().replace(" ", "-"),
        name=make_field(name),
        email=make_field(email),
        contact=contact,
        skills=[],
        experience=[],
        education=[],
        source_files=[f"{origin.lower()}.dat"],
        current_company=make_field(company) if company else None,
        origin=origin,
    )


def test_experience_normalizer_does_not_double_count_overlaps():
    normalizer = ExperienceNormalizer()
    total = normalizer.total_years(["Jan 2020 - Jan 2022", "Jan 2021 - Jan 2023"])
    assert 2.9 <= total <= 3.1


def test_deduplicator_matches_same_phone_without_email():
    csv_profile = make_profile("Jane Doe", phone="+14155550182", origin="CSV")
    resume_profile = make_profile("Jane Doe", phone="+14155550182", origin="RESUME_PDF")

    deduped = Deduplicator().deduplicate([csv_profile, resume_profile], MergeEngine())

    assert len(deduped) == 1
    assert any("same normalized phone number" in note for note in deduped[0].merge_notes)


def test_dry_run_writes_no_output_artifacts(tmp_path):
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    (csv_dir / "candidates.csv").write_text("Candidate Name,Email Address\nJane Doe,jane@example.com\n")
    output_dir = tmp_path / "out"

    config = PipelineConfig(csv_input_dir=str(csv_dir), output_dir=str(output_dir), dry_run=True)
    report = PipelineOrchestrator(config).run()

    assert report["mode"] == "dry_run"
    assert report["input_summary"]["files_processed"] == 1
    assert not output_dir.exists()


def test_validate_only_writes_report_but_not_profile_exports(tmp_path):
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    (csv_dir / "candidates.csv").write_text("Candidate Name,Email Address\nJane Doe,jane@example.com\n")
    output_dir = tmp_path / "out"

    config = PipelineConfig(csv_input_dir=str(csv_dir), output_dir=str(output_dir), validate_only=True)
    report = PipelineOrchestrator(config).run()

    assert report["mode"] == "validate_only"
    assert (output_dir / "report.json").exists()
    assert not (output_dir / "canonical_profiles.json").exists()


def test_missing_all_input_directories_raise_informative_error(tmp_path):
    missing = tmp_path / "missing"
    config = PipelineConfig(csv_input_dir=str(missing), output_dir=str(tmp_path / "out"), dry_run=True)

    try:
        PipelineOrchestrator(config).run()
        assert False, "expected FileNotFoundError"
    except FileNotFoundError as e:
        assert "all configured input directories are missing" in str(e)
