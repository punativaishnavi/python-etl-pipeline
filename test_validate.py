"""Tests for the validate stage."""

import pandas as pd

from src.validate import validate

CFG = {
    "transform": {"min_price": 0.01,
                  "required_columns": ["id", "title", "price", "category"]},
    "validate": {"fail_on_error": False,
                 "quarantine_path": "/tmp/test_quarantine.csv"},
}


def _frame():
    return pd.DataFrame([
        {"id": 1, "title": "Good", "price": 10.0, "discount_pct": 5.0,
         "stock": 3, "category": "c1"},
        {"id": 2, "title": "Bad price", "price": -4.0, "discount_pct": 0.0,
         "stock": 3, "category": "c1"},
        {"id": 3, "title": "Bad stock", "price": 10.0, "discount_pct": 0.0,
         "stock": -1, "category": "c1"},
        {"id": 4, "title": "Bad discount", "price": 10.0, "discount_pct": 150.0,
         "stock": 3, "category": "c1"},
        {"id": 5, "title": "Missing category", "price": 10.0, "discount_pct": 0.0,
         "stock": 3, "category": None},
    ])


def test_validate_splits_valid_and_rejected():
    valid, rejected = validate(_frame(), CFG)
    assert valid["id"].tolist() == [1]
    assert sorted(rejected["id"].tolist()) == [2, 3, 4, 5]


def test_validate_rejection_reasons():
    _, rejected = validate(_frame(), CFG)
    reasons = dict(zip(rejected["id"], rejected["rejection_reason"]))
    assert reasons[2] == "invalid_price"
    assert reasons[3] == "invalid_stock"
    assert reasons[4] == "invalid_discount"
    assert reasons[5] == "missing_required_field"


def test_validate_fail_on_error_raises():
    strict = {**CFG, "validate": {**CFG["validate"], "fail_on_error": True}}
    try:
        validate(_frame(), strict)
    except ValueError as exc:
        assert "failed validation" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")
