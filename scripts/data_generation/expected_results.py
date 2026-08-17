"""Deterministic Seed-42 validation fixtures and expected results."""

from __future__ import annotations

from .config import ITEM_NUMBER_STEP


EXPECTED_DIRECT_PO_ITEMS = 3

EXPECTED_PARTIAL_PO_LINKS = 2

EXPECTED_PO_LIFECYCLE_STATUSES = {
    "PO-001": "active",
    "PO-002": "active",
    "PO-003": "active",
    "PO-004": "active",
    "PO-005": "blocked",
    "PO-006": "active",
    "PO-007": "active",
    "PO-008": "cancelled",
}

EXPECTED_CANCELLED_PO_ITEM_REFERENCES = {
    ("PO-008", ITEM_NUMBER_STEP),
}

EXPECTED_COUNTS = {
    "vendors": 5,
    "plants": 2,
    "purchasing_groups": 3,
    "material_groups": 4,
    "materials": 12,
    "purchase_requisitions": 10,
    "purchase_requisition_items": 18,
    "purchase_orders": 8,
    "purchase_order_items": 15,
    "goods_receipts": 10,
    "invoices": 4,
    "invoice_items": 5,
    "payments": 5,
    "sap_activate_project_tasks": 12,
    "change_requests": 6,
    "data_quality_issues": 7,
}

EXPECTED_GOODS_RECEIPT_IDS = {f"GR-{index:03d}" for index in range(1, 11)}

EXPECTED_RECEIPT_NUMBERS = {str(5000001000 + index) for index in range(1, 11)}

EXPECTED_ACTIVE_NO_RECEIPT_REFERENCES = {
    ("PO-003", 2 * ITEM_NUMBER_STEP),
    ("PO-004", 2 * ITEM_NUMBER_STEP),
    ("PO-007", ITEM_NUMBER_STEP),
}

EXPECTED_BLOCKED_NO_RECEIPT_REFERENCES = {
    ("PO-005", ITEM_NUMBER_STEP),
    ("PO-005", 2 * ITEM_NUMBER_STEP),
}

EXPECTED_CANCELLED_NO_RECEIPT_REFERENCES = {
    ("PO-008", ITEM_NUMBER_STEP),
}

EXPECTED_ITEM_FULFILLMENT_REFERENCES = {
    "complete": {
        ("PO-001", ITEM_NUMBER_STEP),
        ("PO-001", 2 * ITEM_NUMBER_STEP),
        ("PO-003", ITEM_NUMBER_STEP),
        ("PO-003", 3 * ITEM_NUMBER_STEP),
        ("PO-004", ITEM_NUMBER_STEP),
        ("PO-004", 3 * ITEM_NUMBER_STEP),
        ("PO-006", ITEM_NUMBER_STEP),
    },
    "partial": {
        ("PO-002", ITEM_NUMBER_STEP),
        ("PO-002", 2 * ITEM_NUMBER_STEP),
    },
    "open": EXPECTED_ACTIVE_NO_RECEIPT_REFERENCES,
    None: EXPECTED_BLOCKED_NO_RECEIPT_REFERENCES
    | EXPECTED_CANCELLED_NO_RECEIPT_REFERENCES,
}

EXPECTED_PO_FULFILLMENT_STATUSES = {
    "PO-001": "complete",
    "PO-002": "partial",
    "PO-003": "partial",
    "PO-004": "partial",
    "PO-005": None,
    "PO-006": "complete",
    "PO-007": "open",
    "PO-008": None,
}

EXPECTED_OTIF_REFERENCES = {
    ("PO-001", ITEM_NUMBER_STEP),
    ("PO-003", ITEM_NUMBER_STEP),
    ("PO-004", 3 * ITEM_NUMBER_STEP),
}

EXPECTED_ON_TIME_RECEIPT_IDS = {"GR-001", "GR-002", "GR-005", "GR-006", "GR-009"}

EXPECTED_LATE_RECEIPT_DELAYS = {
    "GR-003": 3,
    "GR-004": 1,
    "GR-007": 2,
    "GR-008": 2,
    "GR-010": 3,
}

EXPECTED_INVOICE_IDS = {f"INV-{index:03d}" for index in range(1, 5)}

EXPECTED_INVOICE_ITEM_IDS = {f"INVI-{index:03d}" for index in range(1, 6)}

EXPECTED_INVOICE_NUMBERS = {
    "INV-001": "ANM-2026-001",
    "INV-002": "BTB-2026-001",
    "INV-003": "EPK-2026-001",
    "INV-004": "RSH-2026-001",
}

EXPECTED_INVOICE_HEADER_DETAILS = {
    "INV-001": (
        "VEN-001",
        "2026-02-28",
        "2026-03-01",
        "2026-03-02",
        "TRY",
        "posted",
    ),
    "INV-002": (
        "VEN-004",
        "2026-02-27",
        "2026-02-28",
        "2026-03-01",
        "TRY",
        "posted",
    ),
    "INV-003": (
        "VEN-003",
        "2026-03-01",
        "2026-03-02",
        "2026-03-03",
        "TRY",
        "posted",
    ),
    "INV-004": (
        "VEN-002",
        "2026-03-08",
        "2026-03-09",
        "2026-03-09",
        "EUR",
        "posted",
    ),
}

EXPECTED_INVOICE_ITEM_REFERENCES = {
    "INVI-001": ("INV-001", ITEM_NUMBER_STEP, "POI-001"),
    "INVI-002": ("INV-001", 2 * ITEM_NUMBER_STEP, "POI-002"),
    "INVI-003": ("INV-002", ITEM_NUMBER_STEP, "POI-005"),
    "INVI-004": ("INV-003", ITEM_NUMBER_STEP, "POI-004"),
    "INVI-005": ("INV-004", ITEM_NUMBER_STEP, "POI-014"),
}

EXPECTED_INVOICE_MATCHING_STATUSES = {
    "INVI-001": "matched",
    "INVI-002": "matched",
    "INVI-003": "price mismatch",
    "INVI-004": "quantity mismatch",
    "INVI-005": "missing goods receipt",
}

EXPECTED_INVOICE_BLOCKING = {
    "INV-001": (0, None),
    "INV-002": (1, "price mismatch"),
    "INV-003": (1, "quantity exceeds eligible posted accepted quantity"),
    "INV-004": (1, "missing eligible posted goods receipt"),
}

EXPECTED_PAYMENT_DETAILS = {
    "PAY-001": (
        "INV-001",
        "2026-03-05",
        None,
        2770.20,
        "bank transfer",
        "failed",
        None,
    ),
    "PAY-002": (
        "INV-001",
        "2026-03-07",
        None,
        2770.20,
        "bank transfer",
        "cancelled",
        None,
    ),
    "PAY-003": (
        "INV-001",
        "2026-03-12",
        "2026-03-12",
        1000.00,
        "bank transfer",
        "paid",
        "CLR-2026-000001",
    ),
    "PAY-004": (
        "INV-001",
        "2026-03-20",
        "2026-03-20",
        1770.20,
        "bank transfer",
        "paid",
        "CLR-2026-000002",
    ),
    "PAY-005": (
        "INV-002",
        "2026-03-04",
        None,
        534.60,
        "bank transfer",
        "on hold",
        None,
    ),
}

EXPECTED_PAYMENT_PROGRESS_ROWS = [
    (
        "INV-001",
        "TRY",
        2770.20,
        "posted",
        0,
        "matched",
        0,
        2770.20,
        0.00,
        2,
        "2026-03-20",
        "paid",
    ),
    (
        "INV-002",
        "TRY",
        534.60,
        "posted",
        1,
        "exception",
        0,
        0.00,
        534.60,
        0,
        None,
        "unpaid",
    ),
    (
        "INV-003",
        "TRY",
        744.40,
        "posted",
        1,
        "exception",
        0,
        0.00,
        744.40,
        0,
        None,
        "unpaid",
    ),
    (
        "INV-004",
        "EUR",
        597.00,
        "posted",
        1,
        "exception",
        0,
        0.00,
        597.00,
        0,
        None,
        "unpaid",
    ),
]

EXPECTED_CHANGE_REQUEST_DETAILS = {
    "CR-001": (
        "TASK-006",
        "explore",
        "Add blocked-invoice drill-down to procurement reporting",
        "reporting",
        "medium",
        "implemented",
        "2026-03-02",
        "2026-03-07",
        "Gives procurement and finance a shared view of mismatch reasons without "
        "changing the transaction model.",
    ),
    "CR-002": (
        "TASK-005",
        "explore",
        "Introduce dual approval for high-value purchase orders",
        "process",
        "high",
        "approved",
        "2026-02-25",
        "2026-03-04",
        "Adds a control requirement to future-state procurement design and leaves "
        "configuration and testing work outstanding.",
    ),
    "CR-003": (
        "TASK-007",
        "realize",
        "Map legacy vendor tax-region codes to target values",
        "data",
        "high",
        "under review",
        "2026-03-25",
        None,
        "Unresolved mapping could delay the vendor master load and downstream "
        "validation.",
    ),
    "CR-004": (
        None,
        "realize",
        "Add supplier invoice status feed to finance integration",
        "integration",
        "medium",
        "deferred",
        "2026-04-09",
        "2026-04-17",
        "Useful for automation but not required for Wave 1 go-live; deferred to "
        "avoid integration scope growth.",
    ),
    "CR-005": (
        "TASK-004",
        "prepare",
        "Expand Wave 1 scope to indirect service procurement",
        "scope",
        "critical",
        "rejected",
        "2026-02-09",
        "2026-02-12",
        "Would increase configuration and testing effort beyond agreed Wave 1 "
        "capacity; rejected to protect the timeline.",
    ),
    "CR-006": (
        "TASK-009",
        "deploy",
        "Add buyer exception-report scenario to UAT",
        "requirement",
        "medium",
        "submitted",
        "2026-05-02",
        None,
        "Adds business validation for blocked invoices and missing-receipt "
        "exceptions before UAT sign-off.",
    ),
}

EXPECTED_DATA_QUALITY_ISSUE_DETAILS = {
    "DQ-001": (
        "Legacy vendor extract is missing the withholding-tax classification "
        "required for VEN-005 migration.",
        "TASK-007",
        "vendor",
        "VEN-005",
        "missing value",
        "high",
        "in progress",
        "2026-03-20",
        None,
        1,
        3.0,
    ),
    "DQ-002": (
        "A duplicate legacy material record was found for MAT-008 and consolidated "
        "into the retained target record.",
        "TASK-007",
        "material",
        "MAT-008",
        "duplicate",
        "medium",
        "resolved",
        "2026-03-22",
        "2026-03-28",
        1,
        2.0,
    ),
    "DQ-003": (
        "The UAT extract carried PO-005 as approved although the deterministic "
        "source record is blocked; the transformation rule was corrected.",
        "TASK-009",
        "purchase order",
        "PO-005",
        "inconsistent status",
        "medium",
        "resolved",
        "2026-04-30",
        "2026-05-04",
        0,
        2.0,
    ),
    "DQ-004": (
        "The UAT invoice extract for INV-004 contains an obsolete PO-item "
        "reference that prevents matching.",
        "TASK-009",
        "invoice",
        "INV-004",
        "invalid reference",
        "critical",
        "open",
        "2026-05-01",
        None,
        0,
        4.0,
    ),
    "DQ-005": (
        "The legacy standard price for MAT-009 differs from the approved target "
        "price; the variance was accepted for the initial load and flagged for "
        "post-load review.",
        "TASK-007",
        "material",
        "MAT-009",
        "pricing issue",
        "high",
        "accepted risk",
        "2026-04-02",
        None,
        1,
        3.0,
    ),
    "DQ-006": (
        "The legacy payment-terms code for VEN-002 had no target mapping; the "
        "mapping was added and retested.",
        "TASK-007",
        "vendor",
        "VEN-002",
        "migration mapping issue",
        "critical",
        "resolved",
        "2026-03-21",
        "2026-04-01",
        1,
        4.0,
    ),
    "DQ-007": (
        "A legacy packaging-dimension field is blank for MAT-004, but the field "
        "was removed from Wave 1 migration scope.",
        "TASK-007",
        "material",
        "MAT-004",
        "missing value",
        "low",
        "cancelled",
        "2026-03-19",
        None,
        1,
        1.0,
    ),
}

EXPECTED_CHANGE_REQUEST_PHASE_SUMMARY_ROWS = [
    ("discover", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    ("prepare", 1, 0, 0, 0, 0, 0, 1, 0, 0, 0),
    ("explore", 2, 0, 0, 1, 1, 0, 0, 0, 1, 1),
    ("realize", 2, 0, 1, 0, 0, 1, 0, 0, 1, 1),
    ("deploy", 1, 1, 0, 0, 0, 0, 0, 0, 1, 0),
    ("run", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
]

EXPECTED_PROJECT_READINESS_ROW = (
    10,
    6,
    60.0,
    6,
    3,
    1,
    6,
    3,
    2,
    0,
    7,
    6,
    1,
    2,
    2,
    1,
    3,
    1,
    1,
    50.0,
    66.7,
    "not ready",
)
