from setuptools import setup, find_packages

setup(
    name="candidate-canonicalization",
    version="1.0.0",
    description="Deterministic, explainable pipeline for canonicalizing candidate profiles from recruiter CSVs and resume PDFs.",
    packages=find_packages(include=["src", "src.*"]),
    python_requires=">=3.9",
    install_requires=[
        "pandas>=2.0.0",
        "click>=8.1.0",
        "PyYAML>=6.0",
        "pdfplumber>=0.10.0",
        "pypdf>=4.0.0",
        "phonenumbers>=8.13.0",
        "email-validator>=2.0.0",
        "dateparser>=1.1.0",
        "fuzzywuzzy>=0.18.0",
        "python-Levenshtein>=0.21.0",
        "jsonschema>=4.0.0",
        "openpyxl>=3.1.0",
        "rich>=13.3.0",
    ],
    entry_points={
        "console_scripts": [
            "candidate-pipeline=src.cli.commands:main",
        ],
    },
)
