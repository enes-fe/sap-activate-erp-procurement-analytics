"""Generate synthetic master, SAP Activate, and procurement transaction data."""

from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from faker import Faker


DEFAULT_SEED = 42
DEFAULT_DB_PATH = Path("database") / "marmara_components.db"
ITEM_NUMBER_STEP = 10
FLOAT_TOLERANCE = 0.000001
REPORTING_DATE = "2026-03-31"
EXPECTED_DIRECT_PO_ITEMS = 3
EXPECTED_PARTIAL_PO_LINKS = 2
PO_NUMBER_PREFIX = 4500001000
PR_PRICE_VARIATION_RANGE = (0.95, 1.07)
PO_PRICE_VARIATION_RANGE = (0.98, 1.04)

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
    "sap_activate_project_tasks": 12,
}

DOWNSTREAM_EMPTY_TABLES = (
    "invoices",
    "invoice_items",
    "payments",
    "change_requests",
    "data_quality_issues",
)

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


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return repository_root() / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the synthetic ERP procurement SQLite dataset."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"SQLite database path, relative to the repo root by default ({DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic random seed (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete an existing database before regenerating it.",
    )
    return parser.parse_args()


def prepare_database_path(db_path: Path, reset: bool) -> None:
    if db_path.exists():
        if not reset:
            raise SystemExit(
                f"Database already exists at {db_path}. Re-run with --reset to recreate it."
            )
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)


def create_generators(seed: int) -> tuple[random.Random, Faker]:
    random.seed(seed)
    rng = random.Random(seed)
    fake = Faker("tr_TR")
    fake.seed_instance(seed)
    return rng, fake


def iso_date(value: date) -> str:
    return value.isoformat()


def offset_date(start: date, days: int) -> str:
    return iso_date(start + timedelta(days=days))


def price_from_standard(
    material: dict[str, object],
    rng: random.Random,
    variation_range: tuple[float, float],
) -> float:
    standard_price = material["standard_price"]
    if standard_price is None:
        raise ValueError(f"Material {material['material_id']} has no standard price")
    low, high = variation_range
    return round(float(standard_price) * rng.uniform(low, high), 2)


def po_unit_price(
    material: dict[str, object], vendor: dict[str, object], rng: random.Random
) -> float:
    vendor_id = str(vendor["vendor_id"])
    factor = PO_VENDOR_PRICE_FACTORS[vendor_id]
    return round(price_from_standard(material, rng, PO_PRICE_VARIATION_RANGE) * factor, 2)


def currency_for_vendor(vendor: dict[str, object]) -> str:
    country = str(vendor["country"])
    if country not in VENDOR_COUNTRY_CURRENCY:
        raise ValueError(f"No currency rule configured for vendor country {country}")
    return VENDOR_COUNTRY_CURRENCY[country]


def material_matches_vendor_category(
    vendor_category: str, material_group_id: str, material_type: str
) -> bool:
    rule = VENDOR_COMPATIBILITY_RULES.get(vendor_category)
    if rule is None:
        return False
    return (
        material_group_id in rule["material_group_ids"]
        or material_type in rule["material_types"]
    )


def price_bounds(
    standard_price: object,
    variation_range: tuple[float, float],
    factor: float = 1.0,
) -> tuple[float, float]:
    low, high = variation_range
    reference_price = float(standard_price)
    rounding_tolerance = 0.02
    return (
        round(reference_price * low * factor, 2) - rounding_tolerance,
        round(reference_price * high * factor, 2) + rounding_tolerance,
    )


def generate_vendors(rng: random.Random) -> list[dict[str, object]]:
    base_date = date(2024, 10, 1)
    vendor_specs = [
        (
            "VEN-001",
            "Anadolu Metal Sanayi A.S.",
            "Turkiye",
            "raw material supplier",
            "Net 30",
            1,
            "active",
        ),
        (
            "VEN-002",
            "Ruhr Stahlhandel GmbH",
            "Germany",
            "raw material supplier",
            "Net 45",
            1,
            "active",
        ),
        (
            "VEN-003",
            "Ege Packaging A.S.",
            "Turkiye",
            "packaging supplier",
            "Net 30",
            0,
            "active",
        ),
        (
            "VEN-004",
            "Bursa Teknik Bakim Ltd.",
            "Turkiye",
            "mro supplier",
            "Net 15",
            0,
            "active",
        ),
        (
            "VEN-005",
            "Lombardia Industrial Services S.r.l.",
            "Italy",
            "service supplier",
            "Net 60",
            0,
            "pending review",
        ),
    ]

    vendors = []
    for spec in vendor_specs:
        (
            vendor_id,
            vendor_name,
            country,
            vendor_category,
            payment_terms,
            preferred_vendor_flag,
            vendor_status,
        ) = spec
        vendors.append(
            {
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "country": country,
                "vendor_category": vendor_category,
                "payment_terms": payment_terms,
                "preferred_vendor_flag": preferred_vendor_flag,
                "vendor_status": vendor_status,
                "created_date": offset_date(base_date, rng.randint(0, 90)),
            }
        )
    return vendors


def generate_plants() -> list[dict[str, object]]:
    return [
        {
            "plant_id": "PL-001",
            "plant_name": "Marmara Components Gebze Manufacturing Plant",
            "city": "Gebze",
            "country": "Turkiye",
            "plant_type": "manufacturing",
            "plant_status": "active",
        },
        {
            "plant_id": "PL-002",
            "plant_name": "Marmara Components Bursa Distribution Center",
            "city": "Bursa",
            "country": "Turkiye",
            "plant_type": "distribution",
            "plant_status": "active",
        },
    ]


def generate_purchasing_groups(fake: Faker) -> list[dict[str, object]]:
    return [
        {
            "purchasing_group_id": "PG-001",
            "purchasing_group_name": "Direct Materials Sourcing",
            "manager_name": fake.name(),
            "process_area": "direct materials",
            "status": "active",
        },
        {
            "purchasing_group_id": "PG-002",
            "purchasing_group_name": "Indirect Materials and Packaging",
            "manager_name": fake.name(),
            "process_area": "indirect materials",
            "status": "active",
        },
        {
            "purchasing_group_id": "PG-003",
            "purchasing_group_name": "MRO and Plant Services",
            "manager_name": fake.name(),
            "process_area": "mro",
            "status": "active",
        },
    ]


def generate_material_groups() -> list[dict[str, object]]:
    return [
        {
            "material_group_id": "MG-001",
            "material_group_name": "Metals and Raw Materials",
            "category_owner": "Direct Materials Lead",
            "spend_category": "Direct Materials",
            "status": "active",
        },
        {
            "material_group_id": "MG-002",
            "material_group_name": "Packaging Materials",
            "category_owner": "Packaging Lead",
            "spend_category": "Indirect Materials",
            "status": "active",
        },
        {
            "material_group_id": "MG-003",
            "material_group_name": "MRO Spare Parts",
            "category_owner": "Maintenance Lead",
            "spend_category": "MRO",
            "status": "active",
        },
        {
            "material_group_id": "MG-004",
            "material_group_name": "Plant Consumables and Services",
            "category_owner": "Operations Lead",
            "spend_category": "Services and Consumables",
            "status": "active",
        },
    ]


def generate_materials() -> list[dict[str, object]]:
    material_specs = [
        ("MAT-001", "MG-001", "Cold Rolled Steel Coil", "KG", "raw material", 1.15),
        ("MAT-002", "MG-001", "Aluminum Extrusion Bar", "KG", "raw material", 3.85),
        ("MAT-003", "MG-001", "Copper Busbar", "KG", "raw material", 8.75),
        ("MAT-004", "MG-002", "Corrugated Export Carton", "EA", "packaging", 1.2),
        ("MAT-005", "MG-002", "Stretch Film Roll", "EA", "packaging", 18.5),
        ("MAT-006", "MG-002", "Wooden Export Pallet", "EA", "packaging", 14.75),
        ("MAT-007", "MG-003", "Hydraulic Seal Kit", "EA", "spare part", 42.0),
        ("MAT-008", "MG-003", "CNC Spindle Bearing", "EA", "spare part", 185.0),
        ("MAT-009", "MG-003", "Conveyor Motor Assembly", "EA", "spare part", 420.0),
        ("MAT-010", "MG-004", "Cutting Fluid Concentrate", "L", "consumable", 4.9),
        ("MAT-011", "MG-004", "Industrial Safety Gloves", "EA", "consumable", 6.5),
        ("MAT-012", "MG-004", "Preventive Maintenance Service", "HR", "service", 55.0),
    ]
    return [
        {
            "material_id": material_id,
            "material_group_id": material_group_id,
            "material_name": material_name,
            "base_unit_of_measure": unit,
            "material_type": material_type,
            "standard_price": standard_price,
            "material_status": "active",
        }
        for (
            material_id,
            material_group_id,
            material_name,
            unit,
            material_type,
            standard_price,
        ) in material_specs
    ]


def generate_purchase_requisitions_and_items(
    rng: random.Random, materials: list[dict[str, object]]
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    materials_by_id = {str(material["material_id"]): material for material in materials}
    pr_specs = [
        {
            "pr_id": "PR-001",
            "plant_id": "PL-001",
            "requester_name": "Production Planning",
            "requisition_date": date(2026, 2, 2),
            "approval_date": date(2026, 2, 4),
            "pr_status": "converted",
            "business_reason": "Steel and aluminum demand for March production schedule.",
            "items": [
                ("MAT-001", 1000.0, 18, "converted"),
                ("MAT-002", 420.0, 20, "converted"),
            ],
        },
        {
            "pr_id": "PR-002",
            "plant_id": "PL-001",
            "requester_name": "Warehouse Operations",
            "requisition_date": date(2026, 2, 5),
            "approval_date": date(2026, 2, 7),
            "pr_status": "converted",
            "business_reason": "Export packing material replenishment for finished goods shipments.",
            "items": [
                ("MAT-004", 800.0, 15, "converted"),
                ("MAT-005", 40.0, 18, "converted"),
            ],
        },
        {
            "pr_id": "PR-003",
            "plant_id": "PL-002",
            "requester_name": "Maintenance Department",
            "requisition_date": date(2026, 2, 7),
            "approval_date": date(2026, 2, 10),
            "pr_status": "converted",
            "business_reason": "Critical maintenance spares and cutting fluid for Bursa operations.",
            "items": [
                ("MAT-007", 12.0, 17, "converted"),
                ("MAT-008", 4.0, 25, "converted"),
                ("MAT-010", 120.0, 20, "converted"),
            ],
        },
        {
            "pr_id": "PR-004",
            "plant_id": "PL-001",
            "requester_name": "Production Planning",
            "requisition_date": date(2026, 2, 12),
            "approval_date": date(2026, 2, 14),
            "pr_status": "converted",
            "business_reason": "Additional metal supply for confirmed customer orders.",
            "items": [
                ("MAT-001", 650.0, 18, "converted"),
                ("MAT-003", 180.0, 25, "converted"),
                ("MAT-002", 300.0, 20, "converted"),
            ],
        },
        {
            "pr_id": "PR-005",
            "plant_id": "PL-002",
            "requester_name": "Warehouse Operations",
            "requisition_date": date(2026, 2, 15),
            "approval_date": date(2026, 2, 17),
            "pr_status": "approved",
            "business_reason": "Packaging and safety stock coverage for distribution peaks.",
            "items": [
                ("MAT-006", 50.0, 20, "partially converted"),
                ("MAT-011", 60.0, 14, "approved"),
            ],
        },
        {
            "pr_id": "PR-006",
            "plant_id": "PL-001",
            "requester_name": "Maintenance Department",
            "requisition_date": date(2026, 2, 18),
            "approval_date": date(2026, 2, 20),
            "pr_status": "approved",
            "business_reason": "Conveyor motor standby requirement for planned maintenance window.",
            "items": [
                ("MAT-009", 2.0, 16, "approved"),
            ],
        },
        {
            "pr_id": "PR-007",
            "plant_id": "PL-001",
            "requester_name": "Procurement Operations",
            "requisition_date": date(2026, 2, 21),
            "approval_date": None,
            "pr_status": "submitted",
            "business_reason": "Cutting fluid replenishment awaiting buyer review.",
            "items": [
                ("MAT-010", 200.0, 20, "open"),
            ],
        },
        {
            "pr_id": "PR-008",
            "plant_id": "PL-002",
            "requester_name": "Warehouse Operations",
            "requisition_date": date(2026, 2, 23),
            "approval_date": None,
            "pr_status": "draft",
            "business_reason": "Draft request for carton demand not yet released.",
            "items": [
                ("MAT-004", 250.0, 18, "open"),
            ],
        },
        {
            "pr_id": "PR-009",
            "plant_id": "PL-001",
            "requester_name": "Quality Management",
            "requisition_date": date(2026, 2, 24),
            "approval_date": None,
            "pr_status": "rejected",
            "business_reason": "Request rejected after review of forecast and service budget.",
            "items": [
                ("MAT-003", 75.0, 21, "rejected"),
                ("MAT-012", 16.0, 30, "rejected"),
            ],
        },
        {
            "pr_id": "PR-010",
            "plant_id": "PL-002",
            "requester_name": "Warehouse Operations",
            "requisition_date": date(2026, 2, 25),
            "approval_date": None,
            "pr_status": "cancelled",
            "business_reason": "Stretch film request cancelled after inventory recount.",
            "items": [
                ("MAT-005", 20.0, 17, "cancelled"),
            ],
        },
    ]

    purchase_requisitions = []
    purchase_requisition_items = []
    pr_item_counter = 1
    for spec in pr_specs:
        requisition_date = spec["requisition_date"]
        approval_date = spec["approval_date"]
        purchase_requisitions.append(
            {
                "pr_id": spec["pr_id"],
                "plant_id": spec["plant_id"],
                "requester_name": spec["requester_name"],
                "requisition_date": iso_date(requisition_date),
                "approval_date": iso_date(approval_date) if approval_date else None,
                "pr_status": spec["pr_status"],
                "business_reason": spec["business_reason"],
            }
        )

        for item_index, item_spec in enumerate(spec["items"], start=1):
            material_id, quantity, delivery_offset, item_status = item_spec
            material = materials_by_id[material_id]
            purchase_requisition_items.append(
                {
                    "pr_item_id": f"PRI-{pr_item_counter:03d}",
                    "pr_id": spec["pr_id"],
                    "pr_item_number": item_index * ITEM_NUMBER_STEP,
                    "material_id": material_id,
                    "requested_quantity": quantity,
                    "requested_unit_price": price_from_standard(
                        material, rng, PR_PRICE_VARIATION_RANGE
                    ),
                    "requested_delivery_date": offset_date(
                        requisition_date, delivery_offset
                    ),
                    "pr_item_status": item_status,
                }
            )
            pr_item_counter += 1

    return purchase_requisitions, purchase_requisition_items


def generate_purchase_orders_and_items(
    rng: random.Random,
    vendors: list[dict[str, object]],
    materials: list[dict[str, object]],
    purchase_requisitions: list[dict[str, object]],
    purchase_requisition_items: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    vendors_by_id = {str(vendor["vendor_id"]): vendor for vendor in vendors}
    materials_by_id = {str(material["material_id"]): material for material in materials}
    prs_by_id = {str(pr["pr_id"]): pr for pr in purchase_requisitions}
    pr_items_by_reference = {
        (str(pr_item["pr_id"]), int(pr_item["pr_item_number"])): pr_item
        for pr_item in purchase_requisition_items
    }

    po_specs = [
        {
            "po_id": "PO-001",
            "vendor_id": "VEN-001",
            "plant_id": "PL-001",
            "purchasing_group_id": "PG-001",
            "po_created_date": date(2026, 2, 5),
            "po_approval_date": date(2026, 2, 6),
            "po_lifecycle_status": "active",
            "items": [
                {"pr_ref": ("PR-001", ITEM_NUMBER_STEP), "ordered_quantity": 1000.0, "planned_delivery_date": date(2026, 2, 21)},
                {"pr_ref": ("PR-001", 2 * ITEM_NUMBER_STEP), "ordered_quantity": 420.0, "planned_delivery_date": date(2026, 2, 24)},
            ],
        },
        {
            "po_id": "PO-002",
            "vendor_id": "VEN-003",
            "plant_id": "PL-001",
            "purchasing_group_id": "PG-002",
            "po_created_date": date(2026, 2, 8),
            "po_approval_date": date(2026, 2, 9),
            "po_lifecycle_status": "active",
            "items": [
                {"pr_ref": ("PR-002", ITEM_NUMBER_STEP), "ordered_quantity": 800.0, "planned_delivery_date": date(2026, 2, 25)},
                {"pr_ref": ("PR-002", 2 * ITEM_NUMBER_STEP), "ordered_quantity": 40.0, "planned_delivery_date": date(2026, 2, 28)},
            ],
        },
        {
            "po_id": "PO-003",
            "vendor_id": "VEN-004",
            "plant_id": "PL-002",
            "purchasing_group_id": "PG-003",
            "po_created_date": date(2026, 2, 11),
            "po_approval_date": date(2026, 2, 12),
            "po_lifecycle_status": "active",
            "items": [
                {"pr_ref": ("PR-003", ITEM_NUMBER_STEP), "ordered_quantity": 12.0, "planned_delivery_date": date(2026, 2, 26)},
                {"pr_ref": ("PR-003", 2 * ITEM_NUMBER_STEP), "ordered_quantity": 4.0, "planned_delivery_date": date(2026, 3, 3)},
                {"pr_ref": ("PR-003", 3 * ITEM_NUMBER_STEP), "ordered_quantity": 120.0, "planned_delivery_date": date(2026, 2, 28)},
            ],
        },
        {
            "po_id": "PO-004",
            "vendor_id": "VEN-002",
            "plant_id": "PL-001",
            "purchasing_group_id": "PG-001",
            "po_created_date": date(2026, 2, 15),
            "po_approval_date": date(2026, 2, 17),
            "po_lifecycle_status": "active",
            "items": [
                {"pr_ref": ("PR-004", ITEM_NUMBER_STEP), "ordered_quantity": 650.0, "planned_delivery_date": date(2026, 3, 3)},
                {"pr_ref": ("PR-004", 2 * ITEM_NUMBER_STEP), "ordered_quantity": 180.0, "planned_delivery_date": date(2026, 3, 10)},
                {"pr_ref": ("PR-004", 3 * ITEM_NUMBER_STEP), "ordered_quantity": 300.0, "planned_delivery_date": date(2026, 3, 6)},
            ],
        },
        {
            "po_id": "PO-005",
            "vendor_id": "VEN-003",
            "plant_id": "PL-002",
            "purchasing_group_id": "PG-002",
            "po_created_date": date(2026, 2, 18),
            "po_approval_date": None,
            "po_lifecycle_status": "blocked",
            "items": [
                {"pr_ref": ("PR-005", ITEM_NUMBER_STEP), "ordered_quantity": 20.0, "planned_delivery_date": date(2026, 3, 1)},
                {"pr_ref": ("PR-005", ITEM_NUMBER_STEP), "ordered_quantity": 15.0, "planned_delivery_date": date(2026, 3, 8)},
            ],
        },
        {
            "po_id": "PO-006",
            "vendor_id": "VEN-004",
            "plant_id": "PL-001",
            "purchasing_group_id": "PG-003",
            "po_created_date": date(2026, 2, 19),
            "po_approval_date": date(2026, 2, 20),
            "po_lifecycle_status": "active",
            "items": [
                {"material_id": "MAT-009", "ordered_quantity": 1.0, "planned_delivery_date": date(2026, 3, 6)},
            ],
        },
        {
            "po_id": "PO-007",
            "vendor_id": "VEN-002",
            "plant_id": "PL-002",
            "purchasing_group_id": "PG-001",
            "po_created_date": date(2026, 2, 22),
            "po_approval_date": date(2026, 2, 23),
            "po_lifecycle_status": "active",
            "items": [
                {"material_id": "MAT-002", "ordered_quantity": 150.0, "planned_delivery_date": date(2026, 3, 7)},
            ],
        },
        {
            "po_id": "PO-008",
            "vendor_id": "VEN-005",
            "plant_id": "PL-001",
            "purchasing_group_id": "PG-003",
            "po_created_date": date(2026, 2, 24),
            "po_approval_date": None,
            "po_lifecycle_status": "cancelled",
            "items": [
                {"material_id": "MAT-012", "ordered_quantity": 8.0, "planned_delivery_date": date(2026, 3, 10), "po_item_lifecycle_status": "cancelled"},
            ],
        },
    ]

    purchase_orders = []
    purchase_order_items = []
    po_item_counter = 1
    for po_index, spec in enumerate(po_specs, start=1):
        vendor = vendors_by_id[spec["vendor_id"]]
        purchase_orders.append(
            {
                "po_id": spec["po_id"],
                "vendor_id": spec["vendor_id"],
                "plant_id": spec["plant_id"],
                "purchasing_group_id": spec["purchasing_group_id"],
                "po_number": str(PO_NUMBER_PREFIX + po_index),
                "po_created_date": iso_date(spec["po_created_date"]),
                "po_approval_date": (
                    iso_date(spec["po_approval_date"])
                    if spec["po_approval_date"]
                    else None
                ),
                "document_currency": currency_for_vendor(vendor),
                "po_lifecycle_status": spec["po_lifecycle_status"],
            }
        )

        for item_index, item_spec in enumerate(spec["items"], start=1):
            pr_ref = item_spec.get("pr_ref")
            if pr_ref:
                source_pr_item = pr_items_by_reference[pr_ref]
                source_pr = prs_by_id[source_pr_item["pr_id"]]
                pr_item_id = str(source_pr_item["pr_item_id"])
                material_id = str(source_pr_item["material_id"])
                plant_id = str(source_pr["plant_id"])
                if plant_id != spec["plant_id"]:
                    raise ValueError(
                        f"PO {spec['po_id']} plant does not match linked PR {source_pr['pr_id']}"
                    )
            else:
                pr_item_id = None
                material_id = str(item_spec["material_id"])

            material = materials_by_id[material_id]
            unit_price = po_unit_price(material, vendor, rng)
            ordered_quantity = float(item_spec["ordered_quantity"])
            purchase_order_items.append(
                {
                    "po_item_id": f"POI-{po_item_counter:03d}",
                    "po_id": spec["po_id"],
                    "material_id": material_id,
                    "pr_item_id": pr_item_id,
                    "po_item_number": item_index * ITEM_NUMBER_STEP,
                    "ordered_quantity": ordered_quantity,
                    "unit_price": unit_price,
                    "net_value": round(ordered_quantity * unit_price, 2),
                    "planned_delivery_date": iso_date(item_spec["planned_delivery_date"]),
                    "po_item_lifecycle_status": item_spec.get(
                        "po_item_lifecycle_status", "active"
                    ),
                }
            )
            po_item_counter += 1

    return purchase_orders, purchase_order_items


def generate_goods_receipts(
    purchase_orders: list[dict[str, object]],
    purchase_order_items: list[dict[str, object]],
) -> list[dict[str, object]]:
    purchase_orders_by_id = {
        str(purchase_order["po_id"]): purchase_order
        for purchase_order in purchase_orders
    }
    po_items_by_reference: dict[tuple[str, int], dict[str, object]] = {}
    for po_item in purchase_order_items:
        reference = (str(po_item["po_id"]), int(po_item["po_item_number"]))
        if reference in po_items_by_reference:
            raise ValueError(f"Duplicate PO item business key: {reference}")
        po_items_by_reference[reference] = po_item

    receipt_specs = [
        {
            "goods_receipt_id": "GR-001",
            "receipt_number": "5000001001",
            "po_item_ref": ("PO-001", ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 2, 21),
            "received_quantity": 1000.0,
            "accepted_quantity": 1000.0,
            "rejected_quantity": 0.0,
        },
        {
            "goods_receipt_id": "GR-002",
            "receipt_number": "5000001002",
            "po_item_ref": ("PO-001", 2 * ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 2, 24),
            "received_quantity": 200.0,
            "accepted_quantity": 200.0,
            "rejected_quantity": 0.0,
        },
        {
            "goods_receipt_id": "GR-003",
            "receipt_number": "5000001003",
            "po_item_ref": ("PO-001", 2 * ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 2, 27),
            "received_quantity": 220.0,
            "accepted_quantity": 220.0,
            "rejected_quantity": 0.0,
        },
        {
            "goods_receipt_id": "GR-004",
            "receipt_number": "5000001004",
            "po_item_ref": ("PO-002", ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 2, 26),
            "received_quantity": 500.0,
            "accepted_quantity": 500.0,
            "rejected_quantity": 0.0,
        },
        {
            "goods_receipt_id": "GR-005",
            "receipt_number": "5000001005",
            "po_item_ref": ("PO-002", 2 * ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 2, 28),
            "received_quantity": 40.0,
            "accepted_quantity": 38.0,
            "rejected_quantity": 2.0,
        },
        {
            "goods_receipt_id": "GR-006",
            "receipt_number": "5000001006",
            "po_item_ref": ("PO-003", ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 2, 26),
            "received_quantity": 12.0,
            "accepted_quantity": 12.0,
            "rejected_quantity": 0.0,
        },
        {
            "goods_receipt_id": "GR-007",
            "receipt_number": "5000001007",
            "po_item_ref": ("PO-003", 3 * ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 3, 2),
            "received_quantity": 120.0,
            "accepted_quantity": 120.0,
            "rejected_quantity": 0.0,
        },
        {
            "goods_receipt_id": "GR-008",
            "receipt_number": "5000001008",
            "po_item_ref": ("PO-004", ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 3, 5),
            "received_quantity": 650.0,
            "accepted_quantity": 650.0,
            "rejected_quantity": 0.0,
        },
        {
            "goods_receipt_id": "GR-009",
            "receipt_number": "5000001009",
            "po_item_ref": ("PO-004", 3 * ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 3, 6),
            "received_quantity": 300.0,
            "accepted_quantity": 300.0,
            "rejected_quantity": 0.0,
        },
        {
            "goods_receipt_id": "GR-010",
            "receipt_number": "5000001010",
            "po_item_ref": ("PO-006", ITEM_NUMBER_STEP),
            "receipt_date": date(2026, 3, 9),
            "received_quantity": 1.0,
            "accepted_quantity": 1.0,
            "rejected_quantity": 0.0,
        },
    ]

    goods_receipts = []
    for spec in receipt_specs:
        po_item_ref = spec["po_item_ref"]
        po_item = po_items_by_reference.get(po_item_ref)
        if po_item is None:
            raise ValueError(
                f"Goods receipt {spec['goods_receipt_id']} references missing "
                f"PO item {po_item_ref}"
            )

        po_id = str(po_item["po_id"])
        purchase_order = purchase_orders_by_id.get(po_id)
        if purchase_order is None:
            raise ValueError(
                f"Goods receipt {spec['goods_receipt_id']} references missing "
                f"PO header {po_id}"
            )

        po_lifecycle_status = str(purchase_order["po_lifecycle_status"])
        po_item_lifecycle_status = str(po_item["po_item_lifecycle_status"])
        if po_lifecycle_status in {"blocked", "cancelled", "closed"}:
            raise ValueError(
                f"Goods receipt {spec['goods_receipt_id']} cannot reference "
                f"PO {po_id} with lifecycle status {po_lifecycle_status}"
            )
        if po_lifecycle_status != "active":
            raise ValueError(
                f"Goods receipt {spec['goods_receipt_id']} has unsupported "
                f"PO lifecycle status {po_lifecycle_status}"
            )
        if po_item_lifecycle_status in {"cancelled", "closed"}:
            raise ValueError(
                f"Goods receipt {spec['goods_receipt_id']} cannot reference "
                f"PO item {po_item_ref} with lifecycle status "
                f"{po_item_lifecycle_status}"
            )
        if po_item_lifecycle_status != "active":
            raise ValueError(
                f"Goods receipt {spec['goods_receipt_id']} has unsupported "
                f"PO item lifecycle status {po_item_lifecycle_status}"
            )

        goods_receipts.append(
            {
                "goods_receipt_id": spec["goods_receipt_id"],
                "po_item_id": po_item["po_item_id"],
                "receipt_number": spec["receipt_number"],
                "receipt_date": iso_date(spec["receipt_date"]),
                "received_quantity": spec["received_quantity"],
                "accepted_quantity": spec["accepted_quantity"],
                "rejected_quantity": spec["rejected_quantity"],
                "receipt_status": "posted",
            }
        )

    return goods_receipts


def generate_sap_activate_project_tasks() -> list[dict[str, object]]:
    task_specs = [
        (
            "TASK-001",
            "discover",
            "Procurement",
            "Procurement baseline assessment",
            "Procurement Lead",
            "2026-01-06",
            "2026-01-17",
            "2026-01-16",
            "completed",
            1.2,
            100,
            1,
        ),
        (
            "TASK-002",
            "discover",
            "Reporting",
            "KPI and stakeholder alignment",
            "Reporting Lead",
            "2026-01-13",
            "2026-01-24",
            "2026-01-24",
            "completed",
            0.8,
            100,
            0,
        ),
        (
            "TASK-003",
            "prepare",
            "Data Migration",
            "Data migration strategy and ownership",
            "Data Migration Lead",
            "2026-01-27",
            "2026-02-07",
            "2026-02-07",
            "completed",
            1.3,
            100,
            1,
        ),
        (
            "TASK-004",
            "prepare",
            "Procurement",
            "Procurement project plan and resourcing",
            "Solution Architect",
            "2026-02-03",
            "2026-02-14",
            "2026-02-14",
            "completed",
            0.9,
            100,
            0,
        ),
        (
            "TASK-005",
            "explore",
            "Procurement",
            "Purchase-to-pay fit-gap workshops",
            "Solution Architect",
            "2026-02-17",
            "2026-03-07",
            "2026-03-08",
            "completed",
            1.4,
            100,
            1,
        ),
        (
            "TASK-006",
            "explore",
            "Reporting",
            "Reporting requirements and KPI definitions",
            "Reporting Lead",
            "2026-02-24",
            "2026-03-14",
            "2026-03-14",
            "completed",
            1.0,
            100,
            0,
        ),
        (
            "TASK-007",
            "realize",
            "Data Migration",
            "Vendor and material master data build",
            "Data Migration Lead",
            "2026-03-17",
            "2026-04-18",
            None,
            "in progress",
            1.5,
            78,
            1,
        ),
        (
            "TASK-008",
            "realize",
            "Reporting",
            "Procurement analytics prototype validation",
            "Reporting Lead",
            "2026-04-01",
            "2026-04-25",
            None,
            "delayed",
            0.9,
            62,
            0,
        ),
        (
            "TASK-009",
            "deploy",
            "Testing",
            "User acceptance testing for procurement",
            "Test Manager",
            "2026-04-28",
            "2026-05-16",
            None,
            "in progress",
            1.4,
            45,
            1,
        ),
        (
            "TASK-010",
            "deploy",
            "Training",
            "Key user training and job aids",
            "Training Lead",
            "2026-05-05",
            "2026-05-23",
            None,
            "blocked",
            1.1,
            25,
            1,
        ),
        (
            "TASK-011",
            "run",
            "Cutover",
            "Cutover readiness checkpoint",
            "Cutover Manager",
            "2026-05-26",
            "2026-06-06",
            None,
            "delayed",
            1.5,
            35,
            1,
        ),
        (
            "TASK-012",
            "run",
            "Reporting",
            "Hypercare reporting backlog setup",
            "Reporting Lead",
            "2026-06-09",
            "2026-06-27",
            None,
            "not started",
            0.7,
            0,
            0,
        ),
    ]

    return [
        {
            "task_id": task_id,
            "activate_phase": activate_phase,
            "workstream": workstream,
            "task_name": task_name,
            "task_owner": task_owner,
            "planned_start_date": planned_start_date,
            "planned_finish_date": planned_finish_date,
            "actual_finish_date": actual_finish_date,
            "task_status": task_status,
            "readiness_weight": readiness_weight,
            "completion_percent": completion_percent,
            "critical_flag": critical_flag,
        }
        for (
            task_id,
            activate_phase,
            workstream,
            task_name,
            task_owner,
            planned_start_date,
            planned_finish_date,
            actual_finish_date,
            task_status,
            readiness_weight,
            completion_percent,
            critical_flag,
        ) in task_specs
    ]


def generate_dataset(seed: int) -> dict[str, list[dict[str, object]]]:
    rng, fake = create_generators(seed)
    vendors = generate_vendors(rng)
    plants = generate_plants()
    purchasing_groups = generate_purchasing_groups(fake)
    material_groups = generate_material_groups()
    materials = generate_materials()
    purchase_requisitions, purchase_requisition_items = (
        generate_purchase_requisitions_and_items(rng, materials)
    )
    purchase_orders, purchase_order_items = generate_purchase_orders_and_items(
        rng, vendors, materials, purchase_requisitions, purchase_requisition_items
    )
    goods_receipts = generate_goods_receipts(purchase_orders, purchase_order_items)
    return {
        "vendors": vendors,
        "plants": plants,
        "purchasing_groups": purchasing_groups,
        "material_groups": material_groups,
        "materials": materials,
        "purchase_requisitions": purchase_requisitions,
        "purchase_requisition_items": purchase_requisition_items,
        "purchase_orders": purchase_orders,
        "purchase_order_items": purchase_order_items,
        "goods_receipts": goods_receipts,
        "sap_activate_project_tasks": generate_sap_activate_project_tasks(),
    }


def apply_schema(connection: sqlite3.Connection, schema_path: Path) -> None:
    schema_sql = schema_path.read_text(encoding="utf-8")
    connection.executescript(schema_sql)
    connection.execute("PRAGMA foreign_keys = ON")


def insert_rows(
    connection: sqlite3.Connection, table_name: str, rows: list[dict[str, object]]
) -> None:
    if not rows:
        return

    columns = tuple(rows[0].keys())
    placeholders = ", ".join(f":{column}" for column in columns)
    column_list = ", ".join(columns)
    sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
    connection.executemany(sql, rows)


def insert_dataset(
    connection: sqlite3.Connection, dataset: dict[str, list[dict[str, object]]]
) -> None:
    insertion_order = [
        "vendors",
        "plants",
        "purchasing_groups",
        "material_groups",
        "materials",
        "purchase_requisitions",
        "purchase_requisition_items",
        "purchase_orders",
        "purchase_order_items",
        "goods_receipts",
        "sap_activate_project_tasks",
    ]
    for table_name in insertion_order:
        insert_rows(connection, table_name, dataset[table_name])


def raise_if_rows(rows: list[tuple[object, ...]], message: str) -> None:
    if rows:
        raise RuntimeError(f"{message}: {rows}")


def validate_integrity_checks(connection: sqlite3.Connection) -> None:
    integrity_result = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity_result is None or integrity_result[0] != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity_result}")

    foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_violations:
        raise RuntimeError(f"SQLite foreign key check failed: {foreign_key_violations}")


def validate_expected_counts(connection: sqlite3.Connection) -> dict[str, int]:
    counts = {
        table_name: connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]
        for table_name in EXPECTED_COUNTS
    }
    mismatches = {
        table_name: (EXPECTED_COUNTS[table_name], actual_count)
        for table_name, actual_count in counts.items()
        if actual_count != EXPECTED_COUNTS[table_name]
    }
    if mismatches:
        raise RuntimeError(f"Unexpected table counts: {mismatches}")
    return counts


def validate_item_number_sequences(
    connection: sqlite3.Connection,
    table_name: str,
    parent_column: str,
    item_number_column: str,
) -> None:
    duplicate_rows = connection.execute(
        f"""
        SELECT {parent_column}, {item_number_column}, COUNT(*) AS duplicate_count
        FROM {table_name}
        GROUP BY {parent_column}, {item_number_column}
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    raise_if_rows(duplicate_rows, f"Duplicate item numbers in {table_name}")

    sequence_rows = connection.execute(
        f"""
        SELECT {parent_column}, GROUP_CONCAT({item_number_column}, ',') AS item_numbers
        FROM (
            SELECT {parent_column}, {item_number_column}
            FROM {table_name}
            ORDER BY {parent_column}, {item_number_column}
        )
        GROUP BY {parent_column}
        """
    ).fetchall()
    violations = []
    for parent_id, item_numbers in sequence_rows:
        actual_numbers = [int(value) for value in str(item_numbers).split(",")]
        expected_numbers = list(
            range(
                ITEM_NUMBER_STEP,
                ITEM_NUMBER_STEP * (len(actual_numbers) + 1),
                ITEM_NUMBER_STEP,
            )
        )
        if actual_numbers != expected_numbers:
            violations.append((parent_id, actual_numbers, expected_numbers))
    if violations:
        raise RuntimeError(f"Invalid item number sequence in {table_name}: {violations}")


def validate_pr_date_chronology(connection: sqlite3.Connection) -> None:
    approval_rows = connection.execute(
        """
        SELECT pr_id, pr_status, requisition_date, approval_date
        FROM purchase_requisitions
        WHERE (
            pr_status IN ('approved', 'converted')
            AND approval_date IS NULL
        )
        OR (
            pr_status IN ('draft', 'submitted', 'rejected', 'cancelled')
            AND approval_date IS NOT NULL
        )
        OR (
            approval_date IS NOT NULL
            AND approval_date < requisition_date
        )
        """
    ).fetchall()
    raise_if_rows(approval_rows, "Invalid purchase requisition approval dates")

    delivery_rows = connection.execute(
        """
        SELECT pri.pr_item_id, pr.requisition_date, pri.requested_delivery_date
        FROM purchase_requisition_items AS pri
        JOIN purchase_requisitions AS pr
            ON pr.pr_id = pri.pr_id
        WHERE pri.requested_delivery_date <= pr.requisition_date
        """
    ).fetchall()
    raise_if_rows(delivery_rows, "Invalid purchase requisition delivery dates")


def validate_po_date_chronology(connection: sqlite3.Connection) -> None:
    approval_rows = connection.execute(
        """
        SELECT po_id, po_created_date, po_approval_date
        FROM purchase_orders
        WHERE po_approval_date IS NOT NULL
            AND po_approval_date < po_created_date
        """
    ).fetchall()
    raise_if_rows(approval_rows, "Invalid purchase order approval dates")

    delivery_rows = connection.execute(
        """
        SELECT poi.po_item_id, po.po_created_date, po.po_approval_date,
               poi.planned_delivery_date
        FROM purchase_order_items AS poi
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        WHERE poi.planned_delivery_date <= po.po_created_date
            OR (
                po.po_approval_date IS NOT NULL
                AND poi.planned_delivery_date < po.po_approval_date
            )
        """
    ).fetchall()
    raise_if_rows(delivery_rows, "Invalid purchase order planned delivery dates")


def validate_po_net_values(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT po_item_id, ordered_quantity, unit_price, net_value,
               ROUND(ordered_quantity * unit_price, 2) AS expected_net_value
        FROM purchase_order_items
        WHERE ABS(net_value - ROUND(ordered_quantity * unit_price, 2)) > 0.01
        """
    ).fetchall()
    raise_if_rows(rows, "Invalid purchase order item net values")


def validate_price_variation_ranges(connection: sqlite3.Connection) -> None:
    pr_rows = connection.execute(
        """
        SELECT pri.pr_item_id,
               pri.requested_unit_price,
               m.standard_price
        FROM purchase_requisition_items AS pri
        JOIN materials AS m
            ON m.material_id = pri.material_id
        """
    ).fetchall()
    pr_violations = []
    for pr_item_id, requested_unit_price, standard_price in pr_rows:
        low, high = price_bounds(standard_price, PR_PRICE_VARIATION_RANGE)
        if not (low <= float(requested_unit_price) <= high):
            pr_violations.append((pr_item_id, requested_unit_price, low, high))
    if pr_violations:
        raise RuntimeError(
            "Purchase requisition prices outside configured variation range: "
            f"{pr_violations}"
        )

    po_rows = connection.execute(
        """
        SELECT poi.po_item_id,
               poi.unit_price,
               m.standard_price,
               po.vendor_id
        FROM purchase_order_items AS poi
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        JOIN materials AS m
            ON m.material_id = poi.material_id
        """
    ).fetchall()
    po_violations = []
    for po_item_id, unit_price, standard_price, vendor_id in po_rows:
        vendor_factor = PO_VENDOR_PRICE_FACTORS[str(vendor_id)]
        low, high = price_bounds(
            standard_price, PO_PRICE_VARIATION_RANGE, vendor_factor
        )
        if not (low <= float(unit_price) <= high):
            po_violations.append((po_item_id, unit_price, low, high))
    if po_violations:
        raise RuntimeError(
            "Purchase order prices outside configured variation range: "
            f"{po_violations}"
        )


def validate_linked_po_plants(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT poi.po_item_id, po.plant_id AS po_plant_id, pr.plant_id AS pr_plant_id
        FROM purchase_order_items AS poi
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        JOIN purchase_requisition_items AS pri
            ON pri.pr_item_id = poi.pr_item_id
        JOIN purchase_requisitions AS pr
            ON pr.pr_id = pri.pr_id
        WHERE po.plant_id <> pr.plant_id
        """
    ).fetchall()
    raise_if_rows(rows, "PR-linked purchase order plant mismatch")


def validate_pr_items_use_active_materials(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT pri.pr_item_id, pri.material_id, m.material_status
        FROM purchase_requisition_items AS pri
        JOIN materials AS m
            ON m.material_id = pri.material_id
        WHERE m.material_status <> 'active'
        """
    ).fetchall()
    raise_if_rows(rows, "Purchase requisition items reference inactive materials")


def validate_linked_po_materials(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT poi.po_item_id,
               poi.material_id AS po_material_id,
               pri.material_id AS pr_material_id
        FROM purchase_order_items AS poi
        JOIN purchase_requisition_items AS pri
            ON pri.pr_item_id = poi.pr_item_id
        WHERE poi.pr_item_id IS NOT NULL
            AND poi.material_id <> pri.material_id
        """
    ).fetchall()
    raise_if_rows(rows, "PR-linked purchase order material mismatch")


def validate_direct_po_count(connection: sqlite3.Connection) -> None:
    direct_count = connection.execute(
        "SELECT COUNT(*) FROM purchase_order_items WHERE pr_item_id IS NULL"
    ).fetchone()[0]
    if direct_count != EXPECTED_DIRECT_PO_ITEMS:
        raise RuntimeError(
            f"Expected {EXPECTED_DIRECT_PO_ITEMS} direct PO items, found {direct_count}"
        )


def validate_pr_conversion_quantities(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT pri.pr_item_id,
               pri.pr_item_status,
               pri.requested_quantity,
               COUNT(poi.po_item_id) AS linked_po_item_count,
               COALESCE(
                   SUM(
                       CASE
                           WHEN poi.po_item_lifecycle_status <> 'cancelled'
                           THEN poi.ordered_quantity
                           ELSE 0
                       END
                   ),
                   0
               ) AS active_ordered_quantity
        FROM purchase_requisition_items AS pri
        LEFT JOIN purchase_order_items AS poi
            ON poi.pr_item_id = pri.pr_item_id
        GROUP BY pri.pr_item_id, pri.pr_item_status, pri.requested_quantity
        """
    ).fetchall()

    partial_rows = [row for row in rows if row[1] == "partially converted"]
    if len(partial_rows) != 1:
        raise RuntimeError(
            f"Expected exactly one partially converted PR item, found {partial_rows}"
        )

    partial_row = partial_rows[0]
    _, _, requested_quantity, linked_count, active_quantity = partial_row
    if linked_count != EXPECTED_PARTIAL_PO_LINKS:
        raise RuntimeError(
            "Expected partially converted PR item to be referenced by "
            f"{EXPECTED_PARTIAL_PO_LINKS} PO items: "
            f"{partial_row}"
        )
    if not (0 < float(active_quantity) < float(requested_quantity)):
        raise RuntimeError(
            "Partially converted PR item quantity must be greater than zero and "
            f"less than requested quantity: {partial_row}"
        )

    converted_violations = []
    nonconverted_violations = []
    for pr_item_id, item_status, requested, _linked_count, active in rows:
        active_quantity = float(active)
        requested_quantity = float(requested)
        if item_status == "converted":
            if abs(active_quantity - requested_quantity) > 0.01:
                converted_violations.append(
                    (pr_item_id, requested_quantity, active_quantity)
                )
        elif item_status in {"approved", "open", "rejected", "cancelled"}:
            if active_quantity > 0.01:
                nonconverted_violations.append((pr_item_id, item_status, active_quantity))

    if converted_violations:
        raise RuntimeError(
            "Converted PR item quantities do not equal active PO quantities: "
            f"{converted_violations}"
        )
    if nonconverted_violations:
        raise RuntimeError(
            "Non-converted PR items have active linked PO quantities: "
            f"{nonconverted_violations}"
        )


def validate_vendor_material_compatibility(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT po.po_id,
               poi.po_item_id,
               v.vendor_category,
               m.material_group_id,
               m.material_type
        FROM purchase_order_items AS poi
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        JOIN vendors AS v
            ON v.vendor_id = po.vendor_id
        JOIN materials AS m
            ON m.material_id = poi.material_id
        """
    ).fetchall()
    violations = []
    for po_id, po_item_id, vendor_category, material_group_id, material_type in rows:
        if not material_matches_vendor_category(
            str(vendor_category), str(material_group_id), str(material_type)
        ):
            violations.append(
                (po_id, po_item_id, vendor_category, material_group_id, material_type)
            )
    if violations:
        raise RuntimeError(f"Vendor/material compatibility violations: {violations}")


def validate_currency_by_vendor_country(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT po.po_id, v.country, po.document_currency
        FROM purchase_orders AS po
        JOIN vendors AS v
            ON v.vendor_id = po.vendor_id
        """
    ).fetchall()
    violations = []
    for po_id, country, document_currency in rows:
        expected_currency = VENDOR_COUNTRY_CURRENCY.get(str(country))
        if expected_currency != document_currency:
            violations.append((po_id, country, document_currency, expected_currency))
    if violations:
        raise RuntimeError(f"Vendor country currency violations: {violations}")


def validate_purchasing_group_fit(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT po.po_id,
               poi.po_item_id,
               po.purchasing_group_id,
               m.material_type
        FROM purchase_order_items AS poi
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        JOIN materials AS m
            ON m.material_id = poi.material_id
        """
    ).fetchall()
    violations = []
    for po_id, po_item_id, purchasing_group_id, material_type in rows:
        expected_group_id = PURCHASING_GROUP_BY_MATERIAL_TYPE[str(material_type)]
        if purchasing_group_id != expected_group_id:
            violations.append(
                (po_id, po_item_id, purchasing_group_id, material_type, expected_group_id)
            )
    if violations:
        raise RuntimeError(f"Purchasing group/material fit violations: {violations}")


def validate_downstream_tables_empty(connection: sqlite3.Connection) -> None:
    counts = {
        table_name: connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]
        for table_name in DOWNSTREAM_EMPTY_TABLES
    }
    nonempty_tables = {
        table_name: row_count
        for table_name, row_count in counts.items()
        if row_count != 0
    }
    if nonempty_tables:
        raise RuntimeError(f"Future downstream tables are not empty: {nonempty_tables}")


def validate_pr_header_item_statuses(connection: sqlite3.Connection) -> None:
    allowed_item_statuses_by_header = {
        "converted": {"converted"},
        "approved": {"approved", "partially converted"},
        "submitted": {"open"},
        "draft": {"open"},
        "rejected": {"rejected"},
        "cancelled": {"cancelled"},
    }
    rows = connection.execute(
        """
        SELECT pr.pr_id,
               pr.pr_status,
               pri.pr_item_status,
               COUNT(pri.pr_item_id) OVER (PARTITION BY pr.pr_id) AS item_count
        FROM purchase_requisitions AS pr
        LEFT JOIN purchase_requisition_items AS pri
            ON pri.pr_id = pr.pr_id
        """
    ).fetchall()
    violations = []
    zero_item_headers = []
    for pr_id, pr_status, pr_item_status, item_count in rows:
        if item_count == 0:
            zero_item_headers.append((pr_id, pr_status))
            continue
        allowed_statuses = allowed_item_statuses_by_header[str(pr_status)]
        if pr_item_status not in allowed_statuses:
            violations.append((pr_id, pr_status, pr_item_status))
    if zero_item_headers:
        raise RuntimeError(f"Purchase requisitions with no items: {zero_item_headers}")
    if violations:
        raise RuntimeError(f"PR header/item status consistency violations: {violations}")

    item_count_rows = connection.execute(
        """
        SELECT pr.pr_id, COUNT(pri.pr_item_id) AS item_count
        FROM purchase_requisitions AS pr
        LEFT JOIN purchase_requisition_items AS pri
            ON pri.pr_id = pr.pr_id
        GROUP BY pr.pr_id
        HAVING COUNT(pri.pr_item_id) < 1 OR COUNT(pri.pr_item_id) > 3
        """
    ).fetchall()
    raise_if_rows(item_count_rows, "PR item count outside the 1-to-3 range")


def validate_po_lifecycle_statuses(connection: sqlite3.Connection) -> None:
    header_rows = connection.execute(
        """
        SELECT po_id, po_lifecycle_status
        FROM purchase_orders
        ORDER BY po_id
        """
    ).fetchall()
    actual_header_statuses = {
        str(po_id): str(po_lifecycle_status)
        for po_id, po_lifecycle_status in header_rows
    }
    if actual_header_statuses != EXPECTED_PO_LIFECYCLE_STATUSES:
        raise RuntimeError(
            "Unexpected purchase order lifecycle status map: "
            f"{actual_header_statuses}"
        )

    zero_item_headers = connection.execute(
        """
        SELECT po.po_id, po.po_lifecycle_status
        FROM purchase_orders AS po
        LEFT JOIN purchase_order_items AS poi
            ON poi.po_id = po.po_id
        GROUP BY po.po_id, po.po_lifecycle_status
        HAVING COUNT(poi.po_item_id) = 0
        """
    ).fetchall()
    raise_if_rows(zero_item_headers, "Purchase orders with no items")

    item_rows = connection.execute(
        """
        SELECT po.po_id,
               po.po_lifecycle_status,
               poi.po_item_number,
               poi.po_item_lifecycle_status
        FROM purchase_orders AS po
        JOIN purchase_order_items AS poi
            ON poi.po_id = po.po_id
        ORDER BY po.po_id, poi.po_item_number
        """
    ).fetchall()

    exact_item_status_violations = []
    lifecycle_consistency_violations = []
    for po_id, po_lifecycle_status, po_item_number, po_item_lifecycle_status in item_rows:
        item_reference = (str(po_id), int(po_item_number))
        expected_item_lifecycle_status = (
            "cancelled"
            if item_reference in EXPECTED_CANCELLED_PO_ITEM_REFERENCES
            else "active"
        )
        if po_item_lifecycle_status != expected_item_lifecycle_status:
            exact_item_status_violations.append(
                (
                    po_id,
                    po_item_number,
                    po_item_lifecycle_status,
                    expected_item_lifecycle_status,
                )
            )

        if po_lifecycle_status == "cancelled":
            if po_item_lifecycle_status != "cancelled":
                lifecycle_consistency_violations.append(
                    (po_id, po_lifecycle_status, po_item_number, po_item_lifecycle_status)
                )
        elif po_lifecycle_status in {"active", "blocked"}:
            if po_item_lifecycle_status != "active":
                lifecycle_consistency_violations.append(
                    (po_id, po_lifecycle_status, po_item_number, po_item_lifecycle_status)
                )
        elif po_lifecycle_status == "closed":
            lifecycle_consistency_violations.append(
                (po_id, po_lifecycle_status, po_item_number, po_item_lifecycle_status)
            )

    if exact_item_status_violations:
        raise RuntimeError(
            "Unexpected purchase order item lifecycle statuses: "
            f"{exact_item_status_violations}"
        )
    if lifecycle_consistency_violations:
        raise RuntimeError(
            "PO lifecycle header/item consistency violations: "
            f"{lifecycle_consistency_violations}"
        )


def po_item_reference_set(
    rows: list[tuple[object, ...]],
) -> set[tuple[str, int]]:
    return {(str(po_id), int(po_item_number)) for po_id, po_item_number, *_ in rows}


def validate_goods_receipt_identifiers(connection: sqlite3.Connection) -> None:
    row_count, id_count, receipt_number_count = connection.execute(
        """
        SELECT COUNT(*),
               COUNT(DISTINCT goods_receipt_id),
               COUNT(DISTINCT receipt_number)
        FROM goods_receipts
        """
    ).fetchone()
    if row_count != 10:
        raise RuntimeError(f"Expected 10 goods receipt rows, found {row_count}")
    if id_count != row_count:
        raise RuntimeError("Goods receipt IDs are not unique")
    if receipt_number_count != row_count:
        raise RuntimeError("Goods receipt numbers are not unique")

    actual_ids = {
        str(goods_receipt_id)
        for (goods_receipt_id,) in connection.execute(
            "SELECT goods_receipt_id FROM goods_receipts"
        ).fetchall()
    }
    if actual_ids != EXPECTED_GOODS_RECEIPT_IDS:
        raise RuntimeError(f"Unexpected goods receipt ID set: {actual_ids}")

    actual_receipt_numbers = {
        str(receipt_number)
        for (receipt_number,) in connection.execute(
            "SELECT receipt_number FROM goods_receipts"
        ).fetchall()
    }
    if actual_receipt_numbers != EXPECTED_RECEIPT_NUMBERS:
        raise RuntimeError(
            f"Unexpected goods receipt number set: {actual_receipt_numbers}"
        )

    invalid_reference_rows = connection.execute(
        """
        SELECT gr.goods_receipt_id, gr.po_item_id
        FROM goods_receipts AS gr
        LEFT JOIN purchase_order_items AS poi
            ON poi.po_item_id = gr.po_item_id
        WHERE poi.po_item_id IS NULL
        """
    ).fetchall()
    raise_if_rows(invalid_reference_rows, "Goods receipts with invalid PO item links")


def validate_goods_receipt_quantities(connection: sqlite3.Connection) -> None:
    invalid_quantity_rows = connection.execute(
        f"""
        SELECT goods_receipt_id,
               received_quantity,
               accepted_quantity,
               rejected_quantity,
               receipt_status
        FROM goods_receipts
        WHERE received_quantity <= 0
            OR accepted_quantity < 0
            OR rejected_quantity < 0
            OR ABS(received_quantity - accepted_quantity - rejected_quantity)
                > {FLOAT_TOLERANCE}
            OR receipt_status <> 'posted'
        """
    ).fetchall()
    raise_if_rows(invalid_quantity_rows, "Invalid goods receipt quantity rows")

    totals = connection.execute(
        """
        SELECT COALESCE(SUM(received_quantity), 0),
               COALESCE(SUM(accepted_quantity), 0),
               COALESCE(SUM(rejected_quantity), 0),
               COALESCE(
                   SUM(
                       CASE
                           WHEN receipt_status = 'under review' THEN received_quantity
                           ELSE 0
                       END
                   ),
                   0
               )
        FROM goods_receipts
        """
    ).fetchone()
    expected_totals = (3043.0, 3041.0, 2.0, 0.0)
    if any(
        abs(float(actual) - expected) > FLOAT_TOLERANCE
        for actual, expected in zip(totals, expected_totals)
    ):
        raise RuntimeError(
            "Unexpected goods receipt aggregate quantities: "
            f"actual={totals}, expected={expected_totals}"
        )


def validate_goods_receipt_chronology(connection: sqlite3.Connection) -> None:
    chronology_rows = connection.execute(
        """
        SELECT gr.goods_receipt_id,
               po.po_id,
               gr.receipt_date,
               po.po_created_date,
               po.po_approval_date
        FROM goods_receipts AS gr
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = gr.po_item_id
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        WHERE po.po_approval_date IS NULL
            OR gr.receipt_date < po.po_created_date
            OR gr.receipt_date < po.po_approval_date
        """
    ).fetchall()
    raise_if_rows(chronology_rows, "Goods receipt chronology violations")


def validate_goods_receipt_lifecycle_eligibility(
    connection: sqlite3.Connection,
) -> None:
    ineligible_rows = connection.execute(
        """
        SELECT gr.goods_receipt_id,
               po.po_id,
               po.po_lifecycle_status,
               poi.po_item_number,
               poi.po_item_lifecycle_status
        FROM goods_receipts AS gr
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = gr.po_item_id
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        WHERE po.po_lifecycle_status IN ('blocked', 'cancelled', 'closed')
            OR poi.po_item_lifecycle_status IN ('cancelled', 'closed')
        """
    ).fetchall()
    raise_if_rows(ineligible_rows, "Goods receipt lifecycle eligibility violations")


def validate_goods_receipt_scenarios(connection: sqlite3.Connection) -> None:
    expected_rows = [
        ("GR-001", "5000001001", "PO-001", 10, "2026-02-21", 1000.0, 1000.0, 0.0, "posted"),
        ("GR-002", "5000001002", "PO-001", 20, "2026-02-24", 200.0, 200.0, 0.0, "posted"),
        ("GR-003", "5000001003", "PO-001", 20, "2026-02-27", 220.0, 220.0, 0.0, "posted"),
        ("GR-004", "5000001004", "PO-002", 10, "2026-02-26", 500.0, 500.0, 0.0, "posted"),
        ("GR-005", "5000001005", "PO-002", 20, "2026-02-28", 40.0, 38.0, 2.0, "posted"),
        ("GR-006", "5000001006", "PO-003", 10, "2026-02-26", 12.0, 12.0, 0.0, "posted"),
        ("GR-007", "5000001007", "PO-003", 30, "2026-03-02", 120.0, 120.0, 0.0, "posted"),
        ("GR-008", "5000001008", "PO-004", 10, "2026-03-05", 650.0, 650.0, 0.0, "posted"),
        ("GR-009", "5000001009", "PO-004", 30, "2026-03-06", 300.0, 300.0, 0.0, "posted"),
        ("GR-010", "5000001010", "PO-006", 10, "2026-03-09", 1.0, 1.0, 0.0, "posted"),
    ]
    actual_rows = [
        (
            str(goods_receipt_id),
            str(receipt_number),
            str(po_id),
            int(po_item_number),
            str(receipt_date),
            float(received_quantity),
            float(accepted_quantity),
            float(rejected_quantity),
            str(receipt_status),
        )
        for (
            goods_receipt_id,
            receipt_number,
            po_id,
            po_item_number,
            receipt_date,
            received_quantity,
            accepted_quantity,
            rejected_quantity,
            receipt_status,
        ) in connection.execute(
            """
            SELECT gr.goods_receipt_id,
                   gr.receipt_number,
                   po.po_id,
                   poi.po_item_number,
                   gr.receipt_date,
                   gr.received_quantity,
                   gr.accepted_quantity,
                   gr.rejected_quantity,
                   gr.receipt_status
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    ]
    if actual_rows != expected_rows:
        raise RuntimeError(
            "Unexpected goods receipt scenario rows: "
            f"actual={actual_rows}, expected={expected_rows}"
        )

    receipt_references = po_item_reference_set(
        connection.execute(
            """
            SELECT DISTINCT po.po_id, poi.po_item_number
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            """
        ).fetchall()
    )
    forbidden_references = (
        EXPECTED_ACTIVE_NO_RECEIPT_REFERENCES
        | EXPECTED_BLOCKED_NO_RECEIPT_REFERENCES
        | EXPECTED_CANCELLED_NO_RECEIPT_REFERENCES
    )
    unexpected_receipt_references = receipt_references & forbidden_references
    if unexpected_receipt_references:
        raise RuntimeError(
            "No-receipt scenario references have receipts: "
            f"{unexpected_receipt_references}"
        )

    active_no_receipt_rows = po_item_reference_set(
        connection.execute(
            """
            SELECT po.po_id, poi.po_item_number
            FROM purchase_order_items AS poi
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            LEFT JOIN goods_receipts AS gr
                ON gr.po_item_id = poi.po_item_id
            WHERE po.po_lifecycle_status = 'active'
                AND poi.po_item_lifecycle_status = 'active'
            GROUP BY po.po_id, poi.po_item_number
            HAVING COUNT(gr.goods_receipt_id) = 0
            """
        ).fetchall()
    )
    if active_no_receipt_rows != EXPECTED_ACTIVE_NO_RECEIPT_REFERENCES:
        raise RuntimeError(
            "Unexpected active open items with no receipt: "
            f"{active_no_receipt_rows}"
        )

    rejected_rows = [
        (str(goods_receipt_id), str(po_id), int(po_item_number), float(rejected_quantity))
        for goods_receipt_id, po_id, po_item_number, rejected_quantity in connection.execute(
            """
            SELECT gr.goods_receipt_id,
                   po.po_id,
                   poi.po_item_number,
                   gr.rejected_quantity
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            WHERE gr.rejected_quantity > 0
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    ]
    if rejected_rows != [("GR-005", "PO-002", 20, 2.0)]:
        raise RuntimeError(f"Unexpected rejected-quantity scenarios: {rejected_rows}")

    direct_receipt_rows = [
        (str(goods_receipt_id), str(po_id), int(po_item_number))
        for goods_receipt_id, po_id, po_item_number in connection.execute(
            """
            SELECT gr.goods_receipt_id, po.po_id, poi.po_item_number
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            WHERE poi.pr_item_id IS NULL
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    ]
    if direct_receipt_rows != [("GR-010", "PO-006", 10)]:
        raise RuntimeError(f"Unexpected direct-PO receipt rows: {direct_receipt_rows}")

    multiple_receipt_rows = [
        (str(po_id), int(po_item_number), int(receipt_count))
        for po_id, po_item_number, receipt_count in connection.execute(
            """
            SELECT po.po_id,
                   poi.po_item_number,
                   COUNT(gr.goods_receipt_id) AS receipt_count
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            GROUP BY po.po_id, poi.po_item_number
            HAVING COUNT(gr.goods_receipt_id) > 1
            ORDER BY po.po_id, poi.po_item_number
            """
        ).fetchall()
    ]
    if multiple_receipt_rows != [("PO-001", 20, 2)]:
        raise RuntimeError(
            f"Unexpected multiple goods receipt scenarios: {multiple_receipt_rows}"
        )


def validate_cumulative_receipt_quantities(connection: sqlite3.Connection) -> None:
    overaccepted_rows = connection.execute(
        f"""
        SELECT po.po_id,
               poi.po_item_number,
               poi.ordered_quantity,
               COALESCE(SUM(gr.accepted_quantity), 0) AS total_accepted_quantity
        FROM purchase_order_items AS poi
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        LEFT JOIN goods_receipts AS gr
            ON gr.po_item_id = poi.po_item_id
            AND gr.receipt_status = 'posted'
        GROUP BY po.po_id, poi.po_item_number, poi.ordered_quantity
        HAVING total_accepted_quantity - poi.ordered_quantity > {FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(overaccepted_rows, "PO items with accepted overdelivery")

    negative_open_rows = connection.execute(
        f"""
        SELECT po_id, po_item_number, ordered_quantity, total_accepted_quantity, open_quantity
        FROM vw_po_item_fulfillment
        WHERE open_quantity < -{FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(negative_open_rows, "PO items with negative open quantity")

    rejected_completion_rows = connection.execute(
        """
        SELECT po_id,
               po_item_number,
               ordered_quantity,
               total_received_quantity,
               total_accepted_quantity,
               total_rejected_quantity,
               open_quantity,
               fulfillment_status
        FROM vw_po_item_fulfillment
        WHERE total_rejected_quantity > 0
            AND fulfillment_status = 'complete'
        """
    ).fetchall()
    raise_if_rows(
        rejected_completion_rows,
        "Rejected quantities incorrectly contribute to fulfillment",
    )


def fulfillment_references(
    connection: sqlite3.Connection, status: str | None
) -> set[tuple[str, int]]:
    if status is None:
        rows = connection.execute(
            """
            SELECT po_id, po_item_number
            FROM vw_po_item_fulfillment
            WHERE fulfillment_status IS NULL
            """
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT po_id, po_item_number
            FROM vw_po_item_fulfillment
            WHERE fulfillment_status = ?
            """,
            (status,),
        ).fetchall()
    return po_item_reference_set(rows)


def validate_fulfillment_views(connection: sqlite3.Connection) -> None:
    po_item_count = connection.execute(
        "SELECT COUNT(*) FROM purchase_order_items"
    ).fetchone()[0]
    po_item_view_count = connection.execute(
        "SELECT COUNT(*) FROM vw_po_item_fulfillment"
    ).fetchone()[0]
    if po_item_view_count != po_item_count or po_item_view_count != 15:
        raise RuntimeError(
            "Unexpected vw_po_item_fulfillment row count: "
            f"view={po_item_view_count}, purchase_order_items={po_item_count}"
        )

    item_status_counts = {
        fulfillment_status: row_count
        for fulfillment_status, row_count in connection.execute(
            """
            SELECT fulfillment_status, COUNT(*)
            FROM vw_po_item_fulfillment
            GROUP BY fulfillment_status
            """
        ).fetchall()
    }
    expected_item_status_counts = {None: 3, "complete": 7, "partial": 2, "open": 3}
    if item_status_counts != expected_item_status_counts:
        raise RuntimeError(
            "Unexpected vw_po_item_fulfillment status counts: "
            f"{item_status_counts}"
        )

    for status, expected_references in EXPECTED_ITEM_FULFILLMENT_REFERENCES.items():
        actual_references = fulfillment_references(connection, status)
        if actual_references != expected_references:
            raise RuntimeError(
                f"Unexpected item fulfillment references for {status}: "
                f"{actual_references}"
            )

    po_002_item_20 = connection.execute(
        """
        SELECT ordered_quantity,
               total_received_quantity,
               total_accepted_quantity,
               total_rejected_quantity,
               total_under_review_quantity,
               open_quantity,
               fulfillment_status
        FROM vw_po_item_fulfillment
        WHERE po_id = 'PO-002'
            AND po_item_number = 20
        """
    ).fetchone()
    expected_po_002_item_20 = (40.0, 40.0, 38.0, 2.0, 0.0, 2.0, "partial")
    if po_002_item_20 != expected_po_002_item_20:
        raise RuntimeError(
            "Unexpected PO-002 item 20 fulfillment row: "
            f"{po_002_item_20}"
        )

    po_001_item_20 = connection.execute(
        """
        SELECT ordered_quantity,
               total_received_quantity,
               total_accepted_quantity,
               total_rejected_quantity,
               open_quantity,
               fulfillment_status
        FROM vw_po_item_fulfillment
        WHERE po_id = 'PO-001'
            AND po_item_number = 20
        """
    ).fetchone()
    expected_po_001_item_20 = (420.0, 420.0, 420.0, 0.0, 0.0, "complete")
    if po_001_item_20 != expected_po_001_item_20:
        raise RuntimeError(
            "Unexpected PO-001 item 20 fulfillment row: "
            f"{po_001_item_20}"
        )

    po_count = connection.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
    po_view_count = connection.execute(
        "SELECT COUNT(*) FROM vw_po_fulfillment"
    ).fetchone()[0]
    if po_view_count != po_count or po_view_count != 8:
        raise RuntimeError(
            "Unexpected vw_po_fulfillment row count: "
            f"view={po_view_count}, purchase_orders={po_count}"
        )

    po_statuses = {
        str(po_id): fulfillment_status
        for po_id, fulfillment_status in connection.execute(
            """
            SELECT po_id, fulfillment_status
            FROM vw_po_fulfillment
            ORDER BY po_id
            """
        ).fetchall()
    }
    if po_statuses != EXPECTED_PO_FULFILLMENT_STATUSES:
        raise RuntimeError(f"Unexpected PO fulfillment statuses: {po_statuses}")

    po_status_counts = {
        fulfillment_status: row_count
        for fulfillment_status, row_count in connection.execute(
            """
            SELECT fulfillment_status, COUNT(*)
            FROM vw_po_fulfillment
            GROUP BY fulfillment_status
            """
        ).fetchall()
    }
    expected_po_status_counts = {None: 2, "complete": 2, "partial": 3, "open": 1}
    if po_status_counts != expected_po_status_counts:
        raise RuntimeError(
            "Unexpected vw_po_fulfillment status counts: "
            f"{po_status_counts}"
        )


def delivery_performance_references(
    connection: sqlite3.Connection, status: str | None
) -> set[tuple[str, int]]:
    if status is None:
        rows = connection.execute(
            """
            SELECT po_id, po_item_number
            FROM vw_po_item_delivery_performance
            WHERE delivery_performance_status IS NULL
            """
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT po_id, po_item_number
            FROM vw_po_item_delivery_performance
            WHERE delivery_performance_status = ?
            """,
            (status,),
        ).fetchall()
    return po_item_reference_set(rows)


def validate_delivery_performance(connection: sqlite3.Connection) -> None:
    po_item_count = connection.execute(
        "SELECT COUNT(*) FROM purchase_order_items"
    ).fetchone()[0]
    delivery_view_count = connection.execute(
        "SELECT COUNT(*) FROM vw_po_item_delivery_performance"
    ).fetchone()[0]
    if delivery_view_count != po_item_count or delivery_view_count != 15:
        raise RuntimeError(
            "Unexpected vw_po_item_delivery_performance row count: "
            f"view={delivery_view_count}, purchase_order_items={po_item_count}"
        )

    expected_delivery_references = {
        "on time in full": EXPECTED_OTIF_REFERENCES,
        "late in full": {
            ("PO-001", 2 * ITEM_NUMBER_STEP),
            ("PO-003", 3 * ITEM_NUMBER_STEP),
            ("PO-004", ITEM_NUMBER_STEP),
            ("PO-006", ITEM_NUMBER_STEP),
        },
        "not fulfilled": {
            ("PO-002", ITEM_NUMBER_STEP),
            ("PO-002", 2 * ITEM_NUMBER_STEP),
            ("PO-003", 2 * ITEM_NUMBER_STEP),
            ("PO-004", 2 * ITEM_NUMBER_STEP),
            ("PO-007", ITEM_NUMBER_STEP),
        },
        None: EXPECTED_BLOCKED_NO_RECEIPT_REFERENCES
        | EXPECTED_CANCELLED_NO_RECEIPT_REFERENCES,
    }
    for status, expected_references in expected_delivery_references.items():
        actual_references = delivery_performance_references(connection, status)
        if actual_references != expected_references:
            raise RuntimeError(
                f"Unexpected delivery performance references for {status}: "
                f"{actual_references}"
            )

    eligible_rows = [
        (str(po_id), int(po_item_number), delivery_performance_status)
        for po_id, po_item_number, delivery_performance_status in connection.execute(
            """
            SELECT po_id, po_item_number, delivery_performance_status
            FROM vw_po_item_delivery_performance
            WHERE po_lifecycle_status = 'active'
                AND po_item_lifecycle_status = 'active'
                AND planned_delivery_date <= ?
            ORDER BY po_id, po_item_number
            """,
            (REPORTING_DATE,),
        ).fetchall()
    ]
    otif_references = {
        (po_id, po_item_number)
        for po_id, po_item_number, status in eligible_rows
        if status == "on time in full"
    }
    denominator = len(eligible_rows)
    numerator = len(otif_references)
    otif_rate = numerator / denominator * 100 if denominator else 0.0
    if denominator != 12:
        raise RuntimeError(f"Unexpected OTIF denominator: {denominator}")
    if numerator != 3 or otif_references != EXPECTED_OTIF_REFERENCES:
        raise RuntimeError(
            "Unexpected OTIF numerator references: "
            f"count={numerator}, references={otif_references}"
        )
    if abs(otif_rate - 25.0) > FLOAT_TOLERANCE:
        raise RuntimeError(f"Unexpected OTIF rate: {otif_rate}")

    event_rows = [
        (str(goods_receipt_id), bool(on_time_flag))
        for goods_receipt_id, on_time_flag in connection.execute(
            """
            SELECT gr.goods_receipt_id,
                   gr.receipt_date <= poi.planned_delivery_date AS on_time_flag
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    ]
    on_time_events = {
        goods_receipt_id for goods_receipt_id, on_time_flag in event_rows if on_time_flag
    }
    late_events = {
        goods_receipt_id for goods_receipt_id, on_time_flag in event_rows if not on_time_flag
    }
    event_rate = len(on_time_events) / len(event_rows) * 100 if event_rows else 0.0
    if on_time_events != EXPECTED_ON_TIME_RECEIPT_IDS:
        raise RuntimeError(f"Unexpected on-time receipt events: {on_time_events}")
    if late_events != set(EXPECTED_LATE_RECEIPT_DELAYS):
        raise RuntimeError(f"Unexpected late receipt events: {late_events}")
    if len(event_rows) != 10 or len(on_time_events) != 5 or len(late_events) != 5:
        raise RuntimeError(
            "Unexpected receipt-event timing counts: "
            f"total={len(event_rows)}, on_time={len(on_time_events)}, "
            f"late={len(late_events)}"
        )
    if abs(event_rate - 50.0) > FLOAT_TOLERANCE:
        raise RuntimeError(f"Unexpected receipt-event on-time rate: {event_rate}")

    late_delay_rows = {
        str(goods_receipt_id): int(delay_days)
        for goods_receipt_id, delay_days in connection.execute(
            """
            SELECT gr.goods_receipt_id,
                   CAST(
                       julianday(gr.receipt_date) - julianday(poi.planned_delivery_date)
                       AS INTEGER
                   ) AS delay_days
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            WHERE gr.receipt_date > poi.planned_delivery_date
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    }
    if late_delay_rows != EXPECTED_LATE_RECEIPT_DELAYS:
        raise RuntimeError(f"Unexpected late receipt delays: {late_delay_rows}")

    average_delay = connection.execute(
        """
        SELECT AVG(julianday(gr.receipt_date) - julianday(poi.planned_delivery_date))
        FROM goods_receipts AS gr
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = gr.po_item_id
        WHERE gr.receipt_date > poi.planned_delivery_date
        """
    ).fetchone()[0]
    if abs(float(average_delay) - 2.2) > FLOAT_TOLERANCE:
        raise RuntimeError(f"Unexpected average late receipt delay: {average_delay}")


def validate_phase3_rules(connection: sqlite3.Connection) -> None:
    validate_goods_receipt_identifiers(connection)
    validate_goods_receipt_quantities(connection)
    validate_goods_receipt_chronology(connection)
    validate_goods_receipt_lifecycle_eligibility(connection)
    validate_goods_receipt_scenarios(connection)
    validate_cumulative_receipt_quantities(connection)
    validate_fulfillment_views(connection)
    validate_delivery_performance(connection)


def validate_pr_linked_po_creation_dates(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT poi.po_item_id,
               po.po_created_date,
               pr.pr_id,
               pr.approval_date
        FROM purchase_order_items AS poi
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        JOIN purchase_requisition_items AS pri
            ON pri.pr_item_id = poi.pr_item_id
        JOIN purchase_requisitions AS pr
            ON pr.pr_id = pri.pr_id
        WHERE poi.pr_item_id IS NOT NULL
            AND (
                pr.approval_date IS NULL
                OR po.po_created_date < pr.approval_date
            )
        """
    ).fetchall()
    raise_if_rows(rows, "PR-linked PO creation date is before PR approval")


def validate_phase2_rules(connection: sqlite3.Connection) -> None:
    validate_item_number_sequences(
        connection,
        "purchase_requisition_items",
        "pr_id",
        "pr_item_number",
    )
    validate_item_number_sequences(
        connection,
        "purchase_order_items",
        "po_id",
        "po_item_number",
    )
    validate_pr_date_chronology(connection)
    validate_po_date_chronology(connection)
    validate_po_net_values(connection)
    validate_price_variation_ranges(connection)
    validate_linked_po_plants(connection)
    validate_pr_items_use_active_materials(connection)
    validate_linked_po_materials(connection)
    validate_direct_po_count(connection)
    validate_pr_conversion_quantities(connection)
    validate_vendor_material_compatibility(connection)
    validate_currency_by_vendor_country(connection)
    validate_purchasing_group_fit(connection)
    validate_downstream_tables_empty(connection)
    validate_pr_header_item_statuses(connection)
    validate_po_lifecycle_statuses(connection)
    validate_pr_linked_po_creation_dates(connection)


def validate_database(connection: sqlite3.Connection) -> dict[str, int]:
    validate_integrity_checks(connection)
    counts = validate_expected_counts(connection)
    validate_phase2_rules(connection)
    validate_phase3_rules(connection)
    return counts


def build_database(db_path: Path, seed: int) -> dict[str, int]:
    schema_path = repository_root() / "database" / "schema.sql"
    dataset = generate_dataset(seed)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        apply_schema(connection, schema_path)
        connection.execute("BEGIN")
        insert_dataset(connection, dataset)
        counts = validate_database(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return counts


def print_success_summary(db_path: Path, seed: int, counts: dict[str, int]) -> None:
    print(f"Generated database: {db_path}")
    print(f"Seed: {seed}")
    print("Row counts:")
    for table_name in EXPECTED_COUNTS:
        print(f"  {table_name}: {counts[table_name]}")


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    prepare_database_path(db_path, args.reset)
    counts = build_database(db_path, args.seed)
    print_success_summary(db_path, args.seed, counts)


if __name__ == "__main__":
    main()
