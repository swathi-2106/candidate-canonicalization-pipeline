"""Parses recruiter CSV files into candidate profiles."""
import csv
import io
import logging
import uuid
from typing import List, Dict, Optional

import pandas as pd

from src.models import (
    CandidateProfile, FieldWithProvenance, ContactInfo,
    Provenance, SourceType, Confidence,
)
from src.normalizers.email import EmailNormalizer
from src.normalizers.phone import PhoneNormalizer

logger = logging.getLogger(__name__)

# Default header aliases -> canonical field names
DEFAULT_COLUMN_MAPPING = {
    "name": "name", "candidate name": "name", "full name": "name",
    "email": "email", "email address": "email", "e-mail": "email",
    "phone": "phone", "phone number": "phone", "mobile": "phone", "contact number": "phone",
    "skills": "skills", "skill set": "skills", "key skills": "skills",
    "current company": "current_company", "company": "current_company", "employer": "current_company",
    "current title": "job_title", "job title": "job_title", "title": "job_title", "designation": "job_title",
    "years of experience": "years_of_experience", "experience": "years_of_experience", "yoe": "years_of_experience",
    "linkedin": "linkedin", "linkedin url": "linkedin",
    "address": "address", "location": "address",
    "certifications": "certifications", "certs": "certifications",
}

REQUIRED_FIELDS = ["name", "email"]


class CSVParser:
    """Parses recruiter CSV files into a list of CandidateProfile objects.

    Features:
    - Auto-detects delimiter
    - Flexible column mapping (user-supplied overrides + built-in aliases)
    - Handles missing values gracefully
    - Validates required fields, logging (not raising) on rows that fail
    """

    def __init__(self, column_mapping: Optional[Dict[str, str]] = None):
        """column_mapping: optional dict of {csv_header: canonical_field_name}.
        Merged on top of DEFAULT_COLUMN_MAPPING (case-insensitive on csv_header)."""
        self.column_mapping = dict(DEFAULT_COLUMN_MAPPING)
        if column_mapping:
            for k, v in column_mapping.items():
                self.column_mapping[k.strip().lower()] = v
        self.email_normalizer = EmailNormalizer()
        self.phone_normalizer = PhoneNormalizer()
        self.errors: List[str] = []

    def parse(self, file_path: str) -> List[CandidateProfile]:
        """Parse a CSV file and return a list of CandidateProfile objects.
        Rows that fail validation are skipped (logged), not fatal."""
        self.errors = []
        delimiter = self._detect_delimiter(file_path)
        try:
            df = pd.read_csv(file_path, delimiter=delimiter, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, delimiter=delimiter, dtype=str, keep_default_na=False, encoding="latin-1")
        except Exception as e:
            logger.error("Failed to read CSV %s: %s", file_path, e)
            self.errors.append(f"Failed to read CSV {file_path}: {e}")
            return []

        canonical_cols = self._map_columns(df.columns)

        profiles: List[CandidateProfile] = []
        for idx, row in df.iterrows():
            try:
                profile = self._row_to_profile(row, canonical_cols, file_path, idx)
                if profile:
                    profiles.append(profile)
            except Exception as e:  # graceful failure per-row
                msg = f"Row {idx} in {file_path} failed: {e}"
                logger.warning(msg)
                self.errors.append(msg)
                continue
        return profiles

    def _detect_delimiter(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                sample = f.read(4096)
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=[",", ";", "\t", "|"])
            return dialect.delimiter
        except Exception:
            return ","

    def _map_columns(self, columns) -> Dict[str, str]:
        """Map dataframe column names -> canonical field names."""
        mapped = {}
        for col in columns:
            key = col.strip().lower()
            if key in self.column_mapping:
                mapped[col] = self.column_mapping[key]
        return mapped

    def _row_to_profile(self, row, canonical_cols: Dict[str, str], file_path: str, row_idx: int) -> Optional[CandidateProfile]:
        values: Dict[str, str] = {}
        for csv_col, canon in canonical_cols.items():
            val = str(row.get(csv_col, "")).strip()
            if val:
                values[canon] = val

        missing_required = [f for f in REQUIRED_FIELDS if f not in values]
        if missing_required:
            raise ValueError(f"Missing required field(s): {missing_required}")

        def make_field(field_name: str, transformation: Optional[str] = None, transformed=None) -> FieldWithProvenance:
            raw = values.get(field_name, "")
            prov = Provenance(
                source_type=SourceType.CSV,
                source_file=file_path,
                original_value=raw,
                transformation=transformation,
                transformed_value=transformed,
            )
            value = transformed if transformed is not None else raw
            confidence = Confidence.HIGH if raw else Confidence.UNKNOWN
            return FieldWithProvenance(value=value, confidence=confidence, provenance=prov)

        name_field = make_field("name")

        raw_email = values.get("email", "")
        norm_email = self.email_normalizer.normalize(raw_email)
        email_valid = self.email_normalizer.validate(norm_email)
        email_field = make_field("email", transformation="lowercase+trim", transformed=norm_email)
        email_field.confidence = Confidence.HIGH if email_valid else Confidence.LOW

        contact = ContactInfo(email=email_field)
        if "phone" in values:
            norm_phone = self.phone_normalizer.normalize(values["phone"])
            phone_field = make_field("phone", transformation="E.164 normalize", transformed=norm_phone)
            phone_field.confidence = Confidence.HIGH if self.phone_normalizer.is_valid(values["phone"]) else Confidence.MEDIUM
            contact.phone = phone_field
        if "linkedin" in values:
            contact.linkedin = make_field("linkedin")
        if "address" in values:
            contact.address = make_field("address")

        skills_field_list = []
        if "skills" in values:
            raw_skills = [s.strip() for s in values["skills"].replace(";", ",").split(",") if s.strip()]
            for s in raw_skills:
                prov = Provenance(source_type=SourceType.CSV, source_file=file_path, original_value=s)
                skills_field_list.append(FieldWithProvenance(value=s, confidence=Confidence.HIGH, provenance=prov))

        job_titles = []
        if "job_title" in values:
            job_titles.append(make_field("job_title"))

        certifications = []
        if "certifications" in values:
            for c in [c.strip() for c in values["certifications"].split(",") if c.strip()]:
                prov = Provenance(source_type=SourceType.CSV, source_file=file_path, original_value=c)
                certifications.append(FieldWithProvenance(value=c, confidence=Confidence.MEDIUM, provenance=prov))

        current_company = make_field("current_company") if "current_company" in values else None
        years_exp = None
        if "years_of_experience" in values:
            try:
                yoe_val = float(values["years_of_experience"])
                years_exp = make_field("years_of_experience", transformation="to_float", transformed=yoe_val)
            except ValueError:
                years_exp = make_field("years_of_experience")
                years_exp.confidence = Confidence.LOW

        profile = CandidateProfile(
            profile_id=str(uuid.uuid4()),
            name=name_field,
            email=email_field,
            contact=contact,
            skills=skills_field_list,
            experience=[],
            education=[],
            source_files=[file_path],
            total_confidence=0.0,
            current_company=current_company,
            years_of_experience=years_exp,
            job_titles=job_titles,
            certifications=certifications,
            origin="CSV",
        )
        return profile
