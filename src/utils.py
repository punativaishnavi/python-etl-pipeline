"""Shared helpers: logging, config loading, run-state bookkeeping."""

import json
import logging
import os
from datetime import datetime, timezone

import yaml


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure a console + file logger for the pipeline run."""
    logger = logging.getLogger("etl")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler(f"etl_{datetime.now():%Y%m%d}.log")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    return logger


def load_config(path: str) -> dict:
    """Load the YAML pipeline configuration."""
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def ensure_dirs(*paths: str) -> None:
    for path in paths:
        os.makedirs(path, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_last_run(state_path: str) -> dict | None:
    if os.path.exists(state_path):
        with open(state_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return None


def write_last_run(state_path: str, stats: dict) -> None:
    ensure_dirs(os.path.dirname(state_path))
    payload = {"last_run_at": utc_now_iso(), **stats}
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
