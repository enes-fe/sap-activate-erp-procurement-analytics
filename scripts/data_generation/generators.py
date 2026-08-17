"""Generate deterministic master, project, and procurement data."""

from __future__ import annotations

import random
from datetime import date, timedelta

from faker import Faker

from .config import (
    FLOAT_TOLERANCE,
    ITEM_NUMBER_STEP,
    PO_NUMBER_PREFIX,
    PO_PRICE_VARIATION_RANGE,
    PO_VENDOR_PRICE_FACTORS,
    PR_PRICE_VARIATION_RANGE,
    VENDOR_COUNTRY_CURRENCY,
)


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


def generate_invoices_and_items(
    purchase_orders: list[dict[str, object]],
    purchase_order_items: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    purchase_orders_by_id = {
        str(purchase_order["po_id"]): purchase_order
        for purchase_order in purchase_orders
    }
    purchase_order_items_by_id = {
        str(po_item["po_item_id"]): po_item
        for po_item in purchase_order_items
    }
    invoice_specs = [
        {
            "invoice_id": "INV-001",
            "vendor_id": "VEN-001",
            "invoice_number": "ANM-2026-001",
            "invoice_date": date(2026, 2, 28),
            "invoice_received_date": date(2026, 3, 1),
            "posting_date": date(2026, 3, 2),
            "invoice_currency": "TRY",
            "invoice_status": "posted",
            "blocked_flag": 0,
            "block_reason": None,
            "items": [
                {
                    "invoice_item_id": "INVI-001",
                    "invoice_item_number": ITEM_NUMBER_STEP,
                    "po_item_id": "POI-001",
                    "invoiced_quantity": 1000.0,
                },
                {
                    "invoice_item_id": "INVI-002",
                    "invoice_item_number": 2 * ITEM_NUMBER_STEP,
                    "po_item_id": "POI-002",
                    "invoiced_quantity": 420.0,
                },
            ],
        },
        {
            "invoice_id": "INV-002",
            "vendor_id": "VEN-004",
            "invoice_number": "BTB-2026-001",
            "invoice_date": date(2026, 2, 27),
            "invoice_received_date": date(2026, 2, 28),
            "posting_date": date(2026, 3, 1),
            "invoice_currency": "TRY",
            "invoice_status": "posted",
            "blocked_flag": 1,
            "block_reason": "price mismatch",
            "items": [
                {
                    "invoice_item_id": "INVI-003",
                    "invoice_item_number": ITEM_NUMBER_STEP,
                    "po_item_id": "POI-005",
                    "invoiced_quantity": 12.0,
                    "invoiced_unit_price": 44.55,
                },
            ],
        },
        {
            "invoice_id": "INV-003",
            "vendor_id": "VEN-003",
            "invoice_number": "EPK-2026-001",
            "invoice_date": date(2026, 3, 1),
            "invoice_received_date": date(2026, 3, 2),
            "posting_date": date(2026, 3, 3),
            "invoice_currency": "TRY",
            "invoice_status": "posted",
            "blocked_flag": 1,
            "block_reason": "quantity exceeds eligible posted accepted quantity",
            "items": [
                {
                    "invoice_item_id": "INVI-004",
                    "invoice_item_number": ITEM_NUMBER_STEP,
                    "po_item_id": "POI-004",
                    "invoiced_quantity": 40.0,
                },
            ],
        },
        {
            "invoice_id": "INV-004",
            "vendor_id": "VEN-002",
            "invoice_number": "RSH-2026-001",
            "invoice_date": date(2026, 3, 8),
            "invoice_received_date": date(2026, 3, 9),
            "posting_date": date(2026, 3, 9),
            "invoice_currency": "EUR",
            "invoice_status": "posted",
            "blocked_flag": 1,
            "block_reason": "missing eligible posted goods receipt",
            "items": [
                {
                    "invoice_item_id": "INVI-005",
                    "invoice_item_number": ITEM_NUMBER_STEP,
                    "po_item_id": "POI-014",
                    "invoiced_quantity": 150.0,
                },
            ],
        },
    ]

    invoices = []
    invoice_items = []
    for spec in invoice_specs:
        generated_items = []
        for item_spec in spec["items"]:
            po_item_id = str(item_spec["po_item_id"])
            po_item = purchase_order_items_by_id.get(po_item_id)
            if po_item is None:
                raise ValueError(
                    f"Invoice {spec['invoice_id']} references missing "
                    f"PO item {po_item_id}"
                )

            po_id = str(po_item["po_id"])
            purchase_order = purchase_orders_by_id.get(po_id)
            if purchase_order is None:
                raise ValueError(
                    f"Invoice {spec['invoice_id']} references missing PO {po_id}"
                )
            if purchase_order["vendor_id"] != spec["vendor_id"]:
                raise ValueError(
                    f"Invoice {spec['invoice_id']} vendor does not match PO {po_id}"
                )
            if purchase_order["document_currency"] != spec["invoice_currency"]:
                raise ValueError(
                    f"Invoice {spec['invoice_id']} currency does not match PO {po_id}"
                )
            if purchase_order["po_lifecycle_status"] != "active":
                raise ValueError(
                    f"Invoice {spec['invoice_id']} references non-active PO {po_id}"
                )
            if po_item["po_item_lifecycle_status"] != "active":
                raise ValueError(
                    f"Invoice {spec['invoice_id']} references non-active "
                    f"PO item {po_item_id}"
                )

            invoiced_unit_price = float(
                item_spec.get("invoiced_unit_price", po_item["unit_price"])
            )
            if (
                abs(invoiced_unit_price - round(invoiced_unit_price, 2))
                > FLOAT_TOLERANCE
            ):
                raise ValueError(
                    f"Invoice {spec['invoice_id']} unit price must use "
                    "no more than two decimal places"
                )
            invoiced_quantity = float(item_spec["invoiced_quantity"])
            generated_items.append(
                {
                    "invoice_item_id": item_spec["invoice_item_id"],
                    "invoice_id": spec["invoice_id"],
                    "invoice_item_number": item_spec["invoice_item_number"],
                    "po_item_id": po_item_id,
                    "invoiced_quantity": invoiced_quantity,
                    "invoiced_unit_price": invoiced_unit_price,
                    "invoiced_amount": round(
                        invoiced_quantity * invoiced_unit_price, 2
                    ),
                }
            )

        invoice_total_amount = round(
            sum(float(item["invoiced_amount"]) for item in generated_items), 2
        )
        invoices.append(
            {
                "invoice_id": spec["invoice_id"],
                "vendor_id": spec["vendor_id"],
                "invoice_number": spec["invoice_number"],
                "invoice_date": iso_date(spec["invoice_date"]),
                "invoice_received_date": iso_date(spec["invoice_received_date"]),
                "posting_date": iso_date(spec["posting_date"]),
                "invoice_currency": spec["invoice_currency"],
                "invoice_total_amount": invoice_total_amount,
                "invoice_status": spec["invoice_status"],
                "blocked_flag": spec["blocked_flag"],
                "block_reason": spec["block_reason"],
            }
        )
        invoice_items.extend(generated_items)

    return invoices, invoice_items


def generate_payments() -> list[dict[str, object]]:
    return [
        {
            "payment_id": "PAY-001",
            "invoice_id": "INV-001",
            "payment_status_date": "2026-03-05",
            "payment_date": None,
            "payment_amount": 2770.20,
            "payment_method": "bank transfer",
            "payment_status": "failed",
            "clearing_reference": None,
        },
        {
            "payment_id": "PAY-002",
            "invoice_id": "INV-001",
            "payment_status_date": "2026-03-07",
            "payment_date": None,
            "payment_amount": 2770.20,
            "payment_method": "bank transfer",
            "payment_status": "cancelled",
            "clearing_reference": None,
        },
        {
            "payment_id": "PAY-003",
            "invoice_id": "INV-001",
            "payment_status_date": "2026-03-12",
            "payment_date": "2026-03-12",
            "payment_amount": 1000.00,
            "payment_method": "bank transfer",
            "payment_status": "paid",
            "clearing_reference": "CLR-2026-000001",
        },
        {
            "payment_id": "PAY-004",
            "invoice_id": "INV-001",
            "payment_status_date": "2026-03-20",
            "payment_date": "2026-03-20",
            "payment_amount": 1770.20,
            "payment_method": "bank transfer",
            "payment_status": "paid",
            "clearing_reference": "CLR-2026-000002",
        },
        {
            "payment_id": "PAY-005",
            "invoice_id": "INV-002",
            "payment_status_date": "2026-03-04",
            "payment_date": None,
            "payment_amount": 534.60,
            "payment_method": "bank transfer",
            "payment_status": "on hold",
            "clearing_reference": None,
        },
    ]


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


def generate_change_requests() -> list[dict[str, object]]:
    change_request_specs = [
        (
            "CR-001",
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
        (
            "CR-002",
            "TASK-005",
            "explore",
            "Introduce dual approval for high-value purchase orders",
            "process",
            "high",
            "approved",
            "2026-02-25",
            "2026-03-04",
            "Adds a control requirement to future-state procurement design and "
            "leaves configuration and testing work outstanding.",
        ),
        (
            "CR-003",
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
        (
            "CR-004",
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
        (
            "CR-005",
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
        (
            "CR-006",
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
    ]
    return [
        {
            "change_request_id": change_request_id,
            "related_task_id": related_task_id,
            "activate_phase": activate_phase,
            "change_title": change_title,
            "change_type": change_type,
            "priority": priority,
            "status": status,
            "requested_date": requested_date,
            "decision_date": decision_date,
            "business_impact": business_impact,
        }
        for (
            change_request_id,
            related_task_id,
            activate_phase,
            change_title,
            change_type,
            priority,
            status,
            requested_date,
            decision_date,
            business_impact,
        ) in change_request_specs
    ]


def generate_data_quality_issues() -> list[dict[str, object]]:
    issue_specs = [
        (
            "DQ-001",
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
        (
            "DQ-002",
            "A duplicate legacy material record was found for MAT-008 and "
            "consolidated into the retained target record.",
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
        (
            "DQ-003",
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
        (
            "DQ-004",
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
        (
            "DQ-005",
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
        (
            "DQ-006",
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
        (
            "DQ-007",
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
    ]
    return [
        {
            "data_quality_issue_id": data_quality_issue_id,
            "issue_description": issue_description,
            "related_task_id": related_task_id,
            "affected_entity_type": affected_entity_type,
            "affected_entity_id": affected_entity_id,
            "issue_category": issue_category,
            "severity": severity,
            "issue_status": issue_status,
            "detected_date": detected_date,
            "resolved_date": resolved_date,
            "migration_relevant_flag": migration_relevant_flag,
            "readiness_impact_score": readiness_impact_score,
        }
        for (
            data_quality_issue_id,
            issue_description,
            related_task_id,
            affected_entity_type,
            affected_entity_id,
            issue_category,
            severity,
            issue_status,
            detected_date,
            resolved_date,
            migration_relevant_flag,
            readiness_impact_score,
        ) in issue_specs
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
    invoices, invoice_items = generate_invoices_and_items(
        purchase_orders, purchase_order_items
    )
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
        "invoices": invoices,
        "invoice_items": invoice_items,
        "payments": generate_payments(),
        "sap_activate_project_tasks": generate_sap_activate_project_tasks(),
        "change_requests": generate_change_requests(),
        "data_quality_issues": generate_data_quality_issues(),
    }
