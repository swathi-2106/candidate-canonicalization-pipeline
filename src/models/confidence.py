"""Confidence scoring enum and helpers."""
from enum import Enum


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"

    @property
    def numeric(self) -> float:
        """Numeric weight used for aggregate scoring (0.0 - 1.0)."""
        return {
            Confidence.HIGH: 1.0,
            Confidence.MEDIUM: 0.65,
            Confidence.LOW: 0.35,
            Confidence.UNKNOWN: 0.0,
        }[self]

    @staticmethod
    def from_numeric(score: float) -> "Confidence":
        if score >= 0.85:
            return Confidence.HIGH
        if score >= 0.55:
            return Confidence.MEDIUM
        if score > 0.0:
            return Confidence.LOW
        return Confidence.UNKNOWN
