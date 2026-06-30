"""Regex/keyword-based extraction helpers used by ResumeParser.

Note: This implementation uses regex/keyword heuristics rather than a heavy
NLP/NER model (spaCy) to keep the pipeline lightweight and dependency-free.
The `use_ner` flag on ResumeParser is reserved for future integration of a
real NER model; when unavailable it transparently falls back to these
heuristics, and confidence scores reflect that lower certainty.
"""
import re
from typing import Dict, List, Optional

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")
LINKEDIN_RE = re.compile(r"(https?://)?(www\.)?linkedin\.com/in/[A-Za-z0-9\-_/]+", re.IGNORECASE)

SECTION_HEADERS = {
    "experience": ["experience", "work experience", "professional experience", "employment history"],
    "education": ["education", "academic background", "qualifications"],
    "skills": ["skills", "technical skills", "core competencies", "skill set"],
    "certifications": ["certifications", "certificates", "licenses"],
}

DATE_RANGE_RE = re.compile(
    r"((?:[A-Za-z]{3,9}\.?\s+\d{4})|\d{1,2}/\d{4}|\d{4})\s*(?:-|–|to)\s*"
    r"((?:[A-Za-z]{3,9}\.?\s+\d{4})|\d{1,2}/\d{4}|\d{4}|[Pp]resent|[Cc]urrent)",
)


def extract_email(text: str) -> Optional[str]:
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    match = PHONE_RE.search(text)
    return match.group(0).strip() if match else None


def extract_linkedin(text: str) -> Optional[str]:
    match = LINKEDIN_RE.search(text)
    return match.group(0) if match else None


def extract_name(text: str) -> Optional[str]:
    """Heuristic: the name is usually the first non-empty line that doesn't
    contain an email/phone/digits and looks like 'Title Case Words'."""
    for line in text.strip().splitlines()[:6]:
        line = line.strip()
        if not line or EMAIL_RE.search(line) or PHONE_RE.search(line):
            continue
        if any(ch.isdigit() for ch in line):
            continue
        words = line.split()
        if 1 < len(words) <= 4 and all(w[0:1].isupper() for w in words if w):
            return line
    return None


def split_sections(text: str) -> Dict[str, str]:
    """Split resume text into sections based on common header keywords."""
    lines = text.splitlines()
    sections: Dict[str, List[str]] = {}
    current_section = "header"
    sections[current_section] = []

    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower().strip(":")
        matched_section = None
        for sect, headers in SECTION_HEADERS.items():
            if lowered in headers or (len(lowered.split()) <= 4 and lowered in headers):
                matched_section = sect
                break
        if matched_section:
            current_section = matched_section
            sections.setdefault(current_section, [])
            continue
        sections.setdefault(current_section, []).append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def extract_skills(text: str, taxonomy: List[str]) -> List[str]:
    """Match taxonomy skill keywords (case-insensitive, word-boundary) in text."""
    found = []
    lower_text = text.lower()
    for skill in taxonomy:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, lower_text):
            found.append(skill)
    return found


def extract_experience_entries(section_text: str) -> List[Dict]:
    """Parse the experience section into a list of {title, company, dates, description}."""
    entries = []
    blocks = re.split(r"\n\s*\n", section_text.strip()) if section_text.strip() else []
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        date_match = DATE_RANGE_RE.search(block)
        dates = date_match.group(0) if date_match else None

        header_line = lines[0]
        title, company = None, None
        if " at " in header_line.lower():
            parts = re.split(r"\s+at\s+", header_line, maxsplit=1, flags=re.IGNORECASE)
            title, company = parts[0].strip(), parts[1].strip()
        elif "," in header_line:
            parts = header_line.split(",", 1)
            title, company = parts[0].strip(), parts[1].strip()
        elif "-" in header_line and not date_match:
            parts = header_line.split("-", 1)
            title, company = parts[0].strip(), parts[1].strip()
        else:
            title = header_line

        description = "\n".join(lines[1:]) if len(lines) > 1 else None
        entries.append({
            "title": title,
            "company": company,
            "dates": dates,
            "description": description,
            "current": bool(dates and re.search(r"present|current", dates, re.IGNORECASE)),
        })
    return entries


def extract_education_entries(section_text: str) -> List[Dict]:
    """Parse the education section into a list of {institution, degree, field, date}."""
    entries = []
    blocks = re.split(r"\n\s*\n", section_text.strip()) if section_text.strip() else []
    degree_keywords = ["bachelor", "master", "phd", "doctorate", "b.s.", "m.s.", "b.a.", "m.a.", "mba", "associate"]
    for block in blocks:
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        if not lines:
            continue
        date_match = re.search(r"\b(19|20)\d{2}\b", block)
        grad_date = date_match.group(0) if date_match else None

        degree_line = None
        institution_line = None
        for line in lines:
            if any(kw in line.lower() for kw in degree_keywords):
                degree_line = line
            elif institution_line is None:
                institution_line = line

        entries.append({
            "institution": institution_line or lines[0],
            "degree": degree_line,
            "field_of_study": None,
            "graduation_date": grad_date,
        })
    return entries


def extract_certifications(section_text: str) -> List[str]:
    return [l.strip("-• \t") for l in section_text.splitlines() if l.strip()]
