"""Exports canonical profiles to a flat CSV file."""
import csv
from typing import List, Dict, Any
import pandas as pd

from src.models import CandidateProfile
from src.projection.projection_engine import ProjectionEngine


class CSVExporter:
    """Flattens and exports CandidateProfile objects to CSV."""

    def export(self, profiles: List[CandidateProfile], output_path: str, projection: ProjectionEngine = None) -> str:
        projection = projection or ProjectionEngine()
        rows = projection.project_batch(profiles)
        # flatten any list values to semicolon-joined strings for CSV friendliness
        flat_rows = []
        for row in rows:
            flat = {}
            for k, v in row.items():
                if isinstance(v, list):
                    flat[k] = "; ".join(str(x) for x in v)
                elif isinstance(v, dict):
                    flat[k] = str(v)
                else:
                    flat[k] = v
            flat_rows.append(flat)
        df = pd.DataFrame(flat_rows)
        df.to_csv(output_path, index=False)
        return output_path
