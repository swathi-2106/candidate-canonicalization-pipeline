"""Service for creating and tracking provenance records across a pipeline run."""
from typing import Any, List, Optional
from src.models import Provenance, SourceType, FieldWithProvenance


class ProvenanceService:
    """Creates provenance records and maintains a global audit trail."""

    def __init__(self):
        self.audit_trail: List[Provenance] = []

    def create_provenance(self, source: SourceType, source_file: str, original_value: Any,
                           transformation: Optional[str] = None, transformed_value: Any = None) -> Provenance:
        prov = Provenance(
            source_type=source,
            source_file=source_file,
            original_value=original_value,
            transformation=transformation,
            transformed_value=transformed_value,
        )
        self.audit_trail.append(prov)
        return prov

    def track_field(self, field: FieldWithProvenance, provenance: Provenance) -> None:
        """Attach a provenance record to a field in-place."""
        field.provenance = provenance
        self.audit_trail.append(provenance)

    def get_provenance_chain(self, field: FieldWithProvenance) -> List[Provenance]:
        """Return the provenance chain for a field (currently a single hop;
        list form supports future multi-stage transformation chains)."""
        return [field.provenance] if field.provenance else []

    def export_audit_trail(self) -> List[dict]:
        return [p.to_dict() for p in self.audit_trail]
