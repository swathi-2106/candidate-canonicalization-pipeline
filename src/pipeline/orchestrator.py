"""Coordinates the full canonicalization pipeline: parse -> normalize ->
merge -> provenance/confidence -> validate -> project -> output -> report."""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from src.pipeline.config import PipelineConfig
from src.parsers.csv_parser import CSVParser
from src.parsers.resume_parser import ResumeParser
from src.merge.merge_engine import MergeEngine
from src.merge.deduplicator import Deduplicator
from src.services.confidence_service import ConfidenceService
from src.services.validator import Validator
from src.projection.projection_engine import ProjectionEngine
from src.output.json_exporter import JSONExporter
from src.output.csv_exporter import CSVExporter
from src.output.excel_exporter import ExcelExporter
from src.output.report_generator import ReportGenerator
from src.utils.helpers import list_files, ensure_dir
from src.models import CandidateProfile

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """High-level entry point that runs the entire pipeline end-to-end."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.csv_parser = CSVParser(column_mapping=config.column_mapping)
        self.resume_parser = ResumeParser()
        self.merge_engine = MergeEngine(priority=config.merge_priority, merge_strategy=config.merge_strategy)
        self.deduplicator = Deduplicator()
        self.confidence_service = ConfidenceService()
        self.validator = Validator(schema_path=config.schema_file)
        self.projection_engine = ProjectionEngine(spec=config.projection_spec)

        self.errors: List[str] = []
        self.file_counts = {"csv_files": 0, "resume_files": 0}

    def run(self) -> dict:
        """Run the full pipeline. Returns the generated report dict."""
        started_at = datetime.now()
        self._validate_input_directories()
        if not self.config.dry_run:
            ensure_dir(self.config.output_dir)

        csv_profiles = self._parse_csv_files()
        resume_profiles = self._parse_resume_files()

        all_profiles = csv_profiles + resume_profiles
        logger.info("Parsed %d CSV profile(s) and %d resume profile(s)", len(csv_profiles), len(resume_profiles))

        if self.config.validate_only:
            for profile in all_profiles:
                profile.total_confidence = self.confidence_service.calculate_overall(profile)
            validation_results = self.validator.validate_batch(all_profiles)
            report = self._build_report(started_at, datetime.now(), all_profiles, validation_results,
                                        len(csv_profiles), len(resume_profiles), merge_count=0)
            if not self.config.dry_run:
                self._write_validation_report(report)
            return report

        merged_profiles = self.deduplicator.deduplicate(all_profiles, self.merge_engine)
        logger.info("After dedupe/merge: %d canonical profile(s)", len(merged_profiles))
        merge_count = max(0, len(all_profiles) - len(merged_profiles))

        for profile in merged_profiles:
            profile.total_confidence = self.confidence_service.calculate_overall(profile)

        validation_results = self.validator.validate_batch(merged_profiles)
        invalid_count = sum(1 for r in validation_results if not r.is_valid)
        if invalid_count:
            logger.warning("%d profile(s) failed validation", invalid_count)

        if self.config.dry_run:
            self.projection_engine.project_batch(merged_profiles)
        else:
            self._write_outputs(merged_profiles, validation_results)

        finished_at = datetime.now()
        report = self._build_report(started_at, finished_at, merged_profiles, validation_results,
                                    len(csv_profiles), len(resume_profiles), merge_count=merge_count)
        if not self.config.dry_run:
            self._write_validation_report(report)
        logger.info("Pipeline run complete in %.2fs", report["duration_seconds"])
        return report

    def _build_report(self, started_at, finished_at, profiles, validation_results,
                      csv_count: int, resume_count: int, merge_count: int) -> dict:
        report_gen = ReportGenerator()
        report = report_gen.generate(
            profiles=profiles,
            validation_results=validation_results,
            errors=self.errors,
            started_at=started_at,
            finished_at=finished_at,
            csv_count=csv_count,
            resume_count=resume_count,
        )
        report["input_summary"]["csv_files_processed"] = self.file_counts["csv_files"]
        report["input_summary"]["resume_files_processed"] = self.file_counts["resume_files"]
        report["input_summary"]["files_processed"] = self.file_counts["csv_files"] + self.file_counts["resume_files"]
        report["output_summary"]["merge_count"] = merge_count
        report["mode"] = "dry_run" if self.config.dry_run else ("validate_only" if self.config.validate_only else "run")
        return report

    def _write_validation_report(self, report: dict) -> None:
        report_gen = ReportGenerator()
        report_gen.to_json(report, str(Path(self.config.output_dir) / "report.json"))
        report_gen.to_text(report, str(Path(self.config.output_dir) / "report.txt"))

    def _validate_input_directories(self) -> None:
        configured: List[Tuple[str, Optional[str]]] = [
            ("CSV input directory", self.config.csv_input_dir),
            ("Resume input directory", self.config.resume_input_dir),
        ]
        supplied = [(label, path) for label, path in configured if path]
        missing = [(label, path) for label, path in supplied if not Path(path).exists()]
        for label, path in missing:
            msg = f"{label} does not exist: {path}"
            logger.warning(msg)
            self.errors.append(msg)
        if supplied and len(missing) == len(supplied):
            raise FileNotFoundError("all configured input directories are missing: " + ", ".join(path for _, path in missing))

    def _parse_csv_files(self) -> List[CandidateProfile]:
        if not self.config.csv_input_dir:
            return []
        files = list_files(self.config.csv_input_dir, [".csv"])
        self.file_counts["csv_files"] = len(files)
        profiles: List[CandidateProfile] = []
        if self.config.parallel and len(files) > 1:
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = {executor.submit(self._safe_parse_csv, f): f for f in files}
                for future in as_completed(futures):
                    profiles.extend(future.result())
        else:
            for f in files:
                profiles.extend(self._safe_parse_csv(f))
        return profiles

    def _safe_parse_csv(self, file_path: str) -> List[CandidateProfile]:
        try:
            parser = CSVParser(column_mapping=self.config.column_mapping)
            result = parser.parse(file_path)
            self.errors.extend(parser.errors)
            return result
        except Exception as e:
            msg = f"Failed to parse CSV {file_path}: {e}"
            logger.error(msg)
            self.errors.append(msg)
            return []

    def _parse_resume_files(self) -> List[CandidateProfile]:
        if not self.config.resume_input_dir:
            return []
        files = list_files(self.config.resume_input_dir, [".pdf"])
        self.file_counts["resume_files"] = len(files)
        profiles: List[CandidateProfile] = []
        if self.config.parallel and len(files) > 1:
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                futures = {executor.submit(self._safe_parse_resume, f): f for f in files}
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        profiles.append(result)
        else:
            for f in files:
                result = self._safe_parse_resume(f)
                if result:
                    profiles.append(result)
        return profiles

    def _safe_parse_resume(self, file_path: str) -> Optional[CandidateProfile]:
        try:
            parser = ResumeParser(use_ner=self.config.use_ner, ner_model=self.config.ner_model)
            result = parser.parse(file_path)
            self.errors.extend(parser.errors)
            return result
        except Exception as e:
            msg = f"Failed to parse resume {file_path}: {e}"
            logger.error(msg)
            self.errors.append(msg)
            return None

    def _write_outputs(self, profiles: List[CandidateProfile], validation_results) -> None:
        out_dir = Path(self.config.output_dir)
        formats = [f.lower() for f in self.config.output_formats]

        if "json" in formats:
            JSONExporter().export(profiles, str(out_dir / "canonical_profiles.json"))
            projected = self.projection_engine.project_batch(profiles)
            JSONExporter().export(projected, str(out_dir / "projected_profiles.json"), projected=True)
        if "csv" in formats:
            CSVExporter().export(profiles, str(out_dir / "canonical_profiles.csv"), self.projection_engine)
        if "excel" in formats or "xlsx" in formats:
            ExcelExporter().export(
                profiles, str(out_dir / "canonical_profiles.xlsx"), self.projection_engine,
                validation_results=[r.to_dict() for r in validation_results],
            )
