"""Provenance tracking models."""
from dataclasses import dataclass, field, asdict
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    CSV = "CSV"
    RESUME_PDF = "RESUME_PDF"
    MERGED = "MERGED"
    DERIVED = "DERIVED"
    UNKNOWN = "UNKNOWN"


@dataclass
class Provenance:
    """Tracks where a piece of data came from and any transformation applied to it."""
    source_type: SourceType
    source_file: str
    original_value: Any
    transformation: Optional[str] = None
    transformed_value: Optional[Any] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source_type"] = self.source_type.value if isinstance(self.source_type, SourceType) else self.source_type
        d["timestamp"] = self.timestamp.isoformat()
        return d
