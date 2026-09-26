"""Pipeline orchestrator: extract -> transform -> validate -> load."""

import argparse
import logging
import sys

from .extract import extract
from .load import load
from .transform import transform
from .utils import (
    ensure_dirs,
    load_config,
    read_last_run,
    setup_logging,
    utc_now_iso,
    write_last_run,
)
from .validate import validate

log = logging.getLogger("etl")


def run(config_path: str) -> dict:
    cfg = load_config(config_path)
    setup_logging(cfg.get("pipeline", {}).get("log_level", "INFO"))

    log.info("=== ETL run started (%s) ===", utc_now_iso())

    # Incremental mode: skip if a successful run already exists.
    if cfg.get("pipeline", {}).get("run_mode") == "incremental":
        last = read_last_run(cfg["state"]["path"])
        if last and last.get("status") == "success":
            log.info("Incremental mode: last successful run at %s; skipping",
                     last["last_run_at"])
            return {"status": "skipped", **last}

    # Keep runtime dirs present even on the first run.
    ensure_dirs("data/raw", "data/quarantine", "data/state")

    stats: dict = {}
    try:
        raw = extract(cfg)
        stats["extracted"] = len(raw)

        df = transform(raw, cfg)
        stats["transformed"] = len(df)

        valid, rejected = validate(df, cfg)
        stats["valid"] = len(valid)
        stats["rejected"] = len(rejected)

        load_stats = load(valid, cfg)
        stats.update(load_stats)

        stats["status"] = "success"
        log.info("=== ETL run succeeded: %s ===", stats)
    except Exception as exc:  # noqa: BLE001 - surface any stage failure
        stats["status"] = "failed"
        stats["error"] = str(exc)
        log.exception("=== ETL run failed ===")
        raise
    finally:
        write_last_run(cfg["state"]["path"], stats)

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the e-commerce ETL pipeline.")
    parser.add_argument("--config", default="config/config.yaml",
                        help="Path to the pipeline YAML config")
    args = parser.parse_args()
    try:
        run(args.config)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    main()
