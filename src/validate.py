"""Validate stage: data-quality gate. Bad rows are quarantined, never dropped silently."""

import logging
import os

import pandas as pd

log = logging.getLogger("etl")


def _check_required(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    missing = pd.Series(False, index=df.index)
    for col in columns:
        if col in df.columns:
            missing = missing | df[col].isna()
        else:
            missing = missing | True
    return missing


def validate(df: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split the frame into (valid, rejected). Rejected rows carry a
    `rejection_reason` column and are written to the quarantine CSV.
    """
    tr_cfg = cfg.get("transform", {})
    required = tr_cfg.get("required_columns", ["id", "title", "price", "category"])
    min_price = tr_cfg.get("min_price", 0.01)

    reasons = pd.Series("", index=df.index)

    def flag(mask: pd.Series, reason: str) -> None:
        reasons[mask & (reasons == "")] = reason

    flag(_check_required(df, required), "missing_required_field")
    if "price" in df.columns:
        flag(df["price"].isna() | (df["price"] <= min_price), "invalid_price")
    if "stock" in df.columns:
        flag(df["stock"].isna() | (df["stock"] < 0), "invalid_stock")
    if "discount_pct" in df.columns:
        flag(df["discount_pct"].isna()
             | (df["discount_pct"] < 0)
             | (df["discount_pct"] > 100), "invalid_discount")

    bad = reasons != ""
    rejected = df[bad].copy()
    if not rejected.empty:
        rejected["rejection_reason"] = reasons[bad]
    valid = df[~bad].copy().reset_index(drop=True)

    log.info("Validation: %d valid, %d rejected", len(valid), len(rejected))

    if not rejected.empty:
        qpath = cfg["validate"]["quarantine_path"]
        os.makedirs(os.path.dirname(qpath), exist_ok=True)
        rejected.to_csv(qpath, index=False)
        log.info("Quarantined %d row(s) to %s", len(rejected), qpath)
        if cfg["validate"].get("fail_on_error"):
            raise ValueError(f"{len(rejected)} row(s) failed validation; aborting (fail_on_error=true)")

    return valid, rejected
