"""Validate purchase requisition and purchase order business rules."""

from __future__ import annotations

import sqlite3

from .config import (
    PO_PRICE_VARIATION_RANGE,
    PO_VENDOR_PRICE_FACTORS,
    PR_PRICE_VARIATION_RANGE,
    PURCHASING_GROUP_BY_MATERIAL_TYPE,
    VENDOR_COMPATIBILITY_RULES,
    VENDOR_COUNTRY_CURRENCY,
)
from .expected_results import (
    EXPECTED_CANCELLED_PO_ITEM_REFERENCES,
    EXPECTED_DIRECT_PO_ITEMS,
    EXPECTED_PARTIAL_PO_LINKS,
    EXPECTED_PO_LIFECYCLE_STATUSES,
)
from .validation_common import raise_if_rows, validate_item_number_sequences


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
    validate_pr_header_item_statuses(connection)
    validate_po_lifecycle_statuses(connection)
    validate_pr_linked_po_creation_dates(connection)
