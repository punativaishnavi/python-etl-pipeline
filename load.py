"""Load stage: write clean rows to SQLite and rebuild category aggregates."""

import logging
import os
import sqlite3
from datetime import datetime, timezone

import pandas as pd

log = logging.getLogger("etl")

PRODUCT_COLUMNS = [
    "id", "title", "description", "price", "discount_pct", "discount_amount",
    "final_price", "price_bucket", "rating", "rating_band", "stock",
    "revenue_potential", "brand", "category",
]


def _connect(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def load(df: pd.DataFrame, cfg: dict) -> dict:
    """Load products and rebuild the category summary. Returns row counts."""
    load_cfg = cfg["load"]
    db_path = load_cfg["database_path"]
    products_table = load_cfg.get("products_table", "products")
    summary_table = load_cfg.get("summary_table", "category_summary")

    cols = [c for c in PRODUCT_COLUMNS if c in df.columns]
    frame = df[cols].copy()
    frame["loaded_at"] = datetime.now(timezone.utc).isoformat()

    with _connect(db_path) as conn:
        # Full refresh of the products table keeps the demo simple and idempotent.
        frame.to_sql(products_table, conn, if_exists="replace", index=False)

        summary = (
            frame.groupby("category")
            .agg(
                product_count=("id", "count"),
                avg_price=("final_price", "mean"),
                total_revenue=("revenue_potential", "sum"),
                avg_rating=("rating", "mean"),
                total_stock=("stock", "sum"),
            )
            .reset_index()
            .round(2)
        )
        summary.to_sql(summary_table, conn, if_exists="replace", index=False)

    stats = {"products_loaded": len(frame), "categories": len(summary)}
    log.info("Loaded %d products across %d categories into %s",
             stats["products_loaded"], stats["categories"], db_path)
    return stats
