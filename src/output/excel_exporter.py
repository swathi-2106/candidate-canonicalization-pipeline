"""Exports canonical profiles to a multi-sheet Excel workbook."""
from typing import List, Dict, Any
import pandas as pd

from src.models import CandidateProfile
from src.projection.projection_engine import ProjectionEngine


class ExcelExporter:
    """Exports profiles to an .xlsx workbook with Profiles / Skills / Experience /
    Education / Errors sheets."""

    def export(self, profiles: List[CandidateProfile], output_path: str,
               projection: ProjectionEngine = None, validation_results: List[Dict] = None) -> str:
        projection = projection or ProjectionEngine()
        summary_rows = projection.project_batch(profiles)
        summary_df = pd.DataFrame([
            {k: ("; ".join(str(x) for x in v) if isinstance(v, list) else v) for k, v in row.items()}
            for row in summary_rows
        ])

        skills_rows = []
        for p in profiles:
            for s in p.skills:
                skills_rows.append({"profile_id": p.profile_id, "name": p.name.value, "skill": s.value, "confidence": s.confidence.value})

        experience_rows = []
        for p in profiles:
            for e in p.experience:
                experience_rows.append({
                    "profile_id": p.profile_id, "name": p.name.value,
                    "company": e.company.value if e.company else None,
                    "title": e.title.value if e.title else None,
                    "start_date": e.start_date.value if e.start_date else None,
                    "end_date": e.end_date.value if e.end_date else None,
                    "current": e.current,
                })

        education_rows = []
        for p in profiles:
            for ed in p.education:
                education_rows.append({
                    "profile_id": p.profile_id, "name": p.name.value,
                    "institution": ed.institution.value if ed.institution else None,
                    "degree": ed.degree.value if ed.degree else None,
                    "graduation_date": ed.graduation_date.value if ed.graduation_date else None,
                })

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            (summary_df if not summary_df.empty else pd.DataFrame([{"info": "no profiles"}])).to_excel(writer, sheet_name="Profiles", index=False)
            (pd.DataFrame(skills_rows) if skills_rows else pd.DataFrame([{"info": "no skills"}])).to_excel(writer, sheet_name="Skills", index=False)
            (pd.DataFrame(experience_rows) if experience_rows else pd.DataFrame([{"info": "no experience"}])).to_excel(writer, sheet_name="Experience", index=False)
            (pd.DataFrame(education_rows) if education_rows else pd.DataFrame([{"info": "no education"}])).to_excel(writer, sheet_name="Education", index=False)
            if validation_results:
                pd.DataFrame(validation_results).to_excel(writer, sheet_name="Validation", index=False)

        return output_path
