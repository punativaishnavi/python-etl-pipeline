"""Extract stage: pull raw product records from the API or a local sample file."""

import json
import logging
import os
import time
from datetime import datetime

import requests

log = logging.getLogger("etl")


def _fetch_with_retries(url: str, params: dict, timeout: int, retries: int) -> dict:
    """GET with simple exponential backoff."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:  # noqa: BLE001 - retry on any transport error
            last_err = exc
            wait = 2 ** attempt
            log.warning("Extract attempt %d/%d failed (%s); retrying in %ds",
                        attempt, retries, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"Extract failed after {retries} attempts: {last_err}")


def _snapshot_raw(records: list[dict], snapshot_dir: str) -> str:
    os.makedirs(snapshot_dir, exist_ok=True)
    path = os.path.join(snapshot_dir, f"raw_products_{datetime.now():%Y%m%d_%H%M%S}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2)
    return path


def extract(cfg: dict) -> list[dict]:
    """Return a list of raw product dicts from the configured source."""
    ex = cfg["extract"]
    source = ex.get("source", "api")

    if source == "api":
        log.info("Extracting from API: %s (limit=%s)", ex["api_url"], ex["limit"])
        payload = _fetch_with_retries(
            ex["api_url"],
            params={"limit": ex["limit"]},
            timeout=ex.get("timeout_seconds", 30),
            retries=ex.get("retries", 3),
        )
        records = payload.get("products", [])
    elif source == "sample":
        path = ex["sample_path"]
        log.info("Extracting from sample file: %s", path)
        with open(path, "r", encoding="utf-8") as fh:
            records = json.load(fh)
        if ex.get("limit"):
            records = records[: ex["limit"]]
    else:
        raise ValueError(f"Unknown extract source: {source!r} (expected 'api' or 'sample')")

    log.info("Extracted %d raw records", len(records))
    snapshot = _snapshot_raw(records, ex.get("raw_snapshot_dir", "data/raw"))
    log.info("Raw snapshot written to %s", snapshot)
    return records
