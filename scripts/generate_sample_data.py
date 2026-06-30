#!/usr/bin/env python3
"""Regenerates the sample CSV and resume PDF files under data/input/.
Run from the project root: `python scripts/generate_sample_data.py`
Requires: reportlab (pip install reportlab --break-system-packages)
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "data" / "input" / "csv"
RESUME_DIR = ROOT / "data" / "input" / "resumes"
CSV_DIR.mkdir(parents=True, exist_ok=True)
RESUME_DIR.mkdir(parents=True, exist_ok=True)


def make_resume(path: Path, lines):
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    y = height - 60
    for line in lines:
        if y < 60:
            c.showPage()
            y = height - 60
        c.setFont("Helvetica", 11)
        c.drawString(60, y, line)
        y -= 16
    c.save()


CSV_1 = """Candidate Name,Email Address,Phone Number,Skills,Current Company,Job Title,Years of Experience,LinkedIn
Jane Doe,Jane.Doe@Example.com,(415) 555-0182,"Python, Django, AWS, Docker",Google,Senior Software Engineer,7,linkedin.com/in/janedoe
John Smith,john.smith@mail.com,415-555-0199,"Java, Spring Boot, Kubernetes",Amazon,Backend Engineer,5,linkedin.com/in/johnsmith
Maria Garcia,maria.garcia@workmail.com,650-555-0143,"React, TypeScript, Node.js",Meta,Frontend Engineer,4,
Alex Chen,alex.chen@example.com,212-555-0177,"SQL, Tableau, Python",Microsoft,Data Analyst,3,linkedin.com/in/alexchen
"""

CSV_2 = """full name;email;mobile;key skills;employer;designation;yoe
Priya Patel;priya.patel@example.com;408-555-0166;"Go, gRPC, PostgreSQL";IBM;Platform Engineer;6
Tom Becker;tom.becker@example.com;312-555-0121;"C++, Linux, Embedded Systems";Apple;Systems Engineer;9
"""

(CSV_DIR / "recruiter_export_1.csv").write_text(CSV_1)
(CSV_DIR / "recruiter_export_2.csv").write_text(CSV_2)

resume1 = [
    "Jane Doe", "jane.doe@example.com | (415) 555-0182 | linkedin.com/in/janedoe", "",
    "Skills", "Python, Django, AWS, Docker, PostgreSQL, React, Kubernetes", "",
    "Experience", "Senior Software Engineer at Google", "Jan 2021 - Present",
    "Led backend services migration to microservices architecture using Docker and Kubernetes.", "",
    "Software Engineer at Salesforce", "Jun 2017 - Dec 2020",
    "Built internal tools using Python and Django, improved deployment pipeline with AWS.", "",
    "Education", "Stanford University", "Bachelor of Science in Computer Science", "2017", "",
    "Certifications", "AWS Certified Solutions Architect", "Certified Kubernetes Administrator",
]

resume2 = [
    "John Smith", "john.smith@mail.com", "415-555-0199", "",
    "Skills", "Java, Spring Boot, Kubernetes, SQL, Microservices, REST API", "",
    "Experience", "Backend Engineer at Amazon", "Mar 2019 - Present",
    "Designed scalable REST APIs and microservices for fulfillment systems.", "",
    "Software Developer at Oracle", "Jul 2015 - Feb 2019",
    "Maintained legacy Java applications and migrated to Spring Boot.", "",
    "Education", "University of Michigan", "Master of Science in Computer Science", "2015",
]

resume3 = [
    "Wei Zhang", "wei.zhang@example.com | (206) 555-0134", "",
    "Skills", "Python, TensorFlow, PyTorch, Scikit-learn, Pandas", "",
    "Experience", "Machine Learning Engineer at Microsoft", "Aug 2020 - Present",
    "Built recommendation models serving millions of users.", "",
    "Education", "Carnegie Mellon University", "Master of Science, Machine Learning", "2020",
]

make_resume(RESUME_DIR / "jane_doe_resume.pdf", resume1)
make_resume(RESUME_DIR / "john_smith_resume.pdf", resume2)
make_resume(RESUME_DIR / "wei_zhang_resume.pdf", resume3)

print(f"Wrote sample CSVs to {CSV_DIR} and resumes to {RESUME_DIR}")
