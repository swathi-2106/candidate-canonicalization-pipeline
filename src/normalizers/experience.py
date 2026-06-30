"""Helpers for normalizing/aggregating work-experience data."""
from typing import List
from .date import DateNormalizer


class ExperienceNormalizer:
    """Computes aggregate years-of-experience from a list of experience date ranges."""

    def __init__(self):
        self.date_normalizer = DateNormalizer()

    def total_years(self, date_ranges: List[str]) -> float:
        """Sum (non-overlap-aware, simple) years across a list of 'Start - End' strings."""
        total = 0.0
        for rng in date_ranges:
            total += self.date_normalizer.parse_experience_years(rng)
        return round(total, 1)
