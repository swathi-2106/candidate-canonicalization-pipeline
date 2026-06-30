# Candidate Profile Canonicalization Pipeline

A deterministic, explainable, CLI-based candidate data transformation pipeline built for the **Eightfold AI Engineering Internship Assignment**.

The application ingests recruiter CSV exports (structured data) and resume PDFs (unstructured data), normalizes and merges candidate information into a single canonical profile, tracks provenance and confidence for every field, validates the result against a schema, and generates configurable outputs.

## Features

* Structured source support (Recruiter CSV)
* Unstructured source support (Resume PDF)
* Canonical candidate profile generation
* Email, phone, skill, company, and date normalization
* Deterministic merge engine
* Provenance tracking
* Confidence scoring
* Runtime configurable projection layer
* JSON Schema validation
* JSON, CSV, and Excel export
* Processing reports and structured logging
* Graceful handling of malformed inputs

## Project Structure

```
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

## Installation

Clone the repository and install the dependencies.

```bash
pip install -r requirements.txt
```

## Run the Pipeline

Generate JSON, CSV, and Excel outputs from the sample recruiter CSV files and resume PDFs.

```bash
python main.py run --csv-dir data/input/csv --resume-dir data/input/resumes --output-dir data/output --format json --format csv --format excel
```

## Additional Commands

Inspect a recruiter CSV file:

```bash
python main.py inspect-csv data/input/csv/recruiter_export_1.csv
```

Inspect a resume:

```bash
python main.py inspect-resume data/input/resumes/jane_doe_resume.pdf
```

Run validation only:

```bash
python main.py run --csv-dir data/input/csv --resume-dir data/input/resumes --validate-only
```

Run without generating output files:

```bash
python main.py run --csv-dir data/input/csv --resume-dir data/input/resumes --dry-run
```

Run using a custom projection configuration:

```bash
python main.py run --csv-dir data/input/csv --resume-dir data/input/resumes --projection data/projections/recruiter_summary.json --format json
```

## Sample Output

Running the pipeline on the provided sample inputs generates output similar to:

```text
Pipeline complete: 10 profile(s) generated (9 valid, 1 invalid).
Average confidence: 0.8678
Outputs written to: data/output
```

Generated artifacts:

* `canonical_profiles.json`
* `projected_profiles.json`
* `canonical_profiles.csv`
* `canonical_profiles.xlsx`
* `report.json`
* `report.txt`

## Testing

Execute the complete test suite:

```bash
pytest tests -v
```

## Technologies

* Python
* Pandas
* Pydantic
* PyMuPDF
* pdfplumber
* PyYAML
* JSON Schema
* OpenPyXL
* pytest

## Author

**Swathi S**

Email: [swathirtcc27@gmail.com](mailto:swathirtcc27@gmail.com)

LinkedIn: https://www.linkedin.com/in/swathi-s-cse/

GitHub: https://github.com/swathi-2106/
