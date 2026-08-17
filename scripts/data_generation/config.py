"""Shared immutable configuration for data generation and validation."""

from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


DEFAULT_SEED = 42

DEFAULT_DB_PATH = Path("database") / "marmara_components.db"

ITEM_NUMBER_STEP = 10

FLOAT_TOLERANCE = 0.000001

REPORTING_DATE = "2026-03-31"

PO_NUMBER_PREFIX = 4500001000

PR_PRICE_VARIATION_RANGE = (0.95, 1.07)

PO_PRICE_VARIATION_RANGE = (0.98, 1.04)

VENDOR_COMPATIBILITY_RULES = {
    "raw material supplier": {
        "material_group_ids": ("MG-001",),
        "material_types": ("raw material",),
    },
    "packaging supplier": {
        "material_group_ids": ("MG-002",),
        "material_types": ("packaging",),
    },
    "mro supplier": {
        "material_group_ids": ("MG-003", "MG-004"),
        "material_types": ("spare part", "consumable", "service"),
    },
    "service supplier": {
        "material_group_ids": ("MG-004",),
        "material_types": ("service", "consumable"),
    },
}

PURCHASING_GROUP_BY_MATERIAL_TYPE = {
    "raw material": "PG-001",
    "packaging": "PG-002",
    "spare part": "PG-003",
    "consumable": "PG-003",
    "service": "PG-003",
}

VENDOR_COUNTRY_CURRENCY = {
    "Turkiye": "TRY",
    "Germany": "EUR",
    "Italy": "EUR",
}

PO_VENDOR_PRICE_FACTORS = {
    "VEN-001": 0.99,
    "VEN-002": 1.03,
    "VEN-003": 0.97,
    "VEN-004": 1.01,
    "VEN-005": 1.08,
}
