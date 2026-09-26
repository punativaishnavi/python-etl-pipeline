"""Transform stage: normalize, clean, and enrich raw product records."""

import logging

import pandas as pd

log = logging.getLogger("etl")

# Columns we keep from the raw payload -> warehouse-friendly names.
COLUMN_MAP = {
    "id": "id",
    "title": "title",
    "description": "description",
    "price": "price",
    "discountPercentage": "discount_pct",
    "rating": "rating",
    "stock": "stock",
    "brand": "brand",
    "category": "category",
}


def _price_bucket(price: float) -> str:
    if price < 25:
        return "budget"
    if price < 100:
        return "mid-range"
    if price < 500:
        return "premium"
    return "luxury"


def _rating_band(rating: float) -> str:
    if rating >= 4.5:
        return "excellent"
    if rating >= 4.0:
        return "good"
    if rating >= 3.0:
        return "average"
    return "poor"


def transform(records: list[dict], cfg: dict) -> pd.DataFrame:
    """Normalize raw records into a clean, enriched DataFrame."""
    if not records:
        log.warning("No records to transform; returning empty frame")
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # 1. Keep + rename the columns we care about (ignore anything unexpected).
    keep = [c for c in COLUMN_MAP if c in df.columns]
    df = df[keep].rename(columns=COLUMN_MAP)

    # 2. Coerce numeric types; junk becomes NaN so validation can quarantine it.
    for col in ["price", "discount_pct", "rating", "stock"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 3. Fill text gaps with sensible defaults.
    for col in ["brand", "description"]:
        if col in df.columns:
            df[col] = df[col].fillna("unknown")

    # 4. Drop exact-duplicate product ids, keeping the first occurrence.
    before = len(df)
    df = df.drop_duplicates(subset=["id"], keep="first")
    if len(df) < before:
        log.info("Dropped %d duplicate product id(s)", before - len(df))

    # 5. Enrich.
    df["discount_amount"] = (df["price"] * df["discount_pct"] / 100).round(2)
    df["final_price"] = (df["price"] - df["discount_amount"]).round(2)
    df["price_bucket"] = df["price"].apply(_price_bucket)
    df["rating_band"] = df["rating"].fillna(0).apply(_rating_band)
    df["revenue_potential"] = (df["final_price"] * df["stock"]).round(2)

    log.info("Transformed %d rows x %d columns", *df.shape)
    return df.reset_index(drop=True)
