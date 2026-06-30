"""Loads and validates pipeline run configuration from YAML/JSON + CLI overrides."""
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:  # pragma: no cover
    HAS_DOTENV = False

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    csv_input_dir: Optional[str] = None
    resume_input_dir: Optional[str] = None
    output_dir: str = "data/output"
    output_formats: List[str] = field(default_factory=lambda: ["json"])

    column_mapping: Dict[str, str] = field(default_factory=dict)
    skill_taxonomy_file: Optional[str] = None
    company_synonyms_file: Optional[str] = None
    schema_file: Optional[str] = None

    merge_priority: str = "RESUME"
    merge_strategy: Dict[str, str] = field(default_factory=dict)

    projection_spec: Optional[Dict[str, Any]] = None

    parallel: bool = True
    max_workers: int = 4

    verbose: bool = False
    quiet: bool = False
    log_file: str = "logs/pipeline.log"

    validate_only: bool = False
    dry_run: bool = False

    use_ner: bool = False
    ner_model: Optional[str] = None

    @classmethod
    def load(cls, config_path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> "PipelineConfig":
        if HAS_DOTENV:
            load_dotenv()

        env_defaults = cls._load_env_defaults()
        effective_config_path = config_path or os.getenv("PIPELINE_CONFIG_PATH")

        data: Dict[str, Any] = dict(env_defaults)
        if effective_config_path:
            data.update(cls._load_file(effective_config_path))
        cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        if overrides:
            for k, v in overrides.items():
                if v is not None and hasattr(cfg, k):
                    setattr(cfg, k, v)
        return cfg

    @staticmethod
    def _load_env_defaults() -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        if os.getenv("LOG_FILE"):
            data["log_file"] = os.getenv("LOG_FILE")
        if os.getenv("LOG_LEVEL"):
            level = os.getenv("LOG_LEVEL", "").upper()
            data["verbose"] = level == "DEBUG"
            data["quiet"] = level in {"ERROR", "CRITICAL"}
        if os.getenv("RESUME_USE_NER"):
            data["use_ner"] = os.getenv("RESUME_USE_NER", "").lower() in {"1", "true", "yes", "on"}
        if os.getenv("RESUME_NER_MODEL"):
            data["ner_model"] = os.getenv("RESUME_NER_MODEL")
        return data

    @staticmethod
    def _load_file(config_path: str) -> Dict[str, Any]:
        path = Path(config_path)
        if not path.exists():
            logger.warning("Config file not found: %s. Using defaults.", config_path)
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix in (".yaml", ".yml"):
                    return yaml.safe_load(f) or {}
                if path.suffix == ".json":
                    return json.load(f)
        except Exception as e:
            logger.error("Failed to load config %s: %s", config_path, e)
        return {}
