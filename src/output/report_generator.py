"""Generates a human-readable processing report (metrics, statistics, errors)."""
import json
from datetime import datetime
from typing import List, Dict, Any

from src.models import CandidateProfile
from src.services.validator import ValidationResult


class ReportGenerator:
    """Builds a summary report of a pipeline run: counts, confidence stats,
    validation outcomes, and errors encountered."""

    def generate(self, profiles: List[CandidateProfile], validation_results: List[ValidationResult],
                 errors: List[str], started_at: datetime, finished_at: datetime,
                 csv_count: int = 0, resume_count: int = 0) -> Dict[str, Any]:
        total = len(profiles)
        valid = sum(1 for r in validation_results if r.is_valid)
        invalid = total - valid
        confidences = [p.total_confidence for p in profiles] if profiles else []
        avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

        origin_counts = {"CSV": 0, "RESUME_PDF": 0, "MERGED": 0}
        for p in profiles:
            origin_counts[p.origin] = origin_counts.get(p.origin, 0) + 1

        warnings_total = sum(len(r.warnings) for r in validation_results)

        report = {
            "run_started_at": started_at.isoformat(),
            "run_finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
            "input_summary": {
                "csv_records_parsed": csv_count,
                "resumes_parsed": resume_count,
            },
            "output_summary": {
                "total_profiles": total,
                "valid_profiles": valid,
                "invalid_profiles": invalid,
                "profiles_by_origin": origin_counts,
                "average_confidence": avg_confidence,
            },
            "validation": {
                "total_warnings": warnings_total,
                "details": [r.to_dict() for r in validation_results],
            },
            "errors": errors,
            "error_count": len(errors),
        }
        return report

    def to_json(self, report: Dict[str, Any], output_path: str) -> str:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        return output_path

    def to_text(self, report: Dict[str, Any], output_path: str) -> str:
        lines = [
            "=" * 60,
            "CANDIDATE CANONICALIZATION PIPELINE - PROCESSING REPORT",
            "=" * 60,
            f"Run started:  {report['run_started_at']}",
            f"Run finished: {report['run_finished_at']}",
            f"Duration:     {report['duration_seconds']}s",
            "",
            "-- Input --",
            f"CSV records parsed: {report['input_summary']['csv_records_parsed']}",
            f"Resumes parsed:     {report['input_summary']['resumes_parsed']}",
            "",
            "-- Output --",
            f"Total profiles:    {report['output_summary']['total_profiles']}",
            f"Valid profiles:    {report['output_summary']['valid_profiles']}",
            f"Invalid profiles:  {report['output_summary']['invalid_profiles']}",
            f"By origin:         {report['output_summary']['profiles_by_origin']}",
            f"Average confidence:{report['output_summary']['average_confidence']}",
            "",
            "-- Validation --",
            f"Total warnings: {report['validation']['total_warnings']}",
            "",
            "-- Errors --",
            f"Error count: {report['error_count']}",
        ]
        for e in report["errors"]:
            lines.append(f"  - {e}")
        lines.append("=" * 60)
        text = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        return output_path
