# Candidate Profile Canonicalization Pipeline

A deterministic, explainable, CLI-based pipeline that ingests recruiter CSV exports and resume PDFs, normalizes and merges them into a single canonical candidate profile per person, tracks **provenance** (where every field came from) and **confidence** (how trustworthy each field is), validates the result against a schema, and produces configurable, reproducible outputs (JSON / CSV / Excel) plus a processing report.

## Why this design

- **Deterministic**: no randomness, no LLM calls; the same input always produces the same output (modulo `processing_timestamp`/UUIDs).
- **Explainable**: every field on a canonical profile carries a `Provenance` record (source file, original raw value, transformation applied) and a `Confidence` (HIGH/MEDIUM/LOW/UNKNOWN).
- **Graceful failure**: a malformed CSV row or an unreadable PDF is logged and skipped — it never aborts the whole run.
- **Configurable without code changes**: column mappings, merge strategies, and output **projections** (field selection/renaming) are all driven by config files passed at runtime.

### A note on resume parsing

The spec sheet suggested spaCy-based NER for resume parsing. This implementation instead uses **regex + keyword/taxonomy matching** (`src/parsers/resume_extractors.py`). This keeps the pipeline lightweight, fast, fully deterministic, and dependency-light, at the cost of being less robust to free-form resume layouts than a trained NER model. The `ResumeParser(use_ner=...)` flag and the extractor module are structured so a real NER backend (spaCy/transformers) could be swapped in later without changing any downstream code — every extracted field already flows through the same `FieldWithProvenance`/`Confidence` machinery regardless of how it was extracted.

## Architecture

```
CLI → Pipeline Orchestrator
        ├─ CSV Parser ─────────┐
        ├─ Resume Parser ──────┤
        │                      ▼
        │             Normalization (phone/email/date/skills/company)
        │                      ▼
        │                Merge Engine (conflict resolution, union, priority)
        │                      ▼
        │            Provenance & Confidence Services
        │                      ▼
        │                  Validator (schema + business rules)
        │                      ▼
        │              Projection Engine (configurable shape)
        │                      ▼
        └────────────►  Output Generators (JSON/CSV/Excel) + Report
```

## Project layout

```
candidate-canonicalization/
├── src/
│   ├── pipeline/        # orchestrator.py, config.py
│   ├── parsers/         # csv_parser.py, resume_parser.py, resume_extractors.py
│   ├── normalizers/     # phone, email, date, skills, company, experience
│   ├── models/          # candidate.py, provenance.py, confidence.py
│   ├── merge/           # merge_engine.py, conflict_resolver.py, deduplicator.py
│   ├── services/        # provenance_service.py, confidence_service.py, validator.py
│   ├── projection/      # projection_engine.py
│   ├── output/          # json/csv/excel exporters, report_generator.py
│   ├── cli/             # commands.py
│   └── utils/           # logger.py, helpers.py, validators.py
├── data/
│   ├── input/{csv,resumes}/    # sample input data
│   ├── output/                 # generated output (gitignored in practice)
│   ├── taxonomies/             # skills.json, companies.json, job_titles.json
│   ├── schemas/schema.json     # output JSON Schema
│   └── projections/            # example projection specs
├── tests/                # pytest suite (27 tests)
├── config/                # default.yaml, production.yaml
├── scripts/generate_sample_data.py
├── main.py                # CLI entry point
├── requirements.txt
└── setup.py
```

## Installation

```bash
cd candidate-canonicalization
pip install -r requirements.txt
```

(Sample CSV/resume data is already included under `data/input/`. To regenerate it: `python scripts/generate_sample_data.py`.)

## Quick start

Run the full pipeline against the bundled sample data:

```bash
python main.py run \
  --csv-dir data/input/csv \
  --resume-dir data/input/resumes \
  --output-dir data/output \
  --format json --format csv --format excel
```

This produces, under `data/output/`:
- `canonical_profiles.json` — full canonical profiles with provenance + confidence
- `projected_profiles.json` — the default (slimmer) projection
- `canonical_profiles.csv` — flat CSV (projected fields)
- `canonical_profiles.xlsx` — multi-sheet workbook (Profiles / Skills / Experience / Education / Validation)
- `report.json` / `report.txt` — processing metrics, counts, confidence stats, errors

Example console output:
```
✔ Pipeline complete: 7 profile(s) generated (7 valid, 0 invalid).
  Average confidence: 0.8997
  Outputs written to: data/output
```

## CLI reference

```bash
python main.py run --help
```

Key options:
| Flag | Description |
|---|---|
| `--csv-dir PATH` | Directory of recruiter CSV files |
| `--resume-dir PATH` | Directory of resume PDFs |
| `--output-dir PATH` | Where to write outputs (default `data/output`) |
| `--format [json\|csv\|excel]` | Repeatable; choose one or more output formats |
| `--config PATH` | YAML/JSON file (see `config/default.yaml`) |
| `--merge-priority [CSV\|RESUME]` | Which source wins on unspecified conflicts |
| `--column-mapping PATH` | JSON `{csv_header: canonical_field}` overrides |
| `--projection PATH` | JSON projection spec (see below) |
| `--schema PATH` | JSON Schema to validate output against |
| `--parallel/--no-parallel` | Toggle concurrent file processing (default on) |
| `-v/--verbose`, `-q/--quiet` | Logging verbosity |

Other commands:
```bash
python main.py inspect-csv data/input/csv/recruiter_export_1.csv
python main.py inspect-resume data/input/resumes/jane_doe_resume.pdf
```

## Configurable column mapping (CSV)

The CSV parser ships with built-in header aliases (`"Candidate Name"`, `"full name"`, `"Email Address"`, `"mobile"`, etc. — see `DEFAULT_COLUMN_MAPPING` in `src/parsers/csv_parser.py`), so most recruiter exports work out of the box, delimiter included (comma, semicolon, tab, pipe are auto-detected). For unusual headers, supply a JSON override:

```json
{ "Nom": "name", "Courriel": "email" }
```
```bash
python main.py run --csv-dir ... --column-mapping my_mapping.json
```

## Merge strategy

`MergeEngine` merges a CSV-sourced profile and a resume-sourced profile (matched by normalized email via `Deduplicator`) field by field:

- `csv_preferred` / `resume_preferred` — deterministic winner on conflict
- `longest` — pick the longer string or larger number (used for `years_of_experience`)
- `union` — combine lists, deduping (used for `skills`, `job_titles`, `certifications`)
- `csv_only` / `resume_only` — ignore the other source entirely

When both sources **agree**, confidence is boosted to `HIGH` and a merge note is recorded. When they **conflict**, the loser's value is discarded, the winner is recorded, and confidence is capped at `MEDIUM` — both decisions are logged in `profile.merge_notes` and `profile.<field>.provenance`. Override the defaults via `config/default.yaml`'s `merge_strategy:` block or `--config`.

## Configurable projections (no code changes)

The `ProjectionEngine` reshapes a canonical profile into any output shape via a JSON spec — pick fields, rename them, flatten lists, choose what happens to missing values (`null` / `omit` / `error`), and optionally include confidence/provenance alongside each value:

```json
{
  "fields": [
    {"source": "name.value", "target": "candidate_name"},
    {"source": "skills", "target": "top_skills", "extract": "value", "list": true}
  ],
  "include_confidence": true,
  "missing_value_policy": "omit"
}
```
```bash
python main.py run --csv-dir ... --resume-dir ... --projection data/projections/recruiter_summary.json
```
See `data/projections/recruiter_summary.json` for a complete example. This is what drives the CSV/Excel exports too.

## Provenance & confidence example

Every field on a canonical profile looks like this:
```json
{
  "value": "Jane Doe",
  "confidence": "HIGH",
  "provenance": {
    "source_type": "MERGED",
    "source_file": "merged",
    "original_value": ["Jane Doe", "Jane Doe"],
    "transformation": "agreement_merge",
    "timestamp": "2026-06-30T11:05:13.154419"
  }
}
```

## Validation

`Validator` checks required fields (`profile_id`, `name`, `email`), email format, plausible phone length, plausible `years_of_experience`, and warns (non-fatally) when skills/experience are empty. If `jsonschema` is installed (it's in `requirements.txt`) and `--schema` is supplied, the serialized profile is also validated against `data/schemas/schema.json`. Results are written into the Excel `Validation` sheet and `report.json`.

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
# with coverage:
pytest tests/ --cov=src --cov-report=term-missing
```
27 tests cover parsers (CSV header mapping, delimiter detection, graceful row failure, resume error handling), normalizers (phone/email/date/skills/company/experience), the merge engine (agreement boosting, conflict resolution, dedupe), and the projection engine (renaming, missing-value policies, confidence inclusion).

## Known limitations

- Resume extraction is regex/heuristic-based (see "A note on resume parsing" above); scanned/image-only PDFs with no text layer cannot be parsed (OCR is out of scope) and will be logged as errors and skipped.
- `years_of_experience` derived from resume date ranges sums per-role durations without overlap detection (concurrent roles would be double-counted).
- Company/skill taxonomies (`data/taxonomies/*.json`) are illustrative starter sets — extend them for production use.
