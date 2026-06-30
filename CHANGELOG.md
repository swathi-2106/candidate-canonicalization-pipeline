# Changelog

## [1.0.0] - 2026-06-30
### Added
- Initial release of the Candidate Profile Canonicalization Pipeline.
- CSV parser with flexible column mapping, delimiter auto-detection, and per-row graceful failure.
- PDF resume parser (pdfplumber/pypdf) with regex/keyword-based contact, skills, experience, and education extraction.
- Normalizers: phone (libphonenumber/E.164), email, date (ISO + experience-year math), skills (taxonomy mapping + categorization), company (synonym + suffix stripping).
- Merge engine with configurable per-field strategies (csv_preferred, resume_preferred, longest, union, csv_only, resume_only) and conflict/agreement notes.
- Deduplicator that groups and merges profiles by normalized email.
- Provenance service tracking source file, original value, and transformation per field.
- Confidence service computing per-field and overall profile confidence scores.
- Schema-based validator (jsonschema, with a dependency-free fallback) plus business-rule checks.
- Runtime-configurable projection engine (field selection, renaming, list extraction, missing-value policy) with no code changes required.
- Output generators: JSON (canonical + projected), CSV, multi-sheet Excel.
- Human-readable + JSON processing reports with timing, counts, confidence, and error details.
- CLI (`main.py run`, `inspect-csv`, `inspect-resume`) with parallel file processing, verbose/quiet modes, and config file support.
- Sample CSV/resume data, taxonomy files, schema, default/production configs, and a full pytest suite (27 tests).
