"""Parses PDF resume files and extracts candidate information."""
import logging
import uuid
from typing import Dict, List, Optional

from src.models import (
    CandidateProfile, FieldWithProvenance, ContactInfo,
    Experience, Education, Provenance, SourceType, Confidence,
)
from src.normalizers.email import EmailNormalizer
from src.normalizers.phone import PhoneNormalizer
from src.normalizers.date import DateNormalizer
from src.normalizers.skills import SkillsNormalizer, DEFAULT_TAXONOMY
from . import resume_extractors as ex

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:  # pragma: no cover
    HAS_PDFPLUMBER = False

try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:  # pragma: no cover
    HAS_PYPDF = False


class ResumeParser:
    """Parses PDF resume files into CandidateProfile objects.

    Extraction is regex/keyword-based ("use_ner" reserved for a future real
    NER backend - see resume_extractors.py docstring for rationale).
    """

    def __init__(self, use_ner: bool = False, skill_taxonomy: Optional[List[str]] = None, ner_model: Optional[str] = None):
        self.use_ner = use_ner
        self.ner_model = ner_model or "en_core_web_sm"
        self._nlp = None
        flat_taxonomy = skill_taxonomy or [s for group in DEFAULT_TAXONOMY.values() for s in group]
        self.skill_taxonomy = flat_taxonomy
        self.email_normalizer = EmailNormalizer()
        self.phone_normalizer = PhoneNormalizer()
        self.date_normalizer = DateNormalizer()
        self.skills_normalizer = SkillsNormalizer()
        self.errors: List[str] = []

    def parse(self, file_path: str) -> Optional[CandidateProfile]:
        """Parse a PDF resume and return a CandidateProfile, or None on failure."""
        try:
            text = self._extract_text(file_path)
        except Exception as e:
            logger.error("Failed to extract text from %s: %s", file_path, e)
            self.errors.append(f"Failed to extract text from {file_path}: {e}")
            return None

        if not text or not text.strip():
            msg = f"No extractable text in {file_path} (possibly scanned/image PDF)"
            logger.warning(msg)
            self.errors.append(msg)
            return None

        contact = self._extract_contact(text)
        skills = self._extract_skills(text)
        experience_raw = self._extract_experience(text)
        education_raw = self._extract_education(text)

        def field_with_prov(value, confidence: Confidence, transformation: Optional[str] = None, original=None):
            prov = Provenance(
                source_type=SourceType.RESUME_PDF,
                source_file=file_path,
                original_value=original if original is not None else value,
                transformation=transformation,
                transformed_value=value if transformation else None,
            )
            return FieldWithProvenance(value=value, confidence=confidence, provenance=prov)

        name_val = contact.get("name")
        name_field = field_with_prov(name_val, Confidence.MEDIUM if name_val else Confidence.UNKNOWN)

        raw_email = contact.get("email") or ""
        norm_email = self.email_normalizer.normalize(raw_email)
        email_conf = Confidence.HIGH if (norm_email and self.email_normalizer.validate(norm_email)) else Confidence.UNKNOWN
        email_field = field_with_prov(norm_email, email_conf, transformation="lowercase+trim" if raw_email else None, original=raw_email)

        contact_info = ContactInfo(email=email_field)
        if contact.get("phone"):
            norm_phone = self.phone_normalizer.normalize(contact["phone"])
            phone_conf = Confidence.HIGH if self.phone_normalizer.is_valid(contact["phone"]) else Confidence.MEDIUM
            contact_info.phone = field_with_prov(norm_phone, phone_conf, transformation="E.164 normalize", original=contact["phone"])
        if contact.get("linkedin"):
            contact_info.linkedin = field_with_prov(contact["linkedin"], Confidence.HIGH)

        skill_fields = []
        normalized_skills = self.skills_normalizer.normalize(skills)
        for s in normalized_skills:
            skill_fields.append(field_with_prov(s, Confidence.MEDIUM, transformation="taxonomy_map", original=s))

        experiences = []
        job_titles = []
        for entry in experience_raw:
            company_val = entry.get("company") or ""
            title_val = entry.get("title") or ""
            dates = entry.get("dates")
            start_date, end_date = None, None
            if dates:
                parts = ex.DATE_RANGE_RE.search(dates)
                if parts:
                    start_raw, end_raw = parts.group(1), parts.group(2)
                    start_date = field_with_prov(self.date_normalizer.normalize(start_raw), Confidence.MEDIUM, "date_normalize", start_raw)
                    end_norm = self.date_normalizer.normalize(end_raw)
                    end_date = field_with_prov(end_norm, Confidence.MEDIUM, "date_normalize", end_raw)

            company_field = field_with_prov(company_val, Confidence.MEDIUM if company_val else Confidence.LOW)
            title_field = field_with_prov(title_val, Confidence.MEDIUM if title_val else Confidence.LOW)
            desc_field = field_with_prov(entry.get("description"), Confidence.LOW) if entry.get("description") else None

            experiences.append(Experience(
                company=company_field,
                title=title_field,
                start_date=start_date,
                end_date=end_date,
                description=desc_field,
                current=entry.get("current", False),
            ))
            if title_val:
                job_titles.append(title_field)

        educations = []
        for entry in education_raw:
            inst_field = field_with_prov(entry.get("institution"), Confidence.MEDIUM if entry.get("institution") else Confidence.LOW)
            degree_field = field_with_prov(entry.get("degree"), Confidence.MEDIUM if entry.get("degree") else Confidence.LOW)
            grad_field = None
            if entry.get("graduation_date"):
                grad_field = field_with_prov(
                    self.date_normalizer.normalize(entry["graduation_date"]),
                    Confidence.MEDIUM, "date_normalize", entry["graduation_date"],
                )
            educations.append(Education(
                institution=inst_field,
                degree=degree_field,
                field_of_study=None,
                graduation_date=grad_field,
            ))

        sections = ex.split_sections(text)
        certifications = []
        if "certifications" in sections and sections["certifications"]:
            for c in ex.extract_certifications(sections["certifications"]):
                certifications.append(field_with_prov(c, Confidence.MEDIUM))

        current_company = None
        current_entries = [e for e in experiences if e.current]
        if current_entries:
            current_company = current_entries[0].company
        elif experiences:
            current_company = experiences[0].company

        total_years = None
        date_ranges = [e.get("dates") for e in experience_raw if e.get("dates")]
        if date_ranges:
            from src.normalizers.experience import ExperienceNormalizer
            yrs = ExperienceNormalizer().total_years(date_ranges)
            if yrs > 0:
                total_years = field_with_prov(yrs, Confidence.LOW, transformation="derived_from_date_ranges")

        profile = CandidateProfile(
            profile_id=str(uuid.uuid4()),
            name=name_field,
            email=email_field,
            contact=contact_info,
            skills=skill_fields,
            experience=experiences,
            education=educations,
            source_files=[file_path],
            total_confidence=0.0,
            current_company=current_company,
            years_of_experience=total_years,
            job_titles=job_titles,
            certifications=certifications,
            origin="RESUME_PDF",
        )
        return profile

    def _extract_text(self, file_path: str) -> str:
        """Extract text from PDF, preferring native text and falling back to optional OCR."""
        text = ""
        if HAS_PDFPLUMBER:
            try:
                text_parts = []
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text() or ""
                        text_parts.append(page_text)
                text = "\n".join(text_parts)
                if text.strip():
                    return text
            except Exception as e:
                logger.warning("pdfplumber failed on %s: %s, falling back to pypdf", file_path, e)
        if HAS_PYPDF:
            try:
                reader = PdfReader(file_path)
                text = "\n".join((page.extract_text() or "") for page in reader.pages)
                if text.strip():
                    return text
            except Exception as e:
                logger.warning("pypdf failed on %s: %s, falling back to OCR if available", file_path, e)

        ocr_text = self._extract_text_with_ocr(file_path)
        if ocr_text.strip():
            return ocr_text
        if not HAS_PDFPLUMBER and not HAS_PYPDF:
            raise RuntimeError("No PDF extraction library available (pdfplumber/pypdf)")
        return text

    def _extract_text_with_ocr(self, file_path: str) -> str:
        try:
            from pdf2image import convert_from_path
            import pytesseract
        except ImportError:
            msg = f"OCR dependencies unavailable for {file_path}; install pdf2image and pytesseract to process scanned PDFs"
            logger.warning(msg)
            self.errors.append(msg)
            return ""

        try:
            pages = convert_from_path(file_path)
            return "\n".join(pytesseract.image_to_string(page) for page in pages)
        except Exception as e:
            msg = f"OCR failed for {file_path}: {e}"
            logger.warning(msg)
            self.errors.append(msg)
            return ""

    def _extract_contact(self, text: str) -> Dict:
        contact = {
            "name": ex.extract_name(text),
            "email": ex.extract_email(text),
            "phone": ex.extract_phone(text),
            "linkedin": ex.extract_linkedin(text),
        }
        return self._enhance_contact_with_ner(text, contact)

    def _enhance_contact_with_ner(self, text: str, contact: Dict) -> Dict:
        if not self.use_ner:
            return contact
        try:
            if self._nlp is None:
                import spacy
                self._nlp = spacy.load(self.ner_model)
            doc = self._nlp("\n".join(text.splitlines()[:20]))
            if not contact.get("name"):
                person = next((ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"), None)
                if person:
                    contact["name"] = person
        except Exception as e:
            msg = f"NER extraction unavailable; falling back to regex resume parsing: {e}"
            logger.info(msg)
        return contact

    def _extract_skills(self, text: str) -> List[str]:
        sections = ex.split_sections(text)
        skills_section = sections.get("skills", "")
        found = ex.extract_skills(skills_section, self.skill_taxonomy) if skills_section else []
        # Also scan full text in case skills aren't in a dedicated section
        found_full = ex.extract_skills(text, self.skill_taxonomy)
        merged = list(dict.fromkeys(found + found_full))
        return merged

    def _extract_experience(self, text: str) -> List[Dict]:
        sections = ex.split_sections(text)
        return ex.extract_experience_entries(sections.get("experience", ""))

    def _extract_education(self, text: str) -> List[Dict]:
        sections = ex.split_sections(text)
        return ex.extract_education_entries(sections.get("education", ""))
