"""Skill taxonomy mapping and categorization."""
import json
import logging
from typing import List, Dict, Optional

try:
    from fuzzywuzzy import process as fuzzy_process
    HAS_FUZZYWUZZY = True
except ImportError:  # pragma: no cover
    HAS_FUZZYWUZZY = False

logger = logging.getLogger(__name__)

DEFAULT_TAXONOMY = {
    "Programming Languages": ["Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "SQL"],
    "Web Frameworks": ["React", "Angular", "Vue.js", "Django", "Flask", "FastAPI", "Spring", "Spring Boot", "Express.js", "Node.js", "Ruby on Rails"],
    "Data & ML": ["Pandas", "NumPy", "TensorFlow", "PyTorch", "Scikit-learn", "Spark", "Hadoop", "Tableau", "Power BI"],
    "Cloud & DevOps": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Terraform", "Jenkins", "CI/CD", "Ansible"],
    "Databases": ["PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "DynamoDB", "Oracle", "SQLite"],
    "Other": ["Git", "Linux", "Agile", "Scrum", "REST API", "GraphQL", "Microservices"],
}


class SkillsNormalizer:
    """Maps extracted skill strings to a standardized taxonomy."""

    def __init__(self, taxonomy_file: Optional[str] = None):
        self.taxonomy: Dict[str, List[str]] = self._load_taxonomy(taxonomy_file)
        self._flat_skills: List[str] = [s for group in self.taxonomy.values() for s in group]
        self._lookup = {s.lower(): s for s in self._flat_skills}

    def _load_taxonomy(self, taxonomy_file: Optional[str]) -> Dict[str, List[str]]:
        if taxonomy_file:
            try:
                with open(taxonomy_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Failed to load taxonomy file %s: %s. Using default.", taxonomy_file, e)
        return DEFAULT_TAXONOMY

    def normalize(self, skills: List[str]) -> List[str]:
        """Map a list of raw skill strings to canonical taxonomy names.
        Unrecognized skills are kept as-is (title-cased) for traceability."""
        normalized = []
        seen = set()
        for raw in skills:
            if not raw or not raw.strip():
                continue
            cleaned = raw.strip()
            mapped = self._lookup.get(cleaned.lower())
            if not mapped and HAS_FUZZYWUZZY and self._flat_skills:
                match = fuzzy_process.extractOne(cleaned, self._flat_skills)
                if match and match[1] >= 90:
                    mapped = match[0]
            final = mapped or cleaned
            key = final.lower()
            if key not in seen:
                seen.add(key)
                normalized.append(final)
        return normalized

    def categorize(self, skills: List[str]) -> Dict[str, List[str]]:
        """Group normalized skills into their taxonomy categories."""
        normalized = self.normalize(skills)
        categorized: Dict[str, List[str]] = {cat: [] for cat in self.taxonomy}
        categorized["Uncategorized"] = []
        reverse_lookup = {s: cat for cat, items in self.taxonomy.items() for s in items}
        for skill in normalized:
            cat = reverse_lookup.get(skill, "Uncategorized")
            categorized[cat].append(skill)
        return {k: v for k, v in categorized.items() if v}
