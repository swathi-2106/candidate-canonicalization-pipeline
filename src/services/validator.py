"""Validates canonical candidate profiles against a JSON schema and business rules."""
import json
import logging
from typing import List, Tuple, Optional, Dict, Any

from src.models import CandidateProfile

logger = logging.getLogger(__name__)


class ValidationResult:
    def __init__(self, profile_id: str):
        self.profile_id = profile_id
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def add_error(self, msg: str):
        self.is_valid = False
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class Validator:
    """Validates CandidateProfile objects: required fields, types, and
    optionally a JSON Schema for the serialized output."""

    REQUIRED_FIELDS = ["profile_id", "name", "email"]

    def __init__(self, schema_path: Optional[str] = None):
        self.schema = self._load_schema(schema_path) if schema_path else None

    def _load_schema(self, schema_path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not load schema %s: %s", schema_path, e)
            return None

    def validate(self, profile: CandidateProfile) -> ValidationResult:
        result = ValidationResult(profile.profile_id)

        if not profile.profile_id:
            result.add_error("Missing profile_id")
        if not profile.name or not profile.name.value:
            result.add_error("Missing required field: name")
        if not profile.email or not profile.email.value:
            result.add_error("Missing required field: email")
        elif "@" not in str(profile.email.value):
            result.add_error(f"Invalid email format: {profile.email.value}")

        if profile.contact and profile.contact.phone and profile.contact.phone.value:
            phone_val = str(profile.contact.phone.value)
            if len(phone_val.replace("+", "").strip()) < 7:
                result.add_warning(f"Phone number looks too short: {phone_val}")

        if not profile.skills:
            result.add_warning("No skills found for candidate")
        if not profile.experience:
            result.add_warning("No work experience found for candidate")

        if profile.years_of_experience and profile.years_of_experience.value is not None:
            try:
                yoe = float(profile.years_of_experience.value)
                if yoe < 0 or yoe > 60:
                    result.add_warning(f"years_of_experience looks implausible: {yoe}")
            except (TypeError, ValueError):
                result.add_warning("years_of_experience is not numeric")

        if self.schema:
            self._validate_against_schema(profile, result)

        return result

    def _validate_against_schema(self, profile: CandidateProfile, result: ValidationResult) -> None:
        try:
            import jsonschema
            jsonschema.validate(instance=profile.to_dict(), schema=self.schema)
        except ImportError:
            required = self.schema.get("required", [])
            data = profile.to_dict()
            for field_name in required:
                if field_name not in data or data[field_name] in (None, ""):
                    result.add_error(f"Schema violation: missing required field '{field_name}'")
        except Exception as e:
            result.add_error(f"Schema validation failed: {e}")

    def validate_batch(self, profiles: List[CandidateProfile]) -> List[ValidationResult]:
        return [self.validate(p) for p in profiles]
