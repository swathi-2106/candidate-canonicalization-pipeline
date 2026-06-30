"""Standalone conflict-resolution utilities.

The primary conflict-resolution logic lives in MergeEngine._resolve_conflict
(kept together with merge logic for cohesion). This module exposes small,
independently-testable resolver functions used/extendable beyond MergeEngine.
"""
from typing import Any, Tuple
from src.models import FieldWithProvenance


def resolve_by_confidence(field1: FieldWithProvenance, field2: FieldWithProvenance) -> FieldWithProvenance:
    """Pick whichever field has the higher confidence score; ties favor field1."""
    return field1 if field1.confidence.numeric >= field2.confidence.numeric else field2


def resolve_by_recency(field1: FieldWithProvenance, field2: FieldWithProvenance) -> FieldWithProvenance:
    """Pick whichever field has the more recent provenance timestamp."""
    t1 = field1.provenance.timestamp if field1.provenance else None
    t2 = field2.provenance.timestamp if field2.provenance else None
    if t1 and t2:
        return field1 if t1 >= t2 else field2
    return field1


def resolve_by_completeness(field1: FieldWithProvenance, field2: FieldWithProvenance) -> FieldWithProvenance:
    """Pick whichever field has a non-empty, longer value."""
    v1, v2 = str(field1.value or ""), str(field2.value or "")
    return field1 if len(v1) >= len(v2) else field2
