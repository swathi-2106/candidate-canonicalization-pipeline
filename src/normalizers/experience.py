"""Helpers for normalizing/aggregating work-experience data."""
import re
from datetime import datetime
from typing import List
from .date import DateNormalizer


class ExperienceNormalizer:
    """Computes aggregate years-of-experience from a list of experience date ranges."""

    def __init__(self):
        self.date_normalizer = DateNormalizer()

    def total_years(self, date_ranges: List[str]) -> float:
        """Count total employment duration once across overlapping date ranges."""
        intervals = []
        for rng in date_ranges:
            interval = self._parse_range(rng)
            if interval:
                intervals.append(interval)
        if not intervals:
            return 0.0

        intervals.sort(key=lambda item: item[0])
        merged = []
        for start, end in intervals:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            elif end > merged[-1][1]:
                merged[-1][1] = end

        total_days = sum((end - start).days for start, end in merged)
        return round(max(total_days, 0) / 365.25, 1)

    def _parse_range(self, date_range: str):
        if not date_range:
            return None
        parts = re.split(r"\s*(?:-|â€“|to)\s*", str(date_range), maxsplit=1)
        if len(parts) != 2:
            return None
        start = self.date_normalizer._parse(parts[0].strip())
        end_raw = parts[1].strip()
        end = datetime.now() if end_raw.lower() in {"present", "current", "now", "ongoing", "today"} else self.date_normalizer._parse(end_raw)
        if not start or not end or end < start:
            return None
        return start, end
