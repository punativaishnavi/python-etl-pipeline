"""Tests for the transform stage."""

import pandas as pd

from src.transform import transform

CFG = {"transform": {"min_price": 0.01,
                     "required_columns": ["id", "title", "price", "category"]}}


def _records():
    return [
        {"id": 1, "title": "Cheap", "price": 10.0, "discountPercentage": 10.0,
         "rating": 4.6, "stock": 5, "brand": "B", "category": "c1"},
        {"id": 2, "title": "Pricy", "price": 600.0, "discountPercentage": 0.0,
         "rating": 3.2, "stock": 2, "brand": "B", "category": "c2"},
        # duplicate id -> dropped
        {"id": 2, "title": "Pricy Copy", "price": 600.0, "discountPercentage": 0.0,
         "rating": 3.2, "stock": 2, "brand": "B", "category": "c2"},
    ]


def test_transform_shape_and_dedup():
    df = transform(_records(), CFG)
    assert len(df) == 2
    assert df["id"].tolist() == [1, 2]


def test_transform_enrichment_math():
    df = transform(_records(), CFG)
    cheap = df[df["id"] == 1].iloc[0]
    assert cheap["discount_amount"] == 1.0
    assert cheap["final_price"] == 9.0
    assert cheap["price_bucket"] == "budget"
    assert cheap["rating_band"] == "excellent"
    assert cheap["revenue_potential"] == 45.0

    pricy = df[df["id"] == 2].iloc[0]
    assert pricy["price_bucket"] == "luxury"
    assert pricy["rating_band"] == "average"


def test_transform_empty_input():
    df = transform([], CFG)
    assert isinstance(df, pd.DataFrame)
    assert df.empty
