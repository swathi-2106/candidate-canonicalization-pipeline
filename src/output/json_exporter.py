"""Exports canonical profiles to JSON."""
import json
from typing import List, Dict, Any
from src.models import CandidateProfile


class JSONExporter:
    """Exports CandidateProfile objects (or projected dicts) to a JSON file."""

    def export(self, profiles: List[CandidateProfile], output_path: str, projected: bool = False) -> str:
        if projected:
            data = profiles  # already list of dicts
        else:
            data = [p.to_dict() for p in profiles]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return output_path
