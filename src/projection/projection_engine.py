"""Configurable field selection/renaming/projection without touching business logic."""
import logging
from typing import Any, Dict, List, Optional

from src.models import CandidateProfile

logger = logging.getLogger(__name__)

MissingPolicy = str  # "null" | "omit" | "error"


class ProjectionEngine:
    """Projects a CandidateProfile (or its dict form) into a custom flat/nested
    shape based on a runtime-configurable spec, without changing pipeline logic.

    Spec format (YAML/JSON-friendly dict):
    {
      "fields": [
        {"source": "name.value", "target": "full_name"},
        {"source": "email.value", "target": "email"},
        {"source": "skills", "target": "skills", "extract": "value", "list": true},
        {"source": "current_company.value", "target": "company", "normalize": false},
      ],
      "include_provenance": false,
      "include_confidence": true,
      "missing_value_policy": "null"   # null | omit | error
    }
    """

    def __init__(self, spec: Optional[Dict[str, Any]] = None):
        self.spec = spec or self._default_spec()

    @staticmethod
    def _default_spec() -> Dict[str, Any]:
        return {
            "fields": [
                {"source": "profile_id", "target": "id"},
                {"source": "name.value", "target": "name"},
                {"source": "email.value", "target": "email"},
                {"source": "current_company.value", "target": "current_company"},
                {"source": "years_of_experience.value", "target": "years_of_experience"},
                {"source": "skills", "target": "skills", "extract": "value", "list": True},
                {"source": "total_confidence", "target": "confidence_score"},
            ],
            "include_provenance": False,
            "include_confidence": True,
            "missing_value_policy": "null",
        }

    def project(self, profile: CandidateProfile) -> Dict[str, Any]:
        """Apply the projection spec to a single profile, returning a plain dict."""
        data = profile.to_dict()
        output: Dict[str, Any] = {}
        policy: MissingPolicy = self.spec.get("missing_value_policy", "null")

        for field_spec in self.spec.get("fields", []):
            source_path = field_spec["source"]
            target = field_spec.get("target", source_path)
            value = self._extract(data, source_path)

            if field_spec.get("list") and isinstance(value, list):
                extract_key = field_spec.get("extract")
                if extract_key:
                    value = [item.get(extract_key) for item in value if isinstance(item, dict)]

            if value is None or value == []:
                if policy == "omit":
                    continue
                if policy == "error":
                    raise ValueError(f"Required projection field '{source_path}' is missing for profile {profile.profile_id}")
                value = None

            output[target] = value

            if self.spec.get("include_confidence") and self._has_confidence(data, source_path):
                conf_value = self._extract(data, self._confidence_path(source_path))
                if conf_value is not None:
                    output[f"{target}_confidence"] = conf_value

            if self.spec.get("include_provenance") and self._has_provenance(data, source_path):
                prov_value = self._extract(data, self._provenance_path(source_path))
                if prov_value is not None:
                    output[f"{target}_provenance"] = prov_value

        return output

    def project_batch(self, profiles: List[CandidateProfile]) -> List[Dict[str, Any]]:
        return [self.project(p) for p in profiles]

    @staticmethod
    def _extract(data: Dict[str, Any], path: str) -> Any:
        parts = path.split(".")
        current: Any = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    @staticmethod
    def _confidence_path(source_path: str) -> str:
        if source_path.endswith(".value"):
            return source_path[: -len(".value")] + ".confidence"
        return source_path + ".confidence"

    @staticmethod
    def _provenance_path(source_path: str) -> str:
        if source_path.endswith(".value"):
            return source_path[: -len(".value")] + ".provenance"
        return source_path + ".provenance"

    def _has_confidence(self, data: Dict[str, Any], source_path: str) -> bool:
        return self._extract(data, self._confidence_path(source_path)) is not None

    def _has_provenance(self, data: Dict[str, Any], source_path: str) -> bool:
        return self._extract(data, self._provenance_path(source_path)) is not None
