# Candidate Profile Canonicalization Pipeline

A deterministic, explainable, CLI-based candidate data transformation pipeline built for the **Eightfold AI Engineering Internship Assignment**.

The application ingests recruiter CSV exports (structured data) and resume PDFs (unstructured data), normalizes and merges candidate information into a single canonical profile, tracks provenance and confidence for every field, validates the result against a schema, and generates configurable outputs.

---

## Features

- Structured source support (Recruiter CSV)
- Unstructured source support (Resume PDF)
- Canonical candidate profile generation
- Email, phone, skill, company, and date normalization
- Deterministic merge engine
- Provenance tracking
- Confidence scoring
- Runtime configurable projection layer
- JSON Schema validation
- JSON, CSV, and Excel export
- Processing reports and structured logging
- Graceful handling of malformed inputs

---

## Edge Cases Handled

The pipeline is designed to fail gracefully while maintaining deterministic processing.

- Malformed recruiter CSV rows are logged and skipped without stopping the pipeline.
- Unreadable or corrupted resume PDFs are skipped and reported as processing errors.
- Duplicate candidate profiles are detected and merged using normalized email matching.
- Conflicting field values are resolved using configurable merge strategies.
- Duplicate skills are automatically deduplicated during normalization.
- Missing optional fields are handled without failing profile generation.
- Invalid emails and phone numbers are detected during validation.
- Validation failures are reported while allowing the remaining valid profiles to be processed.
- Multiple recruiter CSV files and resume PDFs can be processed in a single pipeline run.
- Runtime projection configurations safely omit or rename missing fields based on the configured policy.

## Project Structure

```text
candidate-canonicalization/
├── src/
├── config/
├── data/
│   ├── input/
│   └── output/
├── tests/
├── requirements.txt
├── main.py
└── README.md
```

---

# Run Locally

## 1. Clone the Repository

```bash
git clone https://github.com/swathi-2106/candidate-canonicalization.git
```

## 2. Navigate to the Project

```bash
cd candidate-canonicalization
```

## 3. Create a Virtual Environment (Recommended)

### Windows (PowerShell)

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Run the Pipeline

Generate canonical candidate profiles from the sample recruiter CSV files and resume PDFs.

```bash
python main.py run \
  --csv-dir data/input/csv \
  --resume-dir data/input/resumes \
  --output-dir data/output \
  --format json \
  --format csv \
  --format excel
```

---

# Generated Output

After a successful run, the following files are created inside `data/output/`:

- `canonical_profiles.json`
- `projected_profiles.json`
- `canonical_profiles.csv`
- `canonical_profiles.xlsx`
- `report.json`
- `report.txt`

Example console output:

```text
Pipeline complete: 10 profile(s) generated (9 valid, 1 invalid).
Average confidence: 0.8678
Outputs written to: data/output
```

---

# Useful Commands

### Run with a Projection Configuration

```bash
python main.py run \
  --csv-dir data/input/csv \
  --resume-dir data/input/resumes \
  --projection data/projections/recruiter_summary.json \
  --format json
```

### Validate Inputs Only

```bash
python main.py run \
  --csv-dir data/input/csv \
  --resume-dir data/input/resumes \
  --validate-only
```

### Dry Run (No Output Files Generated)

```bash
python main.py run \
  --csv-dir data/input/csv \
  --resume-dir data/input/resumes \
  --dry-run
```

### Inspect a Recruiter CSV

```bash
python main.py inspect-csv data/input/csv/recruiter_export_1.csv
```

### Inspect a Resume

```bash
python main.py inspect-resume data/input/resumes/jane_doe_resume.pdf
```

---

# Running Tests

Execute the complete test suite.

```bash
pytest tests -v
```

---

# Technology Stack

- Python
- Pandas
- Pydantic
- PyMuPDF
- pdfplumber
- PyYAML
- JSON Schema
- OpenPyXL
- pytest

---

# Author

**Swathi S**

**Email:** swathirtcc27@gmail.com

**LinkedIn:** https://www.linkedin.com/in/swathi-s-cse/

**GitHub:** https://github.com/swathi-2106/
